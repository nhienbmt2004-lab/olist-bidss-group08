# Olist BI/DSS — Group 08

Hệ thống BI/DSS phân tích hiệu suất giao hàng, chất lượng người bán và trải nghiệm
khách hàng trên sàn thương mại điện tử Olist (Brazil).

## Mục tiêu

- Phân tích đơn hàng, giao hàng trễ và điểm đánh giá.
- Xây dựng Seller Scorecard và cảnh báo vận hành.
- Dự báo số lượng đơn hàng, GMV và thực hiện phân tích What-if.
- Xây dựng kho dữ liệu SQL Server và semantic model cho Power BI.

Nguồn dữ liệu: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

## Kiến trúc

```text
Olist CSV → SQL Server Staging → Data Warehouse → Power BI → DSS
              Python / SSIS          SQL ETL       TMDL     Notebook
```

## Cấu trúc project

```text
data/raw/          Dữ liệu CSV nguồn (không commit)
diagrams/          Sơ đồ kho dữ liệu
docs/              Quy tắc nghiệp vụ và hướng dẫn triển khai
notebooks/         Notebook BI/DSS và biểu đồ kết quả
powerbi/           Power BI semantic model dạng TMDL
scripts/           Công cụ nạp staging và kiểm tra project
sql/staging/       Bảng và clean views cho staging
sql/warehouse/     Schema, stored procedure và master ETL
sql/validation/    Profiling và reconciliation
ssis/              Package staging, dimension, fact và master
```

## Chạy notebook

Yêu cầu Python 3.11 trở lên. Từ thư mục gốc project:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
jupyter lab notebooks\olist_bi_dss.ipynb
```

Notebook tự tìm project root, đọc dữ liệu từ `data/raw/` và chỉ tải bộ dữ liệu
dùng chung từ Google Drive khi chưa đủ chín file CSV. Biểu đồ được ghi vào
`notebooks/eda_output/`.

## Xây dựng kho dữ liệu

Chạy SQL theo thứ tự:

1. `sql/01_create_databases.sql`
2. `sql/staging/02_create_staging_tables.sql`
3. `sql/validation/03_validate_staging.sql`
4. `sql/staging/03_create_staging_indexes.sql`
5. `sql/validation/04_data_profiling.sql`
6. `sql/staging/05_create_clean_views.sql`
7. `sql/warehouse/06_create_dw_tables.sql`
8. `sql/warehouse/07_create_etl_support.sql`
9. `sql/warehouse/08_load_dimensions.sql`
10. `sql/warehouse/09_load_facts.sql`
11. `sql/validation/11_reconcile_dw.sql`
12. `sql/warehouse/10_master_etl.sql`

Chi tiết quy tắc, grain và bus matrix nằm trong
[`docs/phase-2-design.md`](docs/phase-2-design.md). Hướng dẫn chạy ETL và tạo
Power BI model nằm trong [`docs/phase-3-etl-powerbi.md`](docs/phase-3-etl-powerbi.md).

Để chạy loader Python và master SSIS:

```powershell
python -m pip install -r requirements-etl.txt
.\ssis\master\Run-ETL.ps1 -SqlServer localhost -RawDataDirectory .\data\raw
```

Máy chạy ETL cần SQL Server, `sqlcmd`, ODBC Driver 17/18 và SSIS `dtexec.exe`.

## Power BI

Mở Power BI Desktop, vào **Model → TMDL view**, dán nội dung
`powerbi/Olist_Model.tmdl`, đổi `localhost` thành SQL Server đích nếu cần rồi
chọn **Apply** và refresh dữ liệu.

## Kiểm tra project

Chạy kiểm tra cấu trúc, notebook, Python, XML SSIS và các file bắt buộc:

```powershell
python scripts\validate_project.py
```

Lệnh kiểm tra không kết nối SQL Server và không thay đổi dữ liệu.
