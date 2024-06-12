import datetime
import os
import shutil
import random
from typing import List

from AU2 import BASE_WRITE_LOCATION
from AU2.database.model.database_utils import refresh_databases
from AU2.html_components import HTMLComponent
from AU2.html_components.Checkbox import Checkbox
from AU2.html_components.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.HiddenTextbox import HiddenTextbox
from AU2.html_components.InputWithDropDown import InputWithDropDown
from AU2.html_components.Label import Label
from AU2.html_components.NamedSmallTextbox import NamedSmallTextbox
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export


class BackupPlugin(AbstractPlugin):

    BACKUP_LOCATION = os.path.join(BASE_WRITE_LOCATION, "backup")
    if not os.path.exists(BACKUP_LOCATION):
        os.mkdir(BACKUP_LOCATION)

    def __init__(self):
        super().__init__("BackupPlugin")

        self.html_ids = {
            "Backup Name": self.identifier + "_backup_name",
            "Nuke Database": self.identifier + "_nuke",
            "Secret Number": self.identifier + "_secret_confirm"
        }

        self.exports = [
            Export(
                identifier="create_backup",
                display_name="Backup -> Create Backup",
                ask=self.ask_backup,
                answer=self.answer_backup
            ),
            Export(
                identifier="restore_backup",
                display_name="Backup -> Restore Backup",
                ask=self.ask_restore_backup,
                answer=self.answer_restore_backup
            ),
            Export(
                identifier="reset_database",
                display_name="Reset Database",
                ask=self.ask_reset_database,
                answer=self.answer_reset_database
            ),
        ]

    def ask_backup(self) -> List[HTMLComponent]:
        now = datetime.datetime.now()
        folder_name = now.strftime("backup_%d-%m-%Y_%H-%M-%S")
        return [
            DefaultNamedSmallTextbox(
                identifier=self.html_ids["Backup Name"],
                title="Backup name (you ought to use the name it suggests)",
                default=folder_name
            )
        ]

    def answer_backup(self, htmlResponse) -> List[HTMLComponent]:
        backup_path = os.path.join(self.BACKUP_LOCATION, htmlResponse[self.html_ids["Backup Name"]])
        os.mkdir(backup_path)
        for f in os.listdir(BASE_WRITE_LOCATION):
            if f.endswith(".json"):
                shutil.copy(os.path.join(BASE_WRITE_LOCATION, f), os.path.join(backup_path, f))
        return [Label("[BACKUP] Success!")]

    def ask_restore_backup(self) -> List[HTMLComponent]:
        backups = os.listdir(self.BACKUP_LOCATION)
        return [
            InputWithDropDown(
                identifier=self.html_ids["Backup Name"],
                title="Choose backup to restore",
                options=["Exit"] + backups
            )
        ]

    def answer_restore_backup(self, htmlResponse) -> List[HTMLComponent]:
        chosen_backup = htmlResponse[self.html_ids["Backup Name"]]
        if chosen_backup == "Exit":
            return [Label("[BACKUP] Aborted.")]
        for f in os.listdir(BASE_WRITE_LOCATION):
            if f.endswith(".json"):
                os.remove(os.path.join(BASE_WRITE_LOCATION, f))
        backup_path = os.path.join(self.BACKUP_LOCATION, chosen_backup)
        for f in os.listdir(backup_path):
            shutil.copy(os.path.join(backup_path, f), os.path.join(BASE_WRITE_LOCATION, f))

        refresh_databases()
        return [Label(f"[BACKUP] Restored {chosen_backup}")]

    def ask_reset_database(self) -> List[HTMLComponent]:
        i = random.randint(0, 1000000)
        return [
            Label(
                title="Are you sure you want to COMPLETELY RESET the database?"
            ),
            Label(
                title="!!!! UNSAVED DATA CANNOT BE RECOVERED !!!!"
            ),
            Label(
                title="(You can type anything else and the reset will be aborted.)"
            ),
            HiddenTextbox(
                identifier=self.html_ids["Secret Number"],
                default=str(i)
            ),
            NamedSmallTextbox(
                identifier=self.html_ids["Nuke Database"],
                title=f"Type {i} to reset the database"
            )
        ]

    def answer_reset_database(self, htmlResponse) -> List[HTMLComponent]:
        hidden_number = htmlResponse[self.html_ids["Secret Number"]]
        entered_number = htmlResponse[self.html_ids["Nuke Database"]]
        if hidden_number != entered_number:
            return [Label("[BACKUP] Aborting. You entered the code incorrectly.")]
        for f in os.listdir(BASE_WRITE_LOCATION):
            if f.endswith(".json"):
                os.remove(os.path.join(BASE_WRITE_LOCATION, f))
        refresh_databases()
        return [Label("[BACKUP] Databases successfully reset.")]
