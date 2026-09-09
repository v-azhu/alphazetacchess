import random

from alphazetacchess.core.attack import AttackDetector
from alphazetacchess.core.board import Board
from alphazetacchess.core.move_generator import MoveGenerator
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.rule import Rule


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    return board


def place_kings(board):
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))


def test_attack_detector_matches_rule_for_initial_position():
    board = Board()
    for color in (Color.RED, Color.BLACK):
        king = board.find_king(color)
        opponent = board.opponent(color)
        expected = Rule.is_square_attacked(board, king.x, king.y, opponent)
        assert AttackDetector.is_attacked(board, king.x, king.y, opponent) is expected


def test_rook_and_cannon_attacks():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 4))
    board._place(Piece(PieceType.CANNON, Color.RED, 8, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 6, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 7, 4))

    assert AttackDetector.is_attacked(board, 4, 4, Color.RED) is True
    assert AttackDetector.is_attacked(board, 7, 4, Color.RED) is True
    assert AttackDetector.is_attacked(board, 6, 4, Color.RED) is False


def test_cannon_requires_exactly_one_screen():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.CANNON, Color.RED, 0, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 3, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 5, 4))

    assert AttackDetector.is_attacked(board, 5, 4, Color.RED) is False

    board.board[4][3] = None
    assert AttackDetector.is_attacked(board, 5, 4, Color.RED) is True


def test_horse_attack_respects_leg_block():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.HORSE, Color.RED, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 5, 6))

    assert AttackDetector.is_attacked(board, 5, 6, Color.RED) is False

    board.board[5][4] = None
    assert AttackDetector.is_attacked(board, 5, 6, Color.RED) is True


def test_elephant_attack_respects_eye_and_river():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.ELEPHANT, Color.RED, 2, 0))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 2))

    assert AttackDetector.is_attacked(board, 4, 2, Color.RED) is False

    board.board[2][3] = None
    assert AttackDetector.is_attacked(board, 4, 2, Color.RED) is True

    board.board[2][3] = None
    board.board[4][4] = Piece(PieceType.PAWN, Color.BLACK, 4, 4)
    assert AttackDetector.is_attacked(board, 4, 4, Color.RED) is False


def test_advisor_and_king_attacks_are_palace_local():
    board = empty_board()
    place_kings(board)
    board._place(Piece(PieceType.ADVISOR, Color.RED, 3, 0))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 1))

    assert AttackDetector.is_attacked(board, 4, 1, Color.RED) is True
    assert AttackDetector.is_attacked(board, 2, 1, Color.RED) is True

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

    board.board[4][4].y = 5
    assert AttackDetector.is_attacked(board, 3, 5, Color.RED) is True
    assert AttackDetector.is_attacked(board, 4, 4, Color.RED) is False


def test_detector_differential_against_pseudo_moves_on_occupied_targets():
    rng = random.Random(0xA17AC)
    piece_types = list(PieceType)
    generator = MoveGenerator()

    for _ in range(300):
        board = empty_board()
        occupied = set()
        for color in (Color.RED, Color.BLACK):
            count = rng.randint(1, 12)
            for _ in range(count):
                for _attempt in range(20):
                    x = rng.randrange(Board.WIDTH)
                    y = rng.randrange(Board.HEIGHT)
                    if (x, y) not in occupied:
                        break
                else:
                    continue
                piece_type = rng.choice(piece_types)
                board._place(Piece(piece_type, color, x, y))
                occupied.add((x, y))

        for by_color in (Color.RED, Color.BLACK):
            moves = generator.generate_moves(board, by_color)
            attacked_by_generator = {move.to_pos for move in moves if move.captured_piece is not None}
            opponent = board.opponent(by_color)
            for target in occupied:
                piece = board.get(*target)
                if piece is None or piece.color != opponent:
                    continue
                expected = target in attacked_by_generator
                actual = AttackDetector.is_attacked(board, target[0], target[1], by_color)
                assert actual is expected, (by_color, target)
