# Bằng chứng chạy micro-batch MySQL — 15/11/2026

Nguồn: `olist_bi_group08.stg_Orders`, chọn đơn đã giao có ngày giao, ngày đặt từ 01/07/2018 đến 31/07/2018. Đây là phát lại lịch sử, không phải đơn mới.

| Kiểm tra | Kết quả |
|---|---:|
| Đơn nguồn được chọn | 6.156 |
| Đơn loại do mốc giao không hợp lệ | 26 |
| Đơn đủ điều kiện phát lại | 6.130 |
| Mốc carrier sai thứ tự được bỏ qua | 563 |
| Sự kiện phát lại | 23.983 |
| Số lô, cỡ lô tối đa 500 | 48 |
| `NextEventIndex = TotalEvents = COUNT(DemoOrderEvent) = SUM(DemoReplayBatch.EventCount)` | 23.983 = 23.983 = 23.983 = 23.983 |
| Đơn hiển thị cuối kỳ | 6.130 |
| Số đơn giao trễ trong demo = số tương ứng trong FactOrderDelivery | 208 = 208 |
| Tổng bốn trạng thái cuối kỳ = số đơn hiển thị | 6.130 = 6.130 |
| Cặp `(OrderId, EventType)` bị trùng | 0 |

Sau 3 lô đầu, API dashboard `GET http://127.0.0.1:8765/api/status` trả HTTP 200, checkpoint `1.500/23.983`, 913 đơn đã xuất hiện. Ở checkpoint `22.000/23.983`, dashboard có 6.130 đơn đã xuất hiện, 346 đơn chờ bàn giao, 36 đơn chưa giao quá ngày dự kiến và 20 đơn đã giao trễ. Sau khi chạy tiếp đến cuối, dashboard trả 6.130 đơn đã giao và 208 đơn giao trễ.

Kiểm tra bằng `python -m unittest discover -s testing -p 'test_*replay.py' -v` và `python scripts/validate_project.py` đều đạt. Các số ở đây chỉ thuộc cohort mô phỏng tháng 7/2018; KPI Power BI lịch sử dùng toàn bộ Olist nên không so trực tiếp hai tổng số.
