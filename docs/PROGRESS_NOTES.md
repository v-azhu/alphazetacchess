# AlphaZetaChess Progress Snapshot — V0.6.2 neural evaluation pipeline (untrained)

Snapshot date: 2026-09-05

## What happened this checkpoint

User's local infrastructure (a laptop) can't handle self-play-scale
training. Asked about borrowing Pikafish's (a strong open-source
Xiangqi engine) published training results instead of training from
scratch.

**Investigated before writing any code.** Two real blockers to porting
Pikafish's NNUE weights directly:
- Licensing: Pikafish's own `pikafish.nnue` carries a custom
  non-commercial license ("no commercial use without permission,"
  and it explicitly follows "weights further derived from them") --
  murky enough that embedding it (or a derivative) in this public
  repo isn't a clean call. A CC0 alternative exists for Fairy-
  Stockfish's xiangqi variant but wasn't worth chasing given blocker 2.
- Reimplementation: Pikafish's NNUE uses a specific feature encoding
  (HalfKAv2_xq) and quantized inference -- correctly porting that into
  this project's Python `Board` representation is a substantial,
  bug-prone reverse-engineering project on its own.

**Pivoted to distillation**: run Pikafish locally (on the user's
machine) as an oracle to label positions, train an entirely new, small
network from scratch on those labels. Never redistributes Pikafish's
weights/code -- only its output (a number) as training signal, which
is standard practice across the NNUE-training community.

Built the full pipeline this checkpoint, five independently-tested
pieces:

1. `core/fen.py` -- Xiangqi FEN encode/decode. The one detail that
   would have silently broken everything if missed: Xiangqi has two
   competing piece-letter conventions, and this project's own
   `PieceType.value` (Horse=H, Elephant=E) is the WRONG one for
   talking to Pikafish (which needs Horse=N, Elephant=B). Caught this
   by researching the actual UCCI convention before writing the
   encoder, not after debugging garbled positions.
2. `neural/features.py` -- perspective-relative board encoding
   (1260-dim: "my pieces" vs "opponent pieces", board vertically
   flipped for Black's perspective so both colors share one canonical
   orientation).
3. `neural/network.py` -- `SmallMLP`, a hand-derived 2-hidden-layer
   MLP (pure numpy, no torch). Backprop verified against a direct
   numerical gradient check, not just "training loss went down."
4. `neural/pikafish_client.py` + `tools/label_positions_with_
   pikafish.py` -- minimal UCI client + CLI to label sampled positions
   from real self-play games. Tested against a real fake-engine
   subprocess (`tests/fixtures/fake_uci_engine.py`), not mocked, since
   this project's test suite can't depend on a real Pikafish binary.
5. `tools/train_neural_eval.py` + `neural/evaluator.py` -- training
   script and a thin wrapper so a trained network can be called
   exactly like `evaluate(board, color)`.

## What was verified this checkpoint

```
pytest -q   (full suite)
165 passed in 125.72s
```
23 new tests across the five pieces above. Full pipeline smoke-tested
end to end using a fake UCI engine standing in for Pikafish: labeled
24 real positions sampled from real self-play games, trained a tiny
network on them, confirmed the mechanics (FEN round-trip, feature
extraction, training loop, save/load) all work together correctly.

**Not verified**: whether a network trained on REAL Pikafish
evaluations (which vary meaningfully, unlike the fake engine's
constant output) can learn anything useful. That requires the user's
local Pikafish and hasn't happened yet.

## What changed

- `src/alphazetacchess/core/fen.py` (new): `board_to_fen`, `board_from_fen`.
- `src/alphazetacchess/neural/` (new subpackage): `features.py`,
  `network.py`, `pikafish_client.py`, `evaluator.py`.
- `tools/label_positions_with_pikafish.py`, `tools/train_neural_eval.py` (new).
- `tests/fixtures/fake_uci_engine.py` (new): fake UCI engine for testing.
- `tests/test_fen_v062.py`, `test_network_v062.py`,
  `test_pikafish_client_v062.py`, `test_evaluator_v062.py` (new, 23 tests total).
- `docs/v0.6.2.md` (new): full pipeline design writeup.
- `docs/roadmap.md`: V0.6.2 section + hand-off updated.

## Exact next step

**On the user's machine** (needs a working Pikafish binary -- a
prebuilt release from https://github.com/official-pikafish/Pikafish/releases
is the easy path, no compiling required):
```bash
python tools/label_positions_with_pikafish.py --pikafish-path /path/to/pikafish --sample-every 4
python tools/train_neural_eval.py
```
This labels positions from the existing 99-game real corpus and trains
the first real network. Worth sanity-checking the reported validation
RMSE against a naive "always predict 0" baseline before assuming
anything was learned.

**Here, once a real trained network exists**: add a pluggable
`eval_fn` parameter to `SearchEngine`/`MCTSEngine` (both currently
hardcode calls to `evaluate()`), wire `NeuralEvaluator` in, and run
`tools/compare_engines.py` with it on one side -- the actual test of
whether any of this was worthwhile.

## Handoff rule (unchanged, repeated for visibility)

At the next interruption, update this file with:
1. latest commit / repo state (or "continuing from this session's
   sandbox" when there isn't a fresh GitHub push to check);
2. pytest count/result;
3. benchmark result (or honest non-result, or "deliberately not
   attempted and why");
4. remaining checklist;
5. one exact next command.

This keeps the project resumable without relying on conversation
memory, and keeps each checkpoint's own work small enough to finish
within a single response.
