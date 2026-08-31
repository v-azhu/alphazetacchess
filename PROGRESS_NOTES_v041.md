# V0.4.1 进度快照（棋子位置表 Piece-Square Tables）

生成时间：本次会话恢复后立即打包，测试全绿状态（51/51）。

## 已完成

1. **`src/alphazetacchess/engine/evaluation.py`**：给 马/炮/车/兵 四种棋子加了
   基于中国象棋常识手工构造的位置分表（非抄自某个具体调好参的引擎，逻辑
   在代码注释里逐条写明）：
   - 马：中心格奖励高，边角格奖励为0（马的机动性极度依赖周围空格）；
     另有"发展阶段"奖励，过河后活跃但深入敌营太远会打折（防止孤马冒进）。
   - 炮：中心格奖励幅度比马小（炮不靠占中心取胜）；保留在己方炮位（红方
     y=2/黑方y=7）时奖励较高，符合"炮二平五"这类开局理论；深入敌方无子
     可架（缺少炮架）时奖励转负。
   - 车：奖励幅度最小（车本来哪里都强），沉底车（深入对方底线）有加分，
     对应"沉底车"这一经典强势模式。
   - 兵：过河前后用不同的列奖励表；过河后中路兵奖励远高于边兵，对应"边兵
     价值最低"这条象棋常识。
   - 王/仕/象刻意不在这次范围内（可动格数太少，且"将的安全"被 roadmap
     列为单独一项，不是简单的格子查表能覆盖的）。
   - `evaluate()` 新增 `use_piece_square_tables` 开关（默认True），设为
     False 会精确复现 V0.2/V0.3 的老评估公式，作为A/B对照基线。

2. **`src/alphazetacchess/engine/search.py`**：`SearchEngine.__init__` 新增
   `use_piece_square_tables=True` 构造参数；所有4处调用 `evaluate()` 的地方
   都已经接上这个开关（含主搜索的depth==0分支、静态搜索里的stand-pat和安全
   上限分支）。

3. **`tests/test_evaluation_v041.py`**（6个新测试，已全部通过）：
   - 对称性测试（开局局面双方评分互为相反数）
   - 同等子力下，马在中心 vs 马在角落，位置表必须让中心的分数更高
   - 过河兵：中路 vs 边路，位置表必须让中路分数更高
   - `use_piece_square_tables=False` 精确复现旧公式（手工验证具体数值）
   - 开关确实改变分数（正向验证）
   - 通过 `SearchEngine._quiescence()` 直接调用，验证开关真的传导到了
     搜索引擎内部（绕开"搜索本身能在1步内把马挪走"这种会掩盖差异的干扰）

4. **完整测试套件**：51个测试全部通过。

## 还没做完（下一步接着做）

- [ ] **playing-strength 基准测试还没跑出有效数据**：depth=1、80步上限
      跑了6局 PST开 vs PST关，结果是**6局全部和棋**（撞到步数上限，双方
      在depth=1这么浅的搜索下都没能强杀开对方）——这个结果没有信息量，
      说明 depth=1 太弱，测不出PST的实际强度差异。下一步应该提高深度
      （depth=2）并/或提高步数上限，重新测。深度2每步大概0.5-5秒，一局
      预计比depth=1慢很多，需要控制局数以免超时。
- [ ] `docs/v0.4.1.md` 验收文档还没写（参照 `docs/v0.3.4.md`/`v0.3.5.md`
      的格式：目标/设计/范围/验收标准/实测数据/已知局限/下一步）。
- [ ] `docs/roadmap.md` 里 V0.4 那一节还没更新（目前还是 V0.4 CURRENT 但
      没有子版本记录，需要加上 V0.4.1 COMPLETE + 数据，或者如果基准测试
      还没做完，先如实标注"实现完成，基准测试进行中"）。
- [ ] `PROGRESS_NOTES.md`（顶层那份）还没更新到V0.4.1状态。

## 如果沙盒又没了，怎么从这份文件继续

把这个 zip 里的 `evaluation.py`、`search.py` 覆盖到仓库对应位置，
`tests/test_evaluation_v041.py` 放进 `tests/` 目录，本地跑
`pytest tests/test_evaluation_v041.py` 验证6个测试都过，然后跑
`pytest` 全量测试确认51个全绿，就是在这个基础上继续做上面"还没做完"
的部分——下一步具体命令：

```
python -c "
import sys; sys.path.insert(0,'tools'); sys.path.insert(0,'src')
from benchmark import run_match
from alphazetacchess.engine.search import SearchEngine
run_match(
    lambda: SearchEngine(depth=2, use_piece_square_tables=True),
    lambda: SearchEngine(depth=2, use_piece_square_tables=False),
    games=4, max_moves=100,
)
"
```
