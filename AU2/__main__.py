import sys
import time

PYTHON_VERSION_REQUIREMENT = (3, 9)

# check Python version to give a helpful message
# need to do this before importing AU2 files because type hints can cause errors in old versions of python
if not sys.version_info >= PYTHON_VERSION_REQUIREMENT:
    print(f"Error: AU2 requires Python {'.'.join(str(x) for x in PYTHON_VERSION_REQUIREMENT)} or above. "
          f"You are using Python {'.'.join(str(x) for x in sys.version_info)}.")
    time.sleep(100)
    exit()

from AU2.frontends.inquirer_cli import main

try:
    main()
except Exception as e:
    print(e)
    time.sleep(100)
