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
| Demo cảnh báo giao trễ sớm | [streamlit_late_risk_demo.py](scripts/streamlit_late_risk_demo.py) và [giải thích demo](docs/giai-thich-demo-streamlit.md) |

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

`export_mysql_evidence.py`, `run_mysql_eda.py`, `mysql_dss.py` và `forecast_late_delivery.py` đọc MySQL, ghi bằng chứng vào `docs/evidence/mysql/` và hình vào `notebooks/eda_output/`. Riêng `publish_mysql_forecast.py` **ghi lại bảng phục vụ dự báo Power BI** `PowerBIForecastMonthly`; `run_mysql_demo_cycle.py` ghi và đặt lại **chỉ các bảng `Demo*`**. Chi tiết đối soát: [mysql-migration.md](docs/mysql-migration.md).

`notebooks/olist_bi_dss.ipynb` là bản phân tích CSV lịch sử giữ để tham khảo các phép DSS; **EDA chính để báo cáo hiện tại là kết quả chạy lại từ MySQL** bằng `run_mysql_eda.py`.

Mở project Power BI tại [PBIP](powerbi/pbip_project/G8_Olist_Overview_MySQL.pbip), thiết lập thông tin đăng nhập MySQL trong Power BI Desktop, rồi Refresh. Nguồn hiện tại là `olist_bi_group08`. Bằng chứng KPI nền nằm ở [overview.csv](docs/evidence/mysql/overview.csv); cần đối chiếu sau mỗi lần Refresh trước khi dùng ảnh vào báo cáo.

## Demo Streamlit

Ở terminal thứ nhất:

```powershell
python -m streamlit run scripts/streamlit_late_risk_demo.py
```

Mở `http://localhost:8501`. Nếu muốn tab micro-batch tự thay đổi, ở terminal thứ hai chạy:

```powershell
python scripts/run_mysql_demo_cycle.py
```

Runner phát lại tối đa 500 sự kiện mỗi lô, cách 5 giây, từ đơn mua tháng 07/2018. Nó chỉ đặt lại bảng `Demo*` khi chạy vòng mới. Điểm mô hình đã tính trước trên **các đơn kiểm thử lịch sử đã giao và có nhãn**; đơn chưa có kết quả giao chưa được chấm điểm trong demo offline này. Không có học lại hoặc scoring live theo lô. Xem [tài liệu demo](docs/giai-thich-demo-streamlit.md) và [kiểm toán phương pháp](docs/evidence/mysql/forecast_late_delivery/methodology_audit.md).

## Kiểm tra và giới hạn

`python scripts/validate_project.py` kiểm tra mã, EDA và PBIP mà không thay đổi MySQL. Kết quả phát hiện rủi ro là backtest trên đơn đã giao có nhãn, chưa chứng minh can thiệp làm giảm giao trễ. Phần báo cáo cuối cần phân biệt kết quả đã triển khai với phương án Cloud và các giới hạn dữ liệu.
