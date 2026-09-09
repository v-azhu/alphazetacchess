from threading import Event

from ..core.rule import Rule
from .base import ChessEngine, SearchResult
from .evaluation import evaluate
from .transposition_table import Bound, TranspositionTable
from ..selfplay.opening_book import select_book_move


MATE_SCORE = 100000


class SearchCancelled(Exception):
    """Internal signal used to unwind an interrupted search safely."""


class SearchEngine(ChessEngine):
    """V0.4.2 Negamax + PVS + Quiescence search with iterative deepening and TT.

    V0.3.3 refactored V0.3.2's separate maximizing/minimizing Alpha-Beta
    branches into a single Negamax recursion (valid because Xiangqi is
    a two-player zero-sum game: what is good for one side is exactly
    as bad for the other, so `value(node, color) == -value(node,
    opponent)`). Principal Variation Search (PVS) is layered on top:
    after the first (best-ordered) move at a node, every later move is
    first probed with a cheap null window (`alpha, alpha+1`) and only
    re-searched with the full window if that probe suggests it might
    actually beat the current best -- this prunes more aggressively
    when move ordering is good, without changing the result.

    V0.3.4 adds Quiescence Search at the leaves: instead of statically
    evaluating a position the instant the nominal search depth runs
    out, `_quiescence` keeps searching -- but only "noisy" moves
    (captures, and every legal move while in check) -- until a quiet
    position is reached. This closes the classic horizon effect, where
    a fixed-depth search stops right after a capture that looks like a
    material win without seeing the recapture that actually loses it.
    See `docs/v0.3.4.md` for the full design and measured benchmark.

    A side effect of the Negamax refactor: because every node's score
    is now naturally expressed "from the mover's own point of view"
    (rather than "from the root player's point of view", which the
    old maximizing/minimizing code needed to track separately), the
    transposition table key no longer needs to include the root
    color -- Board.zobrist_hash alone identifies the position, which
    also makes TT entries reusable across searches with different
    root colors, and across the main search and quiescence search.

    V0.4.1 adds Piece-Square Tables to the evaluation function used at
    every leaf (both the plain V0.2-style leaf and inside quiescence):
    a per-square positional bonus for Horse/Cannon/Rook/Pawn, on top
    of the existing material value. Controlled by
    `use_piece_square_tables` (default True); set to False to fall
    back to the exact V0.2/V0.3 evaluation for A/B comparison. See
    `docs/v0.4.1.md` for the rationale behind each table and the
    measured playing-strength benchmark.

    V0.4.2 adds King Safety: a Guard Integrity term (a bonus for each
    surviving Advisor/Elephant of a king's own color) and an Open-File
    Exposure term (a penalty when a clear file runs straight from a
    king to an enemy Rook or Cannon). Controlled by `use_king_safety`
    (default True), independently of `use_piece_square_tables`, so
    each V0.4.x evaluation layer stays separately A/B-comparable. See
    `docs/v0.4.2.md`.
    """

    def __init__(
        self,
        depth=3,
        use_alpha_beta=True,
        iterative_deepening=True,
        use_transposition_table=True,
        use_pvs=True,
        use_quiescence=True,
        quiescence_max_ply=8,
        use_piece_square_tables=True,
        use_king_safety=True,
        use_mobility=False,
        mobility_weight=1,
        use_pawn_structure=False,
        use_piece_coordination=False,
        use_endgame_heuristics=False,
        use_opening_book=False,
        opening_book=None,
        opening_book_min_games=3,
        tt_max_entries=200_000,
        eval_fn=None,
        material_values=None,
    ):
        self.depth = depth
        self.use_alpha_beta = use_alpha_beta
        self.iterative_deepening = iterative_deepening
        self.use_transposition_table = use_transposition_table
        self.use_pvs = use_pvs
        self.use_quiescence = use_quiescence
        self.quiescence_max_ply = quiescence_max_ply
        self.use_piece_square_tables = use_piece_square_tables
        self.use_king_safety = use_king_safety
        self.use_mobility = use_mobility
        self.mobility_weight = mobility_weight
        self.use_pawn_structure = use_pawn_structure
        self.use_piece_coordination = use_piece_coordination
        self.use_endgame_heuristics = use_endgame_heuristics
        self.use_opening_book = use_opening_book
        self.opening_book = opening_book
        self.opening_book_min_games = opening_book_min_games
        self.eval_fn = eval_fn
        self.material_values = material_values
        self.nodes_evaluated = 0
        self.tt = TranspositionTable(tt_max_entries)
        self._stop_event = Event()

    def request_stop(self):
        """Request cooperative cancellation of the current search."""
        self._stop_event.set()

    def clear_stop(self):
        """Clear a previously requested search cancellation."""
        self._stop_event.clear()

    @staticmethod
    def _check_stop(stop_event):
        if stop_event is not None and stop_event.is_set():
            raise SearchCancelled

    def _evaluate(self, board, color):
        """Evaluate a position through the configured evaluator."""
        if self.eval_fn is not None:
            return self.eval_fn(board, color)

        return evaluate(
            board, color,
            use_piece_square_tables=self.use_piece_square_tables,
            use_king_safety=self.use_king_safety,
            use_mobility=self.use_mobility,
            mobility_weight=self.mobility_weight,
            use_pawn_structure=self.use_pawn_structure,
            use_piece_coordination=self.use_piece_coordination,
            use_endgame_heuristics=self.use_endgame_heuristics,
            material_values=self.material_values,
        )

    def choose_move(self, board, color, stop_event=None):
        """Search for a move, optionally using an external cancellation event.

        The external event is intentionally not cleared here: its owner
        controls the lifetime of that event. When no external event is
        supplied, the engine-owned event is cleared at the start of a new
        search and can be triggered through `request_stop()`.

        With iterative deepening enabled, cancellation discards only the
        currently incomplete iteration and returns the last fully completed
        result. If cancellation arrives before depth 1 completes, the first
        legal move is returned as a safe fallback with depth 0.
        """
        if stop_event is None:
            self.clear_stop()
            stop_event = self._stop_event

        self.nodes_evaluated = 0
        self.tt.reset_stats()
        self._check_stop(stop_event)

        if self.use_opening_book and self.opening_book:
            book_move = self._book_move(board, color)
            if book_move is not None:
                return book_move

        legal_moves = Rule.generate_legal_moves(board, color)
        self._check_stop(stop_event)

        if not legal_moves:
            return SearchResult(
                None,
                self._evaluate(board, color),
                self.nodes_evaluated,
                self.depth,
            )

        if not self.iterative_deepening:
            try:
                return self._search_fixed_depth(
                    board, color, legal_moves, self.depth, stop_event
                )
            except SearchCancelled:
                return SearchResult(
                    legal_moves[0],
                    self._evaluate(board, color),
                    self.nodes_evaluated,
                    0,
                )

        best_result = None
        root_moves = list(legal_moves)

        for current_depth in range(1, self.depth + 1):
            try:
                result = self._search_fixed_depth(
                    board,
                    color,
                    root_moves,
                    current_depth,
                    stop_event,
                )
            except SearchCancelled:
                break

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

        if best_result is not None:
            return best_result

        return SearchResult(
            root_moves[0],
            self._evaluate(board, color),
            self.nodes_evaluated,
            0,
        )

    def _book_move(self, board, color):
        """Return a validated opening-book move, or None."""
        book_move = select_book_move(
            self.opening_book, board, color, min_games=self.opening_book_min_games
        )
        if book_move is None:
            return None

        from_pos, to_pos = book_move
        legal_moves = Rule.generate_legal_moves(board, color)
        matching = next(
            (m for m in legal_moves if m.from_pos == from_pos and m.to_pos == to_pos),
            None,
        )
        if matching is None:
            return None

        return SearchResult(matching, None, 0, 0, from_book=True)

    def _search_fixed_depth(self, board, color, legal_moves, depth, stop_event=None):
        root_moves = self._order_root_moves(legal_moves, None)

        best_move = None
        best_score = float("-inf")
        alpha, beta = float("-inf"), float("inf")
        opponent = board.opponent(color)

        for index, move in enumerate(root_moves):
            self._check_stop(stop_event)
            board.move(move.from_pos, move.to_pos)
            try:
                if self.use_alpha_beta and self.use_pvs and index > 0:
                    score = -self._negamax(
                        board, depth - 1, -alpha - 1, -alpha, opponent, depth,
                        use_pruning=True, stop_event=stop_event,
                    )
                    if alpha < score < beta:
                        score = -self._negamax(
                            board, depth - 1, -beta, -score, opponent, depth,
                            use_pruning=True, stop_event=stop_event,
                        )
                else:
                    score = -self._negamax(
                        board, depth - 1, -beta, -alpha, opponent, depth,
                        use_pruning=self.use_alpha_beta, stop_event=stop_event,
                    )
            finally:
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

        preferred = (preferred_move.from_pos, preferred_move.to_pos)

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
        stop_event=None,
    ):
        """Return the minimax value from `current_color`'s own point of view."""
        self._check_stop(stop_event)
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
            score = -(MATE_SCORE - (root_depth - depth))
            if self.use_transposition_table:
                self.tt.store(key, depth, score, Bound.EXACT, None)
            return score

        if depth == 0:
            if self.use_quiescence:
                score = self._quiescence(
                    board, alpha, beta, current_color, root_depth, 0, stop_event
                )
            else:
                score = self._evaluate(board, current_color)
                if self.use_transposition_table:
                    self.tt.store(key, depth, score, Bound.EXACT, None)
            return score

        legal_moves = self._order_moves(legal_moves, preferred_move)

        best_score = float("-inf")
        best_move = None
        opponent = board.opponent(current_color)

        for index, move in enumerate(legal_moves):
            self._check_stop(stop_event)
            board.move(move.from_pos, move.to_pos)
            try:
                if use_pruning and self.use_pvs and index > 0:
                    score = -self._negamax(
                        board, depth - 1, -alpha - 1, -alpha, opponent,
                        root_depth, use_pruning, stop_event,
                    )
                    if alpha < score < beta:
                        score = -self._negamax(
                            board, depth - 1, -beta, -score, opponent,
                            root_depth, use_pruning, stop_event,
                        )
                else:
                    score = -self._negamax(
                        board, depth - 1, -beta, -alpha, opponent,
                        root_depth, use_pruning, stop_event,
                    )
            finally:
                board.undo()

            if score > best_score:
                best_score = score
                best_move = move

            if use_pruning:
                alpha = max(alpha, best_score)
                if alpha >= beta:
                    break

        if self.use_transposition_table:
            if best_score <= alpha_original:
                bound = Bound.UPPER
            elif best_score >= beta:
                bound = Bound.LOWER
            else:
                bound = Bound.EXACT

            self.tt.store(key, depth, best_score, bound, best_move)

        return best_score

    def _quiescence(self, board, alpha, beta, color, root_depth, qply, stop_event=None):
        """Extend the search along captures and forced check evasions."""
        self._check_stop(stop_event)
        self.nodes_evaluated += 1

        key = board.zobrist_hash
        alpha_original = alpha

        if self.use_transposition_table:
            cached_score, _ = self.tt.probe(key, 0, alpha, beta)
            if cached_score is not None:
                return cached_score

        legal_moves = Rule.generate_legal_moves(board, color)

        if not legal_moves:
            score = -(MATE_SCORE - (root_depth + qply))
            if self.use_transposition_table:
                self.tt.store(key, 0, score, Bound.EXACT, None)
            return score

        if qply >= self.quiescence_max_ply:
            return self._evaluate(board, color)

        in_check = Rule.is_in_check(board, color)

        if in_check:
            candidates = legal_moves
            best_score = float("-inf")
        else:
            stand_pat = self._evaluate(board, color)

            if stand_pat >= beta:
                if self.use_transposition_table:
                    self.tt.store(key, 0, stand_pat, Bound.LOWER, None)
                return stand_pat

            alpha = max(alpha, stand_pat)
            best_score = stand_pat

            candidates = [
                move for move in legal_moves if move.captured_piece is not None
            ]

            if not candidates:
                if self.use_transposition_table:
                    self.tt.store(key, 0, stand_pat, Bound.EXACT, None)
                return stand_pat

        opponent = board.opponent(color)

        for move in candidates:
            self._check_stop(stop_event)
            board.move(move.from_pos, move.to_pos)
            try:
                score = -self._quiescence(
                    board, -beta, -alpha, opponent, root_depth, qply + 1, stop_event
                )
            finally:
                board.undo()

            if score > best_score:
                best_score = score

            alpha = max(alpha, score)
            if alpha >= beta:
                break

        if self.use_transposition_table:
            if best_score <= alpha_original:
                bound = Bound.UPPER
            elif best_score >= beta:
                bound = Bound.LOWER
            else:
                bound = Bound.EXACT

            self.tt.store(key, 0, best_score, bound, None)

        return best_score
