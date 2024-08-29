import contextlib
import datetime
import os
import re
from typing import Optional, List

import inquirer
import paramiko

from AU2 import BASE_WRITE_LOCATION
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE, GenericStateDatabase
from AU2.database.model.database_utils import refresh_databases
from AU2.html_components import HTMLComponent
from AU2.html_components.Checkbox import Checkbox
from AU2.html_components.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.HiddenTextbox import HiddenTextbox
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION

SRCF_WEBSITE = "shell.srcf.net"
SSH_PORT = 22

ASSASSINS_PATH = "/societies/assassins"
AU2_DATA_PATH = ASSASSINS_PATH + "/AU2_files"
DATABASES = AU2_DATA_PATH + "/databases"
LOGS = AU2_DATA_PATH + "/logs"

LOCK_FILE = AU2_DATA_PATH + "/lockfile.txt"

ACCESS_LOG = LOGS + "/access.log"
EDIT_LOG = LOGS + "/edit.log"
PUBLISH_LOG = LOGS + "/publish.log"

REMOTE_WEBPAGES_PATH = ASSASSINS_PATH + "/public_html" + "/testing" #delete "/testing" when in prod"
REMOTE_BACKUP_LOCATION = AU2_DATA_PATH + "/backups"
REMOTE_DATABASE_LOCATION = AU2_DATA_PATH + "/databases"


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
                "SRCFPlugin_publish_pages",
                "SRCF -> Upload database and publish pages",
                self.ask_ignore_lock,
                self.answer_publish_pages
            ),
            Export(
                "SRCFPlugin_request_lock",
                "SRCF -> Request lock",
                self.ask_ignore_lock,
                self.answer_lock
            ),
            Export(
                "SRCFPlugin_remote_backup",
                "SRCF -> Remote backup",
                self.ask_backup,
                self.answer_backup
            ),
            Export(
                "SRCFPlugin_restore_backup",
                "SRCF -> Restore remote backup",
                self.ask_restore_backup,
                self.answer_restore_backup
            ),
            Export(
                "SRCFPlugin_manual_sync",
                "SRCF -> Manual database sync",
                self.ask_ignore_lock,
                self.answer_manual_sync
            )
        ]

        self.html_ids = {
            "ignore_lock": self.identifier + "_ignore_lock",
            "requires_claiming": self.identifier + "_requires_claiming",
            "backup_name": self.identifier + "_backup_name",
            "send_all": self.identifier + "_send_all"
        }

        self.hooks = {
            "email": self.identifier + "_email"
        }

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

    def answer_lock(self, htmlResponse) -> List[HTMLComponent]:
        """
        Claims a lock.
        """
        if not htmlResponse[self.html_ids["ignore_lock"]]:
            return [Label("[SRCF Plugin] Aborted.")]
        with self._get_client() as sftp:
            self._lock(sftp)
        return [Label("[SRCF Plugin] Claimed lock.")]

    def ask_restore_backup(self) -> List[HTMLComponent]:
        with self._get_client() as sftp:
            backups = sftp.listdir(REMOTE_BACKUP_LOCATION)
        return [
            InputWithDropDown(
                identifier=self.html_ids["backup_name"],
                title="Choose backup to restore",
                options=["Exit"] + backups
            )
        ] + self.ask_ignore_lock()

    def answer_restore_backup(self, htmlResponse) -> List[HTMLComponent]:
        chosen_backup = htmlResponse[self.html_ids["backup_name"]]
        if chosen_backup == "Exit":
            return [Label("[SRCF Plugin] Aborted.")]
        if not htmlResponse[self.html_ids["ignore_lock"]]:
            return [Label("[SRCF Plugin] Aborted.")]
        with self._get_client() as sftp:
            if htmlResponse[self.html_ids["requires_claiming"]]:
                print("[SRCF Plugin] Claiming lock...")
                self._lock(sftp)

            remote_backup_folder = REMOTE_BACKUP_LOCATION + "/" + chosen_backup
            for db in sftp.listdir(remote_backup_folder):
                localpath = os.path.join(BASE_WRITE_LOCATION, db)
                remotetarget = REMOTE_DATABASE_LOCATION + "/" + db
                remotepath = remote_backup_folder + "/" + db
                self._log_to(sftp, PUBLISH_LOG, f"Trying to restore {remotepath}...")
                sftp.get(remotepath, localpath)
                sftp.put(localpath, remotetarget)
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
                remotepath = REMOTE_WEBPAGES_PATH + "/" + page
                print(f"[SRCF Plugin] Publishing {page}")
                self._log_to(sftp, PUBLISH_LOG, f"Trying to publish {page}")
                sftp.put(localpath, remotepath)
                self._log_to(sftp, PUBLISH_LOG, f"Published {page}")
                os.remove(localpath)

            for database in self._find_jsons(BASE_WRITE_LOCATION):
                localpath = os.path.join(BASE_WRITE_LOCATION, database)
                remotepath = REMOTE_DATABASE_LOCATION + "/" + database
                self._log_to(sftp, PUBLISH_LOG, f"Trying to save {database}")
                sftp.put(localpath, remotepath)
                self._log_to(sftp, PUBLISH_LOG, f"Saved {database}")

        return [Label("[SRCF Plugin] Successfuly published locally generated pages and uploaded database.")]

    def ask_backup(self) -> List[HTMLComponent]:
        now = datetime.datetime.now()
        folder_name = now.strftime("backup_%d-%m-%Y_%H-%M-%S")
        return [
            DefaultNamedSmallTextbox(
                identifier=self.html_ids["backup_name"],
                title="Remote backup name (you ought to use the name it suggests)",
                default=folder_name
            )
        ]

    def answer_backup(self, htmlResponse) -> List[HTMLComponent]:
        backup_path = REMOTE_BACKUP_LOCATION + "/" + htmlResponse[self.html_ids["backup_name"]]

        with self._get_client() as sftp:
            self._makedirs(sftp, backup_path)
            self._log_to(sftp, EDIT_LOG, f"Creating backup at {backup_path}")
            for f in self._find_jsons(BASE_WRITE_LOCATION):
                localpath = os.path.join(BASE_WRITE_LOCATION, f)
                remotepath = backup_path + "/" + f
                sftp.put(localpath, remotepath)
        return [Label("[SRCF Plugin] Success!")]

    def _read_lock_file(self, sftp: paramiko.SFTPClient) -> (Optional[str], Optional[datetime.datetime]):
        """
        Reads a lock file. Deletes it if it's corrupted.
        """
        try:
            sftp.stat(LOCK_FILE)
        except FileNotFoundError:
            return None, None
        lock: str
        with sftp.file(LOCK_FILE, "r") as F:
            lock = F.read().decode()
            self._log_to(sftp, ACCESS_LOG, "Checked lock.")
        if re.match(r"^[a-zA-Z0-9]+,[0-9]+$", lock):
            username, time_str = lock.split(",")
            unix_ts = datetime.datetime.utcfromtimestamp(int(time_str))
            return username, unix_ts
        print("[SRCF Plugin] Found corrupted lock file. Deleting.")
        sftp.remove(LOCK_FILE)
        return None, None

    def _lock(self, sftp: paramiko.SFTPClient):
        """
        Claims a lock.
        """
        if not self.logged_in:
            return
        unix_ts = datetime.datetime.now().timestamp()
        self._makedirs(sftp, os.path.dirname(LOCK_FILE))
        self._log_to(sftp, ACCESS_LOG, "Claimed lock.")
        with sftp.file(LOCK_FILE, "w+") as F:
            F.write(f"{self.username},{int(unix_ts)}")

    def _makedirs(self, sftp: paramiko.SFTPClient, dir: str):
        """
        SFTP lacks the mkdir -p functionality.
        Recursively creates directories if they do not exist.
        """
        dir_list = dir.split("/")
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

    def _log_to(self, sftp: paramiko.SFTPClient, log_path: str, log_entry: str):
        """
        Writes a log entry to a specified file, creating the specified directories
        if they don't exist.

        It manages the logging time for you (so you don't need to include it in the message).
        """
        if not sftp:
            return
        datetime_str = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")
        log_entry = f"{datetime_str} ({self.username}) {log_entry}\n"
        dir_name = os.path.dirname(log_path)
        self._makedirs(sftp, dir_name)
        with sftp.file(log_path, "a+") as F:
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

        remotepath = REMOTE_DATABASE_LOCATION + "/" + os.path.basename(GENERIC_STATE_DATABASE.WRITE_LOCATION)
        exists = True
        try:
            sftp.stat(remotepath)
        except FileNotFoundError:
            exists = False
        if exists:
            localpath = os.path.join(BASE_WRITE_LOCATION, "TemporaryGenericStateDatabase.json")
            sftp.get(remotepath, localpath)

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
                        remotepath = REMOTE_DATABASE_LOCATION + "/" + database

                        self._log_to(sftp, ACCESS_LOG, f"Trying to read {database}")
                        sftp.get(remotepath, localpath)
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
                        remotepath = REMOTE_DATABASE_LOCATION + "/" + database
                        self._log_to(sftp, PUBLISH_LOG, f"Trying to save {database}")
                        sftp.put(localpath, remotepath)
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
                        remotepath = REMOTE_DATABASE_LOCATION + "/" + database

                        self._log_to(sftp, ACCESS_LOG, f"Trying to read {database}")
                        sftp.get(remotepath, localpath)
                        self._log_to(sftp, ACCESS_LOG, f"Read {database}")
                    print("[SRCF Plugin] Success!")
                elif a["confirm"] == "Upload":
                    for database in self._find_jsons(BASE_WRITE_LOCATION):
                        localpath = os.path.join(BASE_WRITE_LOCATION, database)
                        remotepath = REMOTE_DATABASE_LOCATION + "/" + database
                        self._log_to(sftp, PUBLISH_LOG, f"Trying to save {database}")
                        sftp.put(localpath, remotepath)
                        self._log_to(sftp, PUBLISH_LOG, f"Saved {database}")
                    print("[SRCF Plugin] Success!")

        else:
            self._makedirs(sftp, REMOTE_DATABASE_LOCATION)
            for database in self._find_jsons(BASE_WRITE_LOCATION):
                localpath = os.path.join(BASE_WRITE_LOCATION, database)
                remotepath = REMOTE_DATABASE_LOCATION + "/" + database
                self._log_to(sftp, PUBLISH_LOG, f"Trying to save {database}")
                sftp.put(localpath, remotepath)
                self._log_to(sftp, PUBLISH_LOG, f"Saved {database}")
            print("[SRCF Plugin] No databases were found in the SRCF, so local copies have been uploaded.")
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
