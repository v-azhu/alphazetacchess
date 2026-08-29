# AlphaZetaChess

**AlphaZeta 中国象棋 AI 引擎**

An open-source Chinese Chess (Xiangqi / 中国象棋) engine, built incrementally
from a rule-correct playable game toward a full search + neural-network
hybrid engine, inspired by the AlphaZero approach.

本项目从"规则正确的可玩对局"起步，逐步演进到"搜索引擎 + 神经网络"的混合式
中国象棋 AI，设计理念参考 AlphaZero，但开发路线刻意循序渐进（详见
[`docs/roadmap.md`](docs/roadmap.md)）。

---

## 当前进度 (Current Status)

- [x] 棋盘与棋子表示 (Board / Piece representation)
- [x] 七种棋子的完整走子规则 (Full move generation for all 7 piece types)
  - 车 Rook / 马 Horse (含蹩马腿 leg-blocking) / 炮 Cannon (隔子吃 screen-capture)
  - 象 Elephant (塞象眼 + 不能过河) / 士 Advisor (九宫限制) / 将 King (九宫限制)
  - 卒 Pawn (过河前后规则不同)
- [x] 合法性校验：回合规则、将军检测、飞将 (flying general) 规则
- [x] 将死 (checkmate) / 困毙 (stalemate) 判定
- [x] Minimax + Alpha-Beta 搜索引擎，基础评估函数 (material + position)，可配置搜索深度 (v0.2)
- [x] 命令行版 Human (红方) vs SearchEngine AI (黑方) 可玩对局，AI 走法可解释 (显示评估分数与搜索节点数)
- [x] AI vs AI 对局评测工具 (`tools/benchmark.py`)
- [ ] 迭代加深、置换表、走法排序、Negamax/PVS、静态搜索 (Quiescence Search) (v0.3)
- [ ] 更完善的局面评估：机动性、王/将安全、残局知识 (v0.4)
- [ ] 自我对弈与训练数据生成 (v0.5)
- [ ] 神经网络评估 / MCTS (v0.6+)

### V0.2 验收结果 (Acceptance Evidence)

按 `docs/roadmap.md` 里 V0.2 的验收标准（"AI can defeat random players" /
"AI decisions are explainable"），用 `tools/benchmark.py` 实测：

| 引擎 | 局数 | 胜 | 负 | 和 (触发步数上限) | 得分率 | 估算 Elo 差 |
|---|---|---|---|---|---|---|
| SearchEngine(depth=1) vs RandomEngine | 10 | 6 | 0 | 4 | 80% | +241 |
| SearchEngine(depth=2) vs RandomEngine | 6  | 5 | 0 | 1 | 92% | +417 |

两个深度下 SearchEngine 都是零败绩，depth=2 明显更强。默认 `AI_SEARCH_DEPTH = 2`
（详见 `src/main.py` 里的取舍说明：depth=3 已验证明显更强，但目前单步耗时可达
数十秒，优化留给 v0.3 的置换表 / 走法排序）。

完整路线图见 [`docs/roadmap.md`](docs/roadmap.md)，架构设计见
[`docs/architecture.md`](docs/architecture.md)。

---

## 快速开始 (Quick Start)

### 环境要求

```
Python 3.11+
```

当前阶段没有第三方依赖（`requirements.txt` 为空），后续引入
NumPy / PyTorch 时会在此更新。

### 运行游戏 (Human vs Random AI)

```bash
python src/main.py
```

游戏为命令行文字界面，棋盘坐标 `x` 范围 `0-8`（从左到右），`y` 范围
`0-9`（从下到上，红方在 `y=0` 一侧）。走法输入格式为：

```
起点x 起点y 终点x 终点y
```

例如红方开局把左边的车向前走一格（车一进一）：

```
0 0 0 1
```

输入 `quit` 或 `exit` 可随时退出。

### 运行测试

```bash
pip install pytest --break-system-packages   # 如尚未安装
python -m pytest -q
```

### 运行 AI vs AI 评测 (Engine Benchmark)

```bash
python tools/benchmark.py                     # 默认 10 局, depth=2
python tools/benchmark.py --games 20 --depth 1 --max-moves 150
```

按 `docs/roadmap.md` 里"Engine Benchmark"方法论：两个引擎交替执红/黑对局，
统计胜/负/和局数与估算 Elo 差。

---

## 项目结构 (Project Structure)

```
alphazetacchess/
├── docs/                     # 架构 / 设计 / 路线图文档
│   ├── architecture.md
│   ├── roadmap.md
│   ├── development.md
│   └── design/
│       ├── core-design.md
│       └── engine-design.md
├── src/
│   ├── main.py                # 命令行入口：Human vs SearchEngine AI
│   └── alphazetacchess/
│       ├── core/                # 核心层：不含任何 AI 决策逻辑
│       │   ├── piece.py          # 棋子类型 / 颜色 / Piece 对象
│       │   ├── board.py          # 棋盘表示、走子/悔棋、将军/飞将检测辅助
│       │   ├── move.py           # Move 对象
│       │   ├── move_generator.py # 七种棋子的伪合法走法生成
│       │   └── rule.py           # 合法性过滤、将军/将死/困毙判定
│       └── engine/              # 决策层：搜索 + 评估 (V0.2 新增)
│           ├── base.py           # ChessEngine 统一接口 + SearchResult
│           ├── evaluation.py     # 基础评估函数 (material + position)
│           ├── search.py         # Minimax + Alpha-Beta 搜索引擎
│           └── random_engine.py  # V0.1 随机引擎 (现作为评测基准)
├── tests/                     # pytest 测试
├── tools/
│   └── benchmark.py           # AI vs AI 对局评测工具
├── trainingdata/               # 供未来监督学习 / 开局库使用的棋谱数据
└── pyproject.toml
```

设计上，`core/` 层只负责"规则是什么"，不掺杂任何 AI 决策逻辑；`engine/`
层负责"该走哪步"，所有引擎都实现统一的 `ChessEngine.choose_move(board,
color)` 接口（`RandomEngine`、`SearchEngine`，未来的 `MCTSEngine` /
`NeuralEngine` / `HybridEngine`），彼此可以互换而不影响 Core 层或游戏主循环。
具体分层原则见 [`docs/development.md`](docs/development.md) 与
[`docs/design/engine-design.md`](docs/design/engine-design.md)。

---

## 关于困毙规则的说明

中国象棋的困毙（一方无子可走）判负规则与国际象棋不同：**在国际象棋中
无子可走是和棋，但在中国象棋中无子可走的一方直接判负**。`Rule.is_stalemate()`
只负责报告"无合法着法且未被将军"这一事实，胜负判定在游戏主循环
（`main.py`）中处理。

---

## 训练数据 (Training Data)

`trainingdata/` 目录中包含约 14 万盘棋谱（来自
[CGLemon/chinese-chess-PGN](https://github.com/CGLemon/chinese-chess-PGN) 和
[bojone/gpt_cchess](https://github.com/bojone/gpt_cchess)），预留给未来的
开局库构建、监督学习初始化策略网络等用途，目前尚未被任何代码使用。

---

## 开发原则 (Development Principles)

1. 每个版本都必须可运行 (every version must be runnable)。
2. 从简单到复杂：规则 → 搜索 → 评估 → 优化 → 学习。
3. 每一次强度提升都要可测量（AI vs AI 对局、胜率、Elo 估算）。

详见 [`docs/development.md`](docs/development.md)。

---

## License

TBD.
