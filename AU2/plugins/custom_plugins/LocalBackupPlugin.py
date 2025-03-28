import os
import shutil
from typing import List

from AU2 import BASE_WRITE_LOCATION
from AU2.database.model.database_utils import refresh_databases
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.DefaultNamedSmallTextbox import DefaultNamedSmallTextbox
from AU2.html_components.SimpleComponents.InputWithDropDown import InputWithDropDown
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin
from AU2.plugins.util.date_utils import get_now_dt


@registered_plugin
class LocalBackupPlugin(AbstractPlugin):

    BACKUP_LOCATION = os.path.join(BASE_WRITE_LOCATION, "backup")
    if not os.path.exists(BACKUP_LOCATION):
        os.mkdir(BACKUP_LOCATION)

    def __init__(self):
        super().__init__("LocalBackupPlugin")

        self.html_ids = {
            "Backup Name": self.identifier + "_backup_name"
        }

        self.exports = [
            Export(
                identifier="local_backup_create_backup",
                display_name="Backup -> Create Backup",
                ask=self.ask_backup,
                answer=self.answer_backup
            ),
            Export(
                identifier="local_backup_restore_backup",
                display_name="Backup -> Restore Backup",
                ask=self.ask_restore_backup,
                answer=self.answer_restore_backup
            )
        ]

    def ask_backup(self) -> List[HTMLComponent]:
        now = get_now_dt()
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
