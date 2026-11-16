# MySQL Olist: xây dựng, kiểm tra và dùng với Power BI

Schema của đồ án là `olist_bi_group08` trên MySQL Server `127.0.0.1:3306`. MySQL Workbench chỉ là công cụ xem và chạy SQL; nó không phải nơi lưu dữ liệu riêng.

## Xây kho

Đặt chín CSV Olist trong `data/raw/`, dùng mật khẩu MySQL qua biến `OLIST_MYSQL_PASSWORD` hoặc tệp `.mysql-password` ở thư mục gốc (đã được Git bỏ qua). Sau đó chạy:

```powershell
python -m pip install -r requirements-etl.txt
python scripts/build_mysql_dw.py
python scripts/export_mysql_evidence.py
python scripts/run_mysql_eda.py
python scripts/mysql_dss.py
python scripts/publish_mysql_forecast.py
```

`build_mysql_dw.py` tạo schema mới và từ chối ghi đè schema đã có bảng. MySQL có chín `stg_*`, hai bảng `Clean*`, ba bảng `Order*Totals`, sáu `Dim*`, bốn `Fact*`, log ETL/chất lượng, bảng dự báo Power BI, ba bảng demo và sáu view. Các bảng trung gian được giữ để đối soát và tái lập quá trình ETL; không có bảng nào trong schema đồ án được xác nhận là dư để xóa.

## Kiểm tra trong Workbench

```sql
SELECT * FROM olist_bi_group08.ETLRun ORDER BY RunId DESC LIMIT 1;
SELECT * FROM olist_bi_group08.ETLReconciliation ORDER BY ReconciliationId;
SELECT * FROM olist_bi_group08.DataQualityIssues ORDER BY IssueCode;
SELECT * FROM olist_bi_group08.vw_KPIOverview;
```

Bằng chứng nguồn–đích và KPI được xuất trong [docs/evidence/mysql](evidence/mysql/). Phân tích EDA và hình cho năm câu hỏi nằm trong [thư mục EDA](evidence/mysql/eda/README.md).

## Power BI

Mở [PBIP chính](../powerbi/pbip_project/G8_Olist_Overview_MySQL.pbip) bằng Power BI Desktop; cài MySQL Connector/NET trên máy, nhập credential kiểu **Database** cho `127.0.0.1:3306/olist_bi_group08`, rồi Refresh. Project chứa sáu trang và 12 partition MySQL. [PBIX MySQL](../powerbi/G8_Olist_Overview_MySQL.pbix) là snapshot được lưu trước các chỉnh sửa PBIP; nếu cần PBIX cuối, xuất lại từ PBIP trong Power BI Desktop.

Sau Refresh, đối chiếu Orders 99.441, Late Orders 6.534, OTD 93,23% và GMV R$13.591.643,70 với [overview.csv](evidence/mysql/overview.csv). Không coi ảnh dashboard là bằng chứng mới nếu chưa kiểm tra lại dữ liệu của lần Refresh đó.

## Demo và giới hạn

Chạy Streamlit và runner theo [hướng dẫn demo](giai-thich-demo-streamlit.md). Runner chỉ phát lại sự kiện lịch sử vào `Demo*`, không cập nhật fact hay dữ liệu Power BI. Hệ thống chưa nhận đơn hàng live, chưa triển khai Cloud BI và chưa đo hiệu quả can thiệp thực tế.
