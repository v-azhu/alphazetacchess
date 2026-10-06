from alphazetacchess.core.board import Board
from alphazetacchess.core.fen import board_from_fen, board_to_fen
from alphazetacchess.core.move_generator import MoveGenerator
from alphazetacchess.core.piece import Piece, PieceType, Color
from alphazetacchess.core.rule import Rule, TerminationReason


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    return board


def test_initial_position_has_44_legal_moves():
    # Well-known Xiangqi fact: the first player has exactly 44 legal
    # opening moves. This is a strong sanity check that move
    # generation + legality filtering are both correct together.
    board = Board()
    moves = Rule.generate_legal_moves(board, Color.RED)
    assert len(moves) == 44


def test_cannon_must_jump_exactly_one_screen_to_capture():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.CANNON, Color.RED, 0, 0))
    board._place(Piece(PieceType.HORSE, Color.RED, 0, 3))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 0, 6))

    cannon = board.get(0, 0)
    moves = MoveGenerator().generate_piece_moves(board, cannon)
    targets = {m.to_pos for m in moves}

    assert (0, 1) in targets
    assert (0, 2) in targets
    assert (0, 3) not in targets
    assert (0, 6) in targets


def test_elephant_blocked_by_eye_and_cannot_cross_river():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ELEPHANT, Color.RED, 2, 0))

    elephant = board.get(2, 0)
    gen = MoveGenerator()

    moves_free = {m.to_pos for m in gen.generate_piece_moves(board, elephant)}
    assert moves_free == {(0, 2), (4, 2)}

    board._place(Piece(PieceType.PAWN, Color.RED, 3, 1))
    moves_blocked = {m.to_pos for m in gen.generate_piece_moves(board, elephant)}
    assert (4, 2) not in moves_blocked
    assert (0, 2) in moves_blocked


def test_advisor_and_king_cannot_leave_palace():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ADVISOR, Color.RED, 3, 0))

    advisor = board.get(3, 0)
    moves = {m.to_pos for m in MoveGenerator().generate_piece_moves(board, advisor)}
    assert moves == {(4, 1)}


def test_flying_general_rule_forbids_kings_facing():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))

    assert board.kings_facing() is True
    assert Rule.is_in_check(board, Color.RED) is True

    legal_targets = {m.to_pos for m in Rule.generate_legal_moves(board, Color.RED)}
    assert (4, 1) not in legal_targets
    assert legal_targets == {(3, 0), (5, 0)}


def test_horse_delivers_checkmate():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 5, 9))
    board._place(Piece(PieceType.ELEPHANT, Color.BLACK, 4, 8))
    board._place(Piece(PieceType.HORSE, Color.RED, 5, 7))
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))

    assert Rule.is_in_check(board, Color.BLACK) is True
    assert Rule.generate_legal_moves(board, Color.BLACK) == []
    assert Rule.is_checkmate(board, Color.BLACK) is True
    assert Rule.is_stalemate(board, Color.BLACK) is False


def test_stalemate_is_a_loss_for_side_to_move():
    # Known Xiangqi stalemate position. Stalemate is a loss for the side
    # to move, so Black must have no legal moves while not being in check.
    board = board_from_fen("3aca3/1Cnrk4/b3r4/2p1n4/2b6/9/9/9/4C4/ppppcK3 b - - 0 1")

    assert Rule.is_in_check(board, Color.BLACK) is False
    assert Rule.generate_legal_moves(board, Color.BLACK) == []
    assert Rule.is_stalemate(board, Color.BLACK) is True

    result = Rule.game_result(board, Color.BLACK)
    assert result.reason is TerminationReason.STALEMATE
    assert result.winner is Color.RED
    assert result.is_over is True


def test_repetition_becomes_a_draw_after_three_occurrences():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 3, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 5, 9))
    board._place(Piece(PieceType.HORSE, Color.RED, 1, 0))
    board._place(Piece(PieceType.HORSE, Color.BLACK, 7, 9))

    board = board_from_fen("4k4/7n1/9/9/9/9/9/9/1N7/3K5 w - - 0 1")

    cycle = [
        ((1, 1), (0, 3)),
        ((7, 8), (8, 6)),
        ((0, 3), (1, 1)),
        ((8, 6), (7, 8)),
    ]

    assert board.repetition_count() == 1
    for move in cycle:
        board.move(*move)
    assert board.repetition_count() == 2
    assert Rule.game_result(board).is_over is False

    for move in cycle:
        board.move(*move)
    assert board.repetition_count() == 3

    result = Rule.game_result(board)
    assert result.reason is TerminationReason.REPETITION
    assert result.winner is None


def test_capture_generation_and_early_legal_move_check_match_full_legal_moves():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 5, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 5))
    board._place(Piece(PieceType.HORSE, Color.BLACK, 4, 5))

    full_legal_moves = Rule.generate_legal_moves(board, Color.RED)
    captures = Rule.generate_legal_captures(board, Color.RED)

    assert {(move.from_pos, move.to_pos) for move in captures} == {
        (move.from_pos, move.to_pos)
        for move in full_legal_moves
        if move.captured_piece is not None
    }
    assert Rule.has_legal_move(board, Color.RED) is bool(full_legal_moves)
    assert Rule.has_legal_move(board, Color.RED) is True


def test_early_legal_move_checks_detect_stalemate():
    board = board_from_fen(
        "3aca3/1Cnrk4/b3r4/2p1n4/2b6/9/9/9/4C4/ppppcK3 b - - 0 1"
    )

    captures = Rule.generate_legal_captures(board, Color.BLACK)

    assert captures == []
    assert Rule.has_legal_move(board, Color.BLACK) is False


def test_capture_only_moves_match_full_generator_on_opening_positions():
    board = Board()
    positions = [board_to_fen(board)]
    for from_pos, to_pos in (
        ((1, 0), (2, 2)),
        ((1, 9), (2, 7)),
        ((1, 2), (1, 4)),
        ((1, 7), (1, 5)),
    ):
        board.move(from_pos, to_pos)
        positions.append(board_to_fen(board))

    for fen in positions:
        position = board_from_fen(fen)
        for color in (Color.RED, Color.BLACK):
            full_moves = Rule.generate_legal_moves(position, color)
            capture_moves = Rule.generate_legal_captures(position, color)
            expected = {
                (move.from_pos, move.to_pos)
                for move in full_moves
                if move.captured_piece is not None
            }
            actual = {(move.from_pos, move.to_pos) for move in capture_moves}
            assert actual == expected
