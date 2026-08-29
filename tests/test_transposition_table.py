from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.core.piece import Piece, PieceType
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.engine.transposition_table import (
    Bound,
    TranspositionTable,
)


def _move_signature(move):
    if move is None:
        return None
    return move.from_pos, move.to_pos


def empty_board():
    board = Board()
    board.board = [
        [None for _ in range(Board.WIDTH)]
        for _ in range(Board.HEIGHT)
    ]
    board.current_player = Color.RED
    # Empty-board construction is mainly used for isolated test positions.
    from alphazetacchess.core.zobrist import Zobrist
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def small_position():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 3))
    board._place(Piece(PieceType.HORSE, Color.RED, 2, 2))
    board._place(Piece(PieceType.CANNON, Color.BLACK, 4, 6))
    board._place(Piece(PieceType.HORSE, Color.BLACK, 7, 7))
    board._place(Piece(PieceType.PAWN, Color.RED, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 5))
    from alphazetacchess.core.zobrist import Zobrist
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def test_zobrist_hash_round_trip():
    board = Board()
    original = board.zobrist_hash

    board.move((1, 0), (2, 2))
    board.undo()

    assert board.zobrist_hash == original


def test_zobrist_distinguishes_side_to_move():
    board = Board()
    original = board.zobrist_hash

    board.current_player = Color.BLACK
    from alphazetacchess.core.zobrist import Zobrist
    board.zobrist_hash = Zobrist.board_hash(board)

    assert board.zobrist_hash != original


def test_tt_store_and_probe_exact():
    tt = TranspositionTable()

    tt.store(
        123,
        4,
        42,
        Bound.EXACT,
        None,
    )

    score, preferred = tt.probe(
        123,
        3,
        float("-inf"),
        float("inf"),
    )

    assert score == 42
    assert preferred is None
    assert tt.hits == 1
    assert tt.cutoffs == 1


def test_tt_preserves_search_result():
    board = small_position()

    without_tt = SearchEngine(
        depth=2,
        iterative_deepening=False,
        use_transposition_table=False,
    )
    with_tt = SearchEngine(
        depth=2,
        iterative_deepening=False,
        use_transposition_table=True,
    )

    a = without_tt.choose_move(board, Color.RED)
    b = with_tt.choose_move(board, Color.RED)

    assert a.score == b.score
    assert _move_signature(a.best_move) == _move_signature(b.best_move)
    assert with_tt.tt.probes > 0


def test_tt_does_not_increase_nodes_on_reference_position():
    board = small_position()

    without_tt = SearchEngine(
        depth=3,
        iterative_deepening=False,
        use_transposition_table=False,
    )
    with_tt = SearchEngine(
        depth=3,
        iterative_deepening=False,
        use_transposition_table=True,
    )

    a = without_tt.choose_move(board, Color.RED)
    b = with_tt.choose_move(board, Color.RED)

    assert b.score == a.score
    assert _move_signature(b.best_move) == _move_signature(a.best_move)
    assert b.nodes_evaluated <= a.nodes_evaluated
