"""Compatibility entry point for the V0.11.1 unified match runner.

Use the options documented by tools/match.py. Legacy experiment-specific flags
were intentionally consolidated; old JSONL records and opening manifests remain inputs.
"""
from pathlib import Path
import runpy
import sys

runner = Path(__file__).with_name("match.py")
sys.argv[0] = str(runner)
runpy.run_path(str(runner), run_name="__main__")
