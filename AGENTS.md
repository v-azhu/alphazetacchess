# AGENTS.md — Standing instructions for development agents

(Claude Code users: copy or symlink this file as `CLAUDE.md`.)

This repository follows an evidence-driven plan. Read this file fully before touching code.

## 1. Read first, in this order

1. `docs/v0.11.0.md` — **authoritative** plan: evidence (§2), pain points (§3), stop list (§4),
   target architecture (§5), measurement protocol (§6), phases and acceptance criteria (§7),
   owner decisions (§9).
2. `docs/roadmap.md` — "Current checkpoint" and the V0.11–V0.14 sections.
3. `docs/PROGRESS_NOTES.md` and `docs/development.md` (incl. the §12 addendum).

Only then read code. If a document and the code disagree, say so in your report; do not guess.

## 2. Decisions already made — do not reopen

- **D1** native core language: **C++17** (module via pybind11 + standalone UCCI executable).
- **D2** rule set: **Chinese rules** (`chinese_v1`). Do not invent rule semantics — see §3.6.
- **D3** Pikafish evaluations **may be used as training labels**. The Pikafish binary and network are
  never committed or redistributed; record label provenance per data shard.
- D4–D7 (training hardware, license, research track, platforms) are **open**: ask the owner.

## 3. Hard rules

1. **One sub-version at a time**, in the order of `docs/v0.11.0.md` §7. Do not start a later phase
   until the owner says the previous exit gate is accepted.
2. **Respect the stop list** (`v0.11.0.md` §4): no Python hot-path micro-optimizations, no <100-game
   A/B tests, no new `SearchEngine` constructor flags, no new `compare_*` scripts, no numpy-MLP
   evaluator/policy iterations.
3. **Never fabricate results.** If a measurement needs something you do not have (a Pikafish binary
   and network, the owner's Windows machine, hours of CPU), deliver the code, tests and an exact
   runbook, and mark the criterion `PENDING OWNER RUN`. Only write numbers you measured. Report
   negative results as plainly as positive ones — this is the project's culture.
4. **Strength claims need a gate** (`v0.11.0.md` §6): SPRT, ladder or AZ-TAC-500 — never depth or
   node statistics or a sub-100-game match.
5. **Do not change playing behavior in tooling sub-versions.** Defaults of `SearchEngine` must stay
   byte-identical unless the sub-version's task list says otherwise; tests must prove it.
6. **Rules**: implement only semantics written down in `v0.11.0.md` V0.11.3 or in a rule text you can
   cite by clause. Where a rule is ambiguous or you cannot access its text, implement the minimal
   conservative reading, list the uncertainty in the version document, and ask the owner.
7. **Never commit** binaries (Pikafish, NNUE weights, compiled artifacts) or generated files > 1 MB.
   Take external paths from CLI arguments (existing convention: `--pikafish-path`, `--network-path`).
8. **Cross-platform**: the owner uses Windows/PowerShell; CI will use Linux. No POSIX-only calls
   without a fallback (`os.nice`, `os.sched_setaffinity` …). No new hard dependencies (`flask`,
   `numpy` only); optional ones such as `psutil` must degrade gracefully.
9. **Tests**: `python -m pytest -q` is green before every commit (baseline: 402 passed). Every new
   behavior gets a test. Randomized tests are seeded.
10. **Deviations**: if the plan seems wrong, infeasible or contradictory, stop that item, write it
    under "Deviations" in the version document, and ask. Never silently change an acceptance
    criterion or weaken a threshold.

## 4. Workflow

- Branch from `main`: `dev/<version>-<slug>` (existing pattern, e.g. `dev/v0.8.1-attack-detector`),
  such as `dev/v0.11.1-match-runner`. Never commit to `main`; never force-push.
- Small commits, `type: description` (`feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `perf`).
- Each sub-version gets `docs/vX.Y.Z.md` in the existing style: Status / Goal / Design /
  Acceptance criteria (with measured results) / Known limitations / Next checkpoint. At the end
  update `docs/roadmap.md` (status table, checkpoint) and `docs/PROGRESS_NOTES.md` (hand-off).
- Evidence package per claim (`v0.11.0.md` §6.4): reproduction command, game records + manifest,
  replay-validation pass, SPRT result, honest reading.
- File ownership when several agents run in parallel: stay inside the files your prompt assigns.
  Shared files (`roadmap.md`, `PROGRESS_NOTES.md`) are edited only in your final commit, after
  rebasing on the latest `main`.

## 5. Final report format (every task)

1. What was done (files, interfaces).
2. **Acceptance table**: each AC → `PASS` / `FAIL` / `PENDING OWNER RUN`, with the evidence path.
3. Deviations and open questions.
4. Exact commands the owner must run (if any), with expected runtime.
5. Suggested next step.
