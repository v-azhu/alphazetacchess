"""
AlphaZetaChess evaluation calibration tool (V0.6.3).

V0.6.2 spent three checkpoints training an increasingly elaborate
neural network on real Pikafish-labeled positions (more capacity, ~33x
more data, richer features) and each attempt showed the same small,
easily-exhausted improvement -- concluding with the network still
losing to the existing heuristic `evaluate()` by -269 Elo in a real,
converged 20-game comparison (see `docs/v0.6.2.md`).

This tool uses the SAME labeled data completely differently: instead
of training a black-box network to approximate a value function from
scratch, it fits new values for `evaluate()`'s own hand-guessed
constants (`MATERIAL_VALUES`, `PAWN_CROSSED_RIVER_BONUS`, and the
implicit weight-1 given to the piece-square-table/king-safety/
mobility/pawn-structure/piece-coordination/endgame terms) via ordinary
least-squares regression against real Pikafish scores, using
`engine/evaluation.py`'s own `evaluate_components()` as the regression
features. Fully interpretable (every coefficient IS a constant that
already exists in `evaluation.py`, just re-estimated), no black box,
no `eval_fn` indirection needed -- the fitted values could replace the
hand-guessed ones directly.

Usage:
    python tools/calibrate_evaluation.py
    python tools/calibrate_evaluation.py --input data/pikafish_labels.jsonl
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.piece import PieceType
from alphazetacchess.selfplay.recorder import load_records
from alphazetacchess.engine.evaluation import (
    evaluate_components, MATERIAL_VALUES, PAWN_CROSSED_RIVER_BONUS,
)

# Fixed column ordering for the regression matrix -- must match the
# order values are appended in build_feature_matrix() below.
_MATERIAL_KEYS = [
    f"material_{pt.name.lower()}" for pt in MATERIAL_VALUES if pt != PieceType.KING
]
_OTHER_KEYS = [
    "pawn_crossed_river_diff", "pst_balance", "king_safety_balance",
    "mobility_balance", "pawn_structure_balance",
    "piece_coordination_balance", "endgame_balance",
]
_FEATURE_KEYS = _MATERIAL_KEYS + _OTHER_KEYS

# What each column's constant currently is in evaluation.py -- for
# printing "current -> calibrated" side by side. Material entries map
# to MATERIAL_VALUES directly; pawn_crossed_river_diff to its own
# named constant; everything else has an IMPLICIT weight of 1 in
# evaluate() today (they're simply added in, unweighted).
_CURRENT_CONSTANTS = {
    f"material_{pt.name.lower()}": value
    for pt, value in MATERIAL_VALUES.items() if pt != PieceType.KING
}
_CURRENT_CONSTANTS["pawn_crossed_river_diff"] = PAWN_CROSSED_RIVER_BONUS
for key in ("pst_balance", "king_safety_balance", "mobility_balance",
            "pawn_structure_balance", "piece_coordination_balance", "endgame_balance"):
    _CURRENT_CONSTANTS[key] = 1


def build_feature_matrix(records):
    X = np.zeros((len(records), len(_FEATURE_KEYS) + 1), dtype=np.float64)  # +1 for intercept
    y = np.zeros(len(records), dtype=np.float64)

    for i, record in enumerate(records):
        board = board_from_fen(record["fen"])
        components = evaluate_components(board, board.current_player)
        for j, key in enumerate(_FEATURE_KEYS):
            X[i, j] = components[key]
        X[i, -1] = 1.0  # intercept -- captures any systematic first-move/tempo bias
        y[i] = record["score_cp"]

    return X, y


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="data/pikafish_labels.jsonl")
    parser.add_argument("--val-split", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"No labels found at {args.input}. Run tools/label_positions_with_pikafish.py first.")
        return

    print(f"Loading labels from {args.input}...")
    records = load_records(args.input)
    print(f"Loaded {len(records)} labeled position(s)")

    print("Computing evaluate_components() for every position (this replays each FEN)...")
    X, y = build_feature_matrix(records)

    rng = np.random.default_rng(args.seed)
    indices = rng.permutation(len(y))
    val_size = int(len(y) * args.val_split)
    val_idx, train_idx = indices[:val_size], indices[val_size:]
    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    print(f"Train: {len(y_train)}, Validation: {len(y_val)}")

    # Ordinary least squares -- closed-form, no gradient descent needed
    # for a linear model at this feature count.
    coefficients, residuals, rank, singular_values = np.linalg.lstsq(X_train, y_train, rcond=None)

    print("\nCalibrated constants (current hand-guessed value -> fitted value):")
    for key, coef in zip(_FEATURE_KEYS, coefficients[:-1]):
        current = _CURRENT_CONSTANTS[key]
        print(f"  {key:<28} {current:>7.1f} -> {coef:>8.1f}")
    print(f"  {'intercept (tempo bias)':<28} {'  n/a':>7} -> {coefficients[-1]:>8.1f}")

    train_pred = X_train @ coefficients
    val_pred = X_val @ coefficients
    train_rmse = float(np.sqrt(np.mean((train_pred - y_train) ** 2)))
    val_rmse = float(np.sqrt(np.mean((val_pred - y_val) ** 2)))
    val_corr = float(np.corrcoef(val_pred, y_val)[0, 1])
    naive_rmse = float(y_val.std())

    print(f"\nTrain RMSE: {train_rmse:.1f} cp")
    print(f"Held-out validation RMSE: {val_rmse:.1f} cp (naive baseline: {naive_rmse:.1f} cp)")
    print(f"Held-out validation correlation: {val_corr:.3f}")

    # Also report how the CURRENT (uncalibrated) hand-guessed constants
    # do on the same held-out split, for a direct, apples-to-apples
    # before/after comparison.
    current_vector = np.array([_CURRENT_CONSTANTS[key] for key in _FEATURE_KEYS] + [0.0])
    current_pred = X_val @ current_vector
    current_rmse = float(np.sqrt(np.mean((current_pred - y_val) ** 2)))
    current_corr = float(np.corrcoef(current_pred, y_val)[0, 1])
    print(f"\nFor comparison, CURRENT hand-guessed constants on the same held-out split:")
    print(f"  RMSE: {current_rmse:.1f} cp, correlation: {current_corr:.3f}")


if __name__ == "__main__":
    main()
