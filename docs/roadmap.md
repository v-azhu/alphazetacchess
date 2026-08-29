# AlphaZetaChess Roadmap v0.2

## Development Philosophy

Chess Rules → Traditional Engine → Search Optimization → Evaluation → Self Play → Neural Network → Hybrid Engine

Every version must remain runnable, and every claimed improvement should be measurable.

## Version Status

| Version | Status | Goal |
|---|---|---|
| V0.1 | COMPLETE | Chess foundation |
| V0.2 | COMPLETE | Minimax + Alpha-Beta |
| V0.3.1 | CURRENT | Iterative deepening + move ordering |
| V0.3.2 | PLANNED | Transposition table |
| V0.3.3 | PLANNED | Negamax / PVS |
| V0.3.4 | PLANNED | Quiescence search |
| V0.3.5 | PLANNED | Benchmark / regression consolidation |
| V0.4 | PLANNED | Advanced evaluation |
| V0.5 | PLANNED | Self-play / training data |
| V0.6+ | PLANNED | Neural evaluation / MCTS |
| V0.7 | PLANNED | Hybrid engine |
| V1.0 | PLANNED | Complete Xiangqi AI platform |

## V0.1 — COMPLETE

Board/piece representation, all seven piece rules, legal move generation, check/flying-general validation, checkmate/stalemate handling, CLI play and tests.

## V0.2 — COMPLETE

Minimax, Alpha-Beta, basic material + positional evaluation, fixed depth, SearchResult, Human vs SearchEngine, AI benchmark.

Acceptance evidence from the repository:

- depth=1 vs RandomEngine: 10 games, 6 wins, 0 losses, 4 draws
- depth=2 vs RandomEngine: 6 games, 5 wins, 0 losses, 1 draw
- Minimax and Alpha-Beta agree on tested positions
- Alpha-Beta does not visit more nodes than corresponding Minimax

Current baseline: depth=2. Depth=3 is stronger but currently too slow.

## V0.3 — Strong Traditional Engine

### V0.3.1 — Iterative Deepening + Move Ordering — CURRENT

Goal: make deeper Alpha-Beta practical while preserving V0.2 correctness.

Tasks:

- [ ] Iterative deepening
- [ ] Preserve last completed iteration as safe result
- [ ] Root move ordering
- [ ] Previous iteration best move first
- [ ] Tactical moves before quiet moves
- [ ] Search depth/node reporting
- [ ] Regression tests
- [ ] Benchmark against V0.2 fixed-depth search

Acceptance criteria:

1. Depth N completes all shallower iterations first.
2. The final completed iteration is usable.
3. At the same final depth, iterative and fixed-depth search agree on score/best move.
4. Move ordering does not alter the minimax result.
5. Ordered search evaluates no more nodes than the corresponding unordered search on benchmark positions.
6. Benchmarks record depth, time, nodes, NPS, score and best move.
7. Existing tests remain green.

Design boundary: V0.3.1 does not introduce transposition tables, PVS or quiescence search.

### V0.3.2 — Transposition Table — PLANNED

Position hashing, depth-aware entries, exact/lower/upper bounds, replacement policy, correctness tests and node-reduction benchmark.

### V0.3.3 — Negamax / PVS — PLANNED

Refactor search to Negamax, add Principal Variation Search, preserve evaluation semantics and benchmark against Alpha-Beta.

### V0.3.4 — Quiescence Search — PLANNED

Tactical move set, capture search, check extensions, horizon-effect tests and performance/strength benchmark.

### V0.3.5 — Benchmark & Regression — PLANNED

Fixed benchmark positions, reproducible seeds, NPS, strength regression and V0.3 acceptance report.

## V0.4 — Advanced Evaluation — PLANNED

Mobility, piece-square tables, coordination, king safety, pawn structure, endgame knowledge and opening knowledge.

## V0.5 — Self Play — PLANNED

AI vs AI games, data collection, automatic evaluation and training dataset generation.

## V0.6+ — Neural Evaluation / MCTS — PLANNED

Policy/value network, neural evaluation and MCTS integration.

## V0.7 — Hybrid Engine — PLANNED

Neural Network + MCTS/Alpha-Beta + Traditional Evaluation = AlphaZetaChess Engine.

## V1.0 — Complete AI Platform — PLANNED

Human play, analysis, self improvement, UCCI, model management and strength evaluation.

## Progress Tracking / Handoff

The repository is the source of truth. At the end of every step:

1. Update this roadmap.
2. Record the completed sub-version.
3. Record benchmark evidence.
4. Record known limitations.
5. State the exact next step.

Current hand-off:

    V0.2 COMPLETE
        ↓
    V0.3.1 CURRENT
        ↓
    Iterative Deepening + Move Ordering
        ↓
    Benchmark
        ↓
    V0.3.2 Transposition Table

Last updated: 2026-08-29
