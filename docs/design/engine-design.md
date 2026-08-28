# AlphaZetaChess Engine Design v0.1

## 1. Engine Layer Overview

The Engine Layer is responsible for deciding which move to play.

The Core Layer answers:

> What moves are legal?

The Engine Layer answers:

> Which legal move is the best choice?

Architecture:

                     Engine Layer

                          |
            +-------------+-------------+
            |                           |
     Search Engine              Evaluation Engine
            |                           |
     Alpha-Beta                 Position Analysis
     MCTS                       Chess Knowledge
            |
     Move Selection

The Engine Layer must remain independent from the user interface and
game storage.

------------------------------------------------------------------------

# 2. Engine Evolution Strategy

AlphaZetaChess will evolve gradually:

    Random Player

    ↓

    Basic Evaluation

    ↓

    Minimax

    ↓

    Alpha-Beta Search

    ↓

    Advanced Search Engine

    ↓

    MCTS

    ↓

    Neural Network Guidance

    ↓

    Hybrid Engine

The project will not start directly with deep learning.

The purpose is to understand each stage and measure improvement.

------------------------------------------------------------------------

# 3. Engine Interface

The engine should provide a unified interface:

``` python
class ChessEngine:

    def choose_move(game_state):
        pass
```

Future implementations:

    RandomEngine

    SearchEngine

    MCTSEngine

    NeuralEngine

    HybridEngine

All engines should be replaceable without changing the Core Layer.

------------------------------------------------------------------------

# 4. Search Engine Design

## 4.1 Initial Search

First implementation:

    Minimax

Purpose:

-   verify search framework;
-   test move generation;
-   build debugging capability.

------------------------------------------------------------------------

## 4.2 Alpha-Beta Search

Evolution:

    Minimax

    ↓

    Alpha-Beta Pruning

Goal:

Reduce unnecessary calculation.

Basic idea:

Avoid searching branches that cannot influence the final decision.

------------------------------------------------------------------------

## 4.3 Negamax

Because Chinese Chess is a two-player zero-sum game:

    my advantage

    =

    opponent disadvantage

The implementation can simplify to:

    score = -opponent_score

------------------------------------------------------------------------

## 4.4 Iterative Deepening

Search depth increases gradually:

    depth 1

    ↓

    depth 2

    ↓

    depth 3

    ↓

    ...

Benefits:

-   Better time management;
-   Better move ordering;
-   Stable search behavior.

------------------------------------------------------------------------

## 4.5 Transposition Table

Different move sequences may reach the same position.

Example:

    Move A → Move B

    and

    Move C → Move D

            ↓

    Same Position

Use:

    Zobrist Hash

    ↓

    Transposition Table

    ↓

    Reuse calculation

------------------------------------------------------------------------

# 5. Evaluation Engine Design

The evaluation function represents AlphaZetaChess's understanding of
chess.

Initial version:

    Evaluation Score =

    Material

    +

    Position

    +

    Mobility

    +

    King Safety

    +

    Attack

    +

    Defense

------------------------------------------------------------------------

# 6. Human Style Evaluation

One long-term goal of AlphaZetaChess is exploring different playing
styles.

Possible evaluation profiles:

    Aggressive Style

    Balanced Style

    Defensive Style

    Endgame Style

The creator's preferred style:

    Stable

    +

    Calculation-oriented

    +

    Position Control

This style emphasizes:

-   reducing opponent counterplay;
-   maintaining structural advantages;
-   converting small advantages.

------------------------------------------------------------------------

# 7. Search Optimization Roadmap

Possible improvements:

    Alpha-Beta

    ↓

    Move Ordering

    ↓

    Iterative Deepening

    ↓

    Transposition Table

    ↓

    Quiescence Search

    ↓

    Null Move Pruning

    ↓

    Late Move Reduction

    ↓

    Parallel Search

Each optimization must be benchmarked.

------------------------------------------------------------------------

# 8. MCTS Integration

Future AlphaZero-style architecture:

                  MCTS

                   |
           +-------+-------+
           |               |
     Policy Network   Value Network

MCTS responsibilities:

-   explore possible futures;
-   balance exploration and exploitation;
-   select promising moves.

------------------------------------------------------------------------

# 9. Neural Network Integration

Future architecture:

    Board State

    ↓

    Neural Network

    ↓

    Policy Probability

    +

    Position Value

    ↓

    Search Guidance

The neural network will not replace search completely.

Instead:

    Traditional Search

    +

    Machine Learning

    =

    Hybrid Intelligence

------------------------------------------------------------------------

# 10. Evaluation and Benchmark

Every engine improvement should be measured.

Methods:

## Engine Match

    Engine A

    vs

    Engine B

    1000 games

Metrics:

-   win rate;
-   draw rate;
-   estimated Elo.

------------------------------------------------------------------------

## Position Test

Use fixed positions:

-   opening;
-   middle game;
-   endgame;
-   tactical positions.

Measure:

-   search accuracy;
-   best move discovery;
-   calculation depth.

------------------------------------------------------------------------

# 11. Future Engine Architecture

Target architecture:

                     AlphaZetaChess

                           |
                     Engine Interface

                           |
            +--------------+--------------+
            |                             |
     Traditional Engine             Learning Engine

     Alpha-Beta                      MCTS

     Evaluation                     Neural Network

                           |
                     Hybrid Decision

------------------------------------------------------------------------

Version: v0.1

Status: Engine Architecture Design
