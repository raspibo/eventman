#!/usr/bin/env python
"""echo.py - Simply echo the environment and the stdin."""

import os
import sys
import json

def main():
    # NOTE: even if not used, ALWAYS consume sys.stdin to close the pipe.
    print 'STDIN JSON:', repr(json.loads(sys.stdin.read()))
    print ''
    print 'ENV:', repr(os.environ)


if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print 'echo.py error: %s' % e

