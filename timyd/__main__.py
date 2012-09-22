try:
    from timyd.run import main
except ImportError:
    import os
    import sys


    sys.path.insert(0, os.path.realpath('.'))

    from timyd.run import main


main()
