import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import time
import traceback


DIR_NAME = os.path.dirname(os.path.abspath(__file__))
VENV_FOLDER_NAME = "src"
VENV_LOCATION = os.path.join(DIR_NAME, VENV_FOLDER_NAME)
PY_EXECUTABLE_MAC = os.path.join(VENV_LOCATION, "bin", "python3")
PY_EXECUTABLE_WINDOWS = os.path.join(VENV_LOCATION, "Scripts", "python.exe")
REPO_DIR = os.path.join(DIR_NAME, "AU2")

if "windows" in platform.system().lower():
    windows = True
    PY_EXECUTABLE = PY_EXECUTABLE_WINDOWS
else:
    windows = False
    PY_EXECUTABLE = PY_EXECUTABLE_MAC

INQUIRER_PY = os.path.join(REPO_DIR, "AU2", "frontends", "inquirer_cli.py")

AU2_EXE_LOCATION = os.path.join(VENV_LOCATION, "Scripts", "au2.exe")

EASY_RUN_MAC = f"""
#!/bin/bash

# Set the path to the Python executable in the subfolder
PYTHON_BIN="{os.path.abspath(DIR_NAME)}/{VENV_FOLDER_NAME}/bin/python3"

# Run the Python script using the Python binary in the subfolder
"$PYTHON_BIN" -m AU2
"""
EASY_RUN_MAC_NAME = "au2_mac"
EASY_RUN_MAC_LOCATION = os.path.join(DIR_NAME, EASY_RUN_MAC_NAME)



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--use-current-executable",
        action="store_true",
        help="Forces the script to use the current Python executable instead of recursing into a venv executable."
    )

    return parser.parse_args()

try:
    if __name__ == "__main__":
        args = parse_args()
        print(sys.executable)

        if not os.path.exists(PY_EXECUTABLE):
            print(f"Can't find a Python binary (looked for {PY_EXECUTABLE}). Setting up a new virtual environment.")
            if os.path.exists(VENV_LOCATION):
                shutil.rmtree(VENV_LOCATION)
            subprocess.run([sys.executable, "-m", "venv", VENV_LOCATION])
            print("Set up new virtual environment.")
        else:
            print("Found virtual environment.")

        if not args.use_current_executable:
            subprocess.run([PY_EXECUTABLE, os.path.abspath(__file__), "--use-current-executable"])
            exit()

        print("Setting up AU2 source...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-e", REPO_DIR])
        print("Source has been set up.")
        if not windows:
            with open(EASY_RUN_MAC_LOCATION, "w+") as F:
                F.write(EASY_RUN_MAC)
            st = os.stat(EASY_RUN_MAC_LOCATION)
            os.chmod(EASY_RUN_MAC_LOCATION, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            loc = EASY_RUN_MAC_LOCATION

        else:
            os.symlink(src=AU2_EXE_LOCATION, dst=os.path.join(DIR_NAME, "AU2"))
            loc = "the newly created AU2 file"

        print(f"In future, use {loc} to launch AU2.")
        print("Finished.")
        time.sleep(120)
        exit()
except Exception as e:
    print(traceback.format_exc())
    time.sleep(100)


