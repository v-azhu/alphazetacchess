"""
AlphaZetaChess policy network training tool (V0.9.4).

Trains a small MLP (neural/policy_network.py's PolicyMLP) to imitate
Pikafish's chosen best move, using the (FEN, best_move) pairs produced
by tools/label_positions_with_pikafish.py (the best_move field was
added to that tool in V0.9.4 -- see its own docstring; labels
collected before that change don't have it and need relabeling before
they're usable here). Pure numpy, same reasoning as
tools/train_neural_eval.py's own docstring: no GPU, no heavy ML
framework, so this runs comfortably on modest hardware.

Usage:
    python tools/train_policy_network.py
    python tools/train_policy_network.py --input data/pikafish_labels.jsonl \\
        --output data/policy_net.npz --epochs 200 --lr 0.001
"""

import argparse
import os
import sys

import numpy as np

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)

from alphazetacchess.core.fen import board_from_fen
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.core.rule import Rule
from alphazetacchess.selfplay.recorder import load_records
from alphazetacchess.neural.features import board_to_features, FEATURE_DIM
from alphazetacchess.neural.policy_encoding import move_to_policy_index, POLICY_DIM
from alphazetacchess.neural.policy_network import PolicyMLP


def load_dataset(path):
    """
    Load (FEN, best_move) label records and convert each to a feature
    vector + target policy index. `best_move` is in the same
    ICCS/UCCI coordinate notation `GameRecord.move_to_iccs`/
    `move_from_iccs` already use elsewhere in this project (e.g.
    protocol/ucci.py), so no new parsing code is needed.

    Two kinds of records are skipped, each with a reported count
    rather than silently dropped -- a large skip count usually means
    the wrong/stale label file was passed, and that should be obvious
    from the tool's own output, not discovered later from a
    suspiciously bad trained network:

    - no `best_move` field at all (labeled before V0.9.4's labeling
      fix -- see tools/label_positions_with_pikafish.py's docstring).
    - `best_move` isn't actually a legal move in the labeled position.
      A malformed FEN/move pairing, or an engine reporting a move for
      the wrong side, would otherwise silently train the network
      toward nonsense with no visible symptom until real play.
    """
    records = load_records(path)
    skipped_missing_best_move = 0
    skipped_illegal_move = 0
    X_list = []
    y_list = []

    for record in records:
        best_move_str = record.get("best_move")
        if not best_move_str:
            skipped_missing_best_move += 1
            continue

        board = board_from_fen(record["fen"])
        try:
            move = GameRecord.move_from_iccs(best_move_str)
        except ValueError:
            skipped_illegal_move += 1
            continue

        legal_moves = Rule.generate_legal_moves(board, board.current_player)
        is_legal = any(
            m.from_pos == move.from_pos and m.to_pos == move.to_pos
            for m in legal_moves
        )
        if not is_legal:
            skipped_illegal_move += 1
            continue

        X_list.append(board_to_features(board, board.current_player))
        y_list.append(move_to_policy_index(move, board.current_player))

    if skipped_missing_best_move:
        print(
            f"Skipped {skipped_missing_best_move} record(s) with no best_move field "
            f"(labeled before V0.9.4's labeling fix)"
        )
    if skipped_illegal_move:
        print(
            f"Skipped {skipped_illegal_move} record(s) whose best_move wasn't a legal "
            f"move for the labeled position (malformed label, not trusted)"
        )

    X = np.array(X_list, dtype=np.float32) if X_list else np.zeros((0, FEATURE_DIM), dtype=np.float32)
    y = np.array(y_list, dtype=np.int64)
    return X, y


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", default="data/pikafish_labels.jsonl")
    parser.add_argument("--output", default="data/policy_net.npz")
    parser.add_argument(
        "--epochs", type=int, default=800,
        help="maximum epochs -- early stopping (--patience) usually halts sooner",
    )
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden1", type=int, default=64)
    parser.add_argument("--hidden2", type=int, default=32)
    parser.add_argument(
        "--val-split", type=float, default=0.1,
        help="fraction of data held out for validation reporting",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--patience", type=int, default=40,
        help="stop if validation top-1 accuracy hasn't improved for this many "
             "consecutive epochs -- same early-stopping reasoning as "
             "tools/train_neural_eval.py's own --patience (see docs/v0.6.2.md's "
             "4th addendum for the overfitting a fixed epoch count caused there)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"No labels found at {args.input}. Run tools/label_positions_with_pikafish.py first.")
        return

    print(f"Loading labels from {args.input}...")
    X, y = load_dataset(args.input)
    print(f"Loaded {len(y)} usable labeled position(s)")

    if len(y) == 0:
        print("No usable training examples (see skip counts above) -- nothing to train on.")
        return

    rng = np.random.default_rng(args.seed)
    indices = rng.permutation(len(y))
    val_size = int(len(y) * args.val_split)
    val_idx, train_idx = indices[:val_size], indices[val_size:]
    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    print(f"Train: {len(y_train)}, Validation: {len(y_val)}")

    net = PolicyMLP(FEATURE_DIM, POLICY_DIM, hidden1=args.hidden1, hidden2=args.hidden2, seed=args.seed)

    def top1_accuracy(X_set, y_set):
        if len(y_set) == 0:
            return float("nan")
        logits, _ = net.forward(X_set)
        predicted = logits.argmax(axis=1)
        return float(np.mean(predicted == y_set))

    best_val_acc = -1.0
    best_state = None
    best_epoch = 0
    epochs_since_improvement = 0

    for epoch in range(args.epochs):
        epoch_indices = rng.permutation(len(y_train))
        epoch_loss = 0.0
        num_batches = 0
        for start in range(0, len(y_train), args.batch_size):
            batch_idx = epoch_indices[start:start + args.batch_size]
            loss = net.train_step(X_train[batch_idx], y_train[batch_idx], lr=args.lr)
            epoch_loss += loss
            num_batches += 1

        val_acc = top1_accuracy(X_val, y_val)

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch + 1
            epochs_since_improvement = 0
            best_state = {
                "w1": net.w1.copy(), "b1": net.b1.copy(),
                "w2": net.w2.copy(), "b2": net.b2.copy(),
                "w3": net.w3.copy(), "b3": net.b3.copy(),
            }
        else:
            epochs_since_improvement += 1

        if (epoch + 1) % max(args.epochs // 10, 1) == 0 or epoch == 0:
            train_loss = epoch_loss / num_batches
            print(
                f"  epoch {epoch + 1:>4}/{args.epochs}: train loss {train_loss:.4f}, "
                f"val top-1 accuracy {val_acc:.1%}"
            )

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
        print(f"Restored best checkpoint: epoch {best_epoch}, val top-1 accuracy {best_val_acc:.1%}")

    net.save(args.output)
    print(f"Saved trained policy network to {args.output}")


if __name__ == "__main__":
    main()
