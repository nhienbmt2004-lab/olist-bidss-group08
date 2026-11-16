# Dashboard web theo chu kỳ — kiểm tra 15/11/2026

Đã khởi động server cục bộ `scripts/serve_mysql_operational.py` ở `http://127.0.0.1:8765/` và runner `scripts/run_mysql_demo_cycle.py --batch-size 500 --interval-seconds 5 --pause-seconds 20`. Dashboard hỏi lại API mỗi 5 giây; runner phát lại dữ liệu Olist tháng 07/2018 từ MySQL staging. Đây là mô phỏng, không phải đơn phát sinh trực tiếp.

| Kiểm tra | Kết quả |
|---|---:|
| `GET /` | HTTP 200, HTML có bộ hẹn giờ `setInterval(refresh,5000)` |
| `GET /api/status` | HTTP 200, có checkpoint và KPI |
| Mẫu đọc lần 1 | 1.500/23.983 sự kiện; 913 đơn đã xuất hiện |
| Mẫu đọc sau 7 giây | 2.500/23.983 sự kiện; 1.019 đơn đã xuất hiện |
| Mẫu đọc sau đó | 9.500/23.983 sự kiện, 19 lô, 3.100 đơn đã xuất hiện |
| Gần cuối chu kỳ 1 | 22.500/23.983 sự kiện, 45 lô, 6.130 đơn đã xuất hiện |
| Hết chu kỳ 1 | 23.983/23.983 sự kiện, 48 lô |
| Tự lặp chu kỳ 2 sau khoảng nghỉ | API đọc được 2.000/23.983 sự kiện, 4 lô, 924 đơn xuất hiện; log có `cycle 2` |
| Fact lịch sử sau khi đặt lại Demo | `FactOrderDelivery` 99.441 dòng; `FactOrderItem` 112.650 dòng, không đổi |

Tiến độ và số đơn thay đổi qua các lần đọc chứng minh server đang nhận lô mới và API đang phục vụ giá trị hiện tại từ MySQL. Đã quan sát chu kỳ 1 kết thúc và chu kỳ 2 tự bắt đầu, nên chế độ lặp đã được kiểm tra thực tế. Đồng hồ sự kiện trên giao diện là thời điểm năm 2018 của dữ liệu nguồn; đồng hồ nạp là thời gian máy chạy mô phỏng. Luồng lặp đợi 20 giây sau lô cuối rồi đặt lại chỉ các bảng `Demo*`.

Việc tự mở trình duyệt từ phiên công cụ bị Windows từ chối quyền (`Start-Process http://127.0.0.1:8765/` → Access denied). Người dùng mở trực tiếp địa chỉ trên trong trình duyệt của máy. Server/API và runner vẫn chạy nền độc lập với thao tác mở trang.
