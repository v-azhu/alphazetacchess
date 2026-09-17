from ..core.rule import Rule
from .evaluation import CALIBRATED_MATERIAL_VALUES, MATERIAL_VALUES


class StaticExchangeEvaluator:
    """Legality-aware static exchange evaluator for Xiangqi captures.

    SEE answers a narrow question: after a capture on a square, what is the
    net material gain/loss if both sides continue the capture sequence with
    their best legal recaptures? Unlike MVV-LVA, it accounts for the whole
    exchange and for pinned/illegal recaptures because it uses the project's
    legal move generator.

    This implementation deliberately favors correctness and reuse of the
    existing Rule layer over a hand-written attack-map implementation. It is
    intended for move ordering and quiescence pruning; later optimization can
    replace the inner legal-capture scan if profiling shows SEE is hot.
    """

    def __init__(self, material_values=None, max_depth=12):
        self.material_values = material_values or CALIBRATED_MATERIAL_VALUES or MATERIAL_VALUES
        self.max_depth = max_depth

    def piece_value(self, piece):
        if piece is None:
            return 0
        return self.material_values.get(piece.type, 0)

    def evaluate_capture(self, board, move):
        """Return the net material result for the supplied capture.

        Positive means the side making ``move`` wins material in the forced
        exchange; negative means it loses material.
        """
        if move is None or move.captured_piece is None:
            return 0

        target = move.to_pos
        immediate_gain = self.piece_value(move.captured_piece)
        board.move(move.from_pos, move.to_pos)
        try:
            reply = self._exchange(
                board, target, board.current_player, self.max_depth - 1, {}
            )
        finally:
            board.undo()
        return immediate_gain - reply

    def _exchange(self, board, target, side, depth, memo):
        if depth <= 0:
            return 0

        key = (board.zobrist_hash, target, side, depth)
        cached = memo.get(key)
        if cached is not None:
            return cached

        captures = [
            move
            for move in Rule.generate_legal_moves(board, side)
            if move.to_pos == target and move.captured_piece is not None
        ]
        if not captures:
            memo[key] = 0
            return 0

        best = 0
        for capture in captures:
            victim_value = self.piece_value(capture.captured_piece)
            board.move(capture.from_pos, capture.to_pos)
            try:
                gain = victim_value - self._exchange(
                    board, target, board.current_player, depth - 1, memo
                )
            finally:
                board.undo()
            if gain > best:
                best = gain

        memo[key] = best
        return best
