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

Version: v0.1

Status: Initial Development Standard
