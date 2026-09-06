"""Xiangqi FEN (Forsyth-Edwards Notation) encode/decode.

Built specifically to let this project talk to external UCI/UCCI
Xiangqi engines (Pikafish, in particular -- see `docs/v0.6.2.md`) via
the standard `position fen <FEN>` command, which is the only way to
hand an external engine a specific board state.

## The one thing worth reading carefully before touching this file

Xiangqi has **two competing piece-letter conventions** in real-world
use (see https://github.com/fairy-stockfish/Fairy-Stockfish/discussions/544):

1. "WXF"-style: Horse=H, Elephant=E -- this is what this project's own
   `core/piece.py` `PieceType.value` happens to use internally.
2. UCCI/UCI-style (used by Pikafish, Fairy-Stockfish, and every engine
   this module actually needs to talk to): Horse=**N** (knight),
   Elephant=**B** (bishop).

**These are different, and this module deliberately uses convention
(2)**, because that's what Pikafish expects -- `PieceType.value` (`"H"`,
`"E"`) must NOT be reused directly as FEN letters, or every position
sent to Pikafish would silently mislabel Horses and Elephants as
something else. `_FEN_LETTERS` below is the explicit, intentional
translation table for exactly this reason; do not "simplify" it to
`piece.type.value`.

## Orientation and the "w"/"b" active-color field

Xiangqi FEN inherits chess FEN's "White"/"Black" active-color letters
even though Xiangqi has no White or Black pieces: by convention, Red
(the side that moves first, same as this project's `Color.RED`) maps
to `'w'`, and Black maps to `'b'`. Piece placement is listed rank 9
(Black's home rank) down to rank 0 (Red's home rank), matching this
project's own `y=9` (Black's back rank) / `y=0` (Red's back rank)
layout exactly -- no coordinate flip is needed, only iterating `y` in
descending order.

Halfmove clock / fullmove number (FEN fields 5-6) aren't tracked by
this project's `Board` at all (no no-capture-move counter exists) --
`board_to_fen` reports a fullmove number derived from `len(board.
history)` and a halfmove clock of 0 as a reasonable placeholder,
clearly documented as such. Neither field affects Pikafish's static
evaluation of a position, which is this module's only intended use.
"""

from .board import Board
from .piece import Color, Piece, PieceType
from .zobrist import Zobrist

# Convention (2) above -- Horse=N, Elephant=B, NOT this project's own
# PieceType.value strings. See module docstring.
_FEN_LETTERS = {
    PieceType.KING: "k",
    PieceType.ADVISOR: "a",
    PieceType.ELEPHANT: "b",
    PieceType.HORSE: "n",
    PieceType.ROOK: "r",
    PieceType.CANNON: "c",
    PieceType.PAWN: "p",
}
_LETTER_TO_PIECE_TYPE = {letter: piece_type for piece_type, letter in _FEN_LETTERS.items()}


def board_to_fen(board):
    """Encode `board`'s current state as a Xiangqi FEN string."""
    rows = []
    for y in range(board.HEIGHT - 1, -1, -1):
        row_str = ""
        empty_run = 0
        for x in range(board.WIDTH):
            piece = board.board[y][x]
            if piece is None:
                empty_run += 1
                continue
            if empty_run:
                row_str += str(empty_run)
                empty_run = 0
            letter = _FEN_LETTERS[piece.type]
            row_str += letter.upper() if piece.color == Color.RED else letter
        if empty_run:
            row_str += str(empty_run)
        rows.append(row_str)

    placement = "/".join(rows)
    active_color = "w" if board.current_player == Color.RED else "b"
    # Fullmove number: standard FEN starts at 1 and increments after
    # Black's move, same as chess -- len(history) is total half-moves
    # played so far.
    fullmove_number = len(board.history) // 2 + 1

    return f"{placement} {active_color} - - 0 {fullmove_number}"


def board_from_fen(fen):
    """
    Decode a Xiangqi FEN string into a fresh `Board`. Ignores the
    halfmove-clock/fullmove-number fields (see module docstring for
    why) and starts `board.history` empty (a FEN describes a position,
    not how it was reached, so there's nothing meaningful to put in
    move history -- this matters if the caller intends to call
    `board.undo()`, which won't work past this point).
    """
    fields = fen.strip().split()
    if len(fields) < 2:
        raise ValueError(f"Not enough fields in FEN: {fen!r}")

    placement, active_color = fields[0], fields[1]

    board = Board()
    board.board = [[None for _ in range(board.WIDTH)] for _ in range(board.HEIGHT)]
    board.history = []

    rows = placement.split("/")
    if len(rows) != board.HEIGHT:
        raise ValueError(
            f"Expected {board.HEIGHT} ranks in FEN piece placement, got {len(rows)}: {fen!r}"
        )

    for rank_index, row_str in enumerate(rows):
        y = board.HEIGHT - 1 - rank_index
        x = 0
        for ch in row_str:
            if ch.isdigit():
                x += int(ch)
                continue
            piece_type = _LETTER_TO_PIECE_TYPE.get(ch.lower())
            if piece_type is None:
                raise ValueError(f"Unrecognized FEN piece letter {ch!r} in {fen!r}")
            color = Color.RED if ch.isupper() else Color.BLACK
            if x >= board.WIDTH:
                raise ValueError(f"Rank {rank_index} overflows board width in {fen!r}")
            board.board[y][x] = Piece(piece_type, color, x, y)
            x += 1

    if active_color == "w":
        board.current_player = Color.RED
    elif active_color == "b":
        board.current_player = Color.BLACK
    else:
        raise ValueError(f"Unrecognized active color {active_color!r} in {fen!r}")

    board.zobrist_hash = Zobrist.board_hash(board)
    return board
