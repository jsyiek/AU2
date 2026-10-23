import sys
import time
import traceback

PYTHON_VERSION_REQUIREMENT = (3, 9)

# check Python version to give a helpful message
# need to do this before importing AU2 files because type hints can cause errors in old versions of python
if not sys.version_info >= PYTHON_VERSION_REQUIREMENT:
    print(f"Error: AU2 requires Python {'.'.join(str(x) for x in PYTHON_VERSION_REQUIREMENT)} or above. "
          f"You are using Python {'.'.join(str(x) for x in sys.version_info)}.")
    time.sleep(100)
    exit()


from AU2.frontends.inquirer_cli import main



SEPARATOR = "-" * 20


def safe_main():
    """Entry point with crash reporting."""
    try:
        main()
    except Exception as au2_error:
        try:
            from AU2.coredump import write_coredump
            dump_path = write_coredump(au2_error)
            print(f"\nAU2 has crashed. A crash report has been saved to:\n  {dump_path}")
            print(f"\nPlease send this file to the developers for debugging.")
        except Exception as coredump_error:
            print(SEPARATOR)
            print(f"\nCoredump has crashed: {coredump_error}")
            traceback.print_exception(coredump_error, coredump_error, coredump_error.__traceback__)
        print(SEPARATOR)
        print(f"\nAU2 Error: {au2_error}")
        traceback.print_exception(au2_error, au2_error, au2_error.__traceback__)
        time.sleep(100)


safe_main()
