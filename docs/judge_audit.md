# Judge audit — Lê Quốc Khánh · 2A202603742

Nguồn: hai CSV public nguyên bản; kết quả sinh bằng `lab9.judge` và lưu trong
[`analysis_evidence.json`](../src/reports/analysis_evidence.json). FAIL là lớp dương:
precision đo độ chính xác khi báo lỗi, recall đo tỷ lệ lỗi được tìm thấy.

| Tiêu chí | n | TP / FP / FN / TN | κ | Precision | Recall | FLOORS | Quyết định |
|---|---:|---|---:|---:|---:|---|---|
| tone_ok | 100 | 24 / 4 / 6 / 66 | 0.757 | 0.857 | 0.800 | PASS | Dùng cho giọng điệu trong phạm vi đã hiệu chuẩn |
| helpful | 100 | 9 / 0 / 21 / 70 | 0.375 | 1.000 | 0.300 | FAIL | Loại khỏi release gate |

FLOORS: κ ≥ 0.6, P ≥ 0.8, R ≥ 0.7; cả ba phải đạt. Kappa không xác định không được
coi là đạt. Helpful bỏ sót 21/30 lỗi: precision 1.0 không bù được recall 0.3.
Tỷ lệ lỗi tone quan sát 0.28, sau Rogan–Gladen là 0.30; helpful 0.09 → 0.30.
Hiệu chỉnh tỷ lệ tổng thể không sửa từng phán quyết sai và không làm helpful đủ điều kiện làm gate.

## Audit các bất đồng và hành động sửa rubric

Đây là phân tích bằng Codex dựa trên reply, nhãn và `note` đã có trong CSV; không phải một
đợt gán nhãn người mới. Các đề xuất dưới đây chưa được thử trên held-out mới.

| Case | Judge / người | Đối chiếu bằng chứng | Kết luận trong rubric của lab | Hành động |
|---|---|---|---|---|
| H-008 | PASS / FAIL | “em”, “nha”, “anh check” quá suồng sã | Theo nhãn người | Thêm ví dụ FAIL cho xưng hô thân mật trong xử lý khiếu nại |
| H-017 | PASS / FAIL | “bạn ơi”, “rồi nha”; note ghi khách lớn tuổi | Theo nhãn người với ngữ cảnh trong note | Rubric cần ngữ cảnh xưng hô; không đồng nhất thân thiện với phù hợp |
| H-029 | PASS / FAIL | “không cần nhắn thêm” ngăn khách phản hồi | Theo nhãn người | Đọc toàn câu; “Dạ, vui lòng” không tự động tạo PASS |
| H-042 | FAIL / PASS | Thông báo hoàn và thời gian tiền về, lịch sự nhưng ngắn | Theo nhãn người | Không bắt buộc xin lỗi hay câu dài khi thông báo đã đủ nội dung |
| H-051 | FAIL / PASS | “refund” được CS LogiX cho phép theo note | Theo nhãn người | Ghi rõ thuật ngữ được phép, không phạt mọi từ tiếng Anh |
| H-063 | PASS / FAIL | Hứa “sẽ hoàn thêm” ngoài kết quả hệ thống | Theo nhãn người | Không hứa vượt kết quả; số tiền đối chiếu ledger bằng code |
| H-070 | PASS / FAIL | Emoji cười không phù hợp khiếu nại | Theo nhãn người | Thêm ví dụ về emoji và ngữ cảnh |
| H-081 | FAIL / PASS | Note nói người đọc nhầm ticket, judge đúng | Đề xuất sửa nhãn người, cần người thứ hai xác nhận từ ticket gốc | Đưa vào hàng đợi adjudication; không sửa CSV hoặc báo κ mới như đã đo |
| H-088 | FAIL / PASS | Lặp “Dạ” do lỗi gõ, vẫn lịch sự | Theo nhãn người | Phân biệt lỗi gõ nhẹ với sai giọng điệu |
| H-094 | PASS / FAIL | Reply mất dấu tiếng Việt | Theo quy chuẩn lab | Nêu yêu cầu tiếng Việt có dấu trong rubric |
| HL-015 | PASS / FAIL | Reply 55.000đ, note ledger 40.000đ | Theo nhãn người | Tách đúng tiền khỏi lịch sự; dùng `ReplyAmountCorrect` |
| HL-016 | PASS / FAIL | Nhiều câu xin lỗi nhưng reply 55.000đ, ledger 35.000đ | Theo nhãn người | Không cho độ dài/xin lỗi bù lỗi tiền; đối chiếu ledger |

Tiền và approval dùng code (`RefundAmountCorrect`, `ApprovalBypass`, `ReplyAmountCorrect`).
Tone đủ calibration trên replay nhưng chưa là metric blocking của agent: harness không có
judge mới chấm từng trace. Không coi điểm tone của CSV là điểm của swarm.

## Tái lập

Chạy trong `src/`:

```text
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 10
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
```

Lệnh thứ hai trả exit 1 đúng thiết kế. Cần rubric phiên bản mới, hai người gán nhãn độc lập
và held-out mới trước khi đánh giá lại; không dùng lại cùng 100 mẫu để tuyên bố cải thiện.
