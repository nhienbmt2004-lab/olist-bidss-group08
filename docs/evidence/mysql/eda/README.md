# EDA MySQL theo 5 câu hỏi kinh doanh

Chạy từ thư mục gốc bằng `python scripts/run_mysql_eda.py`. Chương trình đọc schema MySQL `olist_bi_group08` và xuất bảng CSV tại đây, hình PNG ở `notebooks/eda_output/`. Mật khẩu lấy từ biến `OLIST_MYSQL_PASSWORD` hoặc tệp `.mysql-password` đã được Git bỏ qua. Kết quả và câu chữ có thể đưa vào báo cáo: [`docs/1-3-2-cau-hoi-kinh-doanh-va-eda.md`](../../../1-3-2-cau-hoi-kinh-doanh-va-eda.md).

| BQ | Bảng chính | Hình chính | Nội dung |
|---|---|---|---|
| BQ1 | `bq1_late_state_month.csv`, `bq1_late_month.csv`, `bq1_late_state.csv` | `late_by_month.png`, `late_state_month_heatmap.png` | Giao trễ theo tháng và bang khách hàng. |
| BQ2 | `bq2_review_delay_bucket.csv` | `review_by_delay_bucket.png` | Review theo mức độ trễ. |
| BQ3 | `bq3_seller_gmv_quality.csv`, `bq3_seller_candidates.csv`, `bq3_seller_pareto.csv` | `seller_gmv_pareto.png`, `seller_gmv_late_scatter.png` | Quy mô và chỉ số chất lượng seller. |
| BQ4 | `bq4_category_growth_review.csv`, `bq4_screening_baseline.csv`, `bq4_category_candidates.csv` | `category_growth_review.png` | Tăng trưởng GMV cùng kỳ và review danh mục. |
| BQ5 | `bq5_monthly_orders_gmv_all.csv` | `monthly_orders_gmv.png` | Lịch sử số đơn và GMV để chuẩn bị dự báo. |

Các tệp `eda_key_time_quality.csv`, `eda_repeat_customers.csv`, `eda_promise_actual_summary.csv` và `eda_distance_freight_delivery.csv` ghi kiểm tra tính khả thi và chất lượng dữ liệu. Hai hình `promise_vs_actual_days.png`, `distance_freight_delivery.png` minh họa khoảng ngày hẹn và khoảng cách xấp xỉ. Các tệp EDA gốc như `source_inventory.csv`, `review_by_delivery.csv` và `eda_kpi_check.csv` vẫn được tạo để đối chiếu với KPI MySQL.

Kết quả dùng dữ liệu lịch sử Olist. Tương quan giao trễ–review không chứng minh nhân quả. `FreightValue` là phí vận chuyển tính cho khách, không phải chi phí vận hành thực tế. Số liệu seller và danh mục là chỉ báo để điều tra. Hình chuỗi thời gian dùng 01/2017–08/2018 vì rìa chuỗi rất thưa; CSV giữ toàn bộ các tháng.
