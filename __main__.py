#!/usr/bin/env python3
"""
TyperTRS - Main executable entry point
Allows the module to be executed with: python -m typertrs
"""

import sys
import curses
from . import main_app

def main():
    try:
        curses.wrapper(main_app)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()