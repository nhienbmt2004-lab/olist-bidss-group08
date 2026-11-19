# Olist BI/DSS — Group 08

Đề tài: **Phân tích giao trễ và hỗ trợ ưu tiên điều tra**, dùng dữ liệu Olist lịch sử. Olist là nguồn dữ liệu công khai, không phải khách hàng đặt hệ thống. Luồng đang dùng là **MySQL → Power BI + DSS/Streamlit**; không có nguồn đơn hàng live hay Cloud BI đã triển khai.

## Bắt đầu từ đâu?

| Việc cần xem | Tệp chính |
| --- | --- |
| Hiểu bài toán, phạm vi, tiến độ báo cáo | [PROJECT_MAP.md](PROJECT_MAP.md) |
| Sơ đồ toàn hệ thống | [draw.io framework](diagrams/olist-bi-dss-framework.drawio) |
| Xây kho dữ liệu MySQL | [build_mysql_dw.py](scripts/build_mysql_dw.py) và [SQL](sql/mysql/) |
| EDA theo 5 câu hỏi kinh doanh | [EDA evidence](docs/evidence/mysql/eda/README.md) và [run_mysql_eda.py](scripts/run_mysql_eda.py) |
| Dashboard 6 trang đang chỉnh sửa | [Power BI Project](powerbi/pbip_project/G8_Olist_Overview_MySQL.pbip) |
| Bản PBIX MySQL lưu trước bản PBIP | [G8_Olist_Overview_MySQL.pbix](powerbi/G8_Olist_Overview_MySQL.pbix) |
| Demo RouteOps phát lại lịch sử | [streamlit_late_risk_demo.py](scripts/streamlit_late_risk_demo.py), đặc tả giao diện trong `document/Demo (2).pdf` và `document/Demo (3).pdf`, cùng [hướng dẫn ba màn hình](docs/giai-thich-demo-streamlit.md) |

**Dùng PBIP làm bản Power BI chính:** PBIP được lưu sau PBIX MySQL và chứa sáu trang BQ đã chỉnh. PBIX chỉ là snapshot cũ hơn; khi cần PBIX mới, mở PBIP trong Power BI Desktop rồi **Save As → Power BI report (*.pbix)**. Không lấy PBIX cũ làm bản báo cáo cuối nếu chưa xuất lại từ PBIP.

## Luồng dữ liệu

```text
9 CSV Olist → MySQL stg_* ──────────────→ phát lại sự kiện theo lô → Demo* → Streamlit
                       └→ Clean*/Order*Totals → 6 Dim + 4 Fact
                                               ├→ Power BI Import: 6 trang
                                               └→ EDA, KPI, DSS, dự báo rủi ro
                                                            └→ điểm đã tính → Streamlit
```

Ba lớp đầu tương ứng **về chức năng** với Bronze–Silver–Gold, nhưng repo hiện triển khai bằng một schema MySQL `olist_bi_group08`, không phải nền tảng Medallion có ba tầng lưu trữ và quản trị riêng. `stg_*` giữ ảnh nguồn CSV, `Clean*`/`Order*Totals` là bảng xử lý trung gian, `Dim*`/`Fact*` phục vụ phân tích. Các bảng `ETL*`/`DataQualityIssues` giữ log và đối soát. `Demo*` chỉ phục vụ phát lại sự kiện. Không xóa các bảng này nếu muốn tái lập ETL và demo.

Kiểm kê chi tiết và lý do giữ từng nhóm: [mysql-schema-audit.md](docs/mysql-schema-audit.md).

## Chạy trên máy cục bộ

Yêu cầu: Python 3.11+, MySQL Server tại `127.0.0.1:3306`, Power BI Desktop và MySQL Connector/NET. Mật khẩu đặt trong `.mysql-password` ở thư mục gốc hoặc biến môi trường `OLIST_MYSQL_PASSWORD`; không đưa mật khẩu vào Git. Chín CSV nguồn đặt trong `data/raw/` (Git bỏ qua).

**Lần đầu, khi schema `olist_bi_group08` chưa có bảng**, chạy:

```powershell
python -m pip install -r requirements-forecast.txt
python scripts/build_mysql_dw.py
```

`build_mysql_dw.py` từ chối chạy nếu schema đã có bảng; **không chạy lại lệnh build để refresh dữ liệu đang dùng**. Trên máy hiện tại schema đã được dựng. Để tạo lại EDA và bằng chứng từ schema đó, chạy:

```powershell
python scripts/export_mysql_evidence.py
python scripts/run_mysql_eda.py
python scripts/mysql_dss.py
python scripts/publish_mysql_forecast.py
python scripts/forecast_late_delivery.py
python scripts/plot_late_forecast.py
python scripts/audit_mysql_schema.py
python scripts/validate_project.py
```

`export_mysql_evidence.py`, `run_mysql_eda.py`, `mysql_dss.py` và `forecast_late_delivery.py` đọc MySQL, ghi bằng chứng vào `docs/evidence/mysql/` và hình vào `notebooks/eda_output/`. Riêng `publish_mysql_forecast.py` **ghi lại bảng phục vụ dự báo Power BI** `PowerBIForecastMonthly`; `run_mysql_demo_cycle.py` ghi và đặt lại các bảng sự kiện/checkpoint/batch `Demo*`. Nhật ký quyết định mô phỏng `DemoActionLog` được giữ riêng qua các chu kỳ và lọc theo lượt replay hiện tại. Chi tiết đối soát: [mysql-migration.md](docs/mysql-migration.md).

`notebooks/olist_bi_dss.ipynb` là bản phân tích CSV lịch sử giữ để tham khảo các phép DSS; **EDA chính để báo cáo hiện tại là kết quả chạy lại từ MySQL** bằng `run_mysql_eda.py`.

Mở project Power BI tại [PBIP](powerbi/pbip_project/G8_Olist_Overview_MySQL.pbip), thiết lập thông tin đăng nhập MySQL trong Power BI Desktop, rồi Refresh. Nguồn hiện tại là `olist_bi_group08`. Bằng chứng KPI nền nằm ở [overview.csv](docs/evidence/mysql/overview.csv); cần đối chiếu sau mỗi lần Refresh trước khi dùng ảnh vào báo cáo.

## Demo Streamlit

Ở terminal thứ nhất:

```powershell
python -m streamlit run scripts/streamlit_late_risk_demo.py
```

Mở `http://localhost:8501`. Demo có ba màn hình trong thanh điều hướng bên trái: Route Overview, Route Detail và Seller Performance. Đồng hồ điều khiển ngày quan sát lịch sử; không phải nguồn đơn hàng live.

Nếu muốn chạy micro-batch MySQL riêng, ở terminal thứ hai chạy:

```powershell
python scripts/run_mysql_demo_cycle.py
```

Runner phát lại các đơn mua tháng 03/2018, tối đa 500 sự kiện mỗi lô, cách 5 giây. Đây là phần micro-batch riêng với RouteOps. Bản đồ geohash thể hiện nơi khách nhận; màu ô kế thừa OTD của tuyến, không phải KPI riêng cho ô. Năm vùng nền suy ra từ `StateCode` vì `DimGeography` không có cột `Region`.

Các bảng để kiểm tra số liệu demo tại **15/03/2018** được xuất ở [output/streamlit_2018-03-15/](output/streamlit_2018-03-15/). Tạo lại bằng `python scripts/export_streamlit_snapshot.py --as-of-date 2018-03-15`; bảng đối soát nằm ở [backend_reconciliation.csv](output/streamlit_2018-03-15/backend_reconciliation.csv), màu và OTD tuyến của từng ô ở [map_geohash_cells.csv](output/streamlit_2018-03-15/map_geohash_cells.csv).

## Kiểm tra và giới hạn

`python scripts/validate_project.py` kiểm tra mã, EDA và PBIP mà không thay đổi MySQL. Kết quả phát hiện rủi ro là backtest trên đơn đã giao có nhãn, chưa chứng minh can thiệp làm giảm giao trễ. Phần báo cáo cuối cần phân biệt kết quả đã triển khai với phương án Cloud và các giới hạn dữ liệu.
