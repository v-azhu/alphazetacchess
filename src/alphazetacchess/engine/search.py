from ..core.rule import Rule
from .base import ChessEngine, SearchResult
from .evaluation import evaluate
from .transposition_table import Bound, TranspositionTable
from ..selfplay.opening_book import select_book_move


MATE_SCORE = 100000


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
    ):
        self.depth = depth
        self.use_alpha_beta = use_alpha_beta
        self.iterative_deepening = iterative_deepening
        self.use_transposition_table = use_transposition_table
        # PVS only makes sense on top of Alpha-Beta pruning; it is
        # automatically disabled whenever use_alpha_beta is False (see
        # _negamax), so the flag only matters when both are True.
        self.use_pvs = use_pvs
        # Quiescence search extends the leaves regardless of
        # use_alpha_beta/use_pvs (it is not a pruning trick, it
        # changes what is being evaluated at the horizon), so both the
        # pruned and unpruned Negamax paths apply it identically --
        # this keeps them comparable for correctness testing.
        self.use_quiescence = use_quiescence
        # Hard safety cap on quiescence recursion depth, to guarantee
        # termination even for a pathologically long forced-capture or
        # forced-check sequence. See _quiescence's docstring.
        self.quiescence_max_ply = quiescence_max_ply
        # V0.4.1: piece-square tables in the evaluation function. Kept
        # toggleable so the current material+mobility baseline (V0.2/
        # V0.3) stays available as the A/B comparison point -- see
        # docs/v0.4.1.md.
        self.use_piece_square_tables = use_piece_square_tables
        # V0.4.2: king safety (guard integrity + open-file exposure)
        # in the evaluation function. Independently toggleable from
        # use_piece_square_tables so each V0.4.x evaluation layer
        # stays separately A/B-comparable -- see docs/v0.4.2.md.
        self.use_king_safety = use_king_safety
        # V0.4.3: optional Mobility evaluation term.
        # Disabled by default to preserve the V0.4.2 baseline.
        self.use_mobility = use_mobility
        self.mobility_weight = mobility_weight
        # V0.4.4: optional Pawn Structure (Connected Pawns) evaluation
        # term. Also disabled by default, same reasoning.
        self.use_pawn_structure = use_pawn_structure
        # V0.4.5: optional Piece Coordination (Doubled Rooks, Rook-
        # Cannon Battery) evaluation term. Also disabled by default,
        # same reasoning.
        self.use_piece_coordination = use_piece_coordination
        # V0.5.3: optional endgame-phase heuristics (Rook/Cannon value
        # shift once major material is low -- see engine/endgame.py).
        # Also disabled by default, same reasoning as every other
        # V0.4.x/V0.5.x evaluation term.
        self.use_endgame_heuristics = use_endgame_heuristics
        # V0.5.2: optional opening book, built from V0.5.1 self-play
        # records (see selfplay/opening_book.py). `opening_book` is
        # the loaded book dict (selfplay.opening_book.load_book(path)),
        # not a path -- SearchEngine doesn't do file I/O itself, so the
        # same loaded book can be reused across many SearchEngine
        # instances without re-reading it from disk each time.
        self.use_opening_book = use_opening_book
        self.opening_book = opening_book
        self.opening_book_min_games = opening_book_min_games
        self.nodes_evaluated = 0
        self.tt = TranspositionTable(tt_max_entries)

    def choose_move(self, board, color):
        self.nodes_evaluated = 0
        self.tt.reset_stats()

        if self.use_opening_book and self.opening_book:
            book_move = self._book_move(board, color)
            if book_move is not None:
                return book_move

        legal_moves = Rule.generate_legal_moves(board, color)
        if not legal_moves:
            return SearchResult(
                None,
                evaluate(
                    board, color,
                    use_piece_square_tables=self.use_piece_square_tables,
                    use_king_safety=self.use_king_safety,
                    use_mobility=self.use_mobility,
                    mobility_weight=self.mobility_weight,
                    use_pawn_structure=self.use_pawn_structure,
                    use_piece_coordination=self.use_piece_coordination,
                    use_endgame_heuristics=self.use_endgame_heuristics,
                ),
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

    def _book_move(self, board, color):
        """
        Return a SearchResult built from the opening book if a
        confident entry exists for this position, otherwise None (in
        which case choose_move falls through to normal search).

        Book entries are validated against the actual current legal
        moves before being trusted -- defensive against a book built
        against a different rule-engine version, or any other reason
        the recorded move might not be legal in the exact position
        it's being looked up in.
        """
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
            if self.use_quiescence:
                # _quiescence performs its own TT probe/store (always
                # at the depth=0 TT slot), so nothing more to do here.
                score = self._quiescence(
                    board, alpha, beta, current_color, root_depth, 0
                )
            else:
                score = evaluate(
                    board, current_color,
                    use_piece_square_tables=self.use_piece_square_tables,
                    use_king_safety=self.use_king_safety,
                    use_mobility=self.use_mobility,
                    mobility_weight=self.mobility_weight,
                    use_pawn_structure=self.use_pawn_structure,
                    use_piece_coordination=self.use_piece_coordination,
                    use_endgame_heuristics=self.use_endgame_heuristics,
                )
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

    def _quiescence(self, board, alpha, beta, color, root_depth, qply):
        """
        Extend the search past the nominal depth limit along "noisy"
        lines -- captures, and every legal move while in check -- until
        a quiet position is reached, to avoid the horizon effect (e.g.
        stopping the search right after a capture that looks like a
        material win, without seeing the recapture that actually loses
        material).

        Fail-soft Negamax convention, same as `_negamax`: returns the
        value from `color`'s own point of view.

        "Check extension": a position where `color` is in check can
        never be treated as quiet -- there is no stand-pat option, and
        every legal move is searched as a forced evasion, even though
        none of them may be captures. This is what forces the search
        to actually resolve a check sequence instead of stopping mid-way
        through it.
        """
        self.nodes_evaluated += 1

        key = board.zobrist_hash
        alpha_original = alpha

        if self.use_transposition_table:
            cached_score, _ = self.tt.probe(key, 0, alpha, beta)
            if cached_score is not None:
                return cached_score

        legal_moves = Rule.generate_legal_moves(board, color)

        if not legal_moves:
            # Checkmate or stalemate reached inside quiescence. Ply is
            # counted from the true root (root_depth, the nominal
            # search's own ply budget, plus qply, how far quiescence
            # has gone past it) so mate-distance scoring stays
            # meaningful even for mates found only via the capture/
            # check search.
            score = -(MATE_SCORE - (root_depth + qply))
            if self.use_transposition_table:
                self.tt.store(key, 0, score, Bound.EXACT, None)
            return score

        if qply >= self.quiescence_max_ply:
            # Hard safety backstop against a pathologically long
            # forced-capture or forced-check sequence. Deliberately
            # NOT cached: the TT key carries no notion of "how much
            # qsearch budget was left when this was computed", so a
            # later, differently-capped probe of the same position
            # could otherwise reuse a value that does not correspond
            # to its own context. See docs/v0.3.4.md.
            return evaluate(
                board, color,
                use_piece_square_tables=self.use_piece_square_tables,
                use_king_safety=self.use_king_safety,
                use_mobility=self.use_mobility,
                mobility_weight=self.mobility_weight,
                use_pawn_structure=self.use_pawn_structure,
                use_piece_coordination=self.use_piece_coordination,
                use_endgame_heuristics=self.use_endgame_heuristics,
            )

        in_check = Rule.is_in_check(board, color)

        if in_check:
            candidates = legal_moves
            best_score = float("-inf")
        else:
            stand_pat = evaluate(
                board, color,
                use_piece_square_tables=self.use_piece_square_tables,
                use_king_safety=self.use_king_safety,
                use_mobility=self.use_mobility,
                mobility_weight=self.mobility_weight,
                use_pawn_structure=self.use_pawn_structure,
                use_piece_coordination=self.use_piece_coordination,
                use_endgame_heuristics=self.use_endgame_heuristics,
            )

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
            board.move(move.from_pos, move.to_pos)
            score = -self._quiescence(
                board, -beta, -alpha, opponent, root_depth, qply + 1
            )
            board.undo()

            if score > best_score:
                best_score = score

            alpha = max(alpha, score)
            if alpha >= beta:
                break  # Beta cutoff.

        if self.use_transposition_table:
            if best_score <= alpha_original:
                bound = Bound.UPPER
            elif best_score >= beta:
                bound = Bound.LOWER
            else:
                bound = Bound.EXACT

            self.tt.store(key, 0, best_score, bound, None)

        return best_score
