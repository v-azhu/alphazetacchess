"""V0.5.3 endgame-phase analysis of recorded self-play games.

`engine/endgame.py`'s Rook-bonus/Cannon-penalty constants are grounded
in known Xiangqi endgame theory ("车赛全局，炮怕残棋"), but -- like
every other evaluation constant added in this project -- they are a
first guess that self-play data should eventually confirm or correct,
not something to trust forever on theory alone. This module is the
"eventually confirm or correct" half: it mines recorded self-play
games (V0.5.1's `recorder.py` format) for the specific signal that
would validate or refute `engine/endgame.py`'s hypothesis.

Mirrors V0.5.2's `opening_book.py` in spirit: build the *mechanism*
now, and let it run against whatever corpus exists (even a tiny smoke
batch), rather than waiting for a large real corpus before writing any
code. Real conclusions still require a real corpus -- see
`docs/v0.5.3.md`'s "Known limitation".
"""

from ..core.board import Board
from ..core.piece import Color, PieceType
from ..engine.endgame import is_endgame, ENDGAME_ROOK_BONUS, ENDGAME_CANNON_PENALTY


def _major_piece_counts(board, color):
    """{PieceType.ROOK/CANNON/HORSE: count} for one color's live majors."""
    counts = {PieceType.ROOK: 0, PieceType.CANNON: 0, PieceType.HORSE: 0}
    for row in board.board:
        for piece in row:
            if piece is not None and piece.color == color and piece.type in counts:
                counts[piece.type] += 1
    return counts


def find_endgame_onset(record):
    """
    Replay one game record and return a dict describing the first ply
    (if any) at which the position satisfies `is_endgame`.

    Returns None if the game never reaches the endgame phase within
    its recorded moves (e.g. a short, decisive game with the major
    pieces still mostly on the board when it ended).

    Otherwise returns:
        {
            "ply": <int, 0-indexed ply at which is_endgame first held>,
            "red_majors": {ROOK: n, CANNON: n, HORSE: n},
            "black_majors": {ROOK: n, CANNON: n, HORSE: n},
        }
    """
    board = Board()

    for ply_index, move_entry in enumerate(record["moves"]):
        from_pos = tuple(move_entry["from"])
        to_pos = tuple(move_entry["to"])
        board.move(from_pos, to_pos)

        if is_endgame(board):
            return {
                "ply": ply_index,
                "red_majors": _major_piece_counts(board, Color.RED),
                "black_majors": _major_piece_counts(board, Color.BLACK),
            }

    return None


def _rook_cannon_edge(majors_for, majors_against):
    """
    A single scalar summarizing "how much better is this side's
    Rook/Cannon mix, per engine/endgame.py's own weighting" -- more
    Rooks and fewer Cannons than the opponent is a positive edge.
    Reuses ROOK_BONUS/CANNON_PENALTY as the weighting so this directly
    measures whether the hypothesis those constants encode actually
    correlates with winning, rather than measuring something else and
    hoping it's related.
    """
    return (
        ENDGAME_ROOK_BONUS * (majors_for[PieceType.ROOK] - majors_against[PieceType.ROOK])
        + ENDGAME_CANNON_PENALTY
        * (majors_for[PieceType.CANNON] - majors_against[PieceType.CANNON])
    )


def summarize_endgame_outcomes(records):
    """
    Aggregate, across all records, whether reaching the endgame with a
    better Rook/Cannon mix (by engine/endgame.py's own weighting)
    actually correlates with winning.

    Returns:
        {
            "games": <int, total records>,
            "reached_endgame": <int, records where is_endgame ever held>,
            "avg_onset_ply": <float or None>,
            "edge_favored_wins": <int>,
            "edge_favored_losses": <int>,
            "edge_favored_draws": <int>,
            "no_edge": <int, onset positions with a tied Rook/Cannon edge>,
        }

    "edge_favored_*" only counts games with a non-zero edge at endgame
    onset for the eventual winner-or-loser side the edge favored --
    i.e. it asks "when one side had the better mix at endgame onset,
    did that side go on to win?", which is exactly the question
    engine/endgame.py's constants are a bet on.
    """
    stats = {
        "games": len(records),
        "reached_endgame": 0,
        "onset_plies": [],
        "edge_favored_wins": 0,
        "edge_favored_losses": 0,
        "edge_favored_draws": 0,
        "no_edge": 0,
    }

    for record in records:
        onset = find_endgame_onset(record)
        if onset is None:
            continue

        stats["reached_endgame"] += 1
        stats["onset_plies"].append(onset["ply"])

        edge = _rook_cannon_edge(onset["red_majors"], onset["black_majors"])
        result = record["result"]  # "RED_WINS" | "BLACK_WINS" | "DRAW"

        if edge == 0:
            stats["no_edge"] += 1
            continue

        favored = Color.RED if edge > 0 else Color.BLACK
        if result == "DRAW":
            stats["edge_favored_draws"] += 1
        elif result == f"{favored.name}_WINS":
            stats["edge_favored_wins"] += 1
        else:
            stats["edge_favored_losses"] += 1

    onset_plies = stats.pop("onset_plies")
    stats["avg_onset_ply"] = (
        sum(onset_plies) / len(onset_plies) if onset_plies else None
    )

    return stats
