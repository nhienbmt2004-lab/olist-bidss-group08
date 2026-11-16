# Dọn repo Olist — 16/11/2026

## Kết quả

- Luồng chính hiện được trình bày nhất quán trong [README](../README.md): **MySQL → EDA/DSS → PBIP 6 trang + Streamlit**. [PROJECT_MAP](../PROJECT_MAP.md) chỉ ra tệp chính cho từng phần.
- Đã chạy lại EDA từ MySQL bằng `python scripts/run_mysql_eda.py`, cập nhật CSV/hình cho BQ1–BQ5. KPI nền vẫn là **99.441 đơn, 6.534/96.470 đơn trễ, OTD 93,23%, GMV R$13.591.643,70**. Đã xuất lại đối soát MySQL và kiểm tra seller/danh mục.
- Power BI chính là `powerbi/pbip_project/G8_Olist_Overview_MySQL.pbip`, có sáu trang và 12 nguồn MySQL. Đã gỡ tab TMDL `Script 1` chứa nguồn SQL Server cũ; ba script MySQL/sửa measure còn lại và semantic model hiện tại được giữ. `G8_Olist_Overview_MySQL.pbix` là snapshot cũ hơn để tham khảo/mở nhanh, chưa phải bản xuất cuối từ PBIP.
- Bộ SQL Server/SSIS cũ, PBIX v2/v4, loader cũ, demo cũ, các bản vá TMDL đã áp dụng và tài liệu nháp lỗi thời được chuyển vào **`temp/repo_cleanup_backup_20261116/`**. Thư mục này nằm trong workspace nhưng bị Git bỏ qua; có thể phục hồi thủ công. Các tệp từng được Git theo dõi sẽ hiện là deleted cho đến khi commit thay đổi.
- [Kiểm kê MySQL](mysql-schema-audit.md): **32 bảng, 6 view**, tất cả có vai trò trong ETL, phân tích, dự báo, log hoặc demo. Không xóa schema/bảng nào; các database khác trên máy không thuộc repo và được giữ nguyên.

## Kiểm tra sau dọn

| Kiểm tra | Kết quả |
| --- | --- |
| EDA MySQL BQ1–BQ5 | Chạy thành công; `eda_kpi_check.csv` khớp `overview.csv` |
| Xuất bằng chứng ETL/KPI MySQL | Chạy thành công; 10 phép đối soát có log |
| Seller/danh mục | 210 seller đủ ngưỡng, tỷ lệ trễ 0–19,02%; 54 danh mục đủ ngưỡng, review 3,618–4,463 |
| `python scripts/validate_project.py` | Đạt: kiểm tra Python, draw.io, local links, PBIP sáu trang/12 nguồn MySQL và EDA |
| `python -m pytest testing/test_mysql_replay.py -q` | Đạt 1 test |

## Việc còn cần thao tác trong Power BI Desktop

Không có công cụ Power BI Desktop để xuất PBIX cuối và chụp sáu trang trong bước dọn repo này. Khi cần bàn giao PBIX, mở **PBIP chính**, Refresh, đối chiếu KPI với [overview.csv](evidence/mysql/overview.csv), kiểm tra từng trang, rồi Save As PBIX. Hai ảnh BQ4/BQ5 hiện có ở `docs/evidence/powerbi/`; các trang còn lại chưa có ảnh xác nhận sau lần Refresh mới.

## Cách gọi kiến trúc trong báo cáo

Schema MySQL có ba lớp xử lý **staging → clean/transform → Dim/Fact**, tương ứng với ý tưởng Bronze–Silver–Gold về vai trò. Chưa triển khai một nền tảng Medallion đầy đủ với ba vùng lưu trữ/quyền/vòng đời riêng; dùng cách gọi “pipeline ba lớp” và giải thích sự tương đồng là chính xác nhất.
