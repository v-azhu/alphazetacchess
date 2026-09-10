"""V0.9.1: confirms MCTSEngine is drop-in compatible with UCCIEngine's
async search worker, now that it supports the same
choose_move(board, color, stop_event=...) contract SearchEngine has
had since V0.7.1/V0.7.2. Uses a real MCTSEngine (not a fake), unlike
tests/test_ucci.py's own tests, specifically to catch any interface
mismatch a fake double would silently paper over.
"""
from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.engine.mcts import MCTSEngine
from alphazetacchess.protocol.ucci import UCCIEngine


def test_mcts_engine_completes_a_full_go_bestmove_cycle_via_ucci():
    engine = UCCIEngine(MCTSEngine(simulations=20))

    assert engine.handle_line("ucci")[-1] == "ucciok"
    assert engine.handle_line("isready") == ["readyok"]
    assert engine.handle_line("go depth 1") == []

    thread = engine._search_thread
    assert thread is not None
    thread.join(timeout=10)
    assert not thread.is_alive()

    responses = engine.handle_line("")
    assert responses
    bestmove_line = next(r for r in responses if r.startswith("bestmove"))
    move = bestmove_line.split()[1]
    assert len(move) == 4
    GameRecord.move_from_iccs(move)  # raises if not a well-formed ICCS move


def test_mcts_engine_responds_to_stop_mid_search():
    engine = UCCIEngine(MCTSEngine(simulations=1_000_000))

    engine.handle_line("ucci")
    assert engine.handle_line("go depth 1") == []
    responses = engine.handle_line("stop")

    assert any(r.startswith("bestmove") for r in responses)
