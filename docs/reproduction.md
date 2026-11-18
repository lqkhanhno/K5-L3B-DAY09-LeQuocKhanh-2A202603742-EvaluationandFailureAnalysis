# Tái lập bài Day 9

- Học viên: **Lê Quốc Khánh — 2A202603742 — L3B**, GitHub `lqkhanhno`.
- Mã gốc Day 8: [VinUni-AI20k/K5-Day8-From-Workflows-to-Agents](https://github.com/VinUni-AI20k/K5-Day8-From-Workflows-to-Agents/tree/034c6c421c198dae67a9211d15e2587d5a378972), commit `034c6c421c198dae67a9211d15e2587d5a378972`.
- Chỉ sao chép `src/`; không dùng ba shape của bài nhóm. Cây Git `src/lab8/` có SHA
  `3c305719d3af16f77f6f6833963ea1f7c12e3083`, bằng cây gốc.
- Mã grader hoàn chỉnh: commit `f4c1ec269ebe629fcba2ea66c889906cd031c11f`; commit của lần
  chạy lại bằng chứng ghi trong `reports/analysis_evidence.json.code_commit`.
- Công cụ AI: **Codex** đọc đề, triển khai TODO, viết test, chạy lệnh và soạn tài liệu dựa trên
  output thật. Không tuyên bố học viên đã tự review hay có phê duyệt Product. Học viên cần
  đọc và giải thích được các quyết định trước khi trình bày bài.

## Một lệnh kiểm lại toàn bộ

PowerShell, từ gốc repo:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r src/requirements.txt -r src/requirements-lab9.txt
$env:PYTHONUTF8 = '1'
cd src
..\.venv\Scripts\python scripts/verify_day9.py
```

Linux/macOS: tạo và kích hoạt venv, cài cùng hai requirements, vào `src/` rồi chạy
`python scripts/verify_day9.py`. Dùng Python 3.11–3.13 theo đề; máy này kiểm bằng 3.12.7.

Script chạy host tests, Day 9 student tests, kiểm eval set, judge, baseline, gate v1/v2,
detection, A/A, mutation và bốn trap. Nó kiểm exit code **mong đợi**: helpful, bản regression
và từng trap phải exit 1. Log nguyên văn sinh vào `reports/verification.json`.
Report sinh bằng `lab9.eval`, trace evidence bằng `lab9.evidence`; không sửa tay.

Dựng lại dữ liệu từ đầu trước verify:

```text
python -m lab9.evalset --build --check
python -m lab9.evalset --v2 --build
```

`.gitattributes` giữ LF cho eval set để SHA không đổi giữa Windows và Linux.
Không chạy song song các eval trên cùng thư mục vì chúng ghi chung `traces/`.

## Phạm vi kiểm chứng

Các test Day 8 cho `workflow/single/orchestrator` vẫn là bài tập stub của repo gốc. Day 9
dùng `swarm` và variant của giảng viên. Chạy host `pytest -q`, student tests `-k lab9`
theo workflow; không sửa stub để biến Day 9 thành bài Day 8.

Key 5 anchor và bộ test ẩn không có trong repo học viên. Taxonomy cung cấp trace thực,
event đầu sai và lệnh tái lập để đối chiếu; kết quả public không phải điểm chấm ẩn.
Bonus Inspect AI/DeepEval là tùy chọn và chưa thực hiện.

## Nộp bài

Commit report bằng `git add -f src/reports/*.json`. PR trong fork: `starter/d09` → `main`;
đính kèm output mutation/A-A/gate và merge khi `eval-gate`, `eval-gate-v2` xanh.
Học viên nộp link repo lên LMS của lớp, kiểm hạn theo ca; repo không cung cấp hạn cụ thể.
