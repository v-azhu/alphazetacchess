"""V0.9.4 `NeuralPolicyEvaluator`: wraps a trained `PolicyMLP` so it can
be called exactly like `engine/mcts.py`'s `policy_fn` parameter expects
-- `(board, color, legal_moves) -> {move: probability}` -- a drop-in
non-uniform, non-heuristic prior source once a policy network has
actually been trained (mirrors `evaluator.py`'s `NeuralEvaluator`,
which does the same thing for `eval_fn`/the value side).

No training pipeline exists yet for this (see `docs/v0.9.4.md`'s scope
boundary) -- this class is the consumption side of a future
`tools/train_policy_network.py`, built and tested now the same way
`NeuralEvaluator` was built before any real Pikafish-labeled training
had happened (V0.6.2's own "mechanism first" precedent).
"""

from .features import board_to_features, FEATURE_DIM
from .policy_encoding import move_to_policy_index, POLICY_DIM
from .policy_network import PolicyMLP


class NeuralPolicyEvaluator:
    def __init__(self, network_path):
        self.net = PolicyMLP.load(network_path)

        loaded_input_dim = self.net.w1.shape[0]
        if loaded_input_dim != FEATURE_DIM:
            raise ValueError(
                f"{network_path} was trained with a {loaded_input_dim}-dimensional "
                f"feature vector, but neural/features.py's current FEATURE_DIM is "
                f"{FEATURE_DIM} -- this network is from a different (likely older) "
                f"version of the feature encoding and is not compatible. Retrain."
            )

        loaded_output_dim = self.net.w3.shape[1]
        if loaded_output_dim != POLICY_DIM:
            raise ValueError(
                f"{network_path} was trained with output dimension "
                f"{loaded_output_dim}, but neural/policy_encoding.py's current "
                f"POLICY_DIM is {POLICY_DIM} -- this network is from a different "
                f"version of the move encoding and is not compatible. Retrain."
            )

    def __call__(self, board, color, legal_moves):
        """Matches `engine/mcts.py`'s `policy_fn(board, color,
        legal_moves)` calling convention exactly -- returns
        `{move: probability}` for every move in `legal_moves`,
        normalized over exactly that set (see `PolicyMLP.
        predict_masked_probs`'s own docstring for why masking to the
        legal set happens here, at inference, rather than during
        training).
        """
        features = board_to_features(board, color)
        index_to_move = {}
        legal_indices = []
        for move in legal_moves:
            index = move_to_policy_index(move, color)
            index_to_move[index] = move
            legal_indices.append(index)

        probs_by_index = self.net.predict_masked_probs(features, legal_indices)
        return {index_to_move[index]: prob for index, prob in probs_by_index.items()}
