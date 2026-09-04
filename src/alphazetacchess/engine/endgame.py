"""V0.5.3 endgame-phase evaluation component.

Xiangqi-specific principle, well established in practical play and
endgame theory: **"车赛全局，炮怕残棋"** -- the Rook's power holds up
(if anything, grows, thanks to open lines) throughout the game,
while the Cannon's power *declines* as the board empties, because a
Cannon needs an intervening piece to capture over and the endgame is
exactly when those screening pieces have mostly been traded off. This
is a rule about *relative piece value changing with game phase*, not
about king activity: unlike Western chess, the Xiangqi King/General
can never leave its palace, at any phase of the game, so "king
activity in the endgame" (a staple Western-chess endgame heuristic)
has no equivalent here. That is deliberately why this module does not
attempt one.

Two pieces:

- `is_endgame(board)`: a simple, symmetric material-threshold phase
  classifier -- endgame is defined as "few major (Rook/Cannon/Horse)
  pieces remain on the board for either side", independent of which
  side is ahead. Kept intentionally simple (a single combined
  threshold, no separate per-side/tapered blending) for the same
  reason every other first version of an evaluation term in this
  project has started simple: V0.4.4's Connected Pawns and V0.4.5's
  Piece Coordination were both "obviously correct in direction, exact
  constant tuned later" rather than trying to get the magnitude right
  immediately.
- `endgame_balance(board, perspective_color)`: applies a flat per-Rook
  bonus and a flat per-Cannon penalty to material already scored by
  `evaluation.py`, but ONLY when `is_endgame(board)` is true --
  everywhere else (opening, middlegame) Rook and Cannon keep their
  ordinary `MATERIAL_VALUES`, unmodified.

## From self-play data

This module's constants (`ENDGAME_MAJOR_MATERIAL_THRESHOLD`,
`ENDGAME_ROOK_BONUS`, `ENDGAME_CANNON_PENALTY`) are principled
first-guesses grounded in a genuinely well-known piece of Xiangqi
endgame theory, not invented from nothing -- but like every other
V0.4.x/V0.5.x evaluation constant in this project, they are exactly
the kind of thing self-play data should eventually confirm or correct,
rather than being trusted forever on theory alone. `selfplay/
endgame_analysis.py` (companion module, same checkpoint) mines
recorded self-play games for exactly the signal that would validate
or refute this: among games that actually reach the endgame phase (as
`is_endgame` defines it), does the side with relatively more Rooks and
fewer Cannons at that point actually win more often? See
`docs/v0.5.3.md` for what that tool found (or didn't find) against
whatever self-play corpus existed at the time, and why -- exactly like
V0.5.2's opening book, the *mechanism* does not require a large corpus
to build and test, but *trusting the specific constants* does, and
that validation is deliberately kept separate and re-runnable as more
data accumulates.

Kept as its own small module with its own toggle
(`use_endgame_heuristics`), following the same pattern as mobility.py/
pawn_structure.py/piece_coordination.py: independently benchmarkable,
independently disableable, and not assumed to help until measured.
"""

from ..core.board import Board
from ..core.piece import PieceType


# Rook + Cannon + Horse are "major" pieces for phase classification --
# Advisors/Elephants are purely defensive and don't meaningfully
# change how sharp or piece-dependent the position is, and Pawns are
# excluded because a position can be pawn-heavy at any phase (pawns
# are rarely traded off early) so counting them would misclassify a
# perfectly normal middlegame as an "endgame".
_MAJOR_PIECE_TYPES = (PieceType.ROOK, PieceType.CANNON, PieceType.HORSE)

# Material value used ONLY for phase classification, deliberately
# independent of evaluation.MATERIAL_VALUES so a future retune of the
# main material table doesn't silently shift where the endgame phase
# boundary falls. Two Rooks + two Cannons + two Horses per side at the
# start of the game is 2*(900+450+400) = 3500 "major material" per
# side, 7000 combined.
_MAJOR_PIECE_PHASE_VALUES = {
    PieceType.ROOK: 900,
    PieceType.CANNON: 450,
    PieceType.HORSE: 400,
}

# Combined (both sides) major-piece material at or below which a
# position counts as "endgame". 2600 is roughly "a bit more than one
# side's worth of major pieces remains in total" (e.g. both sides down
# to one Rook and one Horse each, majors mostly traded off) -- clearly
# past the middlegame under any reasonable reading, without being so
# low that it only fires in bare king-and-pawn-type positions. A
# first-guess threshold, explicitly flagged above for future
# self-play-driven correction.
ENDGAME_MAJOR_MATERIAL_THRESHOLD = 2600

# Applied per Rook / per Cannon a side owns, but only in the endgame
# phase (see module docstring for the "车赛全局，炮怕残棋" rationale).
# Magnitudes kept modest and roughly symmetric on purpose: this is a
# phase-dependent *nudge* to the existing material score, not a
# wholesale re-valuation -- MATERIAL_VALUES already does the heavy
# lifting everywhere.
ENDGAME_ROOK_BONUS = 40
ENDGAME_CANNON_PENALTY = -40


def _major_material(board):
    """Total major-piece phase-material on the board, both colors combined."""
    total = 0
    for row in board.board:
        for piece in row:
            if piece is None:
                continue
            total += _MAJOR_PIECE_PHASE_VALUES.get(piece.type, 0)
    return total


def is_endgame(board):
    """
    True once combined major-piece material has dropped to or below
    `ENDGAME_MAJOR_MATERIAL_THRESHOLD`. Deliberately a single
    board-wide classification (not per-color) -- Xiangqi's own
    material-exchange rules mean pieces are almost always traded in
    matched pairs (a Rook is worth roughly two minor pieces, so trades
    tend to balance out in raw count even when they don't in points),
    so a combined threshold is a reasonable simplification for a first
    version, same as every other V0.4.x/V0.5.x term's "start simple,
    refine later once measured" approach.
    """
    return _major_material(board) <= ENDGAME_MAJOR_MATERIAL_THRESHOLD


def endgame_score(board, color):
    """
    Endgame-phase-only Rook/Cannon adjustment for one side. Returns 0
    outside the endgame phase, and 0 for a side with no Rooks/Cannons
    even inside it.
    """
    if not is_endgame(board):
        return 0

    score = 0
    for row in board.board:
        for piece in row:
            if piece is None or piece.color != color:
                continue
            if piece.type == PieceType.ROOK:
                score += ENDGAME_ROOK_BONUS
            elif piece.type == PieceType.CANNON:
                score += ENDGAME_CANNON_PENALTY
    return score


def endgame_balance(board, perspective_color):
    """Return own endgame-phase score minus the opponent's."""
    opponent = Board.opponent(perspective_color)
    return endgame_score(board, perspective_color) - endgame_score(board, opponent)
