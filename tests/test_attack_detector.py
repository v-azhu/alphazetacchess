import random

from alphazetacchess.core.attack import AttackDetector
from alphazetacchess.core.board import Board
from alphazetacchess.core.move_generator import MoveGenerator
from alphazetacchess.core.piece import Color, Piece, PieceType


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    return board


def place_kings(board):
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))


def test_attack_detector_matches_pseudo_moves_for_initial_kings():
    board = Board()
    generator = MoveGenerator()
    for by_color in (Color.RED, Color.BLACK):
        target = board.find_king(board.opponent(by_color)).position()
        moves = generator.generate_moves(board, by_color)
        expected = any(move.to_pos == target and move.captured_piece is not None for move in moves)
        actual = AttackDetector.is_attacked(board, target[0], target[1], by_color)
        assert actual is expected


def test_rook_and_cannon_attacks():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 4))
    board._place(Piece(PieceType.CANNON, Color.RED, 8, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 6, 4))

    assert AttackDetector.is_attacked(board, 4, 4, Color.RED) is True
    # The cannon has no screen immediately before the target, so it cannot
    # attack the pawn at (6, 4).
    assert AttackDetector.is_attacked(board, 6, 4, Color.RED) is False


def test_cannon_requires_exactly_one_screen():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.CANNON, Color.RED, 0, 4))
    board._place(Piece(PieceType.PAWN, Color.RED, 3, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 5, 4))

    assert AttackDetector.is_attacked(board, 5, 4, Color.RED) is True

    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 4))
    assert AttackDetector.is_attacked(board, 5, 4, Color.RED) is False


def test_horse_attack_respects_leg_block():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.HORSE, Color.RED, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.RED, 4, 5))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 5, 6))

    assert AttackDetector.is_attacked(board, 5, 6, Color.RED) is False

    board.board[5][4] = None
    assert AttackDetector.is_attacked(board, 5, 6, Color.RED) is True


def test_elephant_attack_respects_eye_and_river():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.ELEPHANT, Color.RED, 2, 0))
    board._place(Piece(PieceType.PAWN, Color.RED, 3, 1))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 2))

    assert AttackDetector.is_attacked(board, 4, 2, Color.RED) is False

    board.board[1][3] = None
    assert AttackDetector.is_attacked(board, 4, 2, Color.RED) is True

    board._place(Piece(PieceType.ELEPHANT, Color.RED, 2, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 6))
    assert AttackDetector.is_attacked(board, 4, 6, Color.RED) is False


def test_advisor_and_king_attacks_are_palace_local():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.ADVISOR, Color.RED, 3, 0))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 1))

    assert AttackDetector.is_attacked(board, 4, 1, Color.RED) is True
    assert AttackDetector.is_attacked(board, 2, 1, Color.RED) is False

    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 3))
    assert AttackDetector.is_attacked(board, 4, 3, Color.RED) is False

    board._place(Piece(PieceType.KING, Color.RED, 4, 1))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 2))
    assert AttackDetector.is_attacked(board, 4, 2, Color.RED) is True


def test_pawn_attack_changes_after_crossing_river():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.PAWN, Color.RED, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 5))

    assert AttackDetector.is_attacked(board, 4, 5, Color.RED) is True
    assert AttackDetector.is_attacked(board, 3, 4, Color.RED) is False

    board.board[4][4] = None
    board._place(Piece(PieceType.PAWN, Color.RED, 4, 5))
    assert AttackDetector.is_attacked(board, 3, 5, Color.RED) is True
    assert AttackDetector.is_attacked(board, 4, 4, Color.RED) is False


def _random_position(rng):
    """Create a pseudo-legal position suitable for move/attack differential tests.

    The random boards do not attempt to enforce every Xiangqi legality rule, but
    constrained pieces obey their movement regions: kings and advisors stay in
    their palaces, and elephants stay on their own side of the river.  Exactly
    one king per side is placed so generator queries remain well-defined.
    """
    board = empty_board()
    occupied = set()

    def random_square(color, piece_type):
        if piece_type in (PieceType.KING, PieceType.ADVISOR):
            y_range = range(0, 3) if color is Color.RED else range(7, 10)
            x = rng.randint(3, 5)
            y = rng.choice(tuple(y_range))
            return x, y
        if piece_type is PieceType.ELEPHANT:
            y_range = range(0, 5) if color is Color.RED else range(5, 10)
            return rng.randrange(Board.WIDTH), rng.choice(tuple(y_range))
        return rng.randrange(Board.WIDTH), rng.randrange(Board.HEIGHT)

    for color in (Color.RED, Color.BLACK):
        king_square = (4, 0) if color is Color.RED else (4, 9)
        board._place(Piece(PieceType.KING, color, *king_square))
        occupied.add(king_square)

        count = rng.randint(1, 12)
        candidate_types = [piece_type for piece_type in PieceType if piece_type is not PieceType.KING]
        for _ in range(count):
            piece_type = rng.choice(candidate_types)
            for _attempt in range(50):
                square = random_square(color, piece_type)
                if square not in occupied:
                    break
            else:
                continue
            board._place(Piece(piece_type, color, *square))
            occupied.add(square)

    return board, occupied


def test_detector_differential_against_pseudo_moves_on_occupied_targets():
    rng = random.Random(0xA17AC)
    generator = MoveGenerator()

    for _ in range(300):
        board, occupied = _random_position(rng)

        for by_color in (Color.RED, Color.BLACK):
            moves = generator.generate_moves(board, by_color)
            attacked_by_generator = {
                move.to_pos
                for move in moves
                if move.captured_piece is not None
            }
            opponent = board.opponent(by_color)
            for target in occupied:
                piece = board.get(*target)
                if piece is None or piece.color != opponent:
                    continue
                expected = target in attacked_by_generator
                actual = AttackDetector.is_attacked(board, target[0], target[1], by_color)
                assert actual is expected, (by_color, target)


def test_detector_reports_attacks_on_empty_targets():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 4))
    board._place(Piece(PieceType.HORSE, Color.RED, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.RED, 6, 5))

    assert AttackDetector.is_attacked(board, 0, 7, Color.RED) is True
    assert AttackDetector.is_attacked(board, 5, 6, Color.RED) is True
    assert AttackDetector.is_attacked(board, 5, 5, Color.RED) is True
