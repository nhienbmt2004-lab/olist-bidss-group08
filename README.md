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

\- SQL Server Analysis Services (SSAS Tabular)

\- Power BI

\- Python / Google Colab

\- GitHub

\- Draw.io



\## Kiến trúc dữ liệu dự kiến



Olist CSV

→ SQL Server Staging

→ SSIS ETL

→ Data Warehouse

→ SSAS Tabular

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

├── ssas/

├── powerbi/

├── notebooks/

├── diagrams/

├── testing/

└── docs/

