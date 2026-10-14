"""Calibrate the Pikafish node ladder using the unified fixed-sample runner.

This orchestrator intentionally records measurements rather than asserting that adjacent
rungs must pass. Each adjacent-rung comparison uses at least 200 games by default; the
V0.10 baseline rung probes are smaller and are descriptive anchors only.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "match.py"
RUNGS = (1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000)


def run_match(args, test_id, output, fixed_pairs, seed, a_kind, a_command,
              a_network, a_limit_kind, a_limit_value, b_kind, b_command,
              b_network, b_limit_kind, b_limit_value):
    command = [
        sys.executable, str(RUNNER),
        "--test-id", test_id,
        "--gate", "G2",
        "--fixed-pairs", str(fixed_pairs),
        "--opening-count", str(fixed_pairs),
        "--openings", str(args.openings),
        "--seed", str(seed),
        "--max-moves", str(args.max_moves),
        "--output", str(output),
        "--a-kind", a_kind,
        "--a-limit-kind", a_limit_kind,
        "--a-limit-value", str(a_limit_value),
        "--b-kind", b_kind,
        "--b-limit-kind", b_limit_kind,
        "--b-limit-value", str(b_limit_value),
    ]
    if a_command:
        command += ["--a-command", a_command, "--a-protocol", "uci"]
    if a_network:
        command += ["--a-network-path", a_network]
    if b_command:
        command += ["--b-command", b_command, "--b-protocol", "uci"]
    if b_network:
        command += ["--b-network-path", b_network]
    subprocess.run(command, cwd=ROOT, check=True)
    manifest_path = Path(str(output) + ".manifest.json")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pikafish-path", required=True)
    parser.add_argument("--network-path", required=True)
    parser.add_argument("--openings", required=True)
    parser.add_argument("--output-dir", default="data/ladder-v0111")
    parser.add_argument("--seed", type=int, default=20261101)
    parser.add_argument("--adjacent-pairs", type=int, default=100,
                        help="100 pairs = 200 games per adjacent rung")
    parser.add_argument("--baseline-pairs", type=int, default=20,
                        help="fixed sample per V0.10-vs-rung anchor")
    parser.add_argument("--max-moves", type=int, default=150)
    args = parser.parse_args()
    if args.adjacent_pairs < 100:
        parser.error("--adjacent-pairs must be at least 100 to satisfy AC5")
    if args.baseline_pairs < 1:
        parser.error("--baseline-pairs must be positive")

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        parser.error(f"output directory must be empty: {output_dir}")

    report = {
        "rungs": list(RUNGS),
        "adjacent_pairs": args.adjacent_pairs,
        "baseline_pairs": args.baseline_pairs,
        "seed": args.seed,
        "adjacent": [],
        "baseline": {"500ms": [], "2500ms": []},
        "notes": [
            "Adjacent-rung results are fixed-sample score rates, not SPRT decisions.",
            "Baseline probes use fewer pairs and are descriptive rung anchors, not strength claims.",
            "This script does not bundle or redistribute Pikafish or its network.",
        ],
    }

    for index, (lower, higher) in enumerate(zip(RUNGS, RUNGS[1:])):
        test_id = f"ladder-{lower}-vs-{higher}"
        manifest = run_match(
            args, test_id, output_dir / f"{test_id}.jsonl",
            args.adjacent_pairs, args.seed + index,
            "process", args.pikafish_path, args.network_path, "nodes", higher,
            "process", args.pikafish_path, args.network_path, "nodes", lower,
        )
        score = manifest["candidate_score_rate"]
        report["adjacent"].append({
            "lower_nodes": lower, "higher_nodes": higher,
            "higher_rung_score": score,
            "games": 2 * args.adjacent_pairs,
            "in_target_band_55_to_90_percent": score is not None and 0.55 <= score <= 0.90,
            "manifest": str(output_dir / f"{test_id}.jsonl.manifest.json"),
        })
        print(f"{lower} -> {higher} nodes: higher rung score {score:.1%}", flush=True)

    for budget in (500, 2500):
        key = f"{budget}ms"
        for index, rung in enumerate(RUNGS):
            test_id = f"baseline-{budget}ms-vs-{rung}-nodes"
            manifest = run_match(
                args, test_id, output_dir / f"{test_id}.jsonl",
                args.baseline_pairs, args.seed + 1000 + budget + index,
                "python", None, None, "movetime", budget,
                "process", args.pikafish_path, args.network_path, "nodes", rung,
            )
            score = manifest["candidate_score_rate"]
            report["baseline"][key].append({
                "nodes": rung,
                "v010_score": score,
                "games": 2 * args.baseline_pairs,
                "manifest": str(output_dir / f"{test_id}.jsonl.manifest.json"),
            })
            print(f"V0.10 {budget}ms vs {rung} nodes: AZ score {score:.1%}", flush=True)

    for key, rows in report["baseline"].items():
        below = next((row["nodes"] for row in rows
                      if row["v010_score"] is not None and row["v010_score"] < 0.5), None)
        report["baseline"][key + "_first_rung_below_50_percent"] = below
    report_path = output_dir / "ladder-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Report written: {report_path}")


if __name__ == "__main__":
    main()
