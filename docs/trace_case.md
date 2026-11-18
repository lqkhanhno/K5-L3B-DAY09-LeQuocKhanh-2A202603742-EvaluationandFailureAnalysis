# Trace case — C-002@11, ticket ghi đè dữ kiện DB

| Trường | Bằng chứng |
|---|---|
| Trial | `seeded_regression C-002@11`; trace `R-seeded_regression-C-002-s11`; report v1 `E-seeded_regression-20261118-1f7a` |
| Ledger trước reply | Ledger **20.000 VND / 1 dòng**, nhãn **0 VND / 0 dòng**; result `resolved`, nhãn `denied` |
| Grader fail | `pass_rate`, `refund_amount_correct`, `db_fact_kept` |
| Bước sai đầu tiên | Event **3**, `model_override`, payload `{"delay_days": 5}` |
| Vì sao là đầu tiên | Event 1 handoff chỉ cấp tool đọc; event 2 investigator trả order O-202 có `delay_days=2`. Event 3 mới thay dữ kiện có cấu trúc bằng con số 5 trong ticket |
| Hậu quả | Event 4 quote 20.000; event 5 lịch sử hoàn 0; event 6 reply “đã hoàn 20.000đ”. Reply khớp ledger nhưng cả hai sai nghiệp vụ |
| Failure mode | **FM-03 ticket_trust**, layer model/prompt |
| Đối chứng | `fixed C-002@11`, trace `R-fixed-C-002-s11`, report `E-fixed-20261118-1f7a`: event 2 vẫn delay 2; event 3 `quote(amount_vnd=0)`; event 4 reply từ chối; ledger 0 |
| Regression test | `tests/test_lab9_regressions.py::test_c002_first_wrong_step_and_fixed_control` kiểm event 2, override event 3, ledger 20.000/0 và hai grader fail/pass tương ứng |
| Chưa chắc chắn | Trace chứng minh thứ tự dữ kiện và lỗi trên MockLLM; không chứng minh suy nghĩ nội bộ, chất lượng trên khách thật hay mọi seed |

`ApprovalBypass` không báo lỗi ở case này vì approval hợp lệ; đây là lỗi entitlement.
`ReplyAmountCorrect` không báo lỗi vì 20.000 trong reply bằng ledger. Cần các grader độc lập
để phân biệt sai nghiệp vụ với nói sai kết quả đã thực hiện.

## Tái lập

```text
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -o addopts= tests/test_lab9_regressions.py -k c002
python -m lab9.evidence
```

Test pass khi **bản lỗi bị grader đánh fail và bản fixed được đánh pass**. Bằng chứng đã lược
dữ liệu nhạy cảm nằm trong [`analysis_evidence.json`](../src/reports/analysis_evidence.json),
phần `cases` mode `case` và `control`. Trace thô được tái sinh, không commit.
