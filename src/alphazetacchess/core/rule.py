from dataclasses import dataclass
from enum import Enum

from .piece import Color
from .move_generator import MoveGenerator
from .attack import AttackDetector


class TerminationReason(Enum):
    """Why a Xiangqi game has ended."""

    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    REPETITION = "repetition"


@dataclass(frozen=True)
class GameResult:
    """Structured game status returned by :meth:`Rule.game_result`.

    ``winner`` is the player who wins the game.  It is ``None`` for an
    ongoing game and for a repetition draw.
    """

    reason: TerminationReason | None = None
    winner: Color | None = None

    @property
    def is_over(self):
        return self.reason is not None


class Rule:
    """
    Chinese Chess rule engine.

    Responsibilities:
    - turn pseudo-legal moves (from MoveGenerator) into fully legal
      moves, by rejecting any move that would leave the mover's own
      general in check, or cause the two generals to face each other
      directly ("flying general");
    - detect check, checkmate, and stalemate;
    - provide a structured terminal-game result for the search/game loop.

    Note on stalemate: unlike International Chess, in Chinese Chess a
    player who has no legal move available LOSES the game -- it is
    not a draw. ``is_stalemate()`` reports the rule condition; the
    structured ``game_result()`` therefore awards the win to the opponent.
    """

    _generator = MoveGenerator()

    @classmethod
    def pseudo_legal_moves(cls, board, color):
        return cls._generator.generate_moves(board, color)

    @classmethod
    def is_square_attacked(cls, board, x, y, by_color):
        return AttackDetector.is_attacked(board, x, y, by_color)

    @classmethod
    def is_in_check(cls, board, color):
        king = board.find_king(color)
        if king is None:
            return False

        opponent = board.opponent(color)

        if cls.is_square_attacked(board, king.x, king.y, opponent):
            return True

        if board.kings_facing():
            return True

        return False

    @classmethod
    def generate_legal_moves(cls, board, color):
        legal_moves = []

        for move in cls.pseudo_legal_moves(board, color):
            board.move(move.from_pos, move.to_pos)
            still_in_check = cls.is_in_check(board, color)
            board.undo()

            if not still_in_check:
                legal_moves.append(move)

        return legal_moves

    @classmethod
    def is_legal_move(cls, board, move, color):
        legal_targets = {
            m.to_pos
            for m in cls.generate_legal_moves(board, color)
            if m.from_pos == move.from_pos
        }
        return move.to_pos in legal_targets

    @classmethod
    def is_checkmate(cls, board, color):
        return (
            cls.is_in_check(board, color)
            and len(cls.generate_legal_moves(board, color)) == 0
        )

    @classmethod
    def is_stalemate(cls, board, color):
        return (
            not cls.is_in_check(board, color)
            and len(cls.generate_legal_moves(board, color)) == 0
        )

    @classmethod
    def game_result(cls, board, color=None):
        """Return the structured terminal status for ``color`` to move.

        Checkmate and stalemate are evaluated before repetition because a
        position with no legal move is an immediate game termination.
        Repetition is currently represented as a draw; the more nuanced
        Xiangqi long-check/long-capture adjudication is intentionally kept
        separate for a later rules layer.
        """
        if color is None:
            color = board.current_player

        legal_moves = cls.generate_legal_moves(board, color)
        if not legal_moves:
            if cls.is_in_check(board, color):
                return GameResult(TerminationReason.CHECKMATE, board.opponent(color))
            return GameResult(TerminationReason.STALEMATE, board.opponent(color))

        if board.is_repetition():
            return GameResult(TerminationReason.REPETITION, None)

        return GameResult()

    @classmethod
    def is_game_over(cls, board, color):
        return cls.game_result(board, color).is_over
