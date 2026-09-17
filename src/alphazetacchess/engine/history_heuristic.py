class HistoryHeuristic:
    """Search-local history heuristic for quiet-move ordering.

    A move receives a positive bonus when it causes a beta cutoff and a
    negative adjustment when it fails to improve alpha. Scores are bounded
    so a long search cannot let old history dominate newer evidence.
    """

    MAX_SCORE = 32_000
    BONUS_SCALE = 32

    def __init__(self):
        self._scores = {}

    def clear(self):
        self._scores.clear()

    def get(self, move):
        if move is None:
            return 0
        return self._scores.get((move.from_pos, move.to_pos), 0)

    def update(self, move, bonus):
        if move is None or move.captured_piece is not None:
            return
        key = (move.from_pos, move.to_pos)
        old = self._scores.get(key, 0)
        bonus = max(-self.MAX_SCORE, min(self.MAX_SCORE, bonus))
        # Gravity-style history update: recent evidence matters more while
        # retaining useful information from earlier nodes.
        self._scores[key] = max(
            -self.MAX_SCORE,
            min(self.MAX_SCORE, old + bonus - old * abs(bonus) // self.MAX_SCORE),
        )

    def reward(self, move, depth):
        """Reward a quiet move that produced a beta cutoff."""
        self.update(move, self.BONUS_SCALE * depth * depth)

    def penalize(self, move, depth):
        """Penalize a quiet move searched before the cutoff move."""
        self.update(move, -self.BONUS_SCALE * depth * depth)
