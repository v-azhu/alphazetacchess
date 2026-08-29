from ..core.rule import Rule
from .base import ChessEngine, SearchResult
from .evaluation import evaluate
from .transposition_table import Bound, TranspositionTable


MATE_SCORE = 100000


class SearchEngine(ChessEngine):
    """V0.3.2 Alpha-Beta search with iterative deepening and TT.

    V0.3.2 adds a depth-aware transposition table while preserving the
    V0.3.1 search semantics. The table is optional so the previous
    implementation remains a directly comparable baseline.
    """

    def __init__(
        self,
        depth=3,
        use_alpha_beta=True,
        iterative_deepening=True,
        use_transposition_table=True,
        tt_max_entries=200_000,
    ):
        self.depth = depth
        self.use_alpha_beta = use_alpha_beta
        self.iterative_deepening = iterative_deepening
        self.use_transposition_table = use_transposition_table
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
        opponent = board.opponent(color)

        best_move = None
        best_score = float("-inf")
        alpha, beta = float("-inf"), float("inf")

        for move in root_moves:
            board.move(move.from_pos, move.to_pos)

            if self.use_alpha_beta:
                score = self._alphabeta(
                    board,
                    depth - 1,
                    alpha,
                    beta,
                    opponent,
                    color,
                )
            else:
                score = self._minimax(
                    board,
                    depth - 1,
                    opponent,
                    color,
                )

            board.undo()

            if score > best_score:
                best_score = score
                best_move = move

            if self.use_alpha_beta:
                alpha = max(alpha, best_score)

        return SearchResult(
            best_move,
            best_score,
            self.nodes_evaluated,
            depth,
        )

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

        preferred = (
            preferred_move[0],
            preferred_move[1],
        )

        for index, move in enumerate(moves):
            if (move.from_pos, move.to_pos) == preferred:
                return [move] + list(moves[:index]) + list(moves[index + 1:])

        return list(moves)

    def _tt_key(self, board, root_color):
        # Board.zobrist_hash already contains the side to move.
        # Root color is included because TT scores are evaluated from
        # root_color's perspective.
        return (board.zobrist_hash, root_color)

    def _minimax(self, board, depth, current_color, root_color):
        self.nodes_evaluated += 1
        legal_moves = Rule.generate_legal_moves(board, current_color)

        if not legal_moves:
            return self._terminal_score(
                current_color,
                root_color,
                self.depth - depth,
            )

        if depth == 0:
            return evaluate(board, root_color)

        maximizing = current_color == root_color
        best = float("-inf") if maximizing else float("inf")

        for move in legal_moves:
            board.move(move.from_pos, move.to_pos)
            score = self._minimax(
                board,
                depth - 1,
                board.opponent(current_color),
                root_color,
            )
            board.undo()

            best = max(best, score) if maximizing else min(best, score)

        return best

    def _alphabeta(
        self,
        board,
        depth,
        alpha,
        beta,
        current_color,
        root_color,
    ):
        self.nodes_evaluated += 1

        alpha_original = alpha
        beta_original = beta
        key = self._tt_key(board, root_color)
        preferred_move = None

        if self.use_transposition_table:
            cached_score, preferred_move = self.tt.probe(
                key,
                depth,
                alpha,
                beta,
            )
            if cached_score is not None:
                return cached_score

        legal_moves = Rule.generate_legal_moves(board, current_color)

        if not legal_moves:
            score = self._terminal_score(
                current_color,
                root_color,
                self.depth - depth,
            )
            if self.use_transposition_table:
                self.tt.store(
                    key,
                    depth,
                    score,
                    Bound.EXACT,
                    None,
                )
            return score

        if depth == 0:
            score = evaluate(board, root_color)
            if self.use_transposition_table:
                self.tt.store(
                    key,
                    depth,
                    score,
                    Bound.EXACT,
                    None,
                )
            return score

        legal_moves = self._order_moves(
            legal_moves,
            preferred_move,
        )

        maximizing = current_color == root_color
        best_move = None

        if maximizing:
            value = float("-inf")

            for move in legal_moves:
                board.move(move.from_pos, move.to_pos)

                child_score = self._alphabeta(
                    board,
                    depth - 1,
                    alpha,
                    beta,
                    board.opponent(current_color),
                    root_color,
                )

                board.undo()

                if child_score > value:
                    value = child_score
                    best_move = move

                alpha = max(alpha, value)

                if alpha >= beta:
                    break

        else:
            value = float("inf")

            for move in legal_moves:
                board.move(move.from_pos, move.to_pos)

                child_score = self._alphabeta(
                    board,
                    depth - 1,
                    alpha,
                    beta,
                    board.opponent(current_color),
                    root_color,
                )

                board.undo()

                if child_score < value:
                    value = child_score
                    best_move = move

                beta = min(beta, value)

                if alpha >= beta:
                    break

        if self.use_transposition_table:
            if value <= alpha_original:
                bound = Bound.UPPER
            elif value >= beta_original:
                bound = Bound.LOWER
            else:
                bound = Bound.EXACT

            self.tt.store(
                key,
                depth,
                value,
                bound,
                best_move,
            )

        return value

    def _terminal_score(self, current_color, root_color, ply_from_root):
        score = MATE_SCORE - ply_from_root
        return -score if current_color == root_color else score
