from ..core.rule import Rule
from .base import ChessEngine, SearchResult
from .evaluation import evaluate


MATE_SCORE = 100000


class SearchEngine(ChessEngine):
    """
    V0.2 Search Engine: Minimax and Alpha-Beta pruning over the
    material + simple position evaluation, with a configurable fixed
    search depth.

    Both algorithms are kept side by side (rather than only shipping
    Alpha-Beta) so their equivalence can be verified directly: for the
    same position and depth, both must return the same best move and
    score, while Alpha-Beta visits fewer nodes. Iterative deepening,
    transposition tables, and move ordering are deliberately left for
    V0.3 (see docs/roadmap.md) to keep this version simple and easy
    to reason about.

    Note on terminal positions: unlike International Chess, having no
    legal move is ALWAYS a loss in Xiangqi (checkmate and stalemate /
    困毙 are both losses, never a draw) -- see Rule for details. This
    makes the terminal-score logic below simpler than a general
    chess-style implementation.
    """

    def __init__(self, depth=3, use_alpha_beta=True):
        self.depth = depth
        self.use_alpha_beta = use_alpha_beta
        self.nodes_evaluated = 0

    def choose_move(self, board, color):
        self.nodes_evaluated = 0

        legal_moves = Rule.generate_legal_moves(board, color)
        if not legal_moves:
            return SearchResult(None, evaluate(board, color), self.nodes_evaluated, self.depth)

        opponent = board.opponent(color)
        best_move = None
        best_score = float("-inf")
        alpha, beta = float("-inf"), float("inf")

        for move in legal_moves:
            board.move(move.from_pos, move.to_pos)

            if self.use_alpha_beta:
                score = self._alphabeta(board, self.depth - 1, alpha, beta, opponent, color)
            else:
                score = self._minimax(board, self.depth - 1, opponent, color)

            board.undo()

            if score > best_score:
                best_score = score
                best_move = move

            if self.use_alpha_beta:
                alpha = max(alpha, best_score)

        return SearchResult(best_move, best_score, self.nodes_evaluated, self.depth)

    # ------------------------------------------------------------------
    # Plain Minimax (no pruning). Kept as a reference implementation:
    # Alpha-Beta must always agree with it on best_move and score.
    # ------------------------------------------------------------------
    def _minimax(self, board, depth, current_color, root_color):
        self.nodes_evaluated += 1

        legal_moves = Rule.generate_legal_moves(board, current_color)

        if not legal_moves:
            ply_from_root = self.depth - depth
            return self._terminal_score(current_color, root_color, ply_from_root)

        if depth == 0:
            return evaluate(board, root_color)

        maximizing = current_color == root_color
        best = float("-inf") if maximizing else float("inf")

        for move in legal_moves:
            board.move(move.from_pos, move.to_pos)
            score = self._minimax(board, depth - 1, board.opponent(current_color), root_color)
            board.undo()

            if maximizing:
                best = max(best, score)
            else:
                best = min(best, score)

        return best

    # ------------------------------------------------------------------
    # Alpha-Beta pruning over the exact same tree shape as Minimax.
    # ------------------------------------------------------------------
    def _alphabeta(self, board, depth, alpha, beta, current_color, root_color):
        self.nodes_evaluated += 1

        legal_moves = Rule.generate_legal_moves(board, current_color)

        if not legal_moves:
            ply_from_root = self.depth - depth
            return self._terminal_score(current_color, root_color, ply_from_root)

        if depth == 0:
            return evaluate(board, root_color)

        maximizing = current_color == root_color

        if maximizing:
            value = float("-inf")
            for move in legal_moves:
                board.move(move.from_pos, move.to_pos)
                value = max(
                    value,
                    self._alphabeta(
                        board, depth - 1, alpha, beta,
                        board.opponent(current_color), root_color,
                    ),
                )
                board.undo()
                alpha = max(alpha, value)
                if alpha >= beta:
                    break  # beta cutoff: opponent already has a better alternative
            return value
        else:
            value = float("inf")
            for move in legal_moves:
                board.move(move.from_pos, move.to_pos)
                value = min(
                    value,
                    self._alphabeta(
                        board, depth - 1, alpha, beta,
                        board.opponent(current_color), root_color,
                    ),
                )
                board.undo()
                beta = min(beta, value)
                if alpha >= beta:
                    break  # alpha cutoff
            return value

    def _terminal_score(self, current_color, root_color, ply_from_root):
        # A mate found sooner (smaller ply_from_root) is preferred
        # when winning, and avoided more strongly when losing.
        score = MATE_SCORE - ply_from_root

        if current_color == root_color:
            return -score
        return score
