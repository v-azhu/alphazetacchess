# AlphaZetaChess Development Guide v0.1

## 1. Development Philosophy

AlphaZetaChess is a long-term engineering project.

Development principles:

-   Keep the architecture clean.
-   Make every version runnable.
-   Prefer understandable solutions before complex optimizations.
-   Add tests before large refactoring.
-   Measure AI strength improvements objectively.

The project should evolve from a simple playable engine into a complete
Chinese Chess AI research platform.

------------------------------------------------------------------------

# 2. Technology Stack

## 2.1 Primary Language

Initial development language:

    Python 3.11+

Reasons:

-   Rapid prototyping.
-   Rich AI ecosystem.
-   Easy experimentation.

Future performance-critical modules may migrate to:

    C++
    Rust

if required.

------------------------------------------------------------------------

## 2.2 AI Framework

Potential future components:

-   PyTorch for neural networks.
-   NumPy for numerical computation.
-   Custom MCTS implementation.
-   Custom search engine implementation.

The project should avoid unnecessary dependencies in the early stages.

------------------------------------------------------------------------

# 3. Repository Structure

Recommended structure:

    alphazetacchess/

    ├── docs/
    │
    ├── src/
    │   ├── core/
    │   ├── engine/
    │   ├── ai/
    │   └── protocol/
    │
    ├── tests/
    │
    ├── data/
    │
    ├── tools/
    │
    └── main.py

Responsibilities:

## src/core

Contains fundamental Chinese Chess logic:

-   board representation;
-   pieces;
-   moves;
-   rules.

No AI logic should exist here.

------------------------------------------------------------------------

## src/engine

Contains traditional engine components:

-   search;
-   evaluation;
-   transposition table;
-   move ordering.

------------------------------------------------------------------------

## src/ai

Contains learning-related modules:

-   neural networks;
-   MCTS;
-   self-play;
-   training.

------------------------------------------------------------------------

## tests

Contains automated tests.

Every core rule change should include tests.

------------------------------------------------------------------------

# 4. Coding Standards

## Naming

Python style:

-   Classes: PascalCase

Example:

``` python
class ChessBoard:
    pass
```

-   Functions and variables: snake_case

Example:

``` python
generate_moves()
current_player
```

-   Constants: UPPER_CASE

Example:

``` python
BOARD_WIDTH = 9
```

------------------------------------------------------------------------

# 5. Git Workflow

## Branch Strategy

Main branch:

    main

Stable releases only.

Development branch:

    dev

Daily development.

Feature branches:

    feature/xxx

Examples:

    feature/move-generator
    feature/mcts
    feature/neural-network

------------------------------------------------------------------------

# 6. Commit Convention

Recommended format:

    type: description

Examples:

    feat: add chess board model

    fix: correct horse leg blocking rule

    test: add move generation tests

    docs: update architecture document

    refactor: simplify evaluation module

------------------------------------------------------------------------

# 7. Testing Requirements

## Core Rule Tests

Must verify:

-   every piece movement;
-   illegal move rejection;
-   check detection;
-   checkmate detection.

Example:

    test_knight_blocked_by_leg()
    test_cannon_capture_rule()
    test_general_facing_rule()

------------------------------------------------------------------------

## Engine Tests

Verify:

-   search correctness;
-   evaluation consistency;
-   regression positions.

------------------------------------------------------------------------

# 8. Chess Data Management

Data directory:

    data/

    ├── games/
    │
    ├── opening/
    │
    └── models/

## games

Store:

-   human games;
-   self-play games;
-   test games.

Possible formats:

-   PGN-like format;
-   UCCI record;
-   custom JSON format.

------------------------------------------------------------------------

## opening

Store opening knowledge:

-   common openings;
-   historical games;
-   master games.

------------------------------------------------------------------------

## models

Store:

-   neural network weights;
-   version information;
-   evaluation results.

------------------------------------------------------------------------

# 9. Development Milestones

Each milestone should include:

## Code

Working implementation.

## Tests

Automated verification.

## Documentation

Updated design documents.

## Evaluation

Measured improvement.

------------------------------------------------------------------------

# 10. Performance Optimization Policy

Optimization should follow:

    Correctness

    ↓

    Profiling

    ↓

    Optimization

    ↓

    Benchmark

Do not optimize before measuring.

Priority:

1.  Correct rules.
2.  Search quality.
3.  Algorithm improvement.
4.  Low-level optimization.

------------------------------------------------------------------------

# 11. Future Engineering Goals

Possible future improvements:

-   UCCI protocol support.
-   GUI integration.
-   Opening book system.
-   Endgame database.
-   Distributed self-play.
-   GPU training.
-   Model evaluation framework.

------------------------------------------------------------------------

# 12. Addendum (2026-10-11) — Strength Evidence and Performance Policy

Added by the architecture review in [`v0.11.0.md`](v0.11.0.md). The v0.1 text above stays as the
baseline; the following amends it where measurements showed it no longer fits.

## 12.1 Performance policy: a measured exception

§10 ranks low-level optimization last and says "do not optimize before measuring". The
measurement has now been done: ~10–20K nodes/s, ≈ 414 Python calls per node, mean completed depth
1.4–2.1 against Pikafish (`v0.11.0.md` §2). At that throughput algorithmic improvements cannot be
realized, so **for the V0.11–V0.12 period structural performance work (the native core of §2.1 "if
required") is ranked ahead of further algorithm work.** Python micro-optimizations remain out of
scope (stop list, `v0.11.0.md` §4).

## 12.2 Strength claims require a gate

A change may be called "stronger" only with one of: an accepted SPRT gate (G1/G2/G3), a ladder
result, or an AZ-TAC-500 result — not from depth, node count or a sub-100-game match. Every test is
registered before it runs; reaching the game cap without a decision means *not accepted*; a re-run
needs a code change. Definitions and parameters: `v0.11.0.md` §6.

## 12.3 Evidence package

Every claim ships with: the reproduction command; game records plus manifest (openings, seed,
engine/config hash, binary hash, machine, affinity, `nps` calibration); replay-validation pass;
the SPRT result; a paragraph in the version document with an honest reading, including when it is
negative (existing practice, made uniform).

## 12.4 Configuration and flags

One immutable `EngineConfig` with named presets is the only way to configure an engine; its hash is
stored in every game record. No new constructor flags on `SearchEngine`. A default-on flag requires
an accepted evidence ID in the flag registry; flags without evidence stay off or are removed.

## 12.5 Tools

No new per-feature `compare_*` scripts: extend `tools/match.py`. Generated game records larger
than 1 MB are release assets or LFS objects, with the manifest kept in git.

## 12.6 Native core rules

Contract tests first; the Python engine is the oracle; the native core is accepted only at zero
mismatches on the golden vectors; sanitizers (ASan/UBSan) are part of CI; after parity the Python
engine is frozen (bug fixes only) and remains the no-compiler fallback.

Version: v0.1 (addendum 2026-10-11)

Status: Initial Development Standard; see addendum §12 for the current policy
