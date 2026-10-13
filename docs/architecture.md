# AlphaZetaChess Architecture v0.1

## 1. Project Overview

### 1.1 Project Name

**AlphaZetaChess**

Chinese name:

**AlphaZeta 中国象棋 AI 引擎**

------------------------------------------------------------------------

## 1.2 Naming

The name AlphaZetaChess has three meanings:

-   **AZ** comes from the creator's initials.
-   **AlphaZeta** is inspired by AlphaZero, representing the project's
    ambition to explore self-learning AI.
-   **Chess** represents the chess domain, specifically Chinese Chess
    (Xiangqi).

The project name keeps the personal identity of the creator while paying
tribute to the AlphaZero approach.

------------------------------------------------------------------------

## 1.3 Project Goal

AlphaZetaChess is an open-source Chinese Chess AI research and
engineering project.

The goal is not only to build a chess-playing program, but to explore
how to construct an intelligent system that can continuously improve
through:

-   rule modeling;
-   search algorithms;
-   evaluation functions;
-   self-play;
-   machine learning.

Long-term goals:

-   Implement a complete Chinese Chess engine.
-   Build a high-performance search engine.
-   Develop self-play training capability.
-   Introduce neural network evaluation.
-   Explore AlphaZero-inspired learning methods.
-   Gradually approach advanced Chinese Chess AI strength.

------------------------------------------------------------------------

# 2. Overall Technical Roadmap

AlphaZetaChess follows an evolutionary architecture:

                     AlphaZetaChess

                           |
            +--------------+--------------+
            |                             |
     Traditional Engine             Learning System
            |                             |
     Search Engine                  Neural Network
            |                             |
     Alpha-Beta                     Policy Network
     MCTS                           Value Network
            |
     Evaluation Function

                           |
                           |
                     Self Play System
                           |
                           |
                     Training Pipeline

------------------------------------------------------------------------

# 3. System Architecture

The system is divided into five layers:

    +-----------------------------+
    |      Interface Layer        |
    |  UCCI / GUI / CLI / API     |
    +-------------▲---------------+
                  |
    +-------------┴---------------+
    |      Game Engine Layer      |
    | Board / Move / Rule         |
    +-------------▲---------------+
                  |
    +-------------┴---------------+
    |      Decision Layer         |
    | Search / Evaluation         |
    +-------------▲---------------+
                  |
    +-------------┴---------------+
    |      Learning Layer         |
    | Self Play / Training        |
    +-------------▲---------------+
                  |
    +-------------┴---------------+
    |      Data Layer             |
    | Games / Models / Opening    |
    +-----------------------------+

------------------------------------------------------------------------

# 4. Core Modules

## 4.1 Board Module

Responsible for managing game state.

Functions:

-   initialize board;
-   maintain piece positions;
-   execute moves;
-   undo moves;
-   copy positions;
-   calculate position hash.

------------------------------------------------------------------------

## 4.2 Move Generator

Responsible for generating legal moves.

Supports:

-   rook;
-   knight;
-   cannon;
-   elephant;
-   advisor;
-   king;
-   pawn.

------------------------------------------------------------------------

## 4.3 Rule Engine

Responsible for:

-   check detection;
-   checkmate detection;
-   stalemate detection;
-   repetition rules;
-   draw conditions.

------------------------------------------------------------------------

## 4.4 Search Engine

Evolution path:

    Minimax

    ↓

    Alpha-Beta

    ↓

    Negamax

    ↓

    PVS

    ↓

    Iterative Deepening

    ↓

    Transposition Table

    ↓

    Advanced Pruning

------------------------------------------------------------------------

## 4.5 Evaluation Engine

Initial evaluation:

    Score =
        Material
      + Position
      + Mobility
      + King Safety
      + Attack
      + Defense

Future direction:

    Neural Network Evaluation

------------------------------------------------------------------------

## 4.6 Self Play System

Core of AlphaZero-inspired learning.

    AI

    ↓

    Play Games

    ↓

    Generate Data

    ↓

    Train Model

    ↓

    New AI

------------------------------------------------------------------------

# 5. Project Structure

    alphazetacchess/

    ├── docs/
    │   ├── architecture.md
    │   ├── roadmap.md
    │   └── development.md
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
    │   ├── games/
    │   ├── opening/
    │   └── models/
    │
    ├── tools/
    │
    └── main.py

------------------------------------------------------------------------

# 6. Development Principles

## Principle 1: Every Version Must Be Runnable

Examples:

-   V0.1: Human vs Random AI
-   V0.2: Human vs Search AI
-   V0.3: AI vs AI
-   V0.4: AI Self Play

------------------------------------------------------------------------

## Principle 2: Build From Simple to Complex

Correct order:

    Rules

    ↓

    Search

    ↓

    Evaluation

    ↓

    Optimization

    ↓

    Learning

------------------------------------------------------------------------

## Principle 3: Measure Every Improvement

Every strength improvement should be measurable through:

-   AI vs AI matches;
-   win rate;
-   benchmark positions;
-   human testing.

------------------------------------------------------------------------

# 7. Initial Milestone

## AlphaZetaChess v0.1

Goals:

-   Complete board model.
-   Complete chess rules.
-   Generate legal moves.
-   Support human vs AI.
-   Save chess records.

Not included:

-   advanced search;
-   neural networks;
-   training pipeline.

------------------------------------------------------------------------

# 8. Long-term Vision

AlphaZetaChess aims to become:

> A Chinese Chess AI experimental platform evolving from rules, to
> search, to learning, and finally to self-improvement.

# 9. Addendum (2026-10-11) — Strength Architecture Direction

This document describes the initial v0.1 intent. The architecture review in
[`v0.11.0.md`](v0.11.0.md) found that the pure-Python substrate (~10–30K nodes/s) is the dominant limit
on playing strength, and that the measurement system cannot resolve small improvements. The layered
model of §3 is kept; the following changes the *Game Engine* and *Decision* layers and adds a
measurement layer.

                  Interfaces: Web UI | CLI | UCCI | tools
                                  |
              Engine API (Python): EngineConfig, SearchLimits,
                  SearchResult, core selector native|python|auto
                    /                                  \
        azcore (native, C++17)   <-- differential -->   alphazetacchess (Python)
        Position, movegen,            tests              executable specification,
        RuleSet, Evaluator,                              oracle, no-compiler fallback
        Search, TT, time manager
                                  |
        Measurement and learning (Python): match runner + SPRT,
        Pikafish node ladder, tactics suite, data generation, trainer

Changes relative to §3–§6:

- **Two implementations of one contract.** The Python engine becomes the executable specification
  (rules, legality, baseline evaluation); a native core provides throughput. Parity is enforced by
  versioned golden vectors with a zero-mismatch rule (`v0.11.0.md` §5.4).
- **Rule layer is versioned.** `RuleSet` makes repetition, long check / long chase and the natural move
  limit explicit instead of folding every repetition into a draw (§4.3 listed repetition rules; they
  were never fully implemented).
- **Evaluator is incremental.** The `evaluate(board, color)` function becomes an object with
  `refresh/push/pop/evaluate`, so that handcrafted accumulators and, later, NNUE accumulators update on
  make/unmake.
- **Measurement is a first-class layer** (Principle 3, "Measure Every Improvement", made operational):
  SPRT between versions, a node-limited Pikafish ladder, and a tactics/blunder suite.
- **Learning layer re-scoped.** Alpha-beta with an incrementally updated neural evaluation (V0.14) is the
  strength mainline; AlphaZero-style MCTS with policy/value networks is a gated research track.

Contract and acceptance criteria: `v0.11.0.md` §5 and §7.

Version: v0.1 (addendum 2026-10-11)

Status: Initial Architecture Design; see addendum §9 for the current direction
