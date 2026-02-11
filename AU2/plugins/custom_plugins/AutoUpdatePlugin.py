import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import List, Optional

from AU2 import ROOT_DIR, __version__
from AU2.html_components import HTMLComponent
from AU2.html_components.SimpleComponents.Checkbox import Checkbox
from AU2.html_components.SimpleComponents.Label import Label
from AU2.plugins.AbstractPlugin import AbstractPlugin, Export
from AU2.plugins.CorePlugin import registered_plugin

REPO_ROOT = ROOT_DIR.parent
PACKAGE_DIR = ROOT_DIR
BACKUP_DIR = REPO_ROOT / "_au2_backup"
SETUP_PY_PATH = REPO_ROOT / "setup.py"
REQUIREMENTS_PATH = REPO_ROOT / "requirements.txt"

GITHUB_API_URL = "https://api.github.com/repos/jsyiek/AU2/releases/latest"
GITHUB_ARCHIVE_URL = "https://github.com/jsyiek/AU2/archive/refs/tags/{tag}.zip"


def parse_version(version_str: str) -> tuple:
    """
    Strips leading 'v', removes pre-release suffix, splits on '.', returns comparable tuple of ints.
    Handles formats like 'v1.4.1', '1.5.0', 'v1.4.0-pre3'.
    """
    version_str = version_str.strip().lstrip("v")
    # Remove pre-release suffix (e.g., '-pre3', '-beta1')
    base = version_str.split("-")[0]
    parts = []
    for part in base.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def check_for_update(current_version: str) -> Optional[dict]:
    """
    Checks GitHub API for latest release. Returns release info dict if a newer
    version exists, None otherwise. 10-second timeout, fails silently on error.
    """
    try:
        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            release = json.loads(response.read().decode("utf-8"))

        if release.get("prerelease", False):
            return None

        latest_tag = release.get("tag_name", "")
        if not latest_tag:
            return None

        if parse_version(latest_tag) > parse_version(current_version):
            return release

    except Exception:
        pass

    return None


def _delete_pycache(directory: Path) -> None:
    """Delete __pycache__ directories to avoid Windows file locking issues."""
    for pycache_dir in directory.rglob("__pycache__"):
        shutil.rmtree(pycache_dir, ignore_errors=True)


def apply_update(release_info: dict) -> str:
    """
    Downloads and applies the update from a GitHub release.
    Returns a status message string.
    """
    tag = release_info["tag_name"]
    download_url = GITHUB_ARCHIVE_URL.format(tag=tag)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Download ZIP
        zip_path = tmpdir_path / "update.zip"
        urllib.request.urlretrieve(download_url, zip_path)

        # Extract
        extract_dir = tmpdir_path / "extracted"
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Find the archive root directory (AU2-{tag}/ or AU2-v{tag}/)
        extracted_contents = list(extract_dir.iterdir())
        if len(extracted_contents) != 1:
            return "[UPDATE] Error: unexpected archive structure."
        archive_root = extracted_contents[0]

        new_package_dir = archive_root / "AU2"
        new_setup_py = archive_root / "setup.py"
        new_requirements = archive_root / "requirements.txt"

        if not new_package_dir.is_dir():
            return "[UPDATE] Error: AU2/ not found in downloaded archive."

        # Backup current files
        if BACKUP_DIR.exists():
            shutil.rmtree(BACKUP_DIR)
        BACKUP_DIR.mkdir()

        _delete_pycache(PACKAGE_DIR)

        shutil.copytree(PACKAGE_DIR, BACKUP_DIR / "AU2")
        if SETUP_PY_PATH.exists():
            shutil.copy2(SETUP_PY_PATH, BACKUP_DIR / "setup.py")
        if REQUIREMENTS_PATH.exists():
            shutil.copy2(REQUIREMENTS_PATH, BACKUP_DIR / "requirements.txt")

        # Replace AU2/ package
        _delete_pycache(PACKAGE_DIR)
        shutil.rmtree(PACKAGE_DIR)
        shutil.copytree(new_package_dir, PACKAGE_DIR)

        # Replace setup.py and requirements.txt
        if new_setup_py.exists():
            shutil.copy2(new_setup_py, SETUP_PY_PATH)
        if new_requirements.exists():
            shutil.copy2(new_requirements, REQUIREMENTS_PATH)

        # Re-run pip install -e to update .egg-info and install any new dependencies
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", REPO_ROOT],
            check=True,
        )

    return f"[UPDATE] Successfully updated to {tag}. Please restart AU2 for changes to take effect."


def rollback_update() -> str:
    """
    Restores from _au2_backup/ directory.
    Returns a status message string.
    """
    if not BACKUP_DIR.exists():
        return "[UPDATE] No backup found. Cannot rollback."

    backup_au2 = BACKUP_DIR / "AU2"
    if not backup_au2.exists():
        return "[UPDATE] Backup is incomplete (AU2/ missing). Cannot rollback."

    _delete_pycache(PACKAGE_DIR)
    shutil.rmtree(PACKAGE_DIR)
    shutil.copytree(backup_au2, PACKAGE_DIR)

    # Restore setup.py and requirements.txt
    backup_setup = BACKUP_DIR / "setup.py"
    backup_requirements = BACKUP_DIR / "requirements.txt"
    if backup_setup.exists():
        shutil.copy2(backup_setup, SETUP_PY_PATH)
    if backup_requirements.exists():
        shutil.copy2(backup_requirements, REQUIREMENTS_PATH)

    # Re-run pip install -e to sync dependencies
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", REPO_ROOT],
        check=True,
    )

    return "[UPDATE] Rollback complete. Please restart AU2 for changes to take effect."


@registered_plugin
class AutoUpdatePlugin(AbstractPlugin):

    def __init__(self):
        super().__init__("AutoUpdatePlugin")

        self.exports = [
            Export(
                identifier="auto_update_check",
                display_name="Check for updates",
                ask=self.ask_check_update,
                answer=self.answer_check_update,
            ),
            Export(
                identifier="auto_update_rollback",
                display_name="Rollback last update",
                ask=self.ask_rollback,
                answer=self.answer_rollback,
            ),
        ]

    def ask_check_update(self) -> List[HTMLComponent]:
        components: List[HTMLComponent] = []
        components.append(Label(f"Current version: {__version__}"))

        try:
            update = check_for_update(__version__)
        except Exception:
            update = None

        if update is None:
            components.append(Label("You are up to date (or unable to reach GitHub)."))
            self._pending_update = None
            return components

        tag = update["tag_name"].lstrip("v")
        components.append(Label(f"New version available: {tag}"))

        body = update.get("body", "").strip()
        if body:
            components.append(Label(f"Release notes:\n{body}"))

        components.append(Checkbox(
            identifier="auto_update_confirm",
            title=f"Update to {tag}?",
            checked=False,
        ))

        self._pending_update = update
        return components

    def answer_check_update(self, htmlResponse) -> List[HTMLComponent]:
        if self._pending_update is None:
            return [Label("[UPDATE] No update to apply.")]

        if not htmlResponse.get("auto_update_confirm", False):
            return [Label("[UPDATE] Update cancelled.")]

        try:
            result = apply_update(self._pending_update)
        except Exception as e:
            result = f"[UPDATE] Error applying update: {e}"

        return [Label(result)]

    def ask_rollback(self) -> List[HTMLComponent]:
        if not BACKUP_DIR.exists():
            return [Label("[UPDATE] No backup found. Nothing to rollback.")]

        return [
            Label(f"A backup exists at: {BACKUP_DIR}"),
            Checkbox(
                identifier="auto_update_rollback_confirm",
                title="Restore from backup?",
                checked=False,
            ),
        ]

    def answer_rollback(self, htmlResponse) -> List[HTMLComponent]:
        if not htmlResponse.get("auto_update_rollback_confirm", False):
            return [Label("[UPDATE] Rollback cancelled.")]

        try:
            result = rollback_update()
        except Exception as e:
            result = f"[UPDATE] Error during rollback: {e}"

        return [Label(result)]
