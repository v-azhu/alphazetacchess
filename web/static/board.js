const CELL = 60;
const MARGIN = 40;
const COLS = 9;
const ROWS = 10;

const PIECE_CHARS = {
  RED: { KING: "帥", ADVISOR: "仕", ELEPHANT: "相", ROOK: "俥", HORSE: "傌", CANNON: "炮", PAWN: "兵" },
  BLACK: { KING: "將", ADVISOR: "士", ELEPHANT: "象", ROOK: "車", HORSE: "馬", CANNON: "砲", PAWN: "卒" },
};

const svg = document.getElementById("board");
const statusEl = document.getElementById("status");
const logEl = document.getElementById("log");
const newGameBtn = document.getElementById("new-game-btn");
const depthSelect = document.getElementById("depth-select");

let boardState = null;
let selected = null;      // {x, y} of the currently selected piece, or null
let legalTargets = [];    // [{x, y}, ...] for the current selection
let lastMove = null;      // {from: {x,y}, to: {x,y}} of the most recent move (either side)
let busy = false;
let aiThinking = false;   // true while awaiting POST /api/ai_move

function px(x) { return MARGIN + x * CELL; }
function py(y) { return MARGIN + (ROWS - 1 - y) * CELL; } // y=0 (Red's back rank) at the bottom

function svgEl(tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function buildStaticGrid() {
  const gridLayer = svgEl("g", { id: "grid-layer" });

  // Horizontal lines (one per row).
  for (let row = 0; row < ROWS; row++) {
    gridLayer.appendChild(svgEl("line", {
      class: "grid-line",
      x1: px(0), y1: py(row), x2: px(COLS - 1), y2: py(row),
    }));
  }

  // Vertical lines: full height for the two border columns, split
  // around the river (between row 4 and row 5) for the interior ones.
  for (let col = 0; col < COLS; col++) {
    if (col === 0 || col === COLS - 1) {
      gridLayer.appendChild(svgEl("line", {
        class: "grid-line",
        x1: px(col), y1: py(0), x2: px(col), y2: py(ROWS - 1),
      }));
    } else {
      gridLayer.appendChild(svgEl("line", {
        class: "grid-line",
        x1: px(col), y1: py(0), x2: px(col), y2: py(4),
      }));
      gridLayer.appendChild(svgEl("line", {
        class: "grid-line",
        x1: px(col), y1: py(5), x2: px(col), y2: py(ROWS - 1),
      }));
    }
  }

  // Palace diagonals (九宫), Red at the bottom (rows 0-2), Black at
  // the top (rows 7-9), both spanning columns 3-5.
  const palaceDiagonals = [
    [3, 0, 5, 2], [5, 0, 3, 2],
    [3, 7, 5, 9], [5, 7, 3, 9],
  ];
  for (const [x1, y1, x2, y2] of palaceDiagonals) {
    gridLayer.appendChild(svgEl("line", {
      class: "palace-line", x1: px(x1), y1: py(y1), x2: px(x2), y2: py(y2),
    }));
  }

  // River text.
  const riverY = (py(4) + py(5)) / 2 + 8;
  gridLayer.appendChild(svgEl("text", {
    class: "river-text", x: px(1.5), y: riverY,
  })).textContent = "楚 河";
  gridLayer.appendChild(svgEl("text", {
    class: "river-text", x: px(6.5), y: riverY,
  })).textContent = "漢 界";

  svg.appendChild(gridLayer);

  // One invisible click-target circle per intersection -- all board
  // interaction (selecting a piece, choosing a destination) routes
  // through these, so empty squares and occupied squares behave the
  // same way from a click-handling perspective.
  const pointsLayer = svgEl("g", { id: "points-layer" });
  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      const point = svgEl("circle", {
        class: "point", cx: px(x), cy: py(y), r: 26,
        "data-x": x, "data-y": y,
      });
      point.addEventListener("click", () => onPointClick(x, y));
      pointsLayer.appendChild(point);
    }
  }
  svg.appendChild(pointsLayer);

  svg.appendChild(svgEl("g", { id: "lastmove-layer" }));
  svg.appendChild(svgEl("g", { id: "pieces-layer" }));
  svg.appendChild(svgEl("g", { id: "hints-layer" }));
}

function clearLayer(id) {
  const layer = document.getElementById(id);
  while (layer.firstChild) layer.removeChild(layer.firstChild);
}

function renderPieces() {
  clearLayer("pieces-layer");
  const layer = document.getElementById("pieces-layer");

  for (let y = 0; y < ROWS; y++) {
    for (let x = 0; x < COLS; x++) {
      const cell = boardState.board[y][x];
      if (!cell) continue;

      const isSelected = selected && selected.x === x && selected.y === y;
      const group = svgEl("g", { class: "piece-group" });

      const circleClass = cell.color === "RED" ? "piece-circle-red" : "piece-circle-black";
      const circle = svgEl("circle", {
        class: circleClass + (isSelected ? " piece-selected" : ""),
        cx: px(x), cy: py(y), r: 24,
      });
      const text = svgEl("text", {
        class: cell.color === "RED" ? "piece-text-red" : "piece-text-black",
        x: px(x), y: py(y),
      });
      text.textContent = PIECE_CHARS[cell.color][cell.type];

      group.appendChild(circle);
      group.appendChild(text);
      layer.appendChild(group);
    }
  }
}

function renderHints() {
  clearLayer("hints-layer");
  const layer = document.getElementById("hints-layer");

  for (const target of legalTargets) {
    layer.appendChild(svgEl("circle", {
      class: "move-hint", cx: px(target.x), cy: py(target.y), r: 10,
    }));
  }
}

function renderLastMove() {
  clearLayer("lastmove-layer");
  if (!lastMove) return;
  const layer = document.getElementById("lastmove-layer");

  for (const pos of [lastMove.from, lastMove.to]) {
    layer.appendChild(svgEl("circle", {
      class: "last-move-marker", cx: px(pos.x), cy: py(pos.y), r: 27,
    }));
  }
}

function colorLabel(color) {
  return color === "RED" ? '<span class="turn-red">红方</span>' : '<span class="turn-black">黑方</span>';
}

function renderStatus() {
  if (!boardState) {
    statusEl.innerHTML = "加载中...";
    return;
  }

  let html = `当前走棋: ${colorLabel(boardState.current_player)}`;

  if (boardState.game_over) {
    const winner = colorLabel(boardState.winner);
    const reason = boardState.is_checkmate ? "被将死 (checkmate)" : "无子可走 (stalemate/困毙)";
    html = `<div class="game-over">${colorLabel(boardState.current_player)} ${reason}，${winner} 获胜！</div>`;
  } else if (aiThinking) {
    html += ` &nbsp; <span class="warning">🤔 AI 正在思考...</span>`;
  } else if (boardState.in_check) {
    html += ` &nbsp; <span class="warning">正被将军！</span>`;
  }

  statusEl.innerHTML = html;
}

function appendLog(html) {
  const entry = document.createElement("div");
  entry.className = "log-entry";
  entry.innerHTML = html;
  logEl.insertBefore(entry, logEl.firstChild);
}

function describeMove(color, move) {
  if (!move) return "";
  const who = color === "RED" ? '<span class="who-red">红方</span>' : '<span class="who-black">黑方</span>';
  const capture = move.captured ? `，吃子 ${move.captured}` : "";
  return `${who}: (${move.from.x},${move.from.y}) → (${move.to.x},${move.to.y})${capture}`;
}

function setBusy(value) {
  busy = value;
  newGameBtn.disabled = value;
}

function render() {
  renderPieces();
  renderHints();
  renderLastMove();
  renderStatus();
}

function resetSelection() {
  selected = null;
  legalTargets = [];
}

async function onPointClick(x, y) {
  if (busy || !boardState || boardState.game_over) return;
  if (boardState.current_player !== boardState.human_color) return;

  const cell = boardState.board[y][x];

  if (selected) {
    const isTarget = legalTargets.some((t) => t.x === x && t.y === y);
    if (isTarget) {
      await playMove(selected, { x, y });
      return;
    }
    if (cell && cell.color === boardState.human_color) {
      await selectPiece(x, y);
      return;
    }
    resetSelection();
    render();
    return;
  }

  if (cell && cell.color === boardState.human_color) {
    await selectPiece(x, y);
  }
}

async function selectPiece(x, y) {
  const res = await fetch("/api/legal_moves", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ x, y }),
  });
  const data = await res.json();
  selected = { x, y };
  legalTargets = data.moves;
  render();
}

async function playMove(from, to) {
  setBusy(true);
  resetSelection();
  render();

  try {
    // Step 1: apply ONLY the human's move, and render immediately --
    // this is the actual fix (previously a single request did both
    // the human move AND the AI's reply before responding at all, so
    // Red's own piece never visibly moved until the AI's multi-second
    // "thinking" was already done too; see docs/ui.md "Bug history").
    const res = await fetch("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from, to }),
    });
    const data = await res.json();

    if (!res.ok) {
      appendLog(`<span class="warning">走法被拒绝: ${data.error || "未知错误"}</span>`);
      setBusy(false);
      return;
    }

    boardState = data;

    if (data.human_move) {
      appendLog(describeMove(boardState.human_color, data.human_move));
      lastMove = data.human_move;
    }

    render(); // <-- Red's piece is now visibly in its new position.

    if (boardState.game_over) {
      setBusy(false);
      return;
    }

    // Step 2: separately trigger and wait for the AI's reply, with a
    // "thinking" indicator shown while it's computing.
    aiThinking = true;
    renderStatus();

    const aiRes = await fetch("/api/ai_move", { method: "POST" });
    const aiData = await aiRes.json();

    aiThinking = false;

    if (!aiRes.ok) {
      appendLog(`<span class="warning">AI 出错: ${aiData.error || "未知错误"}</span>`);
      setBusy(false);
      return;
    }

    boardState = aiData;

    if (aiData.ai_move) {
      const info = aiData.ai_info;
      appendLog(
        describeMove(boardState.ai_color, aiData.ai_move) +
        `<span class="meta">评估分数 score=${info.score} · 深度 depth=${info.depth} · ` +
        `节点 nodes=${info.nodes_evaluated} · 用时 ${info.elapsed_seconds}s</span>`
      );
      lastMove = aiData.ai_move;
    }

    render();
  } finally {
    setBusy(false);
  }
}

async function startNewGame() {
  setBusy(true);
  resetSelection();
  lastMove = null;
  logEl.innerHTML = "";

  const aiDepth = parseInt(depthSelect.value, 10);
  const res = await fetch("/api/new_game", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ai_depth: aiDepth }),
  });
  boardState = await res.json();
  render();
  setBusy(false);
}

async function loadInitialState() {
  const res = await fetch("/api/state");
  boardState = await res.json();
  if (boardState.ai_depth) depthSelect.value = String(boardState.ai_depth);
  render();
}

newGameBtn.addEventListener("click", startNewGame);

buildStaticGrid();
loadInitialState();
