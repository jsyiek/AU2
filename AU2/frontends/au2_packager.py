import argparse
import os
import shutil
import tempfile

from typing import List

from AU2 import ROOT_DIR


def parse_args():
    parser = argparse.ArgumentParser("Package an AU2 version for release")
    parser.add_argument("--version-name", required=True, help="Version number of AU2")
    parser.add_argument("--dest", required=True, help="Folder in which to save the release")
    parser.add_argument(
        "--glob-file-types",
        nargs="+",
        default=[".html", ".py", ".txt"],
        help="File types to include"
    )
    return parser.parse_args()

def port_files(source_dir: str, target_dir: str, allowed_filetypes: List[str]):
    """
    Copies all files allowed in allowed_filetypes from the dest into the target.
    This is performed recursively through directories.
    """
    for file in os.listdir(source_dir):
        if file.startswith(".") or file.endswith(".egg-info") or file == "venv" or file.startswith("__pycache__"):
            continue
        source_path = os.path.join(source_dir, file)
        target_path = os.path.join(target_dir, file)
        if os.path.isdir(source_path):
            os.makedirs(target_path, exist_ok=True)
            port_files(source_path, target_path, allowed_filetypes)
        elif any(file.endswith(f) for f in allowed_filetypes):
            shutil.copy(source_path, target_path)
            print("Packaging: ", target_path)

def main():
    args = parse_args()

    print(f"Outputting au2-{args.version_name}.zip...")

    with tempfile.TemporaryDirectory() as tempdir:
        source_code_path = os.path.join(tempdir, "AU2")
        os.mkdir(source_code_path)
        shutil.copy(os.path.join(ROOT_DIR, "frontends", "au2_installer.py"), os.path.join(tempdir, "au2_installer.py"))
        port_files(os.path.join(ROOT_DIR, ".."), source_code_path, args.glob_file_types)

        zip_target = os.path.join(os.path.expanduser(args.dest), f"au2-v{args.version_name}")
        print("Compressing, this may take a while...")
        shutil.make_archive(zip_target, "zip", tempdir)
    print("Success.")


if __name__ == "__main__":
    main()
