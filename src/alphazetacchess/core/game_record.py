"""Standardized Xiangqi game-record container.

The engine internally represents moves as ``Move`` objects with absolute
board coordinates.  This module adds a stable, serializable game-level
representation using ICCS/UCCI coordinate moves (for example ``b2e2``).

A game record deliberately stores the initial FEN and the complete move list
rather than trying to reconstruct a game from the final position.  This makes
records suitable for self-play, engine-vs-engine matches, regression tests,
and later ML dataset generation.
"""

from dataclasses import dataclass, field

from .fen import board_from_fen, board_to_fen
from .move import Move
from .rule import Rule

_FILES = "abcdefghi"


@dataclass
class GameRecord:
    """A replayable, serializable Xiangqi game record."""

    initial_fen: str
    moves: list[str] = field(default_factory=list)
    result: str | None = None
    termination: str | None = None

    @classmethod
    def from_board(cls, board):
        """Create a record whose initial position is the board's current state."""
        return cls(initial_fen=board_to_fen(board))

    @classmethod
    def from_moves(cls, initial_fen, moves, result=None, termination=None):
        """Create a record from an existing ICCS/UCCI move sequence."""
        record = cls(
            initial_fen=initial_fen,
            moves=list(moves),
            result=result,
            termination=termination,
        )
        # Validate the complete sequence immediately.  A record is intended
        # to be a reliable experiment artifact, not an unchecked text log.
        record.replay()
        return record

    @staticmethod
    def move_to_iccs(move):
        """Convert an internal Move to absolute ICCS/UCCI coordinates."""
        fx, fy = move.from_pos
        tx, ty = move.to_pos
        if not (0 <= fx < 9 and 0 <= tx < 9 and 0 <= fy < 10 and 0 <= ty < 10):
            raise ValueError(f"Move coordinates out of bounds: {move!r}")
        return f"{_FILES[fx]}{fy}{_FILES[tx]}{ty}"

    @staticmethod
    def move_from_iccs(text):
        """Convert an absolute ICCS/UCCI coordinate move to a Move."""
        text = text.strip().lower()
        if len(text) != 4:
            raise ValueError(f"Invalid ICCS move {text!r}; expected four characters")
        if text[0] not in _FILES or text[2] not in _FILES:
            raise ValueError(f"Invalid ICCS file in move {text!r}")
        if not (text[1].isdigit() and text[3].isdigit()):
            raise ValueError(f"Invalid ICCS rank in move {text!r}")
        fx = _FILES.index(text[0])
        tx = _FILES.index(text[2])
        fy = int(text[1])
        ty = int(text[3])
        if fy >= 10 or ty >= 10:
            raise ValueError(f"Invalid ICCS rank in move {text!r}")
        return Move((fx, fy), (tx, ty))

    def append_move(self, board, move):
        """Validate and append one legal move to this record.

        The supplied board must represent the position after all existing
        record moves have been played.
        """
        if not Rule.is_legal_move(board, move, board.current_player):
            raise ValueError(f"Illegal move for current position: {self.move_to_iccs(move)}")
        notation = self.move_to_iccs(move)
        board.move(move.from_pos, move.to_pos)
        self.moves.append(notation)
        return notation

    def replay(self):
        """Replay all moves and return the resulting Board.

        Raises ``ValueError`` at the first illegal or malformed move.
        """
        board = board_from_fen(self.initial_fen)
        for index, notation in enumerate(self.moves, start=1):
            move = self.move_from_iccs(notation)
            if not Rule.is_legal_move(board, move, board.current_player):
                raise ValueError(f"Illegal move at ply {index}: {notation!r}")
            board.move(move.from_pos, move.to_pos)
        return board

    def final_fen(self):
        """Return the FEN reached after replaying the complete record."""
        return board_to_fen(self.replay())

    def to_dict(self):
        """Return a JSON-compatible dictionary."""
        return {
            "initial_fen": self.initial_fen,
            "moves": list(self.moves),
            "result": self.result,
            "termination": self.termination,
        }

    @classmethod
    def from_dict(cls, data):
        """Create and validate a record from a JSON-compatible dictionary."""
        return cls.from_moves(
            data["initial_fen"],
            data.get("moves", []),
            result=data.get("result"),
            termination=data.get("termination"),
        )
