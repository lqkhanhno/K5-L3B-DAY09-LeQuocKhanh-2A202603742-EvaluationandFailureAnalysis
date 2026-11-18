"""Generate sanitized trace and calibration evidence; never edit the JSON output manually.

Run from src/: python -m lab9.evidence
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from lab8.shapes import SHAPES
from lab9.eval import load_spec, load_world, make_task
from lab9.graders import GRADERS
from lab9.judge import calibrate
from lab9.variant_agent import make_shape
from lab9.variants import register


def main() -> int:
    register()
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    world, claims = load_world(spec)
    labels = json.loads(Path(spec["labels"]).read_text(encoding="utf-8"))
    probes = [
        ("FM-01", "leaky_trace", "C-010"), ("FM-02", "ignore_denied", "C-007"),
        ("FM-03", "ticket_trust", "C-002"), ("FM-04", "sum_parts", "C-014"),
        ("FM-05", "pre_deducted", "C-014"), ("FM-06", "stale_clause", "C-006"),
        ("FM-07", "sibling_refund", "C-001"), ("FM-08", "misreport", "C-008"),
        ("FM-09", None, "C-110"), ("case", "seeded_regression", "C-002"),
        ("control", None, "C-002"),
    ]
    cases = []
    for mode, bug, claim in probes:
        name = "fixed" if bug is None else bug if bug == "seeded_regression" else f"evidence_{bug}"
        if name not in SHAPES:
            SHAPES[name] = make_shape(name, {"no_override", bug})
        with tempfile.TemporaryDirectory(prefix="lab9-evidence-", ignore_cleanup_errors=True) as tmp:
            trial = make_task(name, world, claims, labels, Path(tmp))({"claim_id": claim, "seed": 11})
        ctx = SimpleNamespace(output=trial, expected_output=labels[claim])
        events = []
        for index, event in enumerate(trial["events"], 1):
            payload = event.get("payload")
            if event["kind"] == "debug_claim_row":
                # Prove the leak without publishing the leaked content.
                payload = {"field_names": sorted(payload), "contains_forbidden": any(
                    token in json.dumps(payload) for token in labels[claim].get("forbid_substrings", []))}
            events.append({"step": index, "kind": event["kind"], "payload": payload})
        cases.append({"mode": mode, "shape": name, "claim": claim, "seed": 11,
                      "run_id": trial["result"]["run_id"],
                      "status": trial["result"]["status"], "proposal": trial["result"]["proposal_amount"],
                      "snapshot": trial["snapshot"], "unexpected_rows": trial["unexpected_rows"],
                      "lab8_reason": trial["lab8_reason"],
                      "graders": {mid: bool(cls().evaluate(ctx).value) for mid, cls in GRADERS.items()},
                      "events": events})
    result = {"code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "judges": {name: calibrate(Path(f"data/eval/judge_{name}_public.csv"))
                         for name in ("tone", "helpful")}, "cases": cases}
    out = Path("reports/analysis_evidence.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out}: {len(cases)} sanitized trace cases, 2 calibrated judges")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
