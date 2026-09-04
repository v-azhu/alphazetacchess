"""V0.5.4 automated strength comparison between two engine configurations.

Extends V0.5.1's self-play infrastructure from "one configuration
playing itself" (`tools/self_play.py`) to "configuration A vs
configuration B", with an Elo-style estimate of the difference --
exactly what `tools/self_play.py`'s own docstring flagged as "V0.5.4's
planned strength comparison between configurations" when it was
written, and what `docs/roadmap.md`'s V0.5.3 hand-off named as the
next increment.

Deliberately reuses `selfplay.recorder.play_recorded_game` (the same
function V0.5.1 built and V0.5.2/V0.5.3's tooling both consume
records from) rather than re-implementing a play loop -- games run
through `run_comparison_match` are automatically full, valid V0.5.1
self-play records, and can be appended to the same `data/selfplay.jsonl`
corpus that feeds the opening book and endgame-heuristic tooling.
`tools/benchmark.py`'s existing SearchEngine-vs-RandomEngine quick
sanity check is untouched -- this is a new, complementary tool for the
configuration-vs-configuration question that benchmark.py was never
designed to answer (RandomEngine has no configuration to compare).
"""

import math

from .recorder import play_recorded_game, append_record


def estimate_elo_diff(win_rate):
    """
    Standard Elo-difference estimate from a win rate (draws counted as
    half a point). Returns None at the 0%/100% extremes, where the
    formula is undefined. Same formula as tools/benchmark.py's own
    `estimate_elo_diff` -- duplicated rather than imported, since
    `tools/` scripts are thin CLI wrappers by convention in this
    project (see build_opening_book.py, analyze_endgame.py) and
    shouldn't be import targets for `src/` modules.
    """
    if win_rate <= 0 or win_rate >= 1:
        return None
    return 400 * math.log10(win_rate / (1 - win_rate))


def run_comparison_match(
    engine_a_factory,
    engine_b_factory,
    games,
    max_moves,
    a_config=None,
    b_config=None,
    output_path=None,
    on_game_complete=None,
    board_factory=None,
):
    """
    Play `games` games between two engine configurations, alternating
    which side (Red/Black) each plays every game so neither enjoys a
    systematic first-move advantage. Each game is played and recorded
    via `play_recorded_game` (so results are true V0.5.1 records, not
    a separate ad hoc format), and appended to `output_path` if given.

    `engine_a_factory`/`engine_b_factory`: zero-arg callables returning
    a fresh engine instance each time (a fresh instance per game keeps
    per-game state -- e.g. RandomizedOpeningEngine's RNG state, or
    SearchEngine's transposition table -- from leaking between games,
    the same reasoning tools/self_play.py's `build_engine` already
    follows).

    `a_config`/`b_config`: opaque dicts describing each side's
    configuration, stored in every record exactly like
    `play_recorded_game` already does for `red_config`/`black_config`.

    `on_game_complete`, if given, is called after each game as
    `on_game_complete(game_index, record, a_is_red)` -- purely for
    progress reporting (see tools/compare_engines.py); this module
    intentionally does no printing itself, matching every other
    `selfplay/*.py` module (recorder.py, opening_book.py,
    endgame_analysis.py all leave printing to their `tools/*.py`
    callers).

    `board_factory`, if given, is a zero-arg callable returning a
    fresh starting `Board` for each game (instead of the default new
    game). Exists mainly for tests that want every game to start from
    a specific, deterministic position -- must return a genuinely new
    `Board` object each call (not the same mutated instance), since
    `play_recorded_game` applies moves directly onto whatever board it
    is given.

    Returns:
        {
            "games": <int>,
            "a_wins": <int>, "b_wins": <int>, "draws": <int>,
            "a_score_rate": <float, 0-1, draws counted as 0.5>,
            "elo_diff": <float or None>,
        }
    """
    a_wins = 0
    b_wins = 0
    draws = 0

    for i in range(games):
        # Alternate colors every game, same convention as
        # tools/benchmark.py's run_match.
        a_is_red = i % 2 == 0
        if a_is_red:
            engine_red, engine_black = engine_a_factory(), engine_b_factory()
            red_config, black_config = a_config, b_config
        else:
            engine_red, engine_black = engine_b_factory(), engine_a_factory()
            red_config, black_config = b_config, a_config

        record = play_recorded_game(
            engine_red, engine_black, max_moves,
            red_config=red_config, black_config=black_config,
            board=board_factory() if board_factory is not None else None,
        )

        if output_path is not None:
            append_record(output_path, record)

        result = record["result"]
        if result == "DRAW":
            draws += 1
        elif (result == "RED_WINS") == a_is_red:
            a_wins += 1
        else:
            b_wins += 1

        if on_game_complete is not None:
            on_game_complete(i, record, a_is_red)

    a_score_rate = (a_wins + 0.5 * draws) / games if games else 0.0

    return {
        "games": games,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "draws": draws,
        "a_score_rate": a_score_rate,
        "elo_diff": estimate_elo_diff(a_score_rate),
    }
