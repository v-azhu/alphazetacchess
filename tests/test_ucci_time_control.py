import time
from threading import Event

from alphazetacchess.core.rule import Rule
from alphazetacchess.engine.base import SearchResult
from alphazetacchess.protocol.ucci import UCCIEngine
from alphazetacchess.protocol.search_limits import SearchLimits


class TimedBlockingSearchEngine:
    depth = 3

    def __init__(self):
        self.started = Event()
        self.stopped = Event()

    def choose_move(self, board, color, stop_event=None):
        self.started.set()
        while not stop_event.is_set():
            time.sleep(0.001)
        self.stopped.set()
        move = Rule.generate_legal_moves(board, color)[0]
        return SearchResult(move, 0, 1, 1)


def test_search_limits_allocate_conservative_time_budget():
    limits = SearchLimits(time_ms=10000, increment_ms=1000, movestogo=10)

    assert limits.time_budget_ms() == 850


def test_ucci_movetime_uses_milliseconds():
    engine = UCCIEngine()

    limits = engine._parse_go(["movetime", "2500"])

    assert limits.movetime_ms == 2500
    assert limits.time_ms is None


def test_ucci_time_defaults_to_seconds():
    engine = UCCIEngine()

    limits = engine._parse_go(["time", "10", "movestogo", "10"])

    assert limits.time_ms == 10000
    assert limits.movestogo == 10


def test_ucci_usemillisec_switches_clock_units():
    engine = UCCIEngine()
    engine.handle_line("setoption name usemillisec true")

    limits = engine._parse_go(["time", "10000", "increment", "100"])

    assert limits.time_ms == 10000
    assert limits.increment_ms == 100


def test_ucci_time_control_stops_search_without_explicit_stop():
    search_engine = TimedBlockingSearchEngine()
    engine = UCCIEngine(search_engine)

    assert engine.handle_line("go movetime 20") == []
    assert search_engine.started.wait(timeout=1)
    assert search_engine.stopped.wait(timeout=1)

    responses = engine.handle_line("")

    assert len(responses) == 1
    assert responses[0].startswith("bestmove ")
    assert engine._searching is False
