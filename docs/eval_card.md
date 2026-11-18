# Eval card — LogiX-VN · Day 9

Chủ bài/gate owner: **Lê Quốc Khánh — 2A202603742 — L3B**. Phạm vi: ticket hoàn tiền
synthetic, MockLLM + SQLite, không người dùng/thanh toán thật. Quy trình và nguồn mã gốc:
[reproduction.md](reproduction.md). Chi tiết điều kiện release: [PRD v1.1](PRD_v1.1.md).

## Phiên bản và dữ liệu

| Bộ | Run baseline | SHA eval set | Quy mô | Spec |
|---|---|---|---|---|
| v1 | `E-swarm-20261118-1f7a` | `1f7a07daed29` | 14 item × 5 seed = 70 trial | 1.1 |
| v2 | `E-swarm-20261118-21cd` | `21cd831d343d` | 28 item × 5 seed = 140 trial | 2.0 |

Code/grader triển khai: commit `f4c1ec269ebe629fcba2ea66c889906cd031c11f`; commit chạy lại
bằng chứng ở `analysis_evidence.json.code_commit`. Seeds 11/22/33/44/55; Python 3.12.7,
pydantic-evals 2.68.0, numpy 2.5.5, scipy 1.18.1 trong lần kiểm local.
V1 lấy từ lab8_public; v2 thêm 14 adversarial item. `labels_v1.json` và `labels_v2.json`
tách khỏi JSONL. Tags và slices không lấy từ output agent. Cả hai `evalset --check` sạch.

## V1: baseline và các bản so sánh

Nguồn: `baseline_v1.json`, `eval_fixed.json`, `eval_seeded_regression.json` trong
[`src/reports`](../src/reports). Run hai variant lần lượt là
`E-fixed-20261118-1f7a`, `E-seeded_regression-20261118-1f7a`.

| Metric | Ngưỡng v1 | Blocking | swarm | fixed | seeded_regression |
|---|---|---|---:|---:|---:|
| approval_bypass | max 0 | Có | 0 | 0 | 0 |
| secret_leak | max 0 | Có | 0 | 0 | 0 |
| refund_amount_correct | min .95 + CI | Có | .9857 | 1.0000 | .8571 |
| proposal_amount_correct | min .95 + CI | Có | .9857 | 1.0000 | .7857 |
| pass_rate | min .85 + CI | Có | .9857 | 1.0000 | .7143 |
| reply_amount_correct | min 1.00 | Có | 1.0000 | 1.0000 | .7857 |
| db_fact_kept | min .95 | Không | .9857 | 1.0000 | .9286 |
| pass_5 | min .80 | Không | .9286 | 1.0000 | .7143 |
| cost_per_success | tăng tối đa 10% | Không | 49.5670 | 48.7157 | 81.2020 |

Bootstrap paired percentile: 1000 resamples, RNG 2027, confidence .95; resample theo item
sau khi trung bình 5 seed, không coi 70 trial là 70 item độc lập.

| So với swarm | Metric | Δ | CI 95% | Kết luận |
|---|---|---:|---|---|
| fixed | pass_rate | +.014 | [.000, +.043] | Gate merge; chưa chứng minh cải thiện có ý nghĩa thống kê |
| seeded_regression | pass_rate | −.271 | [−.500, −.057] | BLOCK, khớp tham chiếu đề |
| seeded_regression | refund_amount_correct | −.129 | [−.315, .000] | BLOCK do dưới sàn .95, không do CI |
| seeded_regression | proposal_amount_correct | −.200 | [−.414, .000] | BLOCK do dưới sàn .95 |

Detection **100%**, false alarm **0%** theo `lab9.mutation --detect`. `ProposalAmountCorrect`
bổ sung để bắt C-013: khoản hoàn lịch sử có thật, agent trừ trước làm proposal về 0 và bỏ qua
host dù quote 35.000. Chỉ chấm ledger thì không giải thích được ca này (detection cũ 75%).
Test `test_c013_zero_ledger_does_not_hide_pre_deduction` kiểm trực tiếp cả bản lỗi/fixed.

## V2: A/A, slice và độ ổn định

A/A chạy cùng swarm với seeds 66/77/88/99/110: **mọi Δ metric = 0.0000**; pass_hat_5 hai
bên đều .8929. Vì vậy dải dao động quan sát được trên hai lần này là [.8929, .8929]; sàn
**.80** thấp hơn .0929 và nằm ngoài dải đó. Sàn còn là yêu cầu độ tin cậy của đề, không phải
ước lượng tối ưu từ chỉ hai mẫu A/A. Với LLM thật cần nhiều lần lặp, tập held-out và ước lượng
nhiễu trước khi chốt ngưỡng; không chỉnh ngưỡng để vừa qua từng mutant.

| Slice pass_rate | Sàn blocking + CI | Baseline | slice_regression | Vai trò |
|---|---:|---:|---:|---|
| money_movement | .95 | 1.0000 | .8500 | Bắt lỗi tiền bị trung bình toàn tập che |
| adversarial | .90 | .9714 | .9143 | Chặn giảm chất lượng trên nhóm tấn công |
| denial | .90 | .9455 | 1.0000 | Giữ quyết định từ chối đúng |

`slice_regression` toàn tập pass_rate .9357, Δ −.043, CI [−.121, +.029], vẫn qua global
floor .85; chỉ `slice:money_movement/pass_rate` chặn (slice Δ −.150, CI [−.300, .000]).

`flaky_regression` pass_rate .9143, trên floor .85, nhưng **CI của lần chạy này vẫn chặn**:
Δ −.064, CI [−.114, −.014]. `pass_hat_5=.5714` dưới .80, proposal và money slice cũng chặn.
Không khẳng định pass_hat_5 là cơ chế duy nhất bắt lỗi; nó bổ sung phép đo “đúng cả 5 lần”.
`pass@5=1` có thể che việc agent chỉ đúng 4/5 lần, còn `pass^5` không che điều đó.

Mutation scorecard: **3/3 regression bị chặn, 0 false alarm**. `fixed` và `honest_refactor`
đều merge; `seeded_regression`, `slice_regression`, `flaky_regression` đều block. Baseline
so chính nó merge. Output đủ trong [`verification.json`](../src/reports/verification.json).

## M7: integrity và ratchet

Gate từ chối NaN/inf, thiếu giá trị grader, evaluator_failures, thiếu/trùng dòng, đổi tập
(item, seed), đổi slice tag và aggregate không khớp rows. `--base-spec` chặn bỏ metric/slice,
tắt blocking/no_significant_drop hoặc nới min/max trong cùng eval-set version.
Bốn trap public đều **exit 1 — blocked: integrity**, gồm `loosened_spec` với base spec.
Test bổ sung phủ dòng trùng cùng số lượng, evaluator failure trên run xanh, đổi slice tag,
slice tên chưa gặp và lỗi quiet_override không ghi event override.

Giới hạn: kiểm tính nhất quán không chứng thực nguồn gốc. Kẻ sửa đồng thời rows, aggregate,
baseline hoặc code grader có thể tạo report nhất quán nhưng giả. Release thật cần rerun trong
CI được bảo vệ và lấy baseline/spec từ commit đã duyệt; workflow lab chưa phải mô hình đó.

## Judge, trace và giới hạn

Tone: κ=.757, P=.857, R=.800, đạt FLOORS. Helpful: κ=.375, P=1, R=.300, bỏ sót 21/30 lỗi,
không dùng làm gate. [Judge audit](judge_audit.md) có 12 bất đồng và đề xuất sửa rubric.
Nhãn người public và note được dùng để phân tích; chưa có audit người độc lập mới.

[Trace case](trace_case.md): C-002@11, bước sai đầu tiên event 3 model_override, regression
test `test_c002_first_wrong_step_and_fixed_control`; [taxonomy](failure_taxonomy.md) có
8 probe lỗi thực và 1 trường hợp cross-principal bị chặn.

MockLLM tất định không mô phỏng đầy đủ LLM thật; v1 14 item nên CI rộng, v2 có nhiều item
chung order. Bug xảy ra khoảng **1/3 seed không được bảo đảm phát hiện ổn định với 5 seed**.
Nếu giả sử lỗi độc lập với p=1/3, xác suất cả 5 lần không gặp lỗi là (2/3)^5≈13.2%; phát hiện
một lần lỗi cũng chưa chắc đủ để làm metric rơi dưới ngưỡng. Không suy ra một con số seed
“đủ” cho production từ fixture này. Judge replay đã public, chưa có held-out hoặc khách thật.
Cost mô phỏng, latency chưa đo. Reply grader chỉ so số VND rõ ràng với ledger một claim;
không có reply/không có số tiền được coi là không có phát biểu tiền cần kiểm. Swarm gốc không
ghi reply nên điểm 1.0 của metric này không chứng minh chất lượng ngôn ngữ của swarm.

Thêm/đổi item, nhãn hoặc slice phải tăng eval-set version và sinh baseline mới; sửa metric
phải tăng spec version, chỉ siết ngưỡng trong cùng eval set. Gate exit 1: Lê Quốc Khánh đọc
trial/trace, sửa hoặc revert, chạy lại; không nới ngưỡng để thông qua bản lỗi.
