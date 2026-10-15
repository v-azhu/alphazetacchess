"""Compatibility CLI for the V0.11.1 unified match runner.

Importing this module is side-effect free. Run this file to invoke the unified
runner; legacy experiment-specific CLI flags have been consolidated in
tools/match.py.
"""
from pathlib import Path
import runpy
import sys


def main() -> None:
    runner = Path(__file__).with_name("match.py")
    sys.argv[0] = str(runner)
    runpy.run_path(str(runner), run_name="__main__")


if __name__ == "__main__":
    main()
