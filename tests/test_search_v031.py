from alphazetacchess.core.board import Board
from alphazetacchess.core.piece import Color
from alphazetacchess.engine.search import SearchEngine


def _move_signature(move):
    return (move.from_pos, move.to_pos)


def test_iterative_deepening_reaches_requested_depth():
    result = SearchEngine(depth=2).choose_move(Board(), Color.RED)

    assert result.best_move is not None
    assert result.depth == 2
    assert result.nodes_evaluated > 0


def test_iterative_deepening_matches_fixed_depth():
    board = Board()

    iterative = SearchEngine(
        depth=2,
        iterative_deepening=True,
    )
    fixed = SearchEngine(
        depth=2,
        iterative_deepening=False,
    )

    iterative_result = iterative.choose_move(board, Color.RED)
    fixed_result = fixed.choose_move(board, Color.RED)

    # Both searches must reach the same minimax value.
    assert iterative_result.score == fixed_result.score

    # Move objects are currently compared by identity rather than by
    # from/to coordinates, so compare their actual chess moves.
    assert _move_signature(iterative_result.best_move) ==         _move_signature(fixed_result.best_move)


def test_root_move_ordering_prefers_previous_best_move():
    board = Board()
    engine = SearchEngine(depth=1)

    from alphazetacchess.core.rule import Rule

    moves = Rule.generate_legal_moves(board, Color.RED)
    preferred = moves[-1]

    ordered = engine._order_root_moves(moves, preferred)

    assert ordered[0] is preferred


def test_mate_score_ply_offset_uses_current_iteration_depth():
    # Regression test: _terminal_score's ply-from-root offset must be
    # computed relative to the CURRENT search call's max depth, not
    # the engine's final requested self.depth. Before the fix, an
    # early iterative-deepening iteration (small root_depth) run
    # inside a search configured for a much larger self.depth would
    # compute an inflated ply offset and return a mate score far
    # below MATE_SCORE even for an immediate (ply=1) mate -- even
    # though the position is only one ply deep in that iteration's
    # own tree.
    #
    # Position notes (see tests/test_search_v033.py for the full
    # writeup of this pitfall): the Red king must NOT share a file
    # with the Black king here, and Black needs a piece (the Rook)
    # whose mobility does not depend on the Black elephant -- both
    # avoid Black being accidentally already stalemated on move 0
    # (which would make this test pass vacuously for any Red move,
    # not specifically for finding the intended mate).
    from alphazetacchess.core.piece import Piece, PieceType
    from alphazetacchess.engine.search import MATE_SCORE

    board = Board()
    board.board = [[None for _ in range(Board.WIDTH)] for _ in range(Board.HEIGHT)]
    board._place(Piece(PieceType.KING, Color.BLACK, 4, 9))
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 3, 9))
    board._place(Piece(PieceType.ADVISOR, Color.BLACK, 5, 9))
    board._place(Piece(PieceType.ELEPHANT, Color.BLACK, 4, 8))
    board._place(Piece(PieceType.ROOK, Color.BLACK, 0, 9))  # unrelated mobility
    board._place(Piece(PieceType.HORSE, Color.RED, 6, 5))  # one move from mate
    board._place(Piece(PieceType.KING, Color.RED, 3, 0))  # off Black's file
    from alphazetacchess.core.zobrist import Zobrist
    board.zobrist_hash = Zobrist.board_hash(board)

    # Sanity check on the fixture itself.
    assert len(_legal_moves(board, Color.BLACK)) > 0

    # Configure the engine for a much larger final depth than the
    # single ply actually needed to search this position.
    engine = SearchEngine(depth=5, iterative_deepening=False)

    # Directly exercise a depth-1 (single ply) search, as an early
    # iterative-deepening iteration would perform internally.
    result = engine._search_fixed_depth(
        board, Color.RED, [m for m in _legal_moves(board, Color.RED)], depth=1
    )

    # It must actually be the real mating move, not merely a high
    # score reached some other way.
    assert result.best_move.from_pos == (6, 5)
    assert result.best_move.to_pos == (5, 7)

    # A mate delivered on the very first ply should score almost
    # exactly MATE_SCORE, regardless of what self.depth was configured
    # to (here, 5) -- not MATE_SCORE offset by (self.depth - 0) = 5.
    assert result.score > MATE_SCORE - 5


def _legal_moves(board, color):
    from alphazetacchess.core.rule import Rule
    return Rule.generate_legal_moves(board, color)
