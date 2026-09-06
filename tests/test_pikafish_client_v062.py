"""V0.6.2 tests for neural/pikafish_client.py.

Uses a real subprocess (tests/fixtures/fake_uci_engine.py) rather than
mocking subprocess.Popen, so the actual stdin/stdout plumbing and
`info` line parsing get exercised end to end. See pikafish_client.py's
own module docstring for why this is the right level of testing given
this project can't depend on a real Pikafish binary being present.
"""

import os
import sys

from alphazetacchess.neural.pikafish_client import PikafishClient, mate_score_to_cp

_FAKE_ENGINE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fixtures", "fake_uci_engine.py"
)
_STARTING_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


def fake_engine_command(score_kind, score_value):
    return [sys.executable, _FAKE_ENGINE, score_kind, str(score_value)]


def test_handshake_completes_without_hanging_or_raising():
    client = PikafishClient(fake_engine_command("cp", 0), movetime_ms=50)
    client.close()


def test_evaluate_fen_parses_a_cp_score():
    client = PikafishClient(fake_engine_command("cp", 37), movetime_ms=50)

    result = client.evaluate_fen(_STARTING_FEN)

    assert result["score_cp"] == 37
    assert result["mate_in"] is None
    assert result["best_move"] == "a0a1"

    client.close()


def test_evaluate_fen_parses_a_mate_score():
    client = PikafishClient(fake_engine_command("mate", 5), movetime_ms=50)

    result = client.evaluate_fen(_STARTING_FEN)

    assert result["score_cp"] is None
    assert result["mate_in"] == 5

    client.close()


def test_evaluate_fen_parses_a_negative_mate_score():
    client = PikafishClient(fake_engine_command("mate", -3), movetime_ms=50)

    result = client.evaluate_fen(_STARTING_FEN)

    assert result["mate_in"] == -3

    client.close()


def test_client_can_be_used_as_a_context_manager():
    with PikafishClient(fake_engine_command("cp", 100), movetime_ms=50) as client:
        result = client.evaluate_fen(_STARTING_FEN)
        assert result["score_cp"] == 100


def test_multiple_evaluate_calls_reuse_the_same_process():
    client = PikafishClient(fake_engine_command("cp", 15), movetime_ms=50)

    first = client.evaluate_fen(_STARTING_FEN)
    second = client.evaluate_fen(_STARTING_FEN)

    assert first["score_cp"] == 15
    assert second["score_cp"] == 15  # fake engine always says the same thing,
    #                                   but this confirms the process survives
    #                                   a second request rather than needing
    #                                   to be relaunched.
    client.close()


# ---------------------------------------------------------------------------
# mate_score_to_cp
# ---------------------------------------------------------------------------

def test_mate_score_to_cp_sign_matches_who_is_winning():
    assert mate_score_to_cp(3) > 0
    assert mate_score_to_cp(-3) < 0


def test_mate_score_to_cp_closer_mate_scores_higher_magnitude():
    close_mate = mate_score_to_cp(1)
    far_mate = mate_score_to_cp(20)

    assert close_mate > far_mate > 0
