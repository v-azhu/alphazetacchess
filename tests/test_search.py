from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Piece, PieceType, Color
from alphazetacchess.engine.search import SearchEngine
from alphazetacchess.engine.evaluation import evaluate


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    return board


def small_midgame_position():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 3))
    board._place(Piece(PieceType.HORSE, Color.RED, 2, 2))
    board._place(Piece(PieceType.CANNON, Color.BLACK, 4, 6))
    board._place(Piece(PieceType.HORSE, Color.BLACK, 7, 7))
    board._place(Piece(PieceType.PAWN, Color.RED, 4, 4))
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 5))
    return board


def test_evaluate_is_symmetric():
    board = Board()
    assert evaluate(board, Color.RED) == -evaluate(board, Color.BLACK)


def test_evaluate_initial_position_is_balanced():
    # Both sides start with identical material/position, so the
    # evaluation must be exactly zero.
    board = Board()
    assert evaluate(board, Color.RED) == 0


def test_alphabeta_matches_minimax_score_and_visits_fewer_nodes():
    for depth in (1, 2, 3):
        board = small_midgame_position()

        minimax = SearchEngine(depth=depth, use_alpha_beta=False)
        alphabeta = SearchEngine(depth=depth, use_alpha_beta=True)

        mm_result = minimax.choose_move(board, Color.RED)
        ab_result = alphabeta.choose_move(board, Color.RED)

        assert mm_result.score == ab_result.score
        assert ab_result.nodes_evaluated <= mm_result.nodes_evaluated


def test_engine_takes_a_free_capture():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 5))
    # An undefended Black horse directly in the rook's path: taking it
    # is a free Rook-captures-Horse trade with nothing else in play.
    board._place(Piece(PieceType.HORSE, Color.BLACK, 4, 5))

    engine = SearchEngine(depth=1)
    result = engine.choose_move(board, Color.RED)

    assert result.best_move.from_pos == (0, 5)
    assert result.best_move.to_pos == (4, 5)
    assert result.best_move.captured_piece is not None
    assert result.best_move.captured_piece.type == PieceType.HORSE


def test_engine_prefers_capturing_more_valuable_piece():
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 4, 5))
    # Two independent, undefended Black targets reachable this move in
    # different directions: a cheap Pawn along the column, and a much
    # more valuable Rook along the row.
    board._place(Piece(PieceType.PAWN, Color.BLACK, 4, 3))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 7, 5))

    engine = SearchEngine(depth=1)
    result = engine.choose_move(board, Color.RED)

    assert result.best_move.captured_piece is not None
    assert result.best_move.captured_piece.type == PieceType.ROOK


def test_engine_avoids_hanging_its_own_rook_when_it_can_see_the_recapture():
    # At depth 2, the engine should see one full round-trip (its move,
    # then the opponent's best reply) and therefore avoid moving its
    # rook to a square where the opponent's rook can simply take it
    # for free, when a safer square is available.
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 5))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 4, 8))  # guards column 4

    engine = SearchEngine(depth=2)
    result = engine.choose_move(board, Color.RED)

    # Moving the rook to (4, 5) would walk it straight into the
    # black rook's line of fire on file 4 for no compensation.
    assert result.best_move.to_pos != (4, 5)
