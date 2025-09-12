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

EASY_RUN_WINDOWS = f"""
@echo off
setlocal

REM Get the path of the folder where the batch file is located
set "SCRIPT_DIR=%~dp0"

REM Run the Python script using the Python binary in the same folder
"%SCRIPT_DIR%{VENV_FOLDER_NAME}\\Scripts\\au2.exe"

endlocal
"""
EASY_RUN_WINDOWS_NAME = "au2_win.bat"
EASY_RUN_WINDOWS_LOCATION = os.path.join(DIR_NAME, EASY_RUN_WINDOWS_NAME)

EASY_RUN_MAC = f"""
#!/bin/bash

# Set the path to the Python executable in the subfolder
PYTHON_BIN="{os.path.abspath(DIR_NAME)}/{VENV_FOLDER_NAME}/bin/python3"

# Run the Python script using the Python binary in the subfolder
"$PYTHON_BIN" -m AU2
"""
EASY_RUN_MAC_NAME = "au2_mac"
EASY_RUN_MAC_LOCATION = os.path.join(DIR_NAME, EASY_RUN_MAC_NAME)

if windows:
    loc = EASY_RUN_WINDOWS_LOCATION
    src = EASY_RUN_WINDOWS
else:
    loc = EASY_RUN_MAC_LOCATION
    src = EASY_RUN_MAC


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
            proc = subprocess.run([sys.executable, "-m", "venv", VENV_LOCATION])
            if proc.returncode != 0:
                print("Failed to set up virtual environment.")
                time.sleep(120)
                exit()
            print("Set up new virtual environment.")
        else:
            print("Found virtual environment.")

        if not args.use_current_executable:
            subprocess.run([PY_EXECUTABLE, os.path.abspath(__file__), "--use-current-executable"])
            exit()

        print("Setting up AU2 source...")
        proc = subprocess.run([sys.executable, "-m", "pip", "install", "-e", REPO_DIR])

        if proc.returncode != 0:
            print("Install failed. Cleaning...")
            shutil.rmtree(VENV_LOCATION)  # clean up failed install
            print("Finished.")
            time.sleep(120)
            exit()

        print("Source has been set up.")

        with open(loc, "w+") as F:
            F.write(src)
        if not windows:
            st = os.stat(loc)
            os.chmod(loc, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        print(f"In future, use {loc} to launch AU2.")
        print("Finished.")
        time.sleep(120)
        exit()
except Exception as e:
    print(traceback.format_exc())
    time.sleep(100)


