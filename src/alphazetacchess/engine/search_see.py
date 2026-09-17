from .search import SearchEngine
from .see import StaticExchangeEvaluator


class SeeSearchEngine(SearchEngine):
    """SearchEngine with SEE-aware capture ordering.

    The base search remains unchanged. SEE is inserted only into move
    ordering, so the feature can be benchmarked and removed without
    changing the core search implementation.
    """

    def __init__(self, *args, use_see=True, see_max_depth=12, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_see = use_see
        self.see = StaticExchangeEvaluator(
            material_values=self.material_values,
            max_depth=see_max_depth,
        )

    def _order_moves(self, moves, preferred_move, ply=None):
        ordered = list(moves)
        preferred = None
        if preferred_move is not None:
            target = (preferred_move[0], preferred_move[1])
            for index, move in enumerate(ordered):
                if (move.from_pos, move.to_pos) == target:
                    preferred = ordered.pop(index)
                    break

        captures = [move for move in ordered if move.captured_piece is not None]
        quiets = [move for move in ordered if move.captured_piece is None]

        if captures:
            if self.use_see:
                captures.sort(key=self.see.evaluate_capture, reverse=True)
            elif self.use_mvv_lva:
                captures.sort(key=self._mvv_lva_score, reverse=True)

        if self.use_killer_moves and ply is not None:
            quiets = self._promote_killer_moves(quiets, ply)

        if self.use_history:
            quiets.sort(key=self.history.get, reverse=True)

        ordered = captures + quiets
        if preferred is not None:
            ordered = [preferred] + ordered
        return ordered
