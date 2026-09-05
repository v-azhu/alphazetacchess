"""V0.6.1 Monte Carlo Tree Search engine skeleton.

This is deliberately the *search mechanism only*, evaluated at each
newly-expanded leaf by the existing V0.4.x/V0.5.3 heuristic
`evaluate()` function -- there is no policy/value neural network yet.
Same incremental strategy this project used for alpha-beta search
itself: V0.3 built the Negamax/Alpha-Beta search skeleton around a
material-only evaluation function, then V0.4 spent five separate
checkpoints (piece-square tables, king safety, mobility, pawn
structure, piece coordination) enriching the evaluation *without*
touching the search skeleton again. MCTSEngine follows the exact same
split: get the tree-search machinery (selection, expansion, backup)
correct and tested first, against whatever evaluation function already
exists, and treat "replace the evaluation call with a learned value
network, and the uniform move priors with a learned policy network"
as a clearly separate, later increment (V0.6.2+) that only has to
change `_expand_and_evaluate`, not the tree-search logic around it.

## Design

Uses PUCT (the AlphaZero selection formula) with **uniform** move
priors (`1 / number of legal moves`), since there is no policy network
yet to supply non-uniform priors -- this is exactly the parameter a
future policy network would replace, and is called out explicitly in
`_MCTSNode.prior`'s own comment for that reason.

At each newly-visited (unexpanded) node, instead of a random rollout
to a terminal position (classic MCTS) or a policy/value network
(AlphaZero), this evaluates the position directly with
`engine.evaluation.evaluate()` and squashes the result through `tanh`
into the bounded [-1, 1] range MCTS value backup assumes. Choosing
"evaluate the leaf directly" over "rollout to terminal" has a
convenient side benefit beyond speed: **each simulation's depth is
bounded by the current size of the tree** (selection only walks
existing, already-expanded nodes; expansion adds exactly one new
level per simulation) -- there is no risk of a single simulation
recursing arbitrarily deep the way a random-rollout-to-terminal
approach could, so no `max_rollout_depth` safety valve is needed.

Terminal positions (no legal moves for the side to move) are always a
certain loss for that side -- `terminal_value = -1.0` exactly,
regardless of whether it's checkmate or Xiangqi's stalemate-is-a-loss
rule (see `core/rule.py`'s own docstring on this point): both cases
are simply "no legal moves," and the distinction doesn't matter for
MCTS's value backup either way.

## Node statistics convention (read this before touching `_select_child`)

Every `_MCTSNode` stores its OWN `visit_count`/`value_sum`, always
from the perspective of whichever color is to move *at that node*
(i.e. before any further move is made from it). This is the single
most error-prone part of any minimax- or MCTS-style implementation to
get backwards, so it's worth stating plainly and testing directly
(see `tests/test_mcts_v061.py`'s `test_select_child_prefers_the_move_good_for_the_parent`):
a **child**'s `value_sum/visit_count` is an average from the
**opponent's** perspective (since the opponent is to move at that
child), so `_select_child` must **negate** it to get the value from
the parent's (the side actually choosing a move) perspective before
comparing children -- using a child's raw average directly would
select for what's good for the *opponent*, not the side to move.
"""

import math

from ..core.board import Board
from ..core.rule import Rule
from ..engine.base import ChessEngine, SearchResult
from ..engine.evaluation import evaluate


class _MCTSNode:
    def __init__(self, prior):
        # `prior`: this node's a-priori move probability as chosen by
        # its PARENT among its siblings -- uniform (1/num_siblings) for
        # now; a future policy network's output plugs in exactly here.
        # Not used by the root itself (root has no parent/prior).
        self.prior = prior
        self.children = None  # dict: Move -> _MCTSNode, set once expanded
        self.visit_count = 0
        self.value_sum = 0.0
        self.is_terminal = False
        self.terminal_value = None

    @property
    def expanded(self):
        return self.children is not None


def _squash(raw_score, value_scale):
    """
    Map an unbounded evaluate()-style score into [-1, 1] via tanh, so
    MCTS value backup (which assumes bounded, comparable values across
    every leaf, terminal or not) has something sane to work with.
    `value_scale` sets how many evaluate() points correspond to
    "meaningfully decisive" -- see MCTSEngine's own docstring for the
    default's reasoning.
    """
    return math.tanh(raw_score / value_scale)


class MCTSEngine(ChessEngine):
    """
    V0.6.1 Monte Carlo Tree Search, using the existing heuristic
    `evaluate()` as a stand-in leaf-value estimator (see module
    docstring). `simulations` controls search effort directly (there
    is no notion of "depth" the way Negamax has one -- `SearchResult
    .depth` is repurposed to hold `simulations` for this engine, since
    that's the closest equivalent "how much search effort" figure).
    """

    def __init__(
        self,
        simulations=200,
        c_puct=1.4,
        value_scale=500,
        use_piece_square_tables=True,
        use_king_safety=True,
        use_mobility=False,
        use_pawn_structure=False,
        use_piece_coordination=False,
        use_endgame_heuristics=False,
    ):
        self.simulations = simulations
        self.c_puct = c_puct
        # 500 (five pawns' worth of MATERIAL_VALUES, see evaluation.py)
        # means a full Rook's material advantage (900) squashes to
        # tanh(1.8) =~ 0.95 (strongly, but not perfectly, decisive) and
        # a single pawn (100) squashes to tanh(0.2) =~ 0.20 (a mild
        # nudge) -- a reasonable first guess for "how much of a raw
        # evaluate() score should read as close to certain," in
        # exactly the same "principled first guess, not yet
        # data-validated" spirit as every other constant introduced in
        # this project (see e.g. engine/endgame.py's own constants).
        self.value_scale = value_scale
        self.eval_kwargs = dict(
            use_piece_square_tables=use_piece_square_tables,
            use_king_safety=use_king_safety,
            use_mobility=use_mobility,
            use_pawn_structure=use_pawn_structure,
            use_piece_coordination=use_piece_coordination,
            use_endgame_heuristics=use_endgame_heuristics,
        )
        self.nodes_evaluated = 0

    def choose_move(self, board, color):
        self.nodes_evaluated = 0
        root = _MCTSNode(prior=1.0)

        for _ in range(self.simulations):
            self._simulate(board, color, root)

        if root.is_terminal or not root.children:
            # No legal moves for `color` even before any search -- the
            # game is already over. Mirrors SearchEngine's own
            # SearchResult(None, ...) convention for this case.
            return SearchResult(None, root.terminal_value or 0.0, self.nodes_evaluated, self.simulations)

        best_move, best_child = max(
            root.children.items(), key=lambda item: item[1].visit_count
        )
        score = (
            best_child.value_sum / best_child.visit_count
            if best_child.visit_count > 0
            else 0.0
        )
        return SearchResult(best_move, score, self.nodes_evaluated, self.simulations)

    def _simulate(self, board, color, node):
        """
        Run one selection->expansion->evaluation->backup pass starting
        at `node` (representing `board`'s current state, `color` to
        move). Mutates `board` via move()/undo() during the call but
        always restores it before returning. Returns this simulation's
        realized value of `node`, from `color`'s perspective.
        """
        if node.is_terminal:
            node.visit_count += 1
            node.value_sum += node.terminal_value
            return node.terminal_value

        if not node.expanded:
            value = self._expand_and_evaluate(board, color, node)
            node.visit_count += 1
            node.value_sum += value
            return value

        move, child = self._select_child(node)
        board.move(move.from_pos, move.to_pos)
        child_value = self._simulate(board, Board.opponent(color), child)
        board.undo()

        # `child_value` is from the OPPONENT's perspective (whoever is
        # to move at `child`) -- negate to get the value of choosing
        # this move from `color`'s (this node's) own perspective.
        value = -child_value
        node.visit_count += 1
        node.value_sum += value
        return value

    def _expand_and_evaluate(self, board, color, node):
        legal_moves = Rule.generate_legal_moves(board, color)

        if not legal_moves:
            # No legal moves is always a loss for `color` in Xiangqi,
            # whether it's checkmate or stalemate (see core/rule.py).
            node.is_terminal = True
            node.terminal_value = -1.0
            return node.terminal_value

        prior = 1.0 / len(legal_moves)
        node.children = {move: _MCTSNode(prior=prior) for move in legal_moves}

        self.nodes_evaluated += 1
        raw_score = evaluate(board, color, **self.eval_kwargs)
        return _squash(raw_score, self.value_scale)

    def _select_child(self, node):
        best_score = None
        best_move = None
        best_child = None

        for move, child in node.children.items():
            if child.visit_count > 0:
                # Negate: child.value_sum/visit_count is an average
                # from the OPPONENT's perspective (see module
                # docstring) -- the value of choosing this move, from
                # `node`'s own perspective, is the negation of that.
                q = -(child.value_sum / child.visit_count)
            else:
                q = 0.0

            u = (
                self.c_puct
                * child.prior
                * math.sqrt(node.visit_count)
                / (1 + child.visit_count)
            )
            score = q + u

            if best_score is None or score > best_score:
                best_score, best_move, best_child = score, move, child

        return best_move, best_child
