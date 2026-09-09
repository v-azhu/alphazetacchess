"""Minimal UCCI protocol adapter for AlphaZetaChess.

The adapter intentionally keeps protocol concerns outside the search engine.
UCCI positions are represented by a FEN plus the move list from that position,
which also lets GameRecord reconstruct exact-position repetition history.
"""

from threading import Event, Lock, Thread, Timer

from ..core.board import Board
from ..core.fen import board_from_fen, board_to_fen
from ..core.game_record import GameRecord
from ..core.rule import Rule
from ..engine.search import SearchCancelled, SearchEngine
from .search_limits import SearchLimits


class UCCIError(ValueError):
    """Raised when a UCCI command is malformed or cannot be applied."""


class UCCIEngine:
    """UCCI command processor with an asynchronous search worker."""

    NAME = "AlphaZetaChess"
    AUTHOR = "v-azhu"

    def __init__(self, search_engine=None):
        self.search_engine = search_engine or SearchEngine(depth=3)
        self.board = Board()
        self.record = GameRecord.from_board(self.board)
        self.debug = False
        self.quit_requested = False
        self.use_millisec = False
        self._searching = False
        self._search_thread = None
        self._search_stop_event = None
        self._search_lock = Lock()
        self._pending_responses = []

    def handle_line(self, line):
        line = line.strip()
        if not line:
            # Empty input is used by the tests and by simple polling clients to
            # retrieve asynchronous search output. Give a worker that has just
            # finished a short opportunity to publish its final responses.
            with self._search_lock:
                thread = self._search_thread
                pending = bool(self._pending_responses)
            if thread is not None and not pending:
                thread.join(timeout=0.1)
            return self._drain_responses()

        parts = line.split()
        command = parts[0].lower()
        if command == "ucci":
            return self._drain_responses() + [
                f"id name {self.NAME}",
                f"id author {self.AUTHOR}",
                "option usemillisec type check default false",
                "option newgame type button",
                "ucciok",
            ]
        if command == "isready":
            return self._drain_responses() + ["readyok"]
        if command == "debug":
            if len(parts) != 2 or parts[1].lower() not in {"on", "off"}:
                raise UCCIError("debug expects 'on' or 'off'")
            self.debug = parts[1].lower() == "on"
            return self._drain_responses()
        if command == "setoption":
            self._handle_setoption(parts[1:])
            return self._drain_responses()
        if command == "position":
            self._handle_position(parts[1:])
            return self._drain_responses()
        if command == "go":
            responses = self._drain_responses()
            return responses + self._handle_go(parts[1:])
        if command == "stop":
            return self._drain_responses() + self._handle_stop()
        if command in {"quit", "bye"}:
            self._handle_stop()
            self.quit_requested = True
            return self._drain_responses()
        raise UCCIError(f"Unknown UCCI command: {parts[0]}")

    def _handle_setoption(self, args):
        if len(args) < 2 or args[0].lower() != "name":
            raise UCCIError("setoption requires 'name'")
        name = args[1].lower()
        if name == "newgame":
            self._ensure_not_searching()
            if len(args) > 2:
                raise UCCIError("newgame does not accept a value")
            self._reset_position()
            return
        if name == "usemillisec":
            value_args = args[2:]
            if value_args and value_args[0].lower() == "value":
                value_args = value_args[1:]
            if len(value_args) != 1 or value_args[0].lower() not in {"true", "false"}:
                raise UCCIError("usemillisec expects true or false")
            self.use_millisec = value_args[0].lower() == "true"
            return
        raise UCCIError(f"Unsupported UCCI option: {args[1]}")

    def _handle_position(self, args):
        self._ensure_not_searching()
        if not args or args[0].lower() != "fen":
            raise UCCIError("UCCI requires 'position fen <fen> [moves ...]'")
        try:
            moves_index = next(
                index
                for index, token in enumerate(args[1:], start=1)
                if token.lower() == "moves"
            )
        except StopIteration:
            moves_index = len(args)
        fen_fields = args[1:moves_index]
        if len(fen_fields) != 6:
            raise UCCIError("FEN must contain exactly six fields")
        fen = " ".join(fen_fields)
        move_texts = args[moves_index + 1:] if moves_index < len(args) else []
        try:
            record = GameRecord.from_moves(fen, move_texts)
            board = record.replay()
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise UCCIError(f"Invalid position: {exc}") from exc
        self.record = record
        self.board = board

    def _handle_go(self, args):
        self._ensure_not_searching()
        limits = self._parse_go(args)
        if limits.depth == 0:
            return ["nobestmove"]
        legal_moves = Rule.generate_legal_moves(self.board, self.board.current_player)
        if not legal_moves:
            return ["nobestmove"]
        if limits.depth is not None:
            self.search_engine.depth = limits.depth
        search_fen = board_to_fen(self.board)
        stop_event = Event()
        with self._search_lock:
            self._searching = True
            self._search_stop_event = stop_event
            self._search_thread = Thread(
                target=self._search_worker,
                args=(search_fen, stop_event, limits),
                name="AlphaZetaChess-search",
                daemon=True,
            )
            self._search_thread.start()
        return []

    def _parse_go(self, args):
        values = {}
        index = 0
        integer_fields = {
            "depth",
            "time",
            "opptime",
            "increment",
            "oppincrement",
            "movestogo",
        }
        while index < len(args):
            name = args[index].lower()
            if name not in integer_fields and name != "movetime":
                raise UCCIError(f"Unsupported UCCI go parameter: {args[index]}")
            if index + 1 >= len(args):
                raise UCCIError(f"Missing value for go parameter: {args[index]}")
            try:
                value = int(args[index + 1])
            except ValueError as exc:
                raise UCCIError(f"Invalid value for go parameter: {args[index]}") from exc
            if value < 0:
                raise UCCIError(f"Negative value for go parameter: {args[index]}")
            values[name] = value
            index += 2
        if "depth" in values and values["depth"] == 0:
            return SearchLimits(depth=0)
        if "movetime" in values and ("time" in values or "opptime" in values):
            raise UCCIError("movetime cannot be combined with time/opptime")

        def normalize_time(name):
            if name not in values:
                return None
            return values[name] if self.use_millisec else values[name] * 1000

        return SearchLimits(
            depth=values.get("depth", self.search_engine.depth),
            movetime_ms=values.get("movetime"),
            time_ms=normalize_time("time"),
            opptime_ms=normalize_time("opptime"),
            increment_ms=normalize_time("increment") or 0,
            oppincrement_ms=normalize_time("oppincrement") or 0,
            movestogo=values.get("movestogo"),
        )

    def _search_worker(self, search_fen, stop_event, limits):
        timer = None
        responses = ["nobestmove"]
        try:
            board = board_from_fen(search_fen)
            color = board.current_player
            budget_ms = limits.time_budget_ms()
            if budget_ms is not None:
                timer = Timer(budget_ms / 1000.0, stop_event.set)
                timer.daemon = True
                timer.start()
            result = self.search_engine.choose_move(board, color, stop_event=stop_event)
            if result.best_move is not None:
                move = GameRecord.move_to_iccs(result.best_move)
                if stop_event.is_set():
                    responses = [f"bestmove {move}"]
                else:
                    responses = [
                        f"info depth {result.depth} nodes {result.nodes_evaluated} pv {move}",
                        f"bestmove {move}",
                    ]
        except SearchCancelled:
            responses = ["nobestmove"]
        except Exception as exc:
            responses = [f"info string search error {exc}", "nobestmove"]
        finally:
            if timer is not None:
                timer.cancel()
            with self._search_lock:
                self._pending_responses.extend(responses)
                self._searching = False
                self._search_stop_event = None
                self._search_thread = None

    def _handle_stop(self):
        with self._search_lock:
            thread = self._search_thread
            stop_event = self._search_stop_event
        if thread is None:
            return self._drain_responses()
        if stop_event is not None:
            stop_event.set()
        thread.join()
        return self._drain_responses()

    def _drain_responses(self):
        with self._search_lock:
            responses = list(self._pending_responses)
            self._pending_responses.clear()
        return responses

    def _ensure_not_searching(self):
        with self._search_lock:
            if self._searching:
                raise UCCIError("Search is in progress; send 'stop' first")

    def _reset_position(self):
        self.board = Board()
        self.record = GameRecord.from_board(self.board)

    def current_fen(self):
        """Return the current UCCI position as FEN."""
        return board_to_fen(self.board)


def run_ucci(input_stream, output_stream, engine=None):
    """Run a line-oriented UCCI loop over file-like streams."""
    engine = engine or UCCIEngine()
    for line in input_stream:
        responses = engine.handle_line(line)
        for response in responses:
            output_stream.write(response + "\n")
            output_stream.flush()
        if engine.quit_requested:
            break
