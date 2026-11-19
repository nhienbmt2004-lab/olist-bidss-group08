# Olist BI/DSS — Group 08

## Mục tiêu

Dự án phân tích hiệu quả giao hàng của Olist bằng MySQL và Power BI, sau đó trình diễn luồng hỗ trợ vận hành theo ngày lịch sử trong Streamlit. Chỉ số vận hành được tính theo dữ liệu đã quan sát đến ngày mô phỏng. Đây là dữ liệu lịch sử; demo không kết nối hãng vận chuyển hay gửi thông báo thật.

## Luồng hệ thống

```text
9 CSV Olist
  → MySQL staging
  → làm sạch và biến đổi ETL
  → Data Warehouse (dimension/fact, KPI, audit)
       ├→ Power BI: phân tích lịch sử, KPI, forecast và what-if
       └→ Streamlit: phát lại sự kiện lịch sử theo micro-batch
                    → Route Overview
                    → Route Detail
                    → Seller Performance
```

- **MySQL** là cơ sở dữ liệu chính. Pipeline không dùng SQLite.
- **Power BI:** chỉ giữ project mới nhất `powerbi/G8_Olist_Final.pbip` cùng hai thư mục `G8_Olist_Final.Report/` và `G8_Olist_Final.SemanticModel/`. Cấu hình MySQL trong Power BI Desktop rồi mới Refresh.
- **Streamlit:** phát lại sự kiện lịch sử vào các bảng `Demo*`; đồng hồ và trạng thái dùng checkpoint trong MySQL. Đây là mô phỏng micro-batch, không phải streaming live.
- **Bản đồ:** các ô geohash biểu diễn cụm vị trí khách nhận đã tổng hợp. Bản đồ nền dùng tile OpenStreetMap; cần giữ attribution của OpenStreetMap.
- Olist không cung cấp mã hãng vận chuyển. Phân tích dừng ở cấp tuyến/bang, không quy lỗi cho một carrier cụ thể. Ngưỡng cảnh báo và kịch bản what-if là giả định minh họa; không được diễn giải thành quan hệ nhân quả hay doanh thu đã cứu được.

## Power BI và Streamlit

### Power BI mới nhất

Mở `powerbi/G8_Olist_Final.pbip` bằng Power BI Desktop. Đây là Power BI project duy nhất trong repo. Khi kết nối MySQL lần đầu, cấu hình host, port và schema của máy cục bộ; không đưa mật khẩu vào file dự án hay Git.

Project có năm trang: **Executive Overview**, **Delivery & Geography**, **Seller Performance Analysis**, **Product/Category Analysis** và **Seller Scorecard**.

### Ba màn hình Streamlit

1. **Route Overview** — tổng quan tuyến và điểm cần chú ý tại ngày mô phỏng.
2. **Route Detail** — hiệu suất tuyến, mô phỏng riêng cho đơn đã giao và nhóm đơn chưa giao, cùng hàng đợi cần xử lý.
3. **Seller Performance** — chỉ số người bán trên tuyến được chọn và phân hạng theo công thức đồ án.

Hành động và mô phỏng chỉ diễn ra trong môi trường demo. Chúng không liên hệ khách hàng/carrier và không thay đổi đơn hàng sản xuất.

## Cài đặt và chạy

Yêu cầu: Python 3.11, MySQL Server ở `127.0.0.1:3306`, schema `olist_bi_group08`, và chín CSV Olist trong `data/raw/`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-forecast.txt
```

Đặt mật khẩu MySQL root thành **một dòng** trong file local `.mysql-password` (đã được Git ignore). Không commit hoặc gửi mật khẩu.

```powershell
python -m streamlit run scripts/streamlit_late_risk_demo.py
```

Mở `http://localhost:8501`. Nếu MySQL không sẵn có, app có thể đọc snapshot `data/processed/streamlit_history_fallback.csv`; snapshot không phát triển theo replay MySQL.

## Pipeline dữ liệu

Các lệnh theo thứ tự khi cần dựng/cập nhật kết quả:

```powershell
# Tạo warehouse khi schema chưa có bảng; script từ chối ghi đè schema không rỗng.
python scripts/build_mysql_dw.py

# Kiểm tra schema, chạy EDA và xuất evidence từ MySQL.
python scripts/audit_mysql_schema.py
python scripts/run_mysql_eda.py
python scripts/export_mysql_evidence.py
python scripts/mysql_dss.py

# Temporal model evaluation; reads MySQL and writes validation evidence.
python scripts/forecast_late_delivery.py
python scripts/plot_late_forecast.py

# Phát lại cohort tháng 03/2018 một lần.
python scripts/run_mysql_demo_cycle.py --from-date 2018-03-01 --to-date 2018-03-31 --cycles 1
```

`run_mysql_demo_cycle.py` làm mới các bảng replay `Demo*` cho lần chạy demo. Không chạy nhiều replay worker đồng thời trên cùng schema. EDA/export tạo hoặc cập nhật CSV và biểu đồ trong `docs/evidence/` và `notebooks/eda_output/`.

Khi cần cập nhật forecast mà Power BI đọc từ MySQL, chạy thêm `python scripts/publish_mysql_forecast.py`. Lệnh này thay dữ liệu dẫn xuất trong `PowerBIForecastMonthly`; không chạy trong smoke test để tránh thay đổi bảng đang được Power BI sử dụng.

## Kiểm tra

```powershell
python scripts/validate_project.py
python -m pytest -q
```

- `validate_project.py` kiểm tra file pipeline, sơ đồ, EDA evidence và cấu trúc PBIP/MySQL.
- Pytest kiểm tra thứ tự sự kiện replay và phép tính route/geohash ở cấp đơn.
- Các bước cần MySQL phải có MySQL đang chạy và `.mysql-password`. ETL không tự ghi đè schema đã có dữ liệu.

## Cấu trúc thư mục

| Thư mục | Nội dung |
|---|---|
| `data/raw/` | Chín CSV Olist nguồn; dữ liệu local, không commit |
| `data/processed/` | Snapshot fallback dùng khi MySQL không sẵn có; CSV dẫn xuất tạo lại bằng `scripts/export_processed_csv.py` khi cần |
| `sql/mysql/` | Schema, biến đổi, views và bảng replay MySQL |
| `scripts/` | ETL, EDA, forecast, kiểm tra, replay và Streamlit |
| `powerbi/` | PBIP hiện hành và các thư mục Report/SemanticModel đi kèm |
| `docs/evidence/` | CSV/ảnh kết quả EDA, KPI, forecast và reconciliation |
| `notebooks/` | Notebook EDA và biểu đồ xuất |
| `document/` | Đặc tả demo của môn học |
| `diagrams/` | Sơ đồ kiến trúc và kho dữ liệu |
| `output/streamlit_2018-03-15/` | CSV đối chiếu demo theo ngày |

## Các bộ requirements

- `requirements-etl.txt`: thư viện ETL/MySQL, pandas, NumPy và statsmodels.
- `requirements-forecast.txt`: ETL cùng Streamlit, bản đồ và thư viện forecast; dùng để chạy demo.
- `requirements.txt`: môi trường notebook/dev (Jupyter, gdown, matplotlib); chỉ cần cài nếu dùng notebook.

Các bộ dependency được tách để người chỉ chạy app không phải cài Jupyter.
