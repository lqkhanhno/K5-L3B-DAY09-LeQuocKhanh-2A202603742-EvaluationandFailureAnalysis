"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def _ratchet(new: dict, old: dict, name: str) -> list[str]:
    problems = []
    if old.get("blocking") and not new.get("blocking"):
        problems.append(f"ratchet {name}: blocking removed")
    nt, ot = new.get("threshold", new), old.get("threshold", old)
    for key in ("min", "max", "max_increase"):
        if key in ot and (key not in nt or not isinstance(nt[key], (int, float))
                          or not math.isfinite(nt[key])
                          or (nt[key] < ot[key] if key == "min" else nt[key] > ot[key])):
            problems.append(f"ratchet {name}: {key} loosened/removed")
    if ot.get("no_significant_drop") and not nt.get("no_significant_drop"):
        problems.append(f"ratchet {name}: no_significant_drop removed")
    return problems


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    graded = {m["id"] for m in spec["metrics"] if m["id"] in GRADERS}
    pair_sets, tags_by_report = [], []
    for name, report in (("PR", pr), ("baseline", base)):
        manifest = report.get("manifest", {})
        rows, metrics = report.get("rows"), report.get("metrics")
        if not isinstance(rows, list) or not isinstance(metrics, dict):
            return [f"{name}: invalid rows/metrics"]
        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator_failures is non-empty")
        for mid, value in metrics.items():
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                problems.append(f"{name}: non-finite/invalid metric {mid}")
        for m in spec["metrics"]:
            mid = m["id"]
            if mid not in metrics or (metrics[mid] is None and m.get("blocking")):
                problems.append(f"{name}: missing metric {mid}")
        seeds, count = manifest.get("seeds"), manifest.get("items")
        if (not isinstance(seeds, list) or not seeds or any(type(s) is not int for s in seeds)
                or len(set(seeds)) != len(seeds) or type(count) is not int or count < 1):
            return [f"{name}: invalid item/seed manifest"]
        if len(rows) != count * len(seeds):
            problems.append(f"{name}: row count does not equal items x seeds")
        pairs, item_tags = [], {}
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("item_id"), str) or type(row.get("seed")) is not int:
                return [f"{name}: malformed item/seed row"]
            pairs.append((row["item_id"], row["seed"]))
            tags = row.get("slices", [])
            if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
                problems.append(f"{name}: invalid slice tags")
                tags = []
            tags = frozenset(tags)
            if row["item_id"] in item_tags and item_tags[row["item_id"]] != tags:
                problems.append(f"{name}: inconsistent slice tags for {row['item_id']}")
            item_tags[row["item_id"]] = tags
            for mid in graded:
                value = row.get(mid)
                if not isinstance(value, (bool, int, float)) or not math.isfinite(value) or value not in (0, 1):
                    problems.append(f"{name}: invalid/missing graded value {mid} at {pairs[-1]}")
            if "cost" in row and (not isinstance(row["cost"], (int, float))
                                  or not math.isfinite(row["cost"]) or row["cost"] < 0):
                problems.append(f"{name}: invalid cost at {pairs[-1]}")
        frequencies = Counter(pairs)
        if any(n != 1 for n in frequencies.values()):
            problems.append(f"{name}: duplicate item/seed rows")
        item_ids = set(item_tags)
        if len(item_ids) != count or set(pairs) != {(i, s) for i in item_ids for s in seeds}:
            problems.append(f"{name}: incomplete item x seed coverage")
        pair_sets.append(set(pairs))
        tags_by_report.append(item_tags)
        # Independently reconstruct aggregates, so editing only the headline cannot hide failures.
        if not problems and rows:
            safe_rows = [{**r, "cost": r.get("cost", 0.0)} for r in rows]
            computed = aggregate(safe_rows, sorted(graded), k_values=spec.get("pass_k", []))
            for mid, expected in computed.items():
                if mid == "cost_per_success" and not all("cost" in r for r in rows):
                    continue
                if mid in metrics and metrics[mid] != expected:
                    problems.append(f"{name}: aggregate {mid} differs from rows")
    if pair_sets[0] != pair_sets[1]:
        problems.append("PR and baseline have different (item_id, seed) sets")
    if tags_by_report[0] != tags_by_report[1]:
        problems.append("PR slice tags differ from baseline")
    if spec.get("seeds") is not None and set(pr["manifest"]["seeds"]) != set(spec["seeds"]):
        problems.append("PR seeds differ from spec")
    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        for section, key in (("metrics", lambda x: x["id"]),
                             ("slices", lambda x: (x["name"], x["metric"]))):
            current = {key(m): m for m in spec.get(section, [])}
            for old in base_spec.get(section, []):
                ident = key(old)
                if ident not in current:
                    problems.append(f"ratchet {section} {ident}: removed")
                else:
                    problems.extend(_ratchet(current[ident], old, f"{section} {ident}"))
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        ident = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        reason = ""
        bad = not a or set(a) != set(b)
        value = sum(a.values()) / len(a) if a else None
        if bad:
            reason = "missing or unmatched slice items"
        else:
            if "min" in rule and value < rule["min"]:
                bad = True
            if rule.get("no_significant_drop"):
                keys = sorted(a)
                d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95))
                reason = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                bad |= hi < 0
        if bad and rule.get("blocking"):
            blocked.append(ident)
        verdict = "BLOCK" if bad and rule.get("blocking") else "warn" if bad else "ok"
        lines.append(f"  {ident} {value} {reason} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if not pr.get("manifest", {}).get("eval_set_sha") or pr["manifest"]["eval_set_sha"] != base.get("manifest", {}).get("eval_set_sha"):
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid) is not None:
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
