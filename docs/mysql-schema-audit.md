# Kiểm kê schema MySQL và quyết định giữ/xóa

Kiểm tra lại ngày 17/11/2026 bằng `python scripts/audit_mysql_schema.py`, chỉ đọc schema `olist_bi_group08`. [Danh sách 39 đối tượng và số dòng tại lúc chạy](evidence/mysql/schema_inventory.csv) gồm **33 bảng, 6 view**; không có đối tượng ngoài các nhóm thiết kế. Số dòng `Demo*` thay đổi khi replay chạy.

| Nhóm | Số bảng/view | Vì sao giữ |
| --- | ---: | --- |
| `stg_*` | 9 bảng | Bản dữ liệu nạp từ CSV, nguồn ETL, EDA và replay; hỗ trợ đối soát lại với CSV. |
| `Clean*`, `Order*Totals`, `OrderReviewLatest` | 5 bảng | Làm sạch và tổng hợp theo khóa đơn trước khi nạp Dim/Fact; cho phép kiểm tra các bước ETL. |
| `Dim*` | 6 bảng | Dimension của star schema và nguồn Power BI. |
| `Fact*` | 4 bảng | Fact đơn giao, item, thanh toán và review; nguồn KPI/EDA/DSS/Power BI. |
| `ETL*`, `DataQualityIssues` | 4 bảng | Log lần chạy, các bước, đối soát và vấn đề chất lượng dữ liệu. |
| `PowerBIForecastMonthly` | 1 bảng | Nguồn của partition `ForecastMonthly` trong PBIP; hiện 46 dòng. |
| `DemoOrderEvent`, `DemoReplayCheckpoint`, `DemoReplayBatch` | 3 bảng | Sự kiện phát lại, checkpoint và log batch cho Streamlit. |
| `DemoActionLog` | 1 bảng | Nhật ký đề xuất xử lý mô phỏng, giữ qua các lượt replay và lọc theo lượt hiện tại. |
| `vw_*` | 6 view | KPI lịch sử, seller và trạng thái/KPI demo. |

**Kết luận:** không có bảng hoặc view nào được chứng minh là dư; **không xóa đối tượng MySQL**. Xóa `Dim*`/`Fact*` làm hỏng Power BI, xóa `stg_*`/bảng trung gian làm mất khả năng tái lập và đối soát, xóa `Demo*` làm hỏng màn hình micro-batch. Những schema khác trong MySQL Server không thuộc đồ án và không được đụng tới.

Server còn nhiều schema khác. `latedeliverydb` chứa các bảng Django như `auth_*`, `django_*` và `order_*`; repo này không tham chiếu tới nó. Đây có thể là ứng dụng khác trên máy, nên **không xóa** khi dọn đồ án Olist. Các schema hệ thống và bài tập khác cũng được giữ nguyên.

`stg_*` → bảng clean/transform → `Dim*`/`Fact*` là ba lớp tương ứng **về chức năng** với Bronze–Silver–Gold. Hiện các lớp cùng nằm trong một schema MySQL, chưa có các vùng lưu trữ, chính sách vòng đời, quyền truy cập và orchestration riêng của một nền tảng Medallion đầy đủ. Trong báo cáo nên gọi là **pipeline ba lớp staging–clean–warehouse**, có thể liên hệ với Medallion, thay vì tuyên bố đã triển khai Medallion Architecture hoàn chỉnh.
