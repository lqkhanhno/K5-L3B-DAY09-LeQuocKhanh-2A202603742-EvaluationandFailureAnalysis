"""Reproduce the Day 9 submission, including expected nonzero gate verdicts.

Run from src/: python scripts/verify_day9.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    results = []
    out = Path("reports")
    out.mkdir(exist_ok=True)

    def run(args: list[str], expected: int = 0) -> None:
        proc = subprocess.run([sys.executable, *args], capture_output=True, text=True,
                              encoding="utf-8", env={**os.environ, "PYTHONUTF8": "1"})
        results.append({"command": "python " + " ".join(args), "expected_exit": expected,
                        "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr})
        out.joinpath("verification.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{proc.returncode}, expected {expected}] python {' '.join(args)}", flush=True)
        if proc.returncode != expected:
            print(proc.stdout + proc.stderr)
            raise SystemExit(1)

    run(["-m", "lab9.smoke"])
    run(["-m", "pytest", "-q"])
    run(["-m", "pytest", "-q", "-m", "student", "-o", "addopts=", "-k", "lab9"])
    run(["-m", "lab9.evalset", "--check"])
    run(["-m", "lab9.evalset", "--v2", "--check"])
    for name, expected in (("tone", 0), ("helpful", 1)):
        run(["-m", "lab9.judge", "--csv", f"data/eval/judge_{name}_public.csv", "--audit", "5"], expected)
    v1, v2 = "config/metric_spec.yaml", "config/metric_spec_v2.yaml"
    for version, spec in (("v1", v1), ("v2", v2)):
        run(["-m", "lab9.eval", "--shape", "swarm", "--spec", spec, "--out", f"reports/baseline_{version}.json"])
        run(["-m", "lab9.gate", "--pr", f"reports/baseline_{version}.json", "--baseline",
             f"reports/baseline_{version}.json", "--spec", spec, "--base-spec", spec])
    for shape, expected in (("fixed", 0), ("seeded_regression", 1)):
        run(["-m", "lab9.eval", "--shape", shape])
        run(["-m", "lab9.gate", "--pr", f"reports/eval_{shape}.json", "--baseline", "reports/baseline_v1.json"], expected)
    run(["-m", "lab9.ci_check", "--pr", "reports/baseline_v1.json", "--baseline", "reports/baseline_v1.json"])
    run(["-m", "lab9.mutation", "--detect"])
    run(["-m", "lab9.mutation", "--spec", v2, "--aa", "66,77,88,99,110"])
    run(["-m", "lab9.mutation", "--spec", v2, "--baseline", "reports/baseline_v2.json", "--base-spec", v2])
    for shape in ("fixed", "honest_refactor", "seeded_regression", "slice_regression", "flaky_regression"):
        run(["-m", "lab9.eval", "--shape", shape, "--spec", v2, "--out", f"reports/eval_{shape}_v2.json"])
        run(["-m", "lab9.gate", "--pr", f"reports/eval_{shape}_v2.json", "--baseline", "reports/baseline_v2.json", "--spec", v2],
            0 if shape in ("fixed", "honest_refactor") else 1)
    run(["-m", "lab9.traps", "--pr", "reports/eval_slice_regression_v2.json", "--baseline", "reports/baseline_v2.json", "--spec", v2])
    for trap in ("evaluator_errors_as_nan", "dropped_failing_rows", "cherry_picked_seeds", "loosened_spec"):
        spec = "reports/traps/loosened_spec.spec.yaml" if trap == "loosened_spec" else v2
        run(["-m", "lab9.gate", "--pr", f"reports/traps/{trap}.json", "--baseline", "reports/baseline_v2.json",
             "--spec", spec, "--base-spec", v2], 1)
    run(["-m", "lab9.evidence"])
    print(f"PASS: {len(results)} commands; expected gate rejections verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
