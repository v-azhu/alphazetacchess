from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color, Piece, PieceType
from alphazetacchess.engine.search import SearchEngine


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board.current_player = Color.RED
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
    return board


def test_pvs_research_uses_the_current_full_window(monkeypatch):
    """A null-window probe may only establish a bound, never a new beta.

    After the first root move establishes alpha, a later PVS move is first
    searched with (-alpha-1, -alpha). If that probe improves alpha, the
    second search must use the node's complete current window (-beta, -alpha).
    Using (-beta, -probe_score) incorrectly turns the probe's lower bound into
    a new beta and can cut off the true score before it is fully searched.
    """
    board = small_position()
    engine = SearchEngine(
        depth=2,
        iterative_deepening=False,
        use_alpha_beta=True,
        use_pvs=True,
        use_transposition_table=False,
        use_quiescence=False,
    )

    calls = []

    def fake_negamax(board, depth, alpha, beta, current_color, root_depth,
                     use_pruning, stop_event=None):
        calls.append((depth, alpha, beta, current_color))

        # Root move #1: establish alpha = 10.
        if len(calls) == 1:
            return -10

        # Root move #2 null-window probe: its true score is known only to
        # exceed alpha. Returning 11 deliberately makes the probe score
        # differ from alpha, exposing implementations that use -score as
        # the full re-search beta.
        return -11

    monkeypatch.setattr(engine, "_negamax", fake_negamax)

    engine._search_fixed_depth(
        board,
        Color.RED,
        __import__("alphazetacchess.core.rule", fromlist=["Rule"]).Rule.generate_legal_moves(board, Color.RED),
        2,
    )

    assert len(calls) >= 3

    # Calls 1 and 2 are the first move's full search and the second move's
    # null-window probe. Call 3 is the mandatory full-window re-search.
    _, probe_alpha, probe_beta, _ = calls[1]
    _, full_alpha, full_beta, _ = calls[2]

    assert probe_alpha == -11
    assert probe_beta == -10
    assert full_alpha == float("-inf")
    assert full_beta == -10
