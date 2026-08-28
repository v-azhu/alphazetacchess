# AlphaZetaChess Roadmap v0.1

## 1. Development Philosophy

AlphaZetaChess will be developed incrementally.

The project avoids starting directly with complex deep learning methods.

The development order is:

    Chess Rules

    ↓

    Traditional Engine

    ↓

    Search Optimization

    ↓

    Evaluation Improvement

    ↓

    Self Play

    ↓

    Neural Network

    ↓

    Hybrid AI Engine

------------------------------------------------------------------------

# 2. Version Roadmap

## V0.1 - Chess Foundation

Goal:

Build a complete playable Chinese Chess environment.

Features:

-   Board representation.
-   Piece movement rules.
-   Legal move generation.
-   Check and checkmate detection.
-   Human vs random AI.
-   Chess record saving.

Acceptance criteria:

-   All legal moves work correctly.
-   Can finish complete games.
-   Can save and replay games.

------------------------------------------------------------------------

## V0.2 - Basic Search Engine

Goal:

Make the AI capable of making reasonable decisions.

Features:

-   Minimax.
-   Alpha-Beta pruning.
-   Basic evaluation function.
-   Search depth control.

Acceptance criteria:

-   AI can defeat random players.
-   AI decisions are explainable.

------------------------------------------------------------------------

## V0.3 - Strong Traditional Engine

Goal:

Build a competitive traditional Chinese Chess engine.

Features:

-   Iterative deepening.
-   Negamax/PVS.
-   Transposition table.
-   Move ordering.
-   Quiescence search.
-   Opening knowledge.

Target:

Reach strong amateur level.

------------------------------------------------------------------------

## V0.4 - Advanced Evaluation System

Goal:

Improve chess understanding.

Features:

-   Better positional evaluation.
-   Pawn structure evaluation.
-   Piece coordination.
-   King safety.
-   Endgame knowledge.

Target:

Approach strong amateur / expert level.

------------------------------------------------------------------------

## V0.5 - Self Play System

Goal:

Create autonomous improvement capability.

Features:

-   AI vs AI games.
-   Game data collection.
-   Automatic evaluation.
-   Training dataset generation.

------------------------------------------------------------------------

## V0.6 - Neural Network Evaluation

Goal:

Introduce AlphaZero-inspired technology.

Features:

-   Policy network.
-   Value network.
-   Neural evaluation.
-   MCTS integration.

------------------------------------------------------------------------

## V0.7 - Hybrid Engine

Goal:

Combine traditional search and machine learning.

Architecture:

    Neural Network

    +

    MCTS / Alpha-Beta

    +

    Traditional Evaluation

    =

    AlphaZetaChess Engine

------------------------------------------------------------------------

## V1.0 - AlphaZetaChess AI Engine

Target:

A complete Chinese Chess AI platform.

Capabilities:

-   Play against humans.
-   Analyze chess games.
-   Self improvement.
-   Support UCCI protocol.
-   Manage AI models.
-   Evaluate chess strength.

------------------------------------------------------------------------

# 3. Strength Evaluation Plan

The project will use multiple evaluation methods:

## Engine Benchmark

AI vs AI:

    Version A
    vs
    Version B

    1000 games

Measure:

-   win rate;
-   draw rate;
-   Elo estimation.

------------------------------------------------------------------------

## Human Testing

Use selected human players:

-   beginner;
-   amateur;
-   advanced amateur.

Special test player:

-   AlphaZetaChess creator (strong amateur benchmark).

------------------------------------------------------------------------

# 4. Future Research Directions

Possible directions:

-   Xiangqi NNUE.
-   AlphaZero-style self play.
-   Opening database learning.
-   Endgame tablebase.
-   Explainable AI analysis.
-   Human-style playing personalities.

------------------------------------------------------------------------

Version: v0.1

Status: Initial Development Roadmap
