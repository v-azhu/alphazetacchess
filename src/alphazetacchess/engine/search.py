from ..core.rule import Rule
from .base import ChessEngine, SearchResult
from .evaluation import evaluate
from .transposition_table import Bound, TranspositionTable


MATE_SCORE = 100000


class SearchEngine(ChessEngine):
    """V0.3.3 Negamax + PVS search with iterative deepening and TT.

    V0.3.3 refactors V0.3.2's separate maximizing/minimizing Alpha-Beta
    branches into a single Negamax recursion (valid because Xiangqi is
    a two-player zero-sum game: what is good for one side is exactly
    as bad for the other, so `value(node, color) == -value(node,
    opponent)`). Principal Variation Search (PVS) is then layered on
    top: after the first (best-ordered) move at a node, every later
    move is first probed with a cheap null window (`alpha, alpha+1`)
    and only re-searched with the full window if that probe suggests
    it might actually beat the current best -- this prunes more
    aggressively when move ordering is good, without changing the
    result.

    This refactor must be score/move-identical to V0.3.2's Alpha-Beta
    on every position -- Negamax and PVS are restructurings of the
    same search, not a different evaluation. See
    tests/test_search_v033.py for the correctness gate, and
    docs/roadmap.md V0.3.3 for the measured benchmark.

    A side effect of the Negamax refactor: because every node's score
    is now naturally expressed "from the mover's own point of view"
    (rather than "from the root player's point of view", which the
    old maximizing/minimizing code needed to track separately), the
    transposition table key no longer needs to include the root
    color -- Board.zobrist_hash alone identifies the position, which
    also makes TT entries reusable across searches with different
    root colors.
    """

    def __init__(
        self,
        depth=3,
        use_alpha_beta=True,
        iterative_deepening=True,
        use_transposition_table=True,
        use_pvs=True,
        tt_max_entries=200_000,
    ):
        self.depth = depth
        self.use_alpha_beta = use_alpha_beta
        self.iterative_deepening = iterative_deepening
        self.use_transposition_table = use_transposition_table
        # PVS only makes sense on top of Alpha-Beta pruning; it is
        # automatically disabled whenever use_alpha_beta is False (see
        # _negamax), so the flag only matters when both are True.
        self.use_pvs = use_pvs
        self.nodes_evaluated = 0
        self.tt = TranspositionTable(tt_max_entries)

    def choose_move(self, board, color):
        self.nodes_evaluated = 0
        self.tt.reset_stats()

        legal_moves = Rule.generate_legal_moves(board, color)
        if not legal_moves:
            return SearchResult(
                None,
                evaluate(board, color),
                self.nodes_evaluated,
                self.depth,
            )

        if not self.iterative_deepening:
            return self._search_fixed_depth(
                board, color, legal_moves, self.depth
            )

        best_result = None
        root_moves = list(legal_moves)

        for current_depth in range(1, self.depth + 1):
            result = self._search_fixed_depth(
                board,
                color,
                root_moves,
                current_depth,
            )
            best_result = SearchResult(
                result.best_move,
                result.score,
                self.nodes_evaluated,
                current_depth,
            )

            if best_result.best_move is not None:
                root_moves = self._order_root_moves(
                    root_moves,
                    best_result.best_move,
                )

        return best_result

    def _search_fixed_depth(self, board, color, legal_moves, depth):
        root_moves = self._order_root_moves(legal_moves, None)

        best_move = None
        best_score = float("-inf")
        alpha, beta = float("-inf"), float("inf")
        opponent = board.opponent(color)

        for index, move in enumerate(root_moves):
            board.move(move.from_pos, move.to_pos)

            if self.use_alpha_beta and self.use_pvs and index > 0:
                # Same PVS pattern as _negamax's own move loop (see its
                # docstring): the root's first (best-ordered) move gets
                # the full window; every later root move is first
                # probed with a null window and only re-searched with
                # the full window if the probe suggests it might
                # actually be better.
                score = -self._negamax(
                    board, depth - 1, -alpha - 1, -alpha, opponent, depth,
                    use_pruning=True,
                )
                if alpha < score < beta:
                    score = -self._negamax(
                        board, depth - 1, -beta, -score, opponent, depth,
                        use_pruning=True,
                    )
            else:
                score = -self._negamax(
                    board, depth - 1, -beta, -alpha, opponent, depth,
                    use_pruning=self.use_alpha_beta,
                )

            board.undo()

            if score > best_score:
                best_score = score
                best_move = move

            if self.use_alpha_beta:
                alpha = max(alpha, best_score)

        return SearchResult(best_move, best_score, self.nodes_evaluated, depth)

    @staticmethod
    def _order_root_moves(moves, preferred_move):
        ordered = list(moves)
        if preferred_move is None:
            return ordered

        preferred = (
            preferred_move.from_pos,
            preferred_move.to_pos,
        )

        for index, move in enumerate(ordered):
            if (move.from_pos, move.to_pos) == preferred:
                return [move] + ordered[:index] + ordered[index + 1:]

        return ordered

    @staticmethod
    def _order_moves(moves, preferred_move):
        if preferred_move is None:
            return list(moves)

        preferred = (preferred_move[0], preferred_move[1])

        for index, move in enumerate(moves):
            if (move.from_pos, move.to_pos) == preferred:
                return [move] + list(moves[:index]) + list(moves[index + 1:])

        return list(moves)

    def _negamax(
        self,
        board,
        depth,
        alpha,
        beta,
        current_color,
        root_depth,
        use_pruning,
    ):
        """
        Return the minimax value of `board` from `current_color`'s own
        point of view (Negamax convention): positive means good for
        `current_color`, negative means good for the opponent.

        `use_pruning=False` reproduces a plain, exhaustive Negamax
        search (still returns the exact minimax value, just without
        Alpha-Beta cutoffs or PVS) -- this is the correctness baseline
        used by test_search.py's minimax-vs-alpha-beta comparison.
        """
        self.nodes_evaluated += 1

        alpha_original = alpha
        key = board.zobrist_hash
        preferred_move = None

        if self.use_transposition_table:
            cached_score, preferred_move = self.tt.probe(key, depth, alpha, beta)
            if cached_score is not None and use_pruning:
                return cached_score

        legal_moves = Rule.generate_legal_moves(board, current_color)

        if not legal_moves:
            # No legal moves is always a loss for `current_color` in
            # Xiangqi (checkmate and stalemate score identically --
            # see Rule's module docstring). `root_depth` is THIS
            # search call's own max depth (not self.depth), so the
            # ply-from-root offset stays correct across iterative
            # deepening's shallower iterations too.
            score = -(MATE_SCORE - (root_depth - depth))
            if self.use_transposition_table:
                self.tt.store(key, depth, score, Bound.EXACT, None)
            return score

        if depth == 0:
            score = evaluate(board, current_color)
            if self.use_transposition_table:
                self.tt.store(key, depth, score, Bound.EXACT, None)
            return score

        legal_moves = self._order_moves(legal_moves, preferred_move)

        best_score = float("-inf")
        best_move = None
        opponent = board.opponent(current_color)

        for index, move in enumerate(legal_moves):
            board.move(move.from_pos, move.to_pos)

            if use_pruning and self.use_pvs and index > 0:
                # Null-window probe: cheaply check whether this move
                # could beat what we already have.
                score = -self._negamax(
                    board, depth - 1, -alpha - 1, -alpha, opponent,
                    root_depth, use_pruning,
                )
                if alpha < score < beta:
                    # It might really be better than our current best
                    # -- re-search with the full window for an exact
                    # value. (Standard PVS re-search.)
                    score = -self._negamax(
                        board, depth - 1, -beta, -score, opponent,
                        root_depth, use_pruning,
                    )
            else:
                score = -self._negamax(
                    board, depth - 1, -beta, -alpha, opponent,
                    root_depth, use_pruning,
                )

            board.undo()

            if score > best_score:
                best_score = score
                best_move = move

            if use_pruning:
                alpha = max(alpha, best_score)
                if alpha >= beta:
                    break  # Beta cutoff.

        if self.use_transposition_table:
            if best_score <= alpha_original:
                bound = Bound.UPPER
            elif best_score >= beta:
                bound = Bound.LOWER
            else:
                bound = Bound.EXACT

            self.tt.store(key, depth, best_score, bound, best_move)

        return best_score
