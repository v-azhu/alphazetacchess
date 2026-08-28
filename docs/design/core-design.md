# AlphaZetaChess Core Design v0.1

## 1. Core Layer Design Goals

The Core Layer is the foundation of AlphaZetaChess.

Its responsibility is to provide a reliable Chinese Chess environment
that can be reused by:

-   Traditional search engine;
-   MCTS engine;
-   Neural network training system;
-   Chess analysis tools;
-   UCCI interface.

The Core Layer must be independent from AI decision logic.

Design priority:

    Correctness

    ↓

    Maintainability

    ↓

    Extensibility

    ↓

    Performance Optimization

------------------------------------------------------------------------

# 2. Coordinate System

## 2.1 Board Size

Chinese Chess board:

    9 columns × 10 rows

Coordinate definition:

    x: 0 - 8

    y: 0 - 9

Example:

          x
    0 1 2 3 4 5 6 7 8

    y=9  black side

    ...

    y=0  red side

The coordinate system must remain consistent across:

-   Board;
-   Move;
-   Rule checking;
-   Search;
-   Serialization.

------------------------------------------------------------------------

# 3. Piece Representation

## 3.1 Piece Type

Recommended design:

``` python
class PieceType(Enum):

    KING = 1
    ADVISOR = 2
    ELEPHANT = 3
    HORSE = 4
    ROOK = 5
    CANNON = 6
    PAWN = 7
```

------------------------------------------------------------------------

## 3.2 Piece Color

``` python
class Color(Enum):

    RED = 1
    BLACK = -1
```

------------------------------------------------------------------------

## 3.3 Piece Object

Example:

``` python
Piece(
    type=PieceType.HORSE,
    color=Color.RED,
    position=(1,0)
)
```

A Piece should only describe itself.

Move legality belongs to Rule Engine.

------------------------------------------------------------------------

# 4. Board Representation

## 4.1 Initial Implementation

Use a two-dimensional array:

``` python
board[10][9]
```

Example:

    [
     [r,h,e,a,k,a,e,h,r],
     [ , , , , , , , , ],
     ...
    ]

Advantages:

-   Easy to understand;
-   Easy to debug;
-   Suitable for early versions.

------------------------------------------------------------------------

## 4.2 Future Optimization

Possible evolution:

    Array Board

    ↓

    Optimized Array

    ↓

    BitBoard / Hybrid Representation

Optimization should only happen after profiling.

------------------------------------------------------------------------

# 5. Move Design

## 5.1 Move Object

A move contains:

``` python
class Move:

    from_position

    to_position

    moved_piece

    captured_piece
```

Example:

    马八进七

can be represented as:

    from=(1,0)

    to=(2,2)

------------------------------------------------------------------------

## 5.2 Move History

The system should support:

-   Execute move;
-   Undo move;
-   Replay game.

This is required for:

-   Search;
-   Analysis;
-   Training.

------------------------------------------------------------------------

# 6. Game State

A complete game state contains:

``` python
GameState:

    board

    current_player

    move_history

    zobrist_hash
```

Future additions:

-   repetition counter;
-   evaluation cache;
-   opening information.

------------------------------------------------------------------------

# 7. Move Generation

Each piece type provides movement generation logic.

Example:

    Horse

    ↓

    Generate candidate moves

    ↓

    Check horse-leg blocking

    ↓

    Return legal moves

Special rules:

-   Horse leg blocking;
-   Cannon jumping capture;
-   Elephant river restriction;
-   Palace restriction;
-   Flying general rule.

------------------------------------------------------------------------

# 8. Rule Engine

The Rule Engine provides:

``` python
is_legal_move()

is_check()

is_checkmate()

is_stalemate()

is_draw()
```

Responsibilities:

-   Validate moves;
-   Maintain game correctness;
-   Determine game status.

------------------------------------------------------------------------

# 9. Zobrist Hash

Zobrist hashing is used for:

-   Transposition table;
-   Position repetition detection;
-   Search optimization.

Concept:

    Piece

    +

    Position

    +

    Side to move

    ↓

    Random keys

    ↓

    Hash value

------------------------------------------------------------------------

# 10. Serialization

The Core Layer should support saving and loading positions.

Possible formats:

## Position

``` json
{
    "board": "...",
    "side": "red"
}
```

## Game Record

``` json
{
    "initial_position": "...",
    "moves": []
}
```

Future support:

-   UCCI;
-   Xiangqi notation;
-   Training data format.

------------------------------------------------------------------------

# 11. Testing Strategy

## 11.1 Piece Tests

Examples:

    test_rook_move()

    test_horse_leg_block()

    test_cannon_capture()

    test_elephant_restriction()

    test_general_facing_rule()

------------------------------------------------------------------------

## 11.2 Position Tests

Important scenarios:

-   Check;
-   Checkmate;
-   Stalemate;
-   Repetition;
-   Illegal moves.

------------------------------------------------------------------------

# 12. Future Evolution

Core Layer evolution:

    V0.x

    Readable Python Implementation

    ↓

    V1.x

    Optimized Engine Core

    ↓

    Future

    C++ / Rust Performance Layer

The external interface should remain stable during optimization.

------------------------------------------------------------------------

Version: v0.1

Status: Core Architecture Design
