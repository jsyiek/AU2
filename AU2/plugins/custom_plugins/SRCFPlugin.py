import contextlib
import datetime
import os
import re
import time
import pathlib
from typing import Optional, List

import inquirer
import paramiko

from AU2 import BASE_WRITE_LOCATION
from AU2.database.AssassinsDatabase import ASSASSINS_DATABASE
from AU2.database.EventsDatabase import EVENTS_DATABASE
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE, GenericStateDatabase
from AU2.database.model import Assassin
from AU2.database.model.database_utils import refresh_databases
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.EmailSelector import EmailSelector
from AU2.html_components.SimpleComponents.HiddenTextbox import HiddenTextbox
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.SimpleComponents.Label import Label
from AU2.html_components.SimpleComponents.LargeTextEntry import LargeTextEntry
from AU2.html_components.SimpleComponents.Table import Table
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export, HookedExport, ConfigExport
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION
from AU2.plugins.util.DeathManager import DeathManager
from AU2.plugins.util.date_utils import get_now_dt

SRCF_WEBSITE = "shell.srcf.net"
SSH_PORT = 22

# Since these are REMOTE paths we want PurePaths,
# not concrete paths for the machine AU2 is running on!
ASSASSINS_PATH = pathlib.PurePosixPath("/societies/assassins")
AU2_DATA_PATH = ASSASSINS_PATH / "AU2_files"
DATABASES = AU2_DATA_PATH / "databases"  # this appears to be unused?
LOGS = AU2_DATA_PATH / "logs"

LOCK_FILE = AU2_DATA_PATH / "lockfile.txt"

ACCESS_LOG = LOGS / "access.log"
EDIT_LOG = LOGS / "edit.log"
PUBLISH_LOG = LOGS / "publish.log"

REMOTE_WEBPAGES_PATH = ASSASSINS_PATH / "public_html"
REMOTE_BACKUP_LOCATION = AU2_DATA_PATH / "backups"
REMOTE_DATABASE_LOCATION = AU2_DATA_PATH / "databases"

EMAIL_TEMPLATE = """\
MAIL FROM:assassins-umpire@srcf.net
RCPT TO:{EMAIL}
DATA
Content-Type: text/plain; charset=UTF-8
From: assassins-umpire@srcf.net
Subject: {SUBJECT}
{CONTENT}
.
"""

EMAIL_FILE_TEMPLATE = """\
{EMAILS}
QUIT
"""

EMAIL_WHO_ARE_YOU_TEMPLATE = """\
Your details:
                Name: {NAME}
             College: {COLLEGE}
             Address: {ADDRESS}
Room Water Weapons Status: {WATER_STATUS}
               Notes: {NOTES}"""

EMAIL_WRITE_LOCATION = os.path.join(BASE_WRITE_LOCATION, "emails")
REMOTE_EMAIL_WRITE_LOCATION = ASSASSINS_PATH / "emails"

BACKUP_DATE_PATTERN1 = re.compile(r"\d{2}-\d{2}-\d{4}")
BACKUP_DATE_PATTERN2 = re.compile(r"\d{4}-\d{2}-\d{2}")
BACKUP_TIME_PATTERN = re.compile(r"(?<!\d)\d{2}-\d{2}-\d{2}(?!\d)")
BACKUP_DATE_FORMAT1 = "%d-%m-%Y"
BACKUP_DATE_FORMAT2 = "%Y-%m-%d"
BACKUP_TIME_FORMAT = "%H-%M-%S"


def backup_sort_key(backup_name: str) -> (float, str):
    """
    Sorts backups by extracting the date and timestamps from their names,
    and sorts in reverse-chronological order.
    Backups with no date stamps are put at the end of the list.
    """
    backup_date = datetime.date.min
    backup_time = datetime.time.min
    if m := BACKUP_DATE_PATTERN1.search(backup_name):
        backup_date = datetime.datetime.strptime(m[0], BACKUP_DATE_FORMAT1).date()
    elif m := BACKUP_DATE_PATTERN2.search(backup_name):
        backup_date = datetime.datetime.strptime(m[0], BACKUP_DATE_FORMAT2).date()

    if m := BACKUP_TIME_PATTERN.search(backup_name):
        backup_time = datetime.datetime.strptime(m[0], BACKUP_TIME_FORMAT).time()
    return -datetime.datetime.combine(backup_date, backup_time).timestamp(), backup_name


class Email:
    def __init__(self, recipient: Assassin):
        self.recipient = recipient
        self.content_list = []
        self.send = False

    def add_content(self, plugin_name: str, content: str, require_send: bool = False):
        self.content_list.append((plugin_name, content))
        self.send |= require_send

    def get_content_as_str(self, delimiter="\n\n---------------\n\n"):
        self.content_list.sort(key=lambda t: t[0])
        return delimiter.join(t[1] for t in self.content_list)


@registered_plugin
class SRCFPlugin(AbstractPlugin):
    def __init__(self):
        """
        The SRCF Plugin overrides self.exports into a @property to enforce logging in.
        It CANNOT call super init.

        I don't currently see a reason to convert exports generally to a @property.
        If more plugins require special actions, it can be considered.
        """
        self.identifier = "SRCFPlugin"
        self.logged_in = False
        self.username = ""
        self.password = ""
        self.__exports = [
            Export(
                "srcf_plugin_publish_pages",
                "SRCF -> Upload database and PUBLISH PAGES",
                self.ask_ignore_lock,
                self.answer_publish_pages
            ),
            Export(
                "srcf_plugin_request_lock",
                "SRCF -> Request lock",
                self.ask_ignore_lock,
                self.answer_lock
            ),
            Export(
                "srcf_plugin_remote_backup",
                "SRCF -> Remote backup",
                self.ask_backup,
                self.answer_backup
            ),
            Export(
                "srcf_plugin_restore_backup",
                "SRCF -> Restore remote backup",
                self.ask_restore_backup,
                self.answer_restore_backup
            ),
            Export(
                "srcf_plugin_manual_sync",
                "SRCF -> Manual database sync",
                self.ask_ignore_lock,
                self.answer_manual_sync
            ),
            Export(
                identifier="SRCFPlugin_raw_page_edit",
                display_name="SRCF -> Raw page editor",
                ask=self.ask_raw_page_edit,
                answer=self.answer_raw_page_edit,
                options_functions=(self.options_raw_page_edit,),
            )
        ]

        self.hooked_exports = [
            HookedExport(
                plugin_name=self.identifier,
                identifier=self.identifier + "_email",
                display_name="SRCF -> Upload database and SEND EMAILS",
                producer=self.email_producer,
                call_order=HookedExport.LAST
            )
        ]

        self.html_ids = {
            "ignore_lock": self.identifier + "_ignore_lock",
            "requires_claiming": self.identifier + "_requires_claiming",
            "backup_name": self.identifier + "_backup_name",
            "send_all": self.identifier + "_send_all",
            "email_subject": self.identifier + "_email_subject",
            "email_message": self.identifier + "_email_message",
            "email_require_send": self.identifier + "_email_require_send",
            "email_file_name": self.identifier + "_email_file_name",
            "should_enable_raw_editor": self.identifier + "_raw_editor",
            "raw_page_contents": self.identifier + "_raw_page_contents",
            "raw_page_filename": self.identifier + "_raw_page_filename",
            "dry_run": self.identifier + "_dry_run"
        }

        self.hooks = {
            "email": self.identifier + "_email"
        }

        self.config_exports = [
            ConfigExport(
                "Enable Raw Page Editor",
                "Enable Raw Page Editor",
                self.ask_enable_raw_page_editor,
                self.answer_enable_raw_page_editor
            )
        ]

    def ask_enable_raw_page_editor(self):
        def say(x, end="\n"):
            print(x, end=end)
            time.sleep(4)

        try:
            say("I see you want to enable raw page editing. I'm going to make you read some text first.")
            say("This is not a good idea.")
            say("It's perfectly safe from a technical point of view, but...")
            say("it is crucial that umpires know how to access SRCF without AU2.")
            say("At some point AU2 will break.")
            say("At some point a computer won't be able to run it.")
            say("At some point you won't be able to get in touch with me to fix it.")
            say("At some point you won't want to fix it.")
            say("You can log into SRCF using ssh. Get in contact with SRCF if you are really stuck.")
            say("You can get in touch with a CompSci.")
            say("You can use something like WinSCP or FileZilla to do this over SFTP.")
            say("If things haven't changed, you can use the following settings for SFTP:")
            say("username=your CRSid")
            say("password=your SRCF password")
            say("url=shell.srcf.net")
            say("port=22")
            say("Can you give this a try first please?")
            say("Please.")
            say("...")
            say("...")
            say(".....")
            say(".....")
            say("........")
            say("You really want to do this?")
            say("Ah, well, I hope you aren't making a habit out of this in the future.")
            say("I hope you know what you're doing.")
            return [Checkbox(identifier=self.html_ids["should_enable_raw_editor"], title="Enable raw editing?",
                             checked=False)]
        except KeyboardInterrupt:

            print("Thank you for going back. You made the right choice. Raw page editor will be disabled.")
            return [HiddenTextbox(identifier=self.html_ids["should_enable_raw_editor"], default=False)]

    def answer_enable_raw_page_editor(self, htmlResponse):
        result = htmlResponse[self.html_ids["should_enable_raw_editor"]]
        GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {})["raw_page_edit"] = bool(result)
        return [Label(f"[SRCF Plugin] Set raw page edit to: {bool(result)}")]

    @property
    def exports(self):
        """
        The SRCF plugin requires logging in to work.
        I've overriden exports, which is checked on each iteration.
        """
        if self.logged_in:
            return self.__exports
        while True:
            questions = [
                inquirer.Text("username", "(SRCF Plugin) Enter your SRCF username"),
                inquirer.Password("password", "*", message="(SRCF Plugin) Enter your SRCF password")
            ]
            answers = {}
            i = 0
            while i < len(questions):
                a = inquirer.prompt([questions[i]])
                if a is None:
                    if i == 0:
                        return self._failed_login()
                    i -= 1
                    continue
                answers.update(a)
                i += 1

            success = self._execute_login(answers["username"], answers["password"])
            if not success:
                a = inquirer.prompt([inquirer.Confirm("retry", message="(SRCF Plugin) Re-attempt login?")])
                if not a or not a["retry"]:
                    return self._failed_login()
                continue
            break
        return self._successful_login()

    def email_producer(self, _):
        emails = []
        for a in ASSASSINS_DATABASE.assassins.values():
            emails.append(Email(a))
        return emails

    def on_request_hook_respond(self, hook: str) -> List[HTMLComponent]:
        if hook == self.hooks["email"]:

            death_manager = DeathManager()
            for e in EVENTS_DATABASE.events.values():
                death_manager.add_event(e)

            # note: hidden assassins will be excluded
            alive_assassins = ASSASSINS_DATABASE.get_identifiers(include=(
                lambda a: a.is_police or not death_manager.is_dead(a)
            ))
            police_assassins = ASSASSINS_DATABASE.get_identifiers(include=lambda a: a.is_police)

            return [
                Checkbox(
                    identifier=self.html_ids["dry_run"],
                    title="Actually send emails? (Choosing 'No' will not send any emails but print out the contents)",
                    checked=True
                ),
                DefaultNamedSmallTextbox(
                    identifier=self.html_ids["email_subject"],
                    title="[SRCFPlugin] Email Subject",
                    default="[Assassins' Guild] Game Update",
                ),
                Label("[SRCFPlugin] Format specifiers (they will be replaced individually for each assassin)"),
                Label("     [P] - First pseudonym of that assassin"),
                Label("     [N] - Real name of that assassin"),
                LargeTextEntry(
                    identifier=self.html_ids["email_message"],
                    title="[SRCFPlugin] Add additional message?",
                ),
                EmailSelector(
                    identifier=self.html_ids["email_require_send"],
                    # note: hidden assassins will be excluded
                    assassins=ASSASSINS_DATABASE.get_identifiers(),
                    alive_assassins=alive_assassins,
                    police_assassins=police_assassins
                )
            ]
        return []

    def on_hook_respond(self, hook: str, htmlResponse, data) -> List[HTMLComponent]:
        components = []
        if hook == self.hooks["email"]:
            email_list: List[Email] = data
            subject = htmlResponse[self.html_ids["email_subject"]]
            message = htmlResponse[self.html_ids["email_message"]]
            send_emails = htmlResponse[self.html_ids["dry_run"]]
            recipients_list = htmlResponse[self.html_ids["email_require_send"]]
            updates_only = "UPDATES ONLY" in recipients_list

            for email in email_list:
                recipient = email.recipient
                email.add_content(
                    plugin_name="!!SRCFPlugin",
                    content=EMAIL_WHO_ARE_YOU_TEMPLATE.format(
                        NAME=recipient.real_name,
                        COLLEGE=recipient.college,
                        ADDRESS=recipient.address,
                        WATER_STATUS=recipient.water_status,
                        NOTES=recipient.notes
                    )
                )
                email.add_content(
                    plugin_name="!SRCFPlugin",
                    content=message.replace("[P]", email.recipient.pseudonyms[0]).replace("[N]",
                                                                                          email.recipient.real_name),
                    require_send=False
                )

            for e in email_list:
                e.send = (e.send and updates_only) or e.recipient.identifier in recipients_list

            email_list = [e for e in email_list if e.send]

            if not email_list:
                components.append(Label("[SRCFPlugin] No emails need to be sent, aborting."))
                return components
            components.append(Label(f"[SRCFPlugin] Found {len(email_list)} emails to send."))

            email_str_list = [
                EMAIL_TEMPLATE.format(
                    SUBJECT=subject,
                    EMAIL=email.recipient.email,
                    CONTENT=email.get_content_as_str()
                ) for email in email_list
            ]

            email_file_contents = EMAIL_FILE_TEMPLATE.format(
                EMAILS="".join(email_str_list)
            )

            now = get_now_dt()
            email_file_name = f"email.{now.day:02}{now.month:02}{now.year}" \
                              f"_{now.hour:02}_{now.minute:02}_{now.second:02}"

            localpath = os.path.join(EMAIL_WRITE_LOCATION, email_file_name)
            os.makedirs(EMAIL_WRITE_LOCATION, exist_ok=True)
            with open(localpath, "w+", encoding="utf-8", errors="ignore") as F:
                F.write(email_file_contents)

            with self._get_ssh_client() as ssh_client:
                with ssh_client.open_sftp() as sftp:
                    self._log_to(sftp, ACCESS_LOG, "Logging in for email")

                    self._makedirs(sftp, REMOTE_EMAIL_WRITE_LOCATION)

                    remotetarget = REMOTE_EMAIL_WRITE_LOCATION / email_file_name
                    sftp.put(localpath, str(remotetarget))

                    self._log_to(sftp, ACCESS_LOG, "Logging out of email")
                    self._log_to(sftp, PUBLISH_LOG, "Trying to send email...")

                    if send_emails:
                        (stdin, stdout, stderr) = ssh_client.exec_command(f"/usr/sbin/sendmail -bS < {remotetarget}")

                        if stdout:
                            print("stdout:")
                            # TODO: Implement proper print
                            print(stdout)
                        if stderr:
                            print("stderr (useful for debugging):")
                            # TODO: Implement proper print
                            print(stderr)

                        components.append(Label("[SRCFPlugin] Sent emails!"))
                    else:
                        components.append(Table([[email_str] for email_str in email_str_list]))

                    self._log_to(sftp, PUBLISH_LOG, "Tried to send emails.")
                    self._publish_databases(sftp)
                    components.append(Label(f"[SRCFPlugin] Uploaded database."))
                    autobackup_name = self._autobackup(sftp)
                    components.append(Label(f"[SRCFPlugin] Created remote backup {autobackup_name}"))
        return components

    def ask_ignore_lock(self) -> List[HTMLComponent]:
        with self._get_client() as sftp:
            (locked_user, locked_datetime) = self._read_lock_file(sftp)
            if locked_user and locked_user != self.username:
                human_date = locked_datetime.strftime('%Y-%m-%d %H:%M:%S')
                return [
                    Checkbox(self.html_ids["ignore_lock"],
                             title=f"{locked_user} requested a lock at {human_date} (UTC). Proceed anyway?",
                             checked=False),
                    HiddenTextbox(
                        self.html_ids["requires_claiming"],
                        default=True
                    )
                ]
            return [
                HiddenTextbox(
                    self.html_ids["ignore_lock"],
                    default=True
                ),
                HiddenTextbox(
                    self.html_ids["requires_claiming"],
                    default=False
                )
            ]

    def options_raw_page_edit(self):
        results = []
        if GENERIC_STATE_DATABASE.arb_state.setdefault(self.identifier, {}).get("raw_page_edit", False):
            with self._get_client() as sftp:
                for f in sftp.listdir("/public/societies/assassins/public_html"):
                    if "." in f:
                        results.append(f)
        return sorted(results)

    def ask_raw_page_edit(self, filename: str):
        contents = ""
        with self._get_client() as sftp:
            with sftp.file(f"/public/societies/assassins/public_html/{filename}", "r", encoding="utf-8",
                           errors="ignore") as F:
                contents = F.read()

        return [
            HiddenTextbox(
                identifier=self.html_ids["raw_page_filename"],
                default=filename
            ),
            LargeTextEntry(
                identifier=self.html_ids["raw_page_contents"],
                title="Raw content of page",
                default=contents.decode()
            )
        ]

    def answer_raw_page_edit(self, htmlResponse):
        filename = htmlResponse[self.html_ids["raw_page_filename"]]
        filepath = f"/public/societies/assassins/public_html/{filename}"
        contents = htmlResponse[self.html_ids["raw_page_contents"]]
        with self._get_client() as sftp:
            with sftp.file(filepath, "w+") as F:
                F.write(contents)
        return [Label(f"[SRCFPlugin] Wrote to: {filepath}")]

    def answer_lock(self, htmlResponse) -> List[HTMLComponent]:
        """
        Claims a lock.
        """
        if not htmlResponse[self.html_ids["ignore_lock"]]:
            return [Label("[SRCFPlugin] Aborted.")]
        with self._get_client() as sftp:
            self._lock(sftp)
        return [Label("[SRCFPlugin] Claimed lock.")]

    def ask_restore_backup(self) -> List[HTMLComponent]:
        with self._get_client() as sftp:
            backups = sorted(sftp.listdir(str(REMOTE_BACKUP_LOCATION)), key=backup_sort_key)
        return [
                   InputWithDropDown(
                       identifier=self.html_ids["backup_name"],
                       title="Choose backup to restore",
                       options=["*EXIT*"] + backups
                   )
               ] + self.ask_ignore_lock()

    def answer_restore_backup(self, htmlResponse) -> List[HTMLComponent]:
        chosen_backup = htmlResponse[self.html_ids["backup_name"]]
        if chosen_backup == "*EXIT*":
            return [Label("[SRCF Plugin] Aborted.")]
        if not htmlResponse[self.html_ids["ignore_lock"]]:
            return [Label("[SRCF Plugin] Aborted.")]
        with self._get_client() as sftp:
            if htmlResponse[self.html_ids["requires_claiming"]]:
                print("[SRCF Plugin] Claiming lock...")
                self._lock(sftp)

            remote_backup_folder = REMOTE_BACKUP_LOCATION / chosen_backup
            for db in sftp.listdir(str(remote_backup_folder)):
                localpath = os.path.join(BASE_WRITE_LOCATION, db)
                remotetarget = REMOTE_DATABASE_LOCATION / db
                remotepath = remote_backup_folder / db
                self._log_to(sftp, PUBLISH_LOG, f"Trying to restore {remotepath}...")
                sftp.get(str(remotepath), localpath)
                sftp.put(localpath, str(remotetarget))
                self._log_to(sftp, PUBLISH_LOG, f"Restored {remotepath}.")

            refresh_databases()
            return [Label(f"[SRCF Plugin] Restored {chosen_backup}")]

    def answer_manual_sync(self, htmlResponse) -> List[HTMLComponent]:
        """
        Manually call the _sync method that is called upon login.
        """
        if not htmlResponse[self.html_ids["ignore_lock"]]:
            return [Label("[SRCF Plugin] Aborted.")]
        with self._get_client() as sftp:
            if htmlResponse[self.html_ids["requires_claiming"]]:
                print("[SRCF Plugin] Claiming lock...")
                self._lock(sftp)
            self._sync(sftp)
        return []

    def answer_publish_pages(self, htmlResponse) -> List[HTMLComponent]:
        """
        Publishes all pages in `WEBSITE_WRITE_LOCATION`, wiping each page it uploads.

        If there's a lock, and we want to proceed, I have it override the claim on the lock.
        The idea is that if two people are simultaneously playing with the SRCF,
        they both need to find that out very quickly.
        """
        if not htmlResponse[self.html_ids["ignore_lock"]]:
            return [Label("[SRCF Plugin] Aborted.")]
        with self._get_client() as sftp:
            if htmlResponse[self.html_ids["requires_claiming"]]:
                print("[SRCF Plugin] Claiming lock...")
                self._lock(sftp)
            self._makedirs(sftp, REMOTE_WEBPAGES_PATH)
            for page in os.listdir(WEBPAGE_WRITE_LOCATION):
                localpath = os.path.join(WEBPAGE_WRITE_LOCATION, page)
                remotepath = REMOTE_WEBPAGES_PATH / page
                print(f"[SRCF Plugin] Publishing {page}")
                self._log_to(sftp, PUBLISH_LOG, f"Trying to publish {page}")
                sftp.put(localpath, str(remotepath))
                self._log_to(sftp, PUBLISH_LOG, f"Published {page}")
                os.remove(localpath)

            self._publish_databases(sftp)
            automatic_backup = self._autobackup(sftp)

        return [
            Label("[SRCFPlugin] Successfuly published locally generated pages and uploaded database."),
            Label(f"[SRCFPlugin] Automatically created backup {automatic_backup}")
        ]

    def _backup_to_remote(self, sftp, backup_name: str):
        backup_path = REMOTE_BACKUP_LOCATION / backup_name
        self._makedirs(sftp, backup_path)
        self._log_to(sftp, EDIT_LOG, f"Creating backup at {backup_path}")
        for f in self._find_jsons(BASE_WRITE_LOCATION):
            localpath = os.path.join(BASE_WRITE_LOCATION, f)
            remotepath = backup_path / f
            sftp.put(localpath, str(remotepath))

    def _autobackup(self, sftp) -> str:
        """
        Creates a REMOTE backup of the (local) database with an auto-generated name.
        The name is of the format "backup_<date>_<time>_<username>",
        where <date> is in YYYY-MM-DD format,
        <time> is in HH-MM-SS format
        and <username> is the username that was used to log into SRCF.
        The reason for this format is so that the backups will be ordered correctly when sorting by name.

        Returns:
            Name of backup created
        """
        now = get_now_dt()
        folder_name = f"backup_{now:%Y-%m-%d_%H-%M-%S}_{self.username}_auto"
        self._backup_to_remote(sftp, folder_name)
        return folder_name

    def ask_backup(self) -> List[HTMLComponent]:
        now = get_now_dt()
        folder_name = f"backup_{now:%Y-%m-%d_%H-%M-%S}_{self.username}"
        return [
            DefaultNamedSmallTextbox(
                identifier=self.html_ids["backup_name"],
                title="Remote backup name (you ought to use the name it suggests)",
                default=folder_name
            )
        ]

    def answer_backup(self, htmlResponse) -> List[HTMLComponent]:
        backup_name = htmlResponse[self.html_ids["backup_name"]]
        with self._get_client() as sftp:
            self._backup_to_remote(sftp, backup_name)
        return [Label("[SRCF Plugin] Success!")]

    def _read_lock_file(self, sftp: paramiko.SFTPClient) -> (Optional[str], Optional[datetime.datetime]):
        """
        Reads a lock file. Deletes it if it's corrupted.
        """
        try:
            sftp.stat(str(LOCK_FILE))
        except FileNotFoundError:
            return None, None
        lock: str
        with sftp.file(str(LOCK_FILE), "r") as F:
            lock = F.read().decode()
            self._log_to(sftp, ACCESS_LOG, "Checked lock.")
        if re.match(r"^[a-zA-Z0-9]+,[0-9]+$", lock):
            username, time_str = lock.split(",")
            unix_ts = datetime.datetime.utcfromtimestamp(int(time_str))
            return username, unix_ts
        print("[SRCF Plugin] Found corrupted lock file. Deleting.")
        sftp.remove(str(LOCK_FILE))
        return None, None

    def _publish_databases(self, sftp: paramiko.SFTPClient):
        """
        Publishes all databases
        """
        for database in self._find_jsons(BASE_WRITE_LOCATION):
            localpath = os.path.join(BASE_WRITE_LOCATION, database)
            remotepath = REMOTE_DATABASE_LOCATION / database
            self._log_to(sftp, PUBLISH_LOG, f"Trying to save {database}")
            sftp.put(localpath, str(remotepath))
            self._log_to(sftp, PUBLISH_LOG, f"Saved {database}")

    def _lock(self, sftp: paramiko.SFTPClient):
        """
        Claims a lock.
        """
        if not self.logged_in:
            return
        unix_ts = get_now_dt().timestamp()
        self._makedirs(sftp, os.path.dirname(LOCK_FILE))
        self._log_to(sftp, ACCESS_LOG, "Claimed lock.")
        with sftp.file(str(LOCK_FILE), "w+") as F:
            F.write(f"{self.username},{int(unix_ts)}")

    def _makedirs(self, sftp: paramiko.SFTPClient, dir_path: pathlib.PurePosixPath):
        """
        SFTP lacks the mkdir -p functionality.
        Recursively creates directories if they do not exist.
        """
        dir_list = str(dir_path).split("/")
        if not dir_list[0]:
            dir_list[1] = "/" + dir_list[1]
            del dir_list[0]
        current_dir = ""
        for d in dir_list:
            current_dir = f"{current_dir}/{d}" if current_dir else d
            try:
                sftp.stat(current_dir)
            except FileNotFoundError:
                sftp.mkdir(current_dir)

    def _log_to(self, sftp: paramiko.SFTPClient, log_path: pathlib.PurePosixPath, log_entry: str):
        """
        Writes a log entry to a specified file, creating the specified directories
        if they don't exist.

        It manages the logging time for you (so you don't need to include it in the message).
        """
        if not sftp:
            return
        datetime_str = get_now_dt().strftime("[%Y-%m-%d %H:%M:%S.%f]")
        log_entry = f"{datetime_str} ({self.username}) {log_entry}\n"
        dir_name = os.path.dirname(log_path)
        self._makedirs(sftp, dir_name)
        with sftp.file(str(log_path), "a+") as F:
            F.write(log_entry)

    def _execute_login(self, username: str, password: str):
        """
        Performs an authentication check to see if the supplied credentials can log into SRCF.
        It offers to update local copy of DB with remote DB if they are out of sync.
        Closes the connection after.
        """
        self.username = username
        self.password = password
        try:
            with self._get_client() as sftp:
                self._sync(sftp)

        except paramiko.ssh_exception.AuthenticationException:
            self.username = ""
            self.password = ""
            return False
        return True

    def _find_jsons(self, path):
        for db in os.listdir(path):
            if db.endswith(".json"):
                yield db

    def _sync(self, sftp: paramiko.SFTPClient):

        remotepath = REMOTE_DATABASE_LOCATION / os.path.basename(GENERIC_STATE_DATABASE.WRITE_LOCATION)
        exists = True
        try:
            sftp.stat(str(remotepath))
        except FileNotFoundError:
            exists = False
        if exists:
            localpath = os.path.join(BASE_WRITE_LOCATION, "TemporaryGenericStateDatabase.json")
            sftp.get(str(remotepath), localpath)

            with open(localpath, "r") as F:
                dump = F.read()

            remote_gsd = GenericStateDatabase.from_json(dump)
            os.remove(localpath)
            if remote_gsd.uniqueId > GENERIC_STATE_DATABASE.uniqueId:
                print("[SRCF Plugin] Your databases appear to be BEHIND the copies on SRCF. "
                      "Do you want to bring the LOCAL copies up to date?")
                a = inquirer.prompt([inquirer.Confirm(
                    "confirm",
                    default=True)
                ])
                if a is not None and a["confirm"]:
                    for database in self._find_jsons(BASE_WRITE_LOCATION):
                        localpath = os.path.join(BASE_WRITE_LOCATION, database)
                        remotepath = REMOTE_DATABASE_LOCATION / database

                        self._log_to(sftp, ACCESS_LOG, f"Trying to read {database}")
                        sftp.get(str(remotepath), localpath)
                        self._log_to(sftp, ACCESS_LOG, f"Read {database}")
                    print("[SRCF Plugin] Success!")
                else:
                    print("[SRCF Plugin] Did not update LOCAL copies.")

            elif remote_gsd.uniqueId < GENERIC_STATE_DATABASE.uniqueId:
                print("[SRCF Plugin] Your databases appear to be AHEAD of the copies on SRCF. "
                      "Do you want to bring the REMOTE copies up to date?")
                a = inquirer.prompt([inquirer.Confirm(
                    "confirm",
                    default=True)
                ])
                if a is not None and a["confirm"]:
                    for database in self._find_jsons(BASE_WRITE_LOCATION):
                        localpath = os.path.join(BASE_WRITE_LOCATION, database)
                        remotepath = REMOTE_DATABASE_LOCATION / database
                        self._log_to(sftp, PUBLISH_LOG, f"Trying to save {database}")
                        sftp.put(localpath, str(remotepath))
                        self._log_to(sftp, PUBLISH_LOG, f"Saved {database}")
                    print("[SRCF Plugin] Success!")
                else:
                    print("[SRCF Plugin] Did not update REMOTE copies.")

            else:
                print("[SRCF Plugin] Your local database APPEARS up to date. This may be the case if only small "
                      "changes were made.")
                print("[SRCF Plugin] Do you want to download remote copies, upload local copies, or do nothing?")
                a = inquirer.prompt([inquirer.List(
                    "confirm",
                    message="Choices",
                    choices=["Download", "Upload", "Nothing"],
                    default="Nothing")
                ])
                if a is None or a["confirm"] == "Nothing":
                    print("[SRCF Plugin] No changes made.")
                elif a["confirm"] == "Download":
                    for database in self._find_jsons(BASE_WRITE_LOCATION):
                        localpath = os.path.join(BASE_WRITE_LOCATION, database)
                        remotepath = REMOTE_DATABASE_LOCATION / database

                        self._log_to(sftp, ACCESS_LOG, f"Trying to read {database}")
                        sftp.get(str(remotepath), localpath)
                        self._log_to(sftp, ACCESS_LOG, f"Read {database}")
                    print("[SRCF Plugin] Success!")
                elif a["confirm"] == "Upload":
                    for database in self._find_jsons(BASE_WRITE_LOCATION):
                        localpath = os.path.join(BASE_WRITE_LOCATION, database)
                        remotepath = REMOTE_DATABASE_LOCATION / database
                        self._log_to(sftp, PUBLISH_LOG, f"Trying to save {database}")
                        sftp.put(localpath, str(remotepath))
                        self._log_to(sftp, PUBLISH_LOG, f"Saved {database}")
                    print("[SRCF Plugin] Success!")

        else:
            self._makedirs(sftp, REMOTE_DATABASE_LOCATION)
            for database in self._find_jsons(BASE_WRITE_LOCATION):
                localpath = os.path.join(BASE_WRITE_LOCATION, database)
                remotepath = REMOTE_DATABASE_LOCATION / database
                self._log_to(sftp, PUBLISH_LOG, f"Trying to save {database}")
                sftp.put(localpath, str(remotepath))
                self._log_to(sftp, PUBLISH_LOG, f"Saved {database}")
            print("[SRCF Plugin] No databases were found in the SRCF, so local copies have been uploaded.")

        refresh_databases()
        return []

    @contextlib.contextmanager
    def _get_client(self) -> paramiko.SFTPClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=SRCF_WEBSITE,
                port=SSH_PORT,
                username=self.username,
                password=self.password
            )
            with client.open_sftp() as sftp:
                self._log_to(sftp, ACCESS_LOG, "Logged in.")
                yield sftp
                self._log_to(sftp, ACCESS_LOG, "Logging out.")
        finally:
            client.close()

    @contextlib.contextmanager
    def _get_ssh_client(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=SRCF_WEBSITE,
                port=SSH_PORT,
                username=self.username,
                password=self.password
            )
            yield client
        finally:
            client.close()

    def _failed_login(self):
        """
        Disables SRCF plugin and prints an error message.
        """
        print("Login cancelled. Disabling SRCFPlugin.")
        GENERIC_STATE_DATABASE.plugin_map["SRCFPlugin"] = False
        return []

    def _successful_login(self):
        """
        Marks the user as logged in and returns exports.
        """
        self.logged_in = True
        return self.__exports
