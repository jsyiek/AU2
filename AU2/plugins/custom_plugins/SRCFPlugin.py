import contextlib
import datetime
import os
import re
import shutil
from typing import Optional, List

import inquirer
import paramiko

from AU2 import BASE_WRITE_LOCATION
from AU2.database.GenericStateDatabase import GENERIC_STATE_DATABASE
from AU2.html_components import HTMLComponent
from AU2.html_components.Checkbox import Checkbox
from AU2.html_components.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.HiddenTextbox import HiddenTextbox
from AU2.html_components.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.constants import WEBPAGE_WRITE_LOCATION

SRCF_WEBSITE = "shell.srcf.net"
SSH_PORT = 22

ASSASSINS_PATH = "assassins"
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
                "SRCF -> Publish pages",
                self.ask_ignore_lock,
                self.answer_publish_pages
            ),
            Export(
                "SRCFPlugin_publish_pages",
                "SRCF -> Request lock",
                self.ask_ignore_lock,
                self.answer_lock
            ),
            Export(
                "SRCFPlugin_publish_pages",
                "SRCF -> Remote backup",
                self.ask_backup,
                self.answer_backup
            )
        ]

        self.html_ids = {
            "ignore_lock": self.identifier + "_ignore_lock",
            "requires_claiming": self.identifier + "_requires_claiming",
            "backup_name": self.identifier + "_backup_name"
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

    def ask_ignore_lock(self):
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

    def answer_lock(self, htmlResponse):
        """
        Claims a lock.
        """
        if not htmlResponse[self.html_ids["ignore_lock"]]:
            return [Label("[SRCF Plugin] Aborted.")]
        with self._get_client() as sftp:
            self._lock(sftp)
        return [Label("[SRCF Plugin] Claimed lock.")]

    def answer_publish_pages(self, htmlResponse):
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
                self._log_to(sftp, PUBLISH_LOG, f"({self.username}) Trying to publish {page}")
                sftp.put(localpath, remotepath)
                self._log_to(sftp, PUBLISH_LOG, f"({self.username}) Published {page}")
                os.remove(localpath)
        return [Label("[SRCF Plugin] Successfuly published locally generated pages.")]

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
            for f in os.listdir(BASE_WRITE_LOCATION):
                if f.endswith(".json"):
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
        Closes the connection after.
        """
        self.username = username
        self.password = password
        try:
            with self._get_client() as sftp:
                pass
        except paramiko.ssh_exception.AuthenticationException:
            self.username = ""
            self.password = ""
            return False
        return True

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
