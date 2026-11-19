# Bản đồ đồ án Olist BI/DSS — 16/11/2026

## Bài toán

Phân tích giao trễ trên dữ liệu Olist lịch sử và hỗ trợ **ưu tiên điều tra** theo bang, tháng, người bán, danh mục và đơn hàng. Dữ liệu không đủ để quy nguyên nhân hay chứng minh can thiệp làm giảm giao trễ. Đây là đề tài tự chọn; Olist không phải khách hàng triển khai hệ thống.

## Luồng đang dùng

```text
9 CSV → MySQL stg_* → Clean*/Order*Totals → 6 Dim + 4 Fact
                                          ├→ EDA theo BQ1–BQ5
                                          ├→ Power BI PBIP, 6 trang
                                          ├→ DSS: scorecard, cảnh báo, forecast, what-if
                                          └→ mô phỏng micro-batch + điểm rủi ro → Streamlit
```

| Thành phần | Tệp đầu vào/chạy | Đầu ra và ý nghĩa |
| --- | --- | --- |
| Nguồn/ETL | [build_mysql_dw.py](scripts/build_mysql_dw.py), [SQL MySQL](sql/mysql/) | Schema `olist_bi_group08`, log chất lượng và [đối soát](docs/evidence/mysql/reconciliation.csv) |
| EDA | [run_mysql_eda.py](scripts/run_mysql_eda.py) | [CSV/hình và giải thích](docs/evidence/mysql/eda/README.md) cho năm câu hỏi kinh doanh |
| Dashboard | [PBIP chính](powerbi/pbip_project/G8_Olist_Overview_MySQL.pbip) | Sáu trang Power BI từ MySQL; [PBIX](powerbi/G8_Olist_Overview_MySQL.pbix) là snapshot cũ hơn |
| DSS định kỳ | [mysql_dss.py](scripts/mysql_dss.py), [publish_mysql_forecast.py](scripts/publish_mysql_forecast.py) | [Scorecard, alert, dự báo, what-if](docs/evidence/mysql/dss/) |
| Dự báo rủi ro | [forecast_late_delivery.py](scripts/forecast_late_delivery.py) | [Điểm và kiểm thử](docs/evidence/mysql/forecast_late_delivery/README.md) trên tập ngoài mẫu |
| Micro-batch | [run_mysql_demo_cycle.py](scripts/run_mysql_demo_cycle.py) | Phát lại 23.983 sự kiện tháng 07/2018 vào `Demo*`, [log kiểm tra](docs/evidence/mysql/micro_batch_run.md) |
| Demo RouteOps | [streamlit_late_risk_demo.py](scripts/streamlit_late_risk_demo.py) | Ba màn: Route Overview, Route Detail, Seller Performance; đặc tả tại `document/Demo (2).pdf` và `document/Demo (3).pdf` |
| Framework | [draw.io](diagrams/olist-bi-dss-framework.drawio) | Kiến trúc từ nguồn đến quyết định |

## MySQL và ba lớp dữ liệu

`stg_*` giữ bản nạp từ CSV; `CleanGeography`, `CleanProducts` và `Order*Totals` chuẩn hóa/tổng hợp; `Dim*`/`Fact*` là kho phân tích. Về chức năng có thể **liên hệ** với Bronze–Silver–Gold. Repo hiện dùng **một schema MySQL**, chưa triển khai Medallion như ba lớp lưu trữ/quản trị độc lập. `ETL*` và `DataQualityIssues` giữ bằng chứng; `Demo*` phục vụ phát lại. Các bảng này có phụ thuộc trong ETL, dashboard hoặc kiểm toán, nên chưa có bảng được xác nhận là dư để xóa.

[Kiểm kê schema và quyết định giữ/xóa](docs/mysql-schema-audit.md): 33 bảng, 6 view (gồm `DemoActionLog`), không có đối tượng không phân loại.

## Số liệu nền đã đối soát

- 99.441 đơn; 96.470 đơn đủ điều kiện KPI giao đúng hạn; 6.534 đơn trễ (**6,77%**), OTD **93,23%**.
- GMV R$13.591.643,70. Nhóm đúng hạn có review trung bình 4,29; nhóm trễ 2,27. Đây là liên hệ quan sát được, chưa phải tác động nhân quả.
- ETL có 10/10 phép đối soát nguồn–đích đạt. EDA đã chạy lại ngày 16/11/2026 từ MySQL; [kết quả EDA](docs/evidence/mysql/eda/README.md).
- Backtest cảnh báo trên cùng 27.639 đơn đủ điều kiện tại mốc bàn giao: top 10% theo điểm sau duyệt tìm 226 đơn trễ, theo điểm lúc bàn giao tìm 364. Đây là so sánh hồi cứu có điều kiện, không phải số đơn đã được cứu khỏi giao trễ. [Giới hạn phương pháp](docs/evidence/mysql/forecast_late_delivery/methodology_audit.md).

## Còn cần chốt trước khi nộp

1. **Báo cáo Word/PDF cuối:** hiện không có trong repo. Cần đối chiếu từng chương với MySQL, PBIP và Streamlit, bỏ mô tả SQL Server/SSIS hoặc Cloud đã triển khai nếu còn trong bản Word.
2. **Ảnh và kiểm thử Power BI:** mở PBIP, Refresh, lưu ảnh sáu trang và đối chiếu KPI hiển thị với `overview.csv`; nếu cần PBIX cuối, xuất từ PBIP.
3. **Hồ sơ nghiệm thu:** chỉ ghi UAT/hiệu năng “đạt” khi có người thử, test case và kết quả. Những phần chưa thử phải ghi là giới hạn.

Chạy `python scripts/validate_project.py` để kiểm tra cấu trúc và nguồn PBIP hiện tại. Lệnh này không sửa MySQL.
