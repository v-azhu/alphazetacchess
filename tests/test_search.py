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
    # This is the STRICT, mathematically-guaranteed property of plain
    # Alpha-Beta pruning (PVS explicitly disabled here): it always
    # visits at most as many nodes as an exhaustive Negamax search,
    # on every position and every depth, because Alpha-Beta only ever
    # skips subtrees that provably cannot affect the result.
    #
    # PVS's node count is NOT covered by this guarantee -- its null-
    # window "probe, then maybe re-search" pattern can cost more
    # nodes than plain Alpha-Beta at shallow depths where there is
    # little subtree left to prune, and only reliably pays off once
    # there is enough depth for tighter windows to cut real work.
    # See test_search_v033.py for PVS's own correctness gate (score
    # and best move must match with PVS on or off) and
    # docs/roadmap.md V0.3.3 for the measured node-count comparison
    # across PVS on/off at several depths.
    for depth in (1, 2, 3):
        board = small_midgame_position()

        minimax = SearchEngine(depth=depth, use_alpha_beta=False)
        alphabeta = SearchEngine(depth=depth, use_alpha_beta=True, use_pvs=False)

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
    #
    # Position notes -- this test went through several broken drafts
    # before landing here, each bitten by the same class of mistake,
    # which is worth spelling out so it isn't repeated a fourth time:
    #
    # 1. Both kings default to file 4 (their real starting squares).
    #    In a full game that file is blocked by the central pawns; in
    #    a hand-built minimal position it usually is NOT, so the two
    #    bare kings end up "flying general" (illegally facing each
    #    other) or, just as commonly, ARE facing each other and the
    #    position is treated as Red already being in check from move
    #    zero -- silently turning "pick your best move" into "resolve
    #    this check", which is a completely different (and much more
    #    constrained) question. Kings here are deliberately on
    #    different files to sidestep this entirely.
    # 2. A bare king (no advisors/elephants) is extremely fragile: with
    #    only two rooks and two naked kings on the board, nearly every
    #    king move in this exact family of positions walks into a real
    #    forced mate a couple of plies deeper (this is a genuine
    #    tactic, not a bug -- confirmed by hand-playing it out). A
    #    search strong enough to see that (which Quiescence Search now
    #    is) will correctly avoid those moves for a real reason, which
    #    defeats the point of a test about a simple hanging piece. Both
    #    kings get their normal advisor + elephant screen here so that
    #    king safety is a non-issue and material is the only thing
    #    actually being decided.
    board = empty_board()
    board._place(Piece(PieceType.KING, Color.RED, 4, 0))
    board._place(Piece(PieceType.ADVISOR, Color.RED, 3, 0))
    board._place(Piece(PieceType.ADVISOR, Color.RED, 5, 0))
    board._place(Piece(PieceType.ELEPHANT, Color.RED, 2, 0))
    board._place(Piece(PieceType.ELEPHANT, Color.RED, 6, 2))
    board._place(Piece(PieceType.ROOK, Color.RED, 0, 5))

    board._place(Piece(PieceType.KING, Color.BLACK, 3, 9))  # different file from Red's king
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 4, 8))
    board._place(Piece(PieceType.ELEPHANT, Color.BLACK, 2, 9))
    board._place(Piece(PieceType.ELEPHANT, Color.BLACK, 6, 7))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 2, 8))  # guards files 2 and rank 8

    from alphazetacchess.core.rule import Rule
    assert not Rule.is_in_check(board, Color.RED)  # fixture sanity check

    engine = SearchEngine(depth=2)
    result = engine.choose_move(board, Color.RED)

    # (3, 5) is a fully safe retreat square (off both the black
    # rook's file and its rank); every alternative either hangs the
    # rook outright or is simply worse.
    assert result.best_move.from_pos == (0, 5)
    assert result.best_move.to_pos == (3, 5)
