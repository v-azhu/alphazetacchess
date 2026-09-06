"""V0.6.2 `NeuralEvaluator`: wraps a trained `SmallMLP` so it can be
called exactly like `engine/evaluation.py`'s `evaluate(board, color)`
-- a drop-in replacement anywhere that function is currently called,
once a network has actually been trained (see `docs/v0.6.2.md` for the
full pipeline: `tools/label_positions_with_pikafish.py` ->
`tools/train_neural_eval.py` -> this class).

Not yet wired into `SearchEngine`/`MCTSEngine` -- both currently call
the module-level `evaluate()` function directly, and swapping in a
pluggable evaluator is a deliberately separate next step (see
`docs/v0.6.2.md`'s Next Step), left until there's an actual trained
network worth plugging in and testing against real search behavior,
rather than wiring up the mechanism ahead of having anything real to
verify it with.
"""

from .features import board_to_features
from .network import SmallMLP


class NeuralEvaluator:
    def __init__(self, network_path):
        self.net = SmallMLP.load(network_path)

    def __call__(self, board, color):
        """Matches `evaluate(board, color)`'s calling convention exactly."""
        features = board_to_features(board, color)
        # SmallMLP.predict expects a batch (N, FEATURE_DIM); wrap this
        # single position as a batch of one and unwrap the result.
        score = self.net.predict(features.reshape(1, -1))[0]
        return float(score)
