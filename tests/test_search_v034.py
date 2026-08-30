"""V0.3.4 correctness gates for Quiescence Search.

These tests deliberately focus on invariants rather than one particular
move ordering. Quiescence is allowed to change a shallow evaluation when
the fixed-depth horizon ends inside a tactical exchange.
"""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Piece, PieceType, Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.core.zobrist import Zobrist
from alphazetacchess.engine.evaluation import evaluate
from alphazetacchess.engine.search import SearchEngine


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.current_player = Color.RED
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def quiet_position():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 3))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 8, 6))
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def recapture_horizon_position():
    """Red can capture a Black cannon, but Black's rook immediately recaptures.

    The important property is not a particular numeric evaluation.  With
    nominal depth=1, the non-quiescent search stops after Red's capture.
    Quiescence continues the forced capture sequence and therefore must
    produce a different tactical value for that leaf.
    """
    board = empty_board()

    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))

    board._place(Piece(PieceType.ROOK, Color.RED, 0, 5))
    board._place(Piece(PieceType.CANNON, Color.BLACK, 4, 5))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 7, 5))

    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def test_quiescence_disabled_preserves_static_leaf_evaluation():
    board = quiet_position()
    engine = SearchEngine(depth=1, use_quiescence=False)

    # Directly exercise the leaf path on a quiet position: there are no
    # captures, so quiescence has nothing to extend and must agree with
    # the ordinary evaluator.
    score = engine._quiescence(
        board,
        float("-inf"),
        float("inf"),
        Color.RED,
        root_depth=1,
        qply=0,
    )

    assert score == evaluate(board, Color.RED)


def test_quiescence_detects_the_recapture_horizon():
    board = recapture_horizon_position()

    without_qs = SearchEngine(
        depth=1,
        use_quiescence=False,
        use_pvs=False,
    )
    with_qs = SearchEngine(
        depth=1,
        use_quiescence=True,
        use_pvs=False,
    )

    a = without_qs.choose_move(board, Color.RED)
    b = with_qs.choose_move(board, Color.RED)

    # The shallow evaluator sees the attractive capture, while QS sees
    # the opponent's immediate recapture. The exact score is intentionally
    # not asserted here because evaluation tuning belongs to V0.4.
    assert a.score != b.score


def test_quiescence_adds_nodes_on_a_tactical_leaf():
    board = recapture_horizon_position()

    without_qs = SearchEngine(
        depth=1,
        use_quiescence=False,
        use_pvs=False,
    )
    with_qs = SearchEngine(
        depth=1,
        use_quiescence=True,
        use_pvs=False,
    )

    a = without_qs.choose_move(board, Color.RED)
    b = with_qs.choose_move(board, Color.RED)

    assert b.nodes_evaluated > a.nodes_evaluated


def test_quiescence_is_forced_to_resolve_check():
    board = empty_board()

    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 4, 5))

    board.zobrist_hash = Zobrist.board_hash(board)

    assert Rule.is_in_check(board, Color.RED)

    engine = SearchEngine(
        depth=1,
        use_quiescence=True,
        use_pvs=False,
    )

    legal = Rule.generate_legal_moves(board, Color.RED)
    assert legal

    # A checked side has no stand-pat option. Calling QS must return a
    # legal-search value and terminate within the configured safety cap.
    score = engine._quiescence(
        board,
        float("-inf"),
        float("inf"),
        Color.RED,
        root_depth=1,
        qply=0,
    )

    assert isinstance(score, (int, float))


def test_quiescence_safety_cap_terminates():
    board = quiet_position()
    engine = SearchEngine(
        depth=1,
        use_quiescence=True,
        quiescence_max_ply=0,
    )

    score = engine._quiescence(
        board,
        float("-inf"),
        float("inf"),
        Color.RED,
        root_depth=1,
        qply=0,
    )

    assert score == evaluate(board, Color.RED)
