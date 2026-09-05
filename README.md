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
- [x] AI vs AI 对局评测工具 (`tools/benchmark.py`, `tools/benchmark_search.py`)
- [x] 迭代加深 + 根节点走法排序 (v0.3.1)：depth=3 从 50-100+ 秒降到 6-16 秒
- [x] Zobrist 哈希 + 深度感知置换表 (v0.3.2)
- [x] Negamax 重构 + PVS 主要变例搜索 (v0.3.3)：与 v0.3.2 结果逐局面校验一致
- [x] 静态搜索 (Quiescence Search) (v0.3.4)
- [x] 更完善的局面评估：棋子位置表、王的安全性、机动性、兵形结构、子力协调 (v0.4.1-4.5，五项评估全部完成)
- [x] Web UI：可视化棋盘、点击走子、评估项开关 (`web/`，见 `docs/ui.md`)
- [x] 自我对弈数据记录 (v0.5.1)：`tools/self_play.py`，JSON-lines 格式，可断点续跑
- [x] 开局库机制 (v0.5.2)：由自我对弈数据构建，按 Zobrist 哈希去重，`use_opening_book` 可开关；开局随机化 (v0.5.2b) 修复了确定性引擎自对弈缺乏多样性的问题
- [x] 残局启发式机制 (v0.5.3)：车/炮在残局阶段的价值调整（"车赛全局，炮怕残棋"），`use_endgame_heuristics` 可开关，并配有从自我对弈数据验证假设的分析工具 (`tools/analyze_endgame.py`)
- [x] 自动化强度对比 (v0.5.4)：任意两组引擎配置互相对局，胜/负/和 + Elo 差值估计 (`tools/compare_engines.py`)，复用 v0.5.1 的对局记录格式，产出可直接被开局库/残局分析工具消费；支持 `--use-opening-book` 用于开局库质量对比
- [x] 首份真实规模数据验证：63→99 局真实对局（`data/selfplay.jsonl`），重建出 1330 个局面的真实开局库并验证可正常调用；开局库、`use_endgame_heuristics` 均得到真实的"无明显提升"零结果（20 局开局库对比 50%/50%，29 局残局启发式对比约 52%），depth=3 vs depth=2 则得到有意义的真实提升（12 局，Elo +88.7）——三条问题均已有真实数据支撑的结论，详见 `docs/v0.5-real-data-checkpoint-3.md`
- [x] MCTS 搜索骨架 (v0.6.1)：`MCTSEngine`（PUCT 选择 + 现有 `evaluate()` 作为叶子价值估计，暂无策略/价值网络），12 个测试含关键的符号约定测试与"与 alpha-beta 独立实现在必胜局面上找到同一步杀棋"的交叉验证；对阵 RandomEngine 的冒烟测试证实真实子力优势（第60步 4150:3600）但在给定的模拟次数下未必能在步数限制内形成杀棋——是符合预期的"无策略网络的原始 MCTS"特征而非 bug，详见 `docs/v0.6.1.md`
- [ ] MCTS 实际强度的真实数据验证（模拟次数调优、CLI 集成）
- [ ] 策略/价值神经网络 (v0.6.2+)

上述开局库、残局启发式与强度对比目前都是"机制已完成，但结论/常量/是否默认启用仍需真实规模数据验证"的状态——三者共用同一份自我对弈数据格式，一次本地长时间运行即可同时回答三个问题，详见
`docs/v0.5.2.md` / `docs/v0.5.3.md` / `docs/v0.5.4.md`。

详细的分版本验收数据（每次性能声明都配有实测数字）见 `docs/roadmap.md`（完整版本历史与验收记录）
与各版本单独文档，如 `docs/v0.3.1-benchmark.md` / `docs/v0.4.5.md` / `docs/v0.5.1.md` /
`docs/v0.5.2.md` / `docs/v0.5.3.md`。

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
├── docs/                     # 架构 / 设计 / 路线图文档，以及每个版本的验收记录
│   ├── architecture.md
│   ├── roadmap.md             # 完整版本历史、验收数据与开发路线图（最新）
│   ├── development.md
│   ├── ui.md                  # Web UI 设计与已知问题
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
│       │   ├── rule.py           # 合法性过滤、将军/将死/困毙判定
│       │   └── zobrist.py        # Zobrist 哈希（置换表 / 开局库键）
│       ├── engine/              # 决策层：搜索 + 评估
│       │   ├── base.py           # ChessEngine 统一接口 + SearchResult
│       │   ├── evaluation.py     # 评估函数（材料 + 可开关的评估项组合）
│       │   ├── search.py         # Negamax + Alpha-Beta + PVS + 静态搜索 + TT
│       │   ├── mobility.py       # 机动性 (V0.4.3)
│       │   ├── pawn_structure.py # 兵形结构 / 联兵 (V0.4.4)
│       │   ├── piece_coordination.py # 子力协调 (V0.4.5)
│       │   ├── endgame.py        # 残局阶段车/炮价值调整 (V0.5.3)
│       │   ├── mcts.py           # MCTS 搜索骨架 (V0.6.1)，暂用现有 evaluate() 作叶子价值
│       │   └── random_engine.py  # V0.1 随机引擎 (现作为评测基准)
│       └── selfplay/             # 自我对弈数据记录、开局库、残局分析、强度对比 (V0.5)
│           ├── recorder.py           # 对弈记录（JSON-lines）
│           ├── opening_randomization.py # 开局阶段随机化（数据多样性）
│           ├── opening_book.py       # 从记录构建开局库
│           ├── endgame_analysis.py   # 从记录验证残局启发式假设
│           └── strength_comparison.py # 两组引擎配置对局 + Elo 差值估计
├── web/                        # 本地图形化对弈 Web UI (Flask + SVG)
│   ├── server.py
│   └── static/
├── tests/                     # pytest 测试（每个版本一个测试文件）
├── tools/
│   ├── benchmark.py            # AI vs AI 对局评测工具 (vs RandomEngine 基准)
│   ├── self_play.py            # 自我对弈数据收集 CLI
│   ├── build_opening_book.py   # 从自我对弈数据构建开局库 CLI
│   ├── analyze_endgame.py      # 从自我对弈数据验证残局启发式 CLI
│   └── compare_engines.py      # 两组引擎配置强度对比 CLI
├── data/                       # 自我对弈数据（默认不入库，见 data/README.md）
├── trainingdata/               # 供未来监督学习 / 开局库使用的历史棋谱数据
└── pyproject.toml
```

设计上，`core/` 层只负责"规则是什么"，不掺杂任何 AI 决策逻辑；`engine/`
层负责"该走哪步"，所有引擎都实现统一的 `ChessEngine.choose_move(board,
color)` 接口（`RandomEngine`、`SearchEngine`，未来的 `MCTSEngine` /
`NeuralEngine` / `HybridEngine`），彼此可以互换而不影响 Core 层或游戏主循环；
`selfplay/` 层消费 `engine/` 产出的对局数据，反过来又可以为 `engine/` 提供
可选的评估项（开局库、残局启发式），二者边界单向、不循环依赖。
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
