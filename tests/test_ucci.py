import io

import pytest

from alphazetacchess.core.game_record import GameRecord
from alphazetacchess.engine.base import SearchResult
from alphazetacchess.protocol.ucci import UCCIEngine, UCCIError, run_ucci


INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"


class FakeSearchEngine:
    depth = 3

    def choose_move(self, board, color):
        from alphazetacchess.core.rule import Rule

        move = Rule.generate_legal_moves(board, color)[0]
        return SearchResult(move, 0, 1, self.depth)


def test_ucci_handshake():
    engine = UCCIEngine(FakeSearchEngine())

    responses = engine.handle_line("ucci")

    assert responses[-1] == "ucciok"
    assert "id name AlphaZetaChess" in responses
    assert "id author v-azhu" in responses


def test_ucci_ready():
    assert UCCIEngine(FakeSearchEngine()).handle_line("isready") == ["readyok"]


def test_position_fen_replays_moves():
    engine = UCCIEngine(FakeSearchEngine())

    engine.handle_line(
        "position fen " + INITIAL_FEN + " moves b0c2 b9c7 c2b0 c7b9"
    )

    assert engine.current_fen() == INITIAL_FEN
    assert engine.record.moves == ["b0c2", "b9c7", "c2b0", "c7b9"]
    assert len(engine.board.position_history) == 5


def test_position_rejects_startpos():
    engine = UCCIEngine(FakeSearchEngine())

    with pytest.raises(UCCIError, match="position fen"):
        engine.handle_line("position startpos")


def test_go_depth_returns_iccs_bestmove():
    engine = UCCIEngine(FakeSearchEngine())

    responses = engine.handle_line("go depth 1")

    assert len(responses) == 1
    assert responses[0].startswith("bestmove ")
    move = responses[0].split()[1]
    assert len(move) == 4
    GameRecord.move_from_iccs(move)


def test_go_depth_zero_returns_nobestmove():
    engine = UCCIEngine(FakeSearchEngine())

    assert engine.handle_line("go depth 0") == ["nobestmove"]


def test_quit_sets_flag():
    engine = UCCIEngine(FakeSearchEngine())

    assert engine.handle_line("quit") == []
    assert engine.quit_requested is True


def test_run_ucci_processes_lines():
    input_stream = io.StringIO("ucci\nisready\nquit\n")
    output_stream = io.StringIO()

    # run_ucci creates the real engine, but these commands do not search.
    run_ucci(input_stream, output_stream)

    output = output_stream.getvalue().splitlines()
    assert output[-1] == "readyok"
    assert "ucciok" in output
