#!/usr/bin/env python
"""echo.py - Simply echo the environment and the stdin."""

import os
import sys
import json

def main():
    print 'STDIN JSON:', json.loads(sys.stdin.read())
    print ''
    print 'ENV:', os.environ


if __name__ == '__main__':
    try:
        main()
    except Exception, e:
        print 'echo.py error: %s' % e

