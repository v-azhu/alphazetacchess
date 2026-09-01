"""V0.4.4 pawn structure (Connected Pawns) tests."""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.evaluation import evaluate
from alphazetacchess.engine.pawn_structure import (
    pawn_structure_score,
    pawn_structure_balance,
    CONNECTED_PAWN_BONUS,
    CONNECTED_PAWN_CROSSED_RIVER_BONUS,
)


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.history = []
    board.current_player = Color.RED
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def put(board, piece_type, color, x, y):
    board.board[y][x] = Piece(piece_type, color, x, y)


def test_isolated_pawn_scores_zero():
    board = empty_board()
    put(board, PieceType.PAWN, Color.RED, 4, 3)  # no neighbors at all

    assert pawn_structure_score(board, Color.RED) == 0


def test_connected_pawns_score_the_base_bonus_each():
    board = empty_board()
    put(board, PieceType.PAWN, Color.RED, 3, 3)
    put(board, PieceType.PAWN, Color.RED, 4, 3)  # adjacent file, same rank

    # Both pawns are connected to each other, so both score the bonus.
    assert pawn_structure_score(board, Color.RED) == 2 * CONNECTED_PAWN_BONUS


def test_connected_pawns_score_extra_once_crossed_the_river():
    board = empty_board()
    put(board, PieceType.PAWN, Color.RED, 3, 6)  # crossed (y >= 5 for Red)
    put(board, PieceType.PAWN, Color.RED, 4, 6)

    expected_per_pawn = CONNECTED_PAWN_BONUS + CONNECTED_PAWN_CROSSED_RIVER_BONUS
    assert pawn_structure_score(board, Color.RED) == 2 * expected_per_pawn


def test_same_file_pawns_are_not_connected():
    # Two pawns on the SAME file (different ranks) are not adjacent-file
    # neighbors -- this term is specifically about side-by-side support,
    # not "any nearby friendly pawn".
    board = empty_board()
    put(board, PieceType.PAWN, Color.RED, 4, 3)
    put(board, PieceType.PAWN, Color.RED, 4, 4)

    assert pawn_structure_score(board, Color.RED) == 0


def test_non_adjacent_files_are_not_connected():
    board = empty_board()
    put(board, PieceType.PAWN, Color.RED, 2, 3)
    put(board, PieceType.PAWN, Color.RED, 4, 3)  # two files apart

    assert pawn_structure_score(board, Color.RED) == 0


def test_enemy_pawns_do_not_count_as_connections():
    board = empty_board()
    put(board, PieceType.PAWN, Color.RED, 3, 3)
    put(board, PieceType.PAWN, Color.BLACK, 4, 3)  # adjacent file, but enemy

    assert pawn_structure_score(board, Color.RED) == 0


def test_pawn_structure_is_symmetric_between_colors():
    board = empty_board()
    put(board, PieceType.PAWN, Color.RED, 3, 3)
    put(board, PieceType.PAWN, Color.RED, 4, 3)
    put(board, PieceType.PAWN, Color.BLACK, 3, 6)
    put(board, PieceType.PAWN, Color.BLACK, 4, 6)

    assert pawn_structure_balance(board, Color.RED) == -pawn_structure_balance(
        board, Color.BLACK
    )


def test_pawn_structure_disabled_by_default_preserves_v043_evaluation():
    board = Board()

    baseline = evaluate(
        board, Color.RED,
        use_piece_square_tables=True, use_king_safety=True, use_mobility=False,
    )
    explicit_off = evaluate(
        board, Color.RED,
        use_piece_square_tables=True, use_king_safety=True, use_mobility=False,
        use_pawn_structure=False,
    )

    assert explicit_off == baseline


def test_pawn_structure_toggle_changes_evaluation_when_relevant():
    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 3, 9)
    put(board, PieceType.PAWN, Color.RED, 3, 3)
    put(board, PieceType.PAWN, Color.RED, 4, 3)

    without = evaluate(
        board, Color.RED,
        use_piece_square_tables=False, use_king_safety=False, use_mobility=False,
        use_pawn_structure=False,
    )
    with_ps = evaluate(
        board, Color.RED,
        use_piece_square_tables=False, use_king_safety=False, use_mobility=False,
        use_pawn_structure=True,
    )

    assert with_ps - without == 2 * CONNECTED_PAWN_BONUS


def test_search_engine_use_pawn_structure_toggle_reaches_evaluation():
    from alphazetacchess.engine.search import SearchEngine

    board = empty_board()
    put(board, PieceType.KING, Color.RED, 4, 0)
    put(board, PieceType.KING, Color.BLACK, 3, 9)
    put(board, PieceType.PAWN, Color.RED, 3, 3)
    put(board, PieceType.PAWN, Color.RED, 4, 3)

    with_ps = SearchEngine(use_pawn_structure=True)
    without_ps = SearchEngine(use_pawn_structure=False)

    score_with = with_ps._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )
    score_without = without_ps._quiescence(
        board, float("-inf"), float("inf"), Color.RED, root_depth=0, qply=0,
    )

    assert score_with == evaluate(board, Color.RED, use_pawn_structure=True)
    assert score_without == evaluate(board, Color.RED, use_pawn_structure=False)
    assert score_with != score_without
