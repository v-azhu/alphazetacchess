"""Compatibility CLI; TimedSearch remains importable for legacy callers."""
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.legacy_compat import TimedSearch


def main() -> None:
    runner = Path(__file__).with_name("match.py")
    sys.argv[0] = str(runner)
    runpy.run_path(str(runner), run_name="__main__")


if __name__ == "__main__":
    main()
