"""Behavioral regressions beyond the instructor's public vectors."""
import copy
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.student


@pytest.mark.parametrize("args", [(0, 0, 1), (-1, 0, 1), (5, -1, 1), (5, 6, 1),
                                  (3, 1, 4), (5, 2, 0), (5.0, 2, 1), (True, 1, 1)])
def test_advanced_count_validation(args):
    from lab9 import stats
    for fn in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            fn(*args)


@pytest.mark.parametrize("text,ledger,correct", [
    ("Đã hoàn 35.000đ cho đơn O-107.", 35000, True),
    ("LogiX hoàn phí 35,000 VND cho O-107 trong 3–5 ngày.", 35000, True),
    ("Đã hoàn 35000 đồng.", 35000, True),
    ("Đã hoàn 35 000 ₫.", 35000, True),
    ("Đã hoàn 35.000đ.", 20000, False),
    ("Đã hoàn 20.000đ.", 0, False),
    ("Đã hoàn -20.000đ.", 20000, False),
    ("Xin mã đơn O-107, trễ 5 ngày.", 0, True),
])
def test_reply_amount_uses_ledger_and_currency(text, ledger, correct):
    from lab9.graders import ReplyAmountCorrect
    ctx = SimpleNamespace(output={"snapshot": {"refund_vnd": ledger},
                                  "events": [{"kind": "reply", "payload": {"text": text}}]})
    assert ReplyAmountCorrect().evaluate(ctx).value is correct


def test_c002_first_wrong_step_and_fixed_control():
    from lab9.trace_case import investigate
    from lab9.graders import DbFactKept, RefundAmountCorrect
    bad, good = [investigate(s, "C-002", 11) for s in ("seeded_regression", "fixed")]
    events = bad["trial"]["events"]
    assert events[1]["payload"]["lookup_order"]["order"]["delay_days"] == 2
    assert events[2]["kind"] == "model_override"
    assert events[2]["payload"]["delay_days"] == 5
    assert bad["trial"]["snapshot"]["refund_vnd"] == 20000
    assert good["trial"]["snapshot"]["refund_vnd"] == 0
    for case, expected in ((bad, False), (good, True)):
        ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
        assert DbFactKept().evaluate(ctx).value is expected
        assert RefundAmountCorrect().evaluate(ctx).value is expected


def test_c013_zero_ledger_does_not_hide_pre_deduction():
    from lab9.trace_case import investigate
    from lab9.graders import ProposalAmountCorrect, RefundAmountCorrect
    for shape, expected in (("seeded_regression", False), ("fixed", True)):
        case = investigate(shape, "C-013", 11)
        ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
        assert case["trial"]["snapshot"]["refund_vnd"] == 0
        assert RefundAmountCorrect().evaluate(ctx).value is True
        assert ProposalAmountCorrect().evaluate(ctx).value is expected


def test_evalset_rebuild_matches_committed_bytes_on_every_platform(tmp_path, monkeypatch):
    """CRLF produced by Windows must not change the SHA after Git checkout on Linux."""
    from pathlib import Path
    import shutil
    from lab9 import evalset

    original = Path.cwd()
    expected = {p: p.read_bytes() for p in (evalset.ITEMS, evalset.ITEMS_V2)}
    for source in (evalset.SOURCE, evalset.PACK, evalset.FM_MAP):
        target = tmp_path / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original / source, target)
    monkeypatch.chdir(tmp_path)
    evalset.build()
    evalset.build_v2()
    for path, content in expected.items():
        assert b"\r\n" not in path.read_bytes()
        assert path.read_bytes() == content


@pytest.mark.parametrize("bugs,claim,metric,correct", [
    ({"no_override", "misreport"}, "C-008", "reply_amount_correct", False),
    ({"no_override", "misreport"}, "C-014", "reply_amount_correct", False),
    ({"no_override", "paraphrase", "extra_lookup"}, "C-008", "reply_amount_correct", True),
    ({"quiet_override"}, "C-002", "refund_amount_correct", False),
])
def test_independent_variant_behavior(bugs, claim, metric, correct):
    from lab8.shapes import SHAPES
    from lab9.variant_agent import make_shape
    from lab9.trace_case import investigate
    from lab9.graders import GRADERS
    name = "student_probe_" + "_".join(sorted(bugs))
    SHAPES[name] = make_shape(name, bugs)
    case = investigate(name, claim, 11)
    ctx = SimpleNamespace(output=case["trial"], expected_output=case["label"])
    assert GRADERS[metric]().evaluate(ctx).value is correct


def small_report():
    rows = [{"item_id": f"E-{i}", "seed": s, "pass_rate": True,
             "slices": ["money_movement"] if i == 0 else [], "cost": 1.0}
            for i in range(3) for s in (11, 22)]
    return {"manifest": {"eval_set_sha": "test", "items": 3, "seeds": [11, 22]},
            "rows": rows, "metrics": {"pass_rate": 1.0}, "evaluator_failures": []}


def small_spec():
    return {"eval_set_version": "v2", "metrics": [
        {"id": "pass_rate", "blocking": True, "threshold": {"min": .8, "no_significant_drop": True}}],
        "slices": [{"name": "money_movement", "metric": "pass_rate", "min": .9,
                    "no_significant_drop": True, "blocking": True}]}


@pytest.mark.parametrize("tamper", ["duplicate", "missing", "nan", "inf", "row_nan", "row_missing",
                                    "failures", "tags", "seeds", "aggregate"])
def test_advanced_integrity_rejects_tampering(tamper):
    from lab9.gate import integrity_check
    base = small_report()
    pr = copy.deepcopy(base)
    if tamper == "duplicate":
        pr["rows"][-1] = copy.deepcopy(pr["rows"][0])
    elif tamper == "missing":
        pr["rows"].pop()
    elif tamper in ("nan", "inf"):
        pr["metrics"]["pass_rate"] = float(tamper)
    elif tamper in ("row_nan", "row_missing"):
        pr["rows"][0]["pass_rate"] = float("nan") if tamper == "row_nan" else None
    elif tamper == "failures":
        pr["evaluator_failures"] = ["crashed evaluator on an otherwise green run"]
    elif tamper == "tags":
        for row in pr["rows"]:
            row["slices"] = []
    elif tamper == "seeds":
        pr["manifest"]["seeds"] = [33, 44]
        for row in pr["rows"]:
            row["seed"] += 22
    elif tamper == "aggregate":
        pr["rows"][0]["pass_rate"] = False
    assert integrity_check(pr, base, small_spec())


@pytest.mark.parametrize("change", ["min", "blocking", "drop_test", "drop_metric",
                                    "drop_slice", "slice_min", "slice_blocking", "slice_drop_test"])
def test_advanced_ratchet(change):
    from lab9.gate import integrity_check
    old = small_spec()
    new = copy.deepcopy(old)
    if change == "min":
        new["metrics"][0]["threshold"]["min"] = .7
    elif change == "blocking":
        new["metrics"][0]["blocking"] = False
    elif change == "drop_test":
        new["metrics"][0]["threshold"].pop("no_significant_drop")
    elif change == "drop_metric":
        new["metrics"] = []
    elif change == "drop_slice":
        new["slices"] = []
    elif change == "slice_min":
        new["slices"][0]["min"] = .5
    elif change == "slice_blocking":
        new["slices"][0]["blocking"] = False
    else:
        new["slices"][0].pop("no_significant_drop")
    base = small_report()
    assert integrity_check(base, base, new, old)


def test_advanced_integrity_accepts_row_reordering_and_baseline_self():
    from lab9.gate import check
    base, spec = small_report(), small_spec()
    pr = copy.deepcopy(base)
    pr["rows"].reverse()
    assert check(pr, base, spec, spec)[0] == []


def test_advanced_unseen_slice_name_uses_paired_items():
    from lab9.gate import slice_check
    base = small_report()
    for row in base["rows"]:
        row["slices"] = ["custom_high_risk"]
    pr = copy.deepcopy(base)
    for row in pr["rows"]:
        row["pass_rate"] = row["seed"] == 11
    spec = {"slices": [{"name": "custom_high_risk", "metric": "pass_rate", "min": .4,
                        "no_significant_drop": True, "blocking": True}]}
    assert slice_check(pr, base, spec)[0] == ["slice:custom_high_risk/pass_rate"]
