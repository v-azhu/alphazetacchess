"""Compatibility CLI for the V0.11.1 unified match runner.

Importing this module is side-effect free. Run this file to invoke the unified
runner; legacy experiment-specific CLI flags have been consolidated in
tools/match.py.
"""
from pathlib import Path
import runpy
import sys


def _config_for_depth(records, depth):
    """Legacy helper retained for tests and callers that import this module."""
    for record in records:
        for side in ("red_config", "black_config"):
            config = record.get(side, {})
            if config.get("depth") == depth:
                result = dict(config)
                result["depth"] = depth
                return result
    return {
        "engine": "search",
        "depth": depth,
        "use_mobility": False,
        "use_pawn_structure": False,
        "use_piece_coordination": False,
        "use_endgame_heuristics": False,
        "use_killer_moves": True,
        "use_mvv_lva": False,
        "use_opening_book": False,
        "use_neural_eval": False,
        "use_calibrated_material": False,
        "use_calibrated_weights": False,
    }


def main() -> None:
    runner = Path(__file__).with_name("match.py")
    sys.argv[0] = str(runner)
    runpy.run_path(str(runner), run_name="__main__")


if __name__ == "__main__":
    main()
