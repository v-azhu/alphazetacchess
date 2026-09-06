"""
AlphaZetaChess neural evaluator training tool (V0.6.2).

Trains a small MLP (neural/network.py's SmallMLP) to regress toward
Pikafish's evaluations, using the (FEN, score_cp) pairs produced by
tools/label_positions_with_pikafish.py. Pure numpy -- no GPU, no
heavy ML framework -- specifically so this runs comfortably on modest
hardware (see docs/v0.6.2.md for the full rationale).

Usage:
    python tools/train_neural_eval.py
    python tools/train_neural_eval.py --input data/pikafish_labels.jsonl \\
        --output data/neural_eval.npz --epochs 200 --lr 0.001
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.selfplay.recorder import load_records
from alphazetacchess.neural.features import board_to_features, FEATURE_DIM
from alphazetacchess.neural.network import SmallMLP


def load_dataset(path):
    """
    Load (FEN, score_cp) label records and convert each to a feature
    vector + target. The label's score_cp is from the side-to-move's
    perspective (standard UCI convention -- see pikafish_client.py's
    docstring), and `board_from_fen` sets `board.current_player` to
    exactly that side, so encoding features "from board.current_player"
    lines up with the label with no sign flip needed.
    """
    records = load_records(path)
    X = np.zeros((len(records), FEATURE_DIM), dtype=np.float32)
    y = np.zeros(len(records), dtype=np.float32)

    for i, record in enumerate(records):
        board = board_from_fen(record["fen"])
        X[i] = board_to_features(board, board.current_player)
        y[i] = record["score_cp"]

    return X, y


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", default="data/pikafish_labels.jsonl")
    parser.add_argument("--output", default="data/neural_eval.npz")
    parser.add_argument("--epochs", type=int, default=800, help="maximum epochs -- early stopping (--patience) usually halts sooner")
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden1", type=int, default=64)
    parser.add_argument("--hidden2", type=int, default=32)
    parser.add_argument("--val-split", type=float, default=0.1, help="fraction of data held out for validation reporting")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--patience", type=int, default=40,
        help="stop if validation RMSE hasn't improved for this many consecutive epochs "
             "(the fixed --epochs count that was right for a small dataset silently became "
             "too many once the corpus grew 30x larger -- see docs/v0.6.2.md's 4th addendum "
             "for the overfitting this caused before early stopping was added)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"No labels found at {args.input}. Run tools/label_positions_with_pikafish.py first.")
        return

    print(f"Loading labels from {args.input}...")
    X, y = load_dataset(args.input)
    print(f"Loaded {len(y)} labeled position(s), feature dim {X.shape[1]}")

    rng = np.random.default_rng(args.seed)
    indices = rng.permutation(len(y))
    val_size = int(len(y) * args.val_split)
    val_idx, train_idx = indices[:val_size], indices[val_size:]
    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    print(f"Train: {len(y_train)}, Validation: {len(y_val)}")

    net = SmallMLP(FEATURE_DIM, hidden1=args.hidden1, hidden2=args.hidden2, seed=args.seed)
    # Standardize targets before training -- Pikafish's raw score_cp
    # labels range up to +/-9000 (see pikafish_client.py's
    # mate_score_to_cp), and training directly against targets that
    # large at a learning rate tuned for roughly unit-scale targets is
    # exactly what caused this project's first real training run to
    # diverge (weights blew up to ~1e24-1e27). See network.py's module
    # docstring for the full story. net.predict() always returns
    # real-scale (centipawn) values regardless of this -- only
    # train_step needs standardized targets.
    net.y_mean = float(y_train.mean())
    net.y_std = float(y_train.std()) or 1.0  # guard against a
    #                                           degenerate all-identical-label dataset
    y_train_standardized = (y_train - net.y_mean) / net.y_std
    print(f"Target standardization: mean={net.y_mean:.1f} cp, std={net.y_std:.1f} cp")

    # Early stopping: evaluate validation RMSE every epoch (cheap --
    # one forward pass) and keep the BEST checkpoint seen, not just
    # whatever weights happen to exist after --epochs runs out. This
    # matters more than it might look: the fixed epoch count that was
    # right for a ~2900-example dataset turned out to be badly wrong
    # once the corpus grew ~30x larger (validation RMSE bottomed out
    # around epoch 160 and then WORSENED through epoch 800 while
    # training RMSE kept dropping -- classic overfitting, and a fixed
    # epoch count has no way to know in advance where that point will
    # be for a dataset it hasn't seen yet). See docs/v0.6.2.md's 4th
    # addendum for the real run this was discovered on.
    best_val_rmse = float("inf")
    best_state = None
    best_epoch = 0
    epochs_since_improvement = 0

    for epoch in range(args.epochs):
        epoch_indices = rng.permutation(len(y_train))
        epoch_loss = 0.0
        num_batches = 0
        for start in range(0, len(y_train), args.batch_size):
            batch_idx = epoch_indices[start:start + args.batch_size]
            loss = net.train_step(X_train[batch_idx], y_train_standardized[batch_idx], lr=args.lr)
            epoch_loss += loss
            num_batches += 1

        val_pred = net.predict(X_val) if len(y_val) else np.array([])
        val_rmse = float(np.sqrt(np.mean((val_pred - y_val) ** 2))) if len(y_val) else float("nan")

        if val_rmse < best_val_rmse:
            best_val_rmse = val_rmse
            best_epoch = epoch + 1
            epochs_since_improvement = 0
            best_state = {
                "w1": net.w1.copy(), "b1": net.b1.copy(),
                "w2": net.w2.copy(), "b2": net.b2.copy(),
                "w3": net.w3.copy(), "b3": net.b3.copy(),
                "y_mean": net.y_mean, "y_std": net.y_std,
            }
        else:
            epochs_since_improvement += 1

        if (epoch + 1) % max(args.epochs // 10, 1) == 0 or epoch == 0:
            train_rmse_standardized = (epoch_loss / num_batches) ** 0.5
            train_rmse = train_rmse_standardized * net.y_std
            print(f"  epoch {epoch + 1:>4}/{args.epochs}: train RMSE {train_rmse:.1f} cp, val RMSE {val_rmse:.1f} cp")

        if len(y_val) and epochs_since_improvement >= args.patience:
            print(
                f"  stopping early at epoch {epoch + 1} -- no validation improvement "
                f"in the last {args.patience} epochs"
            )
            break

    if best_state is not None:
        net.w1, net.b1 = best_state["w1"], best_state["b1"]
        net.w2, net.b2 = best_state["w2"], best_state["b2"]
        net.w3, net.b3 = best_state["w3"], best_state["b3"]
        net.y_mean, net.y_std = best_state["y_mean"], best_state["y_std"]
        print(f"Restored best checkpoint: epoch {best_epoch}, val RMSE {best_val_rmse:.1f} cp")

    max_weight = max(
        np.abs(w).max() for w in (net.w1, net.b1, net.w2, net.b2, net.w3, net.b3)
    )
    if max_weight > 1e6:
        print(
            f"\nWARNING: largest weight magnitude after training is {max_weight:.2e} -- "
            f"this looks like training diverged (a healthy small MLP's weights should "
            f"stay well under 100). Try a smaller --lr before trusting this network."
        )

    net.save(args.output)
    print(f"Saved trained network to {args.output}")


if __name__ == "__main__":
    main()
