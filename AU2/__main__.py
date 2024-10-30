import time

from AU2.frontends.inquirer_cli import main

try:
    main()
except Exception as e:
    print(e)
    time.sleep(100)
