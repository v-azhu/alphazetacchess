# AlphaZetaChess Progress Snapshot — 99-game checkpoint + V0.6.1 MCTS skeleton

Snapshot date: 2026-09-05

## What happened this checkpoint

Two distinct pieces of work: (1) analyzed a third round of real
self-play data the user collected locally, and (2) pivoted to V0.6,
building the first MCTS engine skeleton.

### 1. Third real data checkpoint (99 games)

User ran the three comparisons the previous checkpoint's hand-off
suggested, then interrupted early (depth=3 games are slow) — still
appended 36 complete, valid records before stopping.
`data/selfplay.jsonl`: 63 → 99 real games. All three open questions
now have real answers:

- **Opening book**: 20 games, exactly 50%/50%, Elo diff +0 — no
  measurable benefit yet. Notable side observation: zero draws across
  all 20 games (vs. the corpus's overall ~60% draw rate) — a
  tentative, not yet confirmed, hypothesis in
  `docs/v0.5-real-data-checkpoint-3.md`.
- **Depth=3 vs Depth=2**: 12 games, 62.5% score for depth=3, Elo diff
  **+88.7** — the first real, meaningfully-sized effect this project's
  self-play history has shown, matching strong prior chess-engine
  intuition.
- **`use_endgame_heuristics` at depth=3**: only 4 games completed
  before the interruption; combined with existing depth=2 data (29
  games total), still a flat ~52% / Elo +12 — consistent with the
  earlier depth=2-only null result.

`tools/analyze_endgame.py` on the full 99-game corpus: 20 decided
Rook/Cannon-edge positions — the first run where the tool's own
"sample too small" note doesn't print — still exactly 50%. Opening
book rebuilt again (1330 positions, up from 1057). Both
`use_endgame_heuristics` and the opening book remain off by default.

**Decision**: given depth=3-vs-depth=2 is now fairly confidently
answered and the other two comparisons both cleared "not just too
small" and came back null, moved to V0.6 rather than grinding out more
depth=3 games for diminishing returns on two already-answered
questions.

### 2. V0.6.1 — MCTS search skeleton

`src/alphazetacchess/engine/mcts.py`: `MCTSEngine`, PUCT-based MCTS
using the *existing* `evaluate()` function as leaf value estimator
(tanh-squashed to `[-1,1]`) and uniform move priors — deliberately no
policy/value network yet, following the same "search skeleton first,
evaluation second" split V0.3/V0.4 used historically.

12 new tests (`tests/test_mcts_v061.py`), most notably:
- A dedicated unit test for the single most error-prone part of any
  minimax/MCTS implementation (negating a child's value before
  comparing it from the parent's perspective).
- A cross-validation test: on a forced-mate fixture, `MCTSEngine`
  finds the *exact same* mating move an independently-implemented
  `SearchEngine(depth=2)` finds — much stronger evidence of
  correctness than hand-verifying the winning square myself.

**Smoke test initially looked concerning**: MCTSEngine vs RandomEngine,
6 games at simulations=150 → 6/6 draws (move limit), zero decisive
results. Investigated directly rather than dismissing or assuming a
bug — tracked material every 10 plies in a real game and confirmed
MCTSEngine reliably builds a genuine, growing advantage (4150 vs 3600
by ply 60). The mechanism works; it just doesn't reliably *convert*
that advantage into checkmate within a 150-move cap at the simulation
budgets tried (100-800) — an expected characteristic of vanilla MCTS
without a policy network (needs far more simulations per move than
alpha-beta needs plies), not a correctness bug.

## What was verified this checkpoint

```
pytest tests/test_mcts_v061.py -q
12 passed in 0.30s

pytest -q   (full suite)
142 passed in 162.56s
```

Manual smoke tests (documented in `docs/v0.6.1.md`):
```
MCTSEngine(simulations=100).choose_move(Board(), Color.RED)
  -> legal move, 0.31s

run_match(MCTSEngine(simulations=150), RandomEngine, games=6, max_moves=150)
  -> 6/6 draws (move limit)

MCTSEngine(simulations=300) as Red vs RandomEngine as Black, material tracked every 10 plies:
  ply 60: Red 4150 / Black 3600 -- real, growing material advantage confirmed
```

## What changed

- `data/selfplay.jsonl`: 63 → 99 real games (user's local runs).
- `data/opening_book.json`: rebuilt fresh from 99 games (1057 → 1330
  positions).
- `docs/v0.5-real-data-checkpoint-3.md` (new): full breakdown of all
  three real comparisons.
- `src/alphazetacchess/engine/mcts.py` (new): `MCTSEngine`, `_MCTSNode`,
  `_squash`.
- `tests/test_mcts_v061.py` (new, 12 tests).
- `docs/v0.6.1.md` (new): full design writeup.
- `docs/roadmap.md`: V0.5 line closed out as complete; V0.6.1 section
  added; hand-off updated.
- `README.md`: status checklist and project-structure tree updated
  through V0.6.1.

## Exact next step

Two independent directions:

**Tune/benchmark MCTSEngine** (needs real compute + small CLI
addition):
```bash
# Not yet supported -- tools/compare_engines.py only builds
# SearchEngine instances currently. Adding an --a-engine/--b-engine
# selector (mcts vs search) is the natural small next increment.
```
Goal: find the simulation count where `MCTSEngine` reliably beats
`RandomEngine` decisively (not just materially) within a reasonable
move limit, and where it starts competing with `SearchEngine` at
various depths.

**Design V0.6.2 (policy/value network)**: `_expand_and_evaluate`'s
`evaluate()` call and uniform priors are deliberately left as
placeholders for exactly this. Needs training data/infrastructure that
doesn't exist yet — a bigger undertaking than any single prior
checkpoint, worth designing carefully before writing code.

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
