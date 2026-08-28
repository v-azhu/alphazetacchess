from .piece import Color
from .move_generator import MoveGenerator


class Rule:
    """
    Chinese Chess rule engine.

    Responsibilities:
    - turn pseudo-legal moves (from MoveGenerator) into fully legal
      moves, by rejecting any move that would leave the mover's own
      general in check, or cause the two generals to face each other
      directly ("flying general");
    - detect check, checkmate, and stalemate.

    Note on stalemate: unlike International Chess, in Chinese Chess a
    player who has no legal move available LOSES the game -- it is
    not a draw. is_stalemate() below simply reports "no legal moves
    and not currently in check"; the game loop decides the outcome.
    """

    _generator = MoveGenerator()

    @classmethod
    def pseudo_legal_moves(cls, board, color):
        return cls._generator.generate_moves(board, color)

    @classmethod
    def is_square_attacked(cls, board, x, y, by_color):
        for move in cls._generator.generate_moves(board, by_color):
            if move.to_pos == (x, y):
                return True
        return False

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
    def is_game_over(cls, board, color):
        return len(cls.generate_legal_moves(board, color)) == 0
