# Source — Day 9 LogiX-VN

Thư mục này gồm `lab8/` nguyên bản giảng viên và harness `lab9/` đã hoàn thành M0–M7.
Mọi lệnh Python của bài chạy tại đây. Không cần API key hay model thật.

| Thành phần | Vai trò |
|---|---|
| `lab8/` | Agent/host/ledger gốc, không sửa; dùng swarm cho baseline Day 9 |
| `lab9/stats.py`, `graders.py`, `evalset.py` | Thống kê, grader, dựng dữ liệu và tách nhãn |
| `lab9/gate.py` | Gate global, slice, integrity và ratchet |
| `config/metric_spec.yaml`, `metric_spec_v2.yaml` | Ngưỡng theo version, seed cố định |
| `config/fm_map.yaml` | Cơ chế tấn công → mã failure mode |
| `data/eval/` | Eval set v1/v2, nhãn riêng, CSV judge replay và pack adversarial |
| `reports/` | Bằng chứng do script sinh; phải force-add trước commit |
| `tests/test_lab9_*.py` | Test công khai và regression test bổ sung |
| `scripts/verify_day9.py` | Chạy trọn bộ kiểm tra, xác nhận cả exit 1 mong đợi |
| `lab9/evidence.py` | Sinh trace evidence đã lược dữ liệu nhạy cảm và judge calibration |

## Cài và chạy

Từ gốc repo, tạo venv và cài `src/requirements.txt`, `src/requirements-lab9.txt`.
Chi tiết PowerShell/Linux: [reproduction](../docs/reproduction.md).
Sau khi kích hoạt venv, từ `src/`:

```text
python -m lab9.smoke
python -m lab9.evalset --build --check
python -m lab9.evalset --v2 --build
python scripts/verify_day9.py
```

`pytest -q` là cổng host. Student tests Day 9 dùng
`python -m pytest -q -m student -o addopts= -k lab9`.
Ba shape bài tập Day 8 vẫn là stub của nguồn gốc; không chạy ma trận student Day 8 trên cả
ba stub rồi coi đó là regression Day 9.

## Báo cáo và nộp bài

Tài liệu chính: [eval card](../docs/eval_card.md), [PRD](../docs/PRD_v1.1.md),
[taxonomy](../docs/failure_taxonomy.md), [trace case](../docs/trace_case.md),
[judge audit](../docs/judge_audit.md).

Từ `src/`: `git add -f reports/*.json`. Không commit trace thô, SQLite, venv hay secret.
Không sửa tay report, nhãn public, agent Day 8, variant hoặc trap để đổi kết quả chấm.
Ngưỡng chỉ siết trong cùng version. Thủ tục GitHub/LMS: [SUBMISSION](../SUBMISSION.md).
