"""
V0.3.3 correctness gates: Negamax refactor + Principal Variation Search.

Per docs/roadmap.md V0.3.3, this refactor must be score/move-identical
to V0.3.2's Alpha-Beta on every position -- Negamax and PVS restructure
*how* the search is carried out, not *what* result it computes.
"""

from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Piece, PieceType, Color
from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.search import SearchEngine


def _move_signature(move):
    if move is None:
        return None
    return move.from_pos, move.to_pos


def empty_board():
    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    from alphazetacchess.core.zobrist import Zobrist
    board.zobrist_hash = Zobrist.board_hash(board)
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
    from alphazetacchess.core.zobrist import Zobrist
    board.zobrist_hash = Zobrist.board_hash(board)
    return board


def test_pvs_matches_plain_alpha_beta_on_initial_position():
    for depth in (1, 2, 3):
        board = Board()

        no_pvs = SearchEngine(depth=depth, use_pvs=False)
        with_pvs = SearchEngine(depth=depth, use_pvs=True)

        a = no_pvs.choose_move(board, Color.RED)
        b = with_pvs.choose_move(board, Color.RED)

        assert a.score == b.score
        assert _move_signature(a.best_move) == _move_signature(b.best_move)


def test_pvs_matches_plain_alpha_beta_on_midgame_position():
    for depth in (1, 2, 3):
        board = small_midgame_position()

        no_pvs = SearchEngine(depth=depth, use_pvs=False)
        with_pvs = SearchEngine(depth=depth, use_pvs=True)

        a = no_pvs.choose_move(board, Color.RED)
        b = with_pvs.choose_move(board, Color.RED)

        assert a.score == b.score
        assert _move_signature(a.best_move) == _move_signature(b.best_move)


def test_pvs_benefit_grows_with_depth():
    # PVS's null-window "probe, then maybe re-search" pattern has real
    # overhead: at shallow depth (little subtree left to prune), it can
    # visit slightly MORE nodes than plain Alpha-Beta. Its benefit is
    # expected to show up as depth increases and move ordering has more
    # opportunity to pay off. This test locks in that qualitative shape
    # rather than a specific node count (which is position-dependent).
    board = small_midgame_position()

    shallow_ratio = _pvs_node_ratio(board, depth=1)
    deep_ratio = _pvs_node_ratio(board, depth=3)

    # At depth 3, PVS should be doing at least as well relative to
    # plain Alpha-Beta as it was at depth 1 (i.e. its relative
    # overhead should not be growing with depth).
    assert deep_ratio <= shallow_ratio


def _pvs_node_ratio(board, depth):
    no_pvs = SearchEngine(depth=depth, use_pvs=False)
    with_pvs = SearchEngine(depth=depth, use_pvs=True)

    a = no_pvs.choose_move(board, Color.RED)
    b = with_pvs.choose_move(board, Color.RED)

    return b.nodes_evaluated / a.nodes_evaluated


def test_negamax_terminal_scoring_matches_checkmate_detection():
    # Regression check that the Negamax refactor still agrees with
    # Rule.is_checkmate on a constructed forced-mate position (same
    # position as tests/test_rule.py::test_horse_delivers_checkmate,
    # one ply earlier so Red must find the mating move).
    #
    # Two position-construction pitfalls to avoid here (both bit an
    # earlier draft of this test):
    #
    # 1. The Red and Black kings must NOT sit on the same file. Even
    #    with the Black elephant blocking that file, any Red king
    #    move that lands back on Black's file would (if the elephant
    #    ever moved) expose "flying general" -- which pins the
    #    elephant in place via the normal check-legality filter. Since
    #    Black's king/advisors are already fully boxed in by their own
    #    pieces here, an accidentally-pinned elephant leaves Black with
    #    ZERO legal moves regardless of what Red plays, which competes
    #    with (and can numerically tie) the intended mate-in-1 and
    #    make the test pass or fail depending on move-ordering
    #    coincidence rather than on the actual tactic.
    # 2. Black needs at least one piece whose mobility is completely
    #    unrelated to the mating tactic (the Rook here), so that
    #    "Black has zero legal moves" can only mean the real
    #    checkmate, not an accidental full-board paralysis.
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 5, 9))
    board._place(Piece(PieceType.ELEPHANT, Color.BLACK, 4, 8))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 0, 9))  # unrelated mobility
    board._place(Piece(PieceType.HORSE, Color.RED, 6, 5))  # one move from mate
    board._place(Piece(PieceType.KING, Color.RED, 3, 0))  # off Black's file
    from alphazetacchess.core.zobrist import Zobrist
    board.zobrist_hash = Zobrist.board_hash(board)

    # Sanity check on the fixture itself: Black must have genuine
    # mobility before Red moves, or this isn't testing anything.
    assert len(Rule.generate_legal_moves(board, Color.BLACK)) > 0

    engine = SearchEngine(depth=2)
    result = engine.choose_move(board, Color.RED)

    assert result.best_move.from_pos == (6, 5)
    assert result.best_move.to_pos == (5, 7)

    board.move(result.best_move.from_pos, result.best_move.to_pos)
    assert Rule.is_checkmate(board, Color.BLACK)
