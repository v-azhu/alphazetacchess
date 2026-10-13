# Agent Kickoff Prompts (V0.11–V0.12.0)

Status: **READY** — companion to [`v0.11.0.md`](v0.11.0.md); standing rules are in [`../AGENTS.md`](../AGENTS.md).

## 使用说明（中文）

1. 先把仓库根目录的 `AGENTS.md` 合并到 `main`（Claude Code 请复制为 `CLAUDE.md`），agent 会自动读取。
2. **一次只发一个 Prompt**；上一阶段的验收表经你确认后，再发下一个。Prompt 里不重复验收标准，
   只引用 `v0.11.0.md` §7，避免两处文档漂移。
3. 第一批可并行：**1A**（对局工具与 SPRT）和 **1B**（测试集）。两者的文件边界在各自 Prompt 里写明。
4. agent 在自己的环境里跑不了 Pikafish 或你的 Windows 构建时，会交付代码 + 运行手册，并把对应验收项标为
   `PENDING OWNER RUN`——这些命令需要你在本机执行，把结果文件放回分支。
5. 开发开始前，建议先在 `8b7d917` 上打基线标签：`git tag baseline-v0.10 8b7d917`。

## Order and parallelism

| Step | Prompt | Depends on | Can run in parallel with |
|---|---|---|---|
| 1 | **1A** V0.11.1 runner + SPRT | — | 1B |
| 1 | **1B** V0.11.1 suites | — | 1A |
| 2 | **2** V0.11.2 real-play fixes | 1A + 1B accepted | 3 |
| 2 | **3** V0.11.3 rules (Chinese) | 1A accepted | 2 |
| 3 | **4** V0.12.0 C++17 spike + ADR | nothing (touches no shared files) | 2, 3 (recommended start: with 2) |
| later | template at the end | previous exit gate accepted | — |

---

## Prompt 1A — V0.11.1: unified match runner and SPRT (critical path)

```text
You are the implementation agent for AlphaZetaChess, work package V0.11.1-A.

Read AGENTS.md, then docs/v0.11.0.md (§2.3, §4, §6, and §7 "V0.11.1"), then docs/roadmap.md's
V0.11.1 section. Authority for acceptance criteria is docs/v0.11.0.md §7 V0.11.1 AC1-AC9 -
do not restate or weaken them.

Your scope (and only this - another agent is building the suites in parallel):
1. SPRT core as an importable, pure-Python module (suggested: src/alphazetacchess/selfplay/sprt.py):
   pentanomial generalized SPRT on opening-PAIR scores {0, 0.5, 1, 1.5, 2}; logistic Elo bounds
   (H0, H1); alpha = beta = 0.05; states CONTINUE / ACCEPT_H1 / ACCEPT_H0 / INCONCLUSIVE (game cap).
   Gates G1/G2/G3 as in v0.11.0.md §6.2 as named presets.
   Required tests: LLR against an independent hand-computed reference; Monte-Carlo with a fixed seed
   (>= 10,000 simulated tests) showing accept-H1 rate ~alpha at the H0 boundary and ~1-beta at the
   H1 boundary (state your tolerance); degenerate input (zero variance, e.g. all pairs scoring 1.0)
   must not divide by zero and must return CONTINUE/INCONCLUSIVE with a reason.
2. tools/match.py: one runner.
   - Engine specs: in-process Python SearchEngine (class + EngineConfig-like kwargs) and process
     engines through ONE adapter: UCI (Pikafish) and UCCI (own engines). Reuse the existing
     PikafishClient; do not copy-paste it. Node limits (`go nodes N`) apply to process engines only;
     do NOT modify SearchEngine in this work package.
   - Limits: movetime, fixed depth, fixed nodes.
   - Paired openings in the existing format (records with "initial_fen" and "opening_prefix", as
     produced by selfplay/paired_openings.select_paired_openings). Another agent will deliver
     data/suites/openings_8ply_v1.json in that shape; until then use the existing data/ sources.
   - Reuse (extract, do not re-implement) the replay validation, adjudication and result logic that
     already exists in tools/compare_*_paired.py.
   - Pair-wise SPRT with live LLR output; JSONL records + manifest (openings, seed, engine/config
     hash, binary hash, machine, affinity, nps calibration, load per game, git revision).
   - Test registration: before game 1 write a registration record (test id, git revision, config
     hashes, opening set, seed, gate). Refuse to re-run an identical registration (same gate,
     configs, git revision) that ended INCONCLUSIVE or ACCEPT_H0 unless the revision changed.
   - Hardware discipline: refuse --workers above physical cores; set CPU affinity where the OS
     allows (Windows and Linux; degrade gracefully, record "affinity: none"); optional psutil only;
     reference-nps benchmark at start; record load per game.
3. Consolidation: replace the five tools/compare_*_paired.py scripts and tools/compare_engines.py
   with wrappers of <= 40 lines over tools/match.py (or delete with a note). Old manifests/records
   must still load. Existing tests must stay green.
4. Controls AC2-AC4: implement them as a reproducible procedure (script or documented commands).
   Note: a deterministic engine playing itself with swapped colors yields identical pairs (zero
   variance); the null control must use time-based limits so games are not identical - document
   where the non-determinism comes from. Run scaled-down versions in your environment to validate
   the machinery; mark full-size runs, the Pikafish reproduction (AC1) and the ladder calibration
   (AC5) as PENDING OWNER RUN with exact commands and expected runtimes.
5. Write docs/v0.11.1.md (project style) for your part; leave the suites part as a stub section
   that the other agent fills.

Files you own: tools/match.py, tools/compare_*.py (wrappers), src/alphazetacchess/selfplay/ (new
modules), their tests. Do not touch src/alphazetacchess/engine/ or core/.

Branch: dev/v0.11.1-match-runner. Report in the format of AGENTS.md section 5.
```

---

## Prompt 1B — V0.11.1: opening suite, AZ-TAC-500, AZ-FALLBACK-25

```text
You are the implementation agent for AlphaZetaChess, work package V0.11.1-B.

Read AGENTS.md, then docs/v0.11.0.md (§2.1, §4, §6.1, §6.3 and §7 "V0.11.1"). Acceptance authority:
V0.11.1 AC5-AC6 (suites part) in docs/v0.11.0.md - do not restate or weaken them. Another agent is
building tools/match.py and the SPRT in parallel; do not touch those files.

Your scope:
1. tools/build_opening_suite.py -> data/suites/openings_8ply_v1.json
   >= 2,000 distinct, legal, Red-to-move 8-ply openings from the game archive (use
   selfplay/paired_openings conventions: {"initial_fen", "opening_prefix"} records), deduplicated by
   position, balanced by |Pikafish eval| <= 100 cp. If Pikafish is unavailable in your environment
   the tool must still run with a material-only filter and write "pikafish_filtered": false in the
   manifest; the owner will re-run it with Pikafish (--pikafish-path, --network-path).
2. tools/extract_fallback_positions.py -> data/suites/az_fallback_25.json
   Replay data/v0.10_pikafish_vs_search_500ms_10openings_post_qsearch_dispatch.jsonl, extract the
   positions where AlphaZeta's recorded depth was 0 (25 expected; verify), with game/ply metadata.
   Then a measurement tool that runs a COMPLETE depth<=1 and depth<=2 search on all 25 and records
   nodes and time (machine info included). v0.11.0.md §2.1 reports a 12-position sample (depth<=1:
   2,509-5,379 nodes, median ~2,750); you measure all 25 and report honestly, including if the
   sample figures do not reproduce.
3. tools/build_tactics_suite.py + tools/eval_tactics.py -> data/suites/az_tac_500.json
   500 positions from the archive at plies 10-120, dev/test split 300/200 fixed by a hash of the FEN,
   categories and thresholds as in v0.11.0.md §6.1. Propose exact category rules in docs/v0.11.1.md for
   owner review (e.g. what counts as "only-move"). Labels come from Pikafish (depth >= 25 for the
   top moves). Evaluation must NOT need Pikafish: store, per position, the score of every legal
   move (if all-legal-moves at depth 25 is too slow, store top-5 at depth >= 25 and the rest at the
   highest depth you can afford; record depths and flag it as a deviation). eval_tactics.py reports
   solve rate, blunder rate (loses >= 300 cp vs best), mean centipawn loss, for any engine spec and
   time limit, including a "first generated legal move" baseline strategy.
   The labeling run itself is PENDING OWNER RUN (needs Pikafish): deliver the builder, a unit test
   using a fake labeler, a 20-position smoke suite, and an exact runbook with expected runtime.
4. Fill the suites part of docs/v0.11.1.md (coordinate: the other agent creates the file; rebase).

Files you own: tools/build_*.py, tools/extract_fallback_positions.py, tools/eval_tactics.py,
data/suites/ (files < 1 MB each; larger outputs are generated by the owner, not committed), tests.
Do not touch src/alphazetacchess/engine/, core/, or tools/match.py.

Branch: dev/v0.11.1-suites. Report in the format of AGENTS.md section 5.
```

---

## Prompt 2 — V0.11.2: real-play correctness and reliable shallow search

Send only after 1A and 1B are accepted.

```text
You are the implementation agent for AlphaZetaChess, work package V0.11.2.

Read AGENTS.md, docs/v0.11.0.md (§2.1, §2.4, §3 P2-P3, §4, §7 "V0.11.2") and docs/v0.11.1.md.
Acceptance authority: V0.11.2 AC1-AC7 in docs/v0.11.0.md. All strength tests use tools/match.py,
the SPRT gates and the suites from V0.11.1; no ad-hoc comparisons.

Scope (tasks exactly as listed under V0.11.2 in v0.11.0.md):
- UCCI: the search worker must search a board that carries the replayed game's histories
  (currently board_from_fen resets them; see v0.11.0.md §2.4 and Appendix A.1 for the repro).
- EngineConfig (immutable) + presets (play, analysis, test, baseline-v0.11) + flag registry
  (flag, default, evidence id). This REPLACES adding constructor flags; one resolution path for CLI,
  Web, UCCI and tools/match.py. Wire up or remove silent no-op flags.
- Never an arbitrary move: defer stop until iteration 1 completes; 1-ply static fallback with a
  SEE-safe filter instead of root_moves[0]; use the best-so-far move of an interrupted iteration
  under the rule in v0.11.0.md.
- Time manager: soft/hard limits; `go time` no longer capped at depth 5; a root that already counts
  as repeated must still return a legal move.
- Quiescence budget: capture ordering, delta pruning, no stalemate probing in q-nodes, q-TT keyed
  without q-ply splitting - each change justified by AZ-FALLBACK-25 node counts and AZ-TAC-500.

The V0.10 baseline for G1 is the tag baseline-v0.10 (commit 8b7d917), launched from a git
worktree as a separate process (two versions of the package cannot share one Python process).
The baseline's UCCI path is history-blind (the bug you fix): give the baseline its game history
through a small worker so the comparison is not biased in your favor, or document the residual bias.

Do not make unrelated engine changes; do not tune evaluation; do not add forward-pruning features.
Branch: dev/v0.11.2-real-play. Report in the format of AGENTS.md section 5.
```

---

## Prompt 3 — V0.11.3: rules fidelity v1 (Chinese rules)

Send after 1A is accepted; may run in parallel with Prompt 2 (rules code lives in `core/`; the other agent works in `engine/` and `protocol/`).

```text
You are the implementation agent for AlphaZetaChess, work package V0.11.3.

Read AGENTS.md (especially hard rule 6), docs/v0.11.0.md (§2.4, §3 P3, §5.3 RuleSet, §7 "V0.11.3").
Owner decision D2: the default rule set is Chinese rules. Acceptance authority: V0.11.3 AC1-AC5.

Scope: RuleSet abstraction (simple_draw = exact current behavior; chinese_v1), long check (loss for
the checking side; mutual long check = draw), check-aware in-tree repetition scoring, structured
Rule.game_result reasons, natural move limit (configurable; Chinese-style default to be confirmed
in your spec), >= 40 rule vectors with a clause reference each, adjudication audit of the game
archive. Long chase is SPECIFIED in docs/v0.11.3.md but NOT implemented.

Important: you must not invent rule semantics. Cite the competition-rule clause behind every
vector. Where the text is ambiguous or you cannot access it, implement the minimal conservative
reading listed in v0.11.0.md, record the uncertainty in docs/v0.11.3.md under "Open questions for
the owner", and continue with the rest. simple_draw must reproduce V0.10 results exactly (test).

The vectors will be reused as the golden V-RULES set for the C++ core (V0.12.1): store them as a
language-neutral JSON file with FEN, move list, and expected adjudication/score.
Files you own: src/alphazetacchess/core/rule*.py (and a new ruleset module), tests, vectors, docs.
Do not change search code except the minimal call-site wiring needed for in-tree repetition scoring,
which you coordinate in the report. Branch: dev/v0.11.3-rules.
```

---

## Prompt 4 — V0.12.0: C++17 feasibility spike and ADR

```text
You are the implementation agent for AlphaZetaChess, work package V0.12.0. Owner decision D1: the
native core is C++17.

Read AGENTS.md, docs/v0.11.0.md (§5, §7 "V0.12.0" including the options table). Acceptance authority:
V0.12.0 AC1-AC5. This is a time-boxed spike (<= 1 week of effort): scratch code in native/spike/
only; do NOT change pyproject/packaging or any Python source.

Scope: implement perft (make/unmake + move generation + legality) in C++17 for the two candidate
board representations - padded mailbox with tables, and 128-bit bitboards - behind one small CLI
(`perft <fen> <depth>`). Add CMake and CI (.github/workflows) building Linux and Windows. Write
build instructions for Windows (MSVC Build Tools and a MinGW alternative) tested from a clean
checkout as far as your environment allows.
Verification: compare counts against the Python reference for depths <= 3 (and 4 where feasible)
on the initial position and >= 20 positions sampled from the archive; do NOT hard-code reference
constants you have not verified. The depth-5 check against Pikafish `go perft 5`, the throughput
go/no-go on the owner's machine (AC2: >= 5 M leaves/s, below 2 M re-plan), and the Windows build
are PENDING OWNER RUN with exact commands.
Also demonstrate that `pip install -e .` and `python -m pytest -q` still pass without a compiler
(AC4). Write docs/v0.12.0.md as an ADR: options, measurements (Linux numbers are indicative only,
say so), recommendation, risks. Branch: dev/v0.12.0-native-spike.
```

---

## Template for later sub-versions (V0.12.1 → V0.14)

```text
You are the implementation agent for AlphaZetaChess, work package <VERSION>.

Read AGENTS.md, then docs/v0.11.0.md (§4, §5, §6 and §7 "<VERSION>"), the previous version
documents, and the "Current checkpoint" of docs/roadmap.md. Acceptance authority: <VERSION> AC1-ACn
in docs/v0.11.0.md - do not restate or weaken them.

Scope: the tasks listed under <VERSION> in docs/v0.11.0.md, nothing else. Files you own: <LIST>.
Owner decisions already made: D1 C++17, D2 Chinese rules, D3 Pikafish labels allowed. Anything
that needs D4-D7 (training hardware, license, research track, platforms) - stop and ask.
Strength claims only through registered SPRT gates, the ladder, or AZ-TAC-500. Measurements you
cannot run are PENDING OWNER RUN with exact commands. Branch: dev/<version>-<slug>.
Write docs/<version>.md in project style and report in the format of AGENTS.md section 5.
```
