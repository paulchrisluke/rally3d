#!/usr/bin/env python3
import runpy
from pathlib import Path
import sys


def main():
    tool_path = Path(__file__).resolve().parents[1] / "tools" / "calibrate_manual.py"
    sys.argv[0] = str(tool_path)
    runpy.run_path(str(tool_path), run_name="__main__")


if __name__ == "__main__":
    main()
