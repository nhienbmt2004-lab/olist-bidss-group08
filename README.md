\# Olist BI/DSS - Group 08



\## Tên đề tài



Xây dựng hệ thống BI/DSS phân tích hiệu suất giao hàng và chất lượng người bán nhằm nâng cao trải nghiệm khách hàng trên sàn thương mại điện tử Olist (Brazil).



\## Dataset



Brazilian E-Commerce Public Dataset by Olist.



Nguồn dữ liệu:

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce



\## Mục tiêu dự án



\- Phân tích hiệu suất giao hàng.

\- Phân tích tình trạng giao hàng trễ.

\- Đánh giá chất lượng người bán.

\- Phân tích trải nghiệm khách hàng thông qua Review Score.

\- Xây dựng Seller Scorecard.

\- Xây dựng hệ thống cảnh báo ngoại lệ.

\- Dự báo số lượng đơn hàng và GMV.

\- Thực hiện What-if Analysis hỗ trợ ra quyết định.



\## Công nghệ sử dụng



\- SQL Server

\- SQL Server Management Studio

\- SQL Server Integration Services (SSIS)

\- Power BI semantic model

\- Power BI

\- Python / Google Colab

\- GitHub

\- Draw.io



\## Kiến trúc dữ liệu dự kiến



Olist CSV

→ SQL Server Staging

→ SSIS ETL

→ Data Warehouse

→ Power BI

→ DSS



\## Cấu trúc Project



```text

olist-bidss-group08/

│

├── data/

│   ├── raw/

│   └── sample/

│

├── sql/

│   ├── staging/

│   ├── warehouse/

│   └── validation/

│

├── ssis/

│   ├── staging/

│   ├── dimensions/

│   ├── facts/

│   └── master/

│

├── powerbi/

├── notebooks/

├── diagrams/

├── testing/

└── docs/

## Phase 2: Data Profiling, Cleaning and Warehouse Design

Run the scripts after staging is loaded, in this order:

1. `sql/validation/04_data_profiling.sql` — quality issues, column inventory and value ranges.
2. `sql/staging/05_create_clean_views.sql` — normalized staging views.
3. `sql/warehouse/06_create_dw_tables.sql` — DW dimensions, facts, keys and indexes, on an empty `Olist_DW` database.

See `docs/phase-2-design.md` for business rules, grain and bus matrix, and `diagrams/olist-dw.drawio` for the editable fact constellation (`diagrams/olist-dw.md` is the Mermaid version).

## Phase 3: Warehouse ETL and Power BI

See `docs/phase-3-etl-powerbi.md` for setup and execution. The warehouse load is implemented in `sql/warehouse/07_create_etl_support.sql` through `10_master_etl.sql`, with `sql/validation/11_reconcile_dw.sql`. `ssis/master/Run-ETL.ps1` loads the nine UTF-8 CSVs into staging, updates staging indexes/statistics, then runs `Master_ETL.dtsx`. The Power BI model and measures are in `powerbi/Olist_Model.tmdl`.

