# 1.3.2. Câu hỏi kinh doanh và bằng chứng EDA

## Vấn đề cần giải quyết

Dữ liệu giao dịch Olist cho thấy 6.534 trong 96.470 đơn đã giao và đủ ngày để đánh giá bị trễ so với ngày hẹn (6,77%). Điểm review trung bình của đơn trễ là 2,27, so với 4,29 của đơn đúng hạn. Tuy nhiên, chỉ nhìn tỷ lệ toàn hệ thống không cho biết cần ưu tiên bang, thời điểm, nhà bán hay danh mục nào; cũng chưa đủ để chuẩn bị năng lực vận hành cho các tháng tới. Vì vậy, đề tài xây dựng BI/DSS để **phát hiện nơi tập trung giao trễ, mô tả mối liên hệ với phản hồi khách hàng, sàng lọc đối tượng cần điều tra và dự báo khối lượng đơn cùng GMV**. Các kết quả theo seller và danh mục là tín hiệu sàng lọc, không quy trách nhiệm hay khẳng định quan hệ nhân quả.

Trong đề tài, GMV là tổng giá sản phẩm (`FactOrderItem.Price`), chưa trừ hoàn tiền, chiết khấu hay chi phí vận chuyển. “Trễ” nghĩa là giao sau ngày dự kiến trong dữ liệu; 8 đơn có nhãn `delivered` nhưng thiếu ngày giao hoặc ngày dự kiến được loại khỏi mẫu số KPI đúng hạn.

## Bảng 1.3. Câu hỏi kinh doanh của đề tài

| Mã | Câu hỏi kinh doanh | Mục đích và chỉ số chính | Loại phân tích | Quyết định hỗ trợ |
|---|---|---|---|---|
| BQ1 | Tỷ lệ giao trễ theo bang khách hàng và tháng mua là bao nhiêu? | Số đơn đủ điều kiện, số đơn trễ, tỷ lệ trễ; tìm điểm nóng có đủ cỡ mẫu. | Mô tả, chẩn đoán ban đầu | Ưu tiên kiểm tra các bang và giai đoạn có tỷ lệ trễ cao; xem tiếp tuyến vận chuyển và năng lực xử lý. |
| BQ2 | Tình trạng và mức độ giao trễ **liên hệ** thế nào với điểm review? | Điểm review trung bình và tỷ lệ 1–2 sao theo đúng hạn, trễ 1–3, 4–7, 8–14, >14 ngày. | Chẩn đoán mô tả | Chọn ngưỡng cảnh báo và ưu tiên điều tra trải nghiệm giao hàng. |
| BQ3 | Nhà bán nào có GMV lớn nhưng chỉ số giao hàng hoặc review thấp? | GMV sản phẩm, số đơn đủ điều kiện, tỷ lệ trễ và review theo seller; chỉ xếp hạng khi đủ cỡ mẫu. | Chẩn đoán, sàng lọc ưu tiên | Lập danh sách nhà bán cần kiểm tra nguyên nhân và hỗ trợ cải thiện. |
| BQ4 | Danh mục nào tăng GMV nhanh hơn toàn bộ danh mục nhưng review dưới mức chung? | Tăng trưởng GMV tháng 1–8/2018 so với cùng kỳ 2017; review của cùng kỳ 2018. | Chẩn đoán, sàng lọc ưu tiên | Rà soát danh mục có cơ hội tăng trưởng đi kèm rủi ro trải nghiệm. |
| BQ5 | Số đơn và GMV các tháng tới dự kiến ra sao? | Chuỗi số đơn và GMV theo tháng làm đầu vào; sai số kiểm tra của mô hình dự báo trình bày ở phần DSS. | Dự báo | Dự trù nhân lực và năng lực giao vận theo tháng. |

**Giới hạn quyết định:** Dữ liệu lịch sử không có log chi tiết từng bước trong kho, hợp đồng carrier hoặc chi phí thực tế. Do đó BQ1–BQ4 chỉ khoanh vùng để điều tra, không xác định được đơn vị hay công đoạn gây lãng phí chi phí nhất. BQ5 dùng xu hướng lịch sử, không phải dữ liệu thời gian thực hoặc dự báo đã được kiểm chứng cho tương lai.

## Bảng ánh xạ BQ → EDA → hình/bảng → kết luận có thể viết

| BQ | Phân tích EDA đã bổ sung | Hình và bảng số | Insight hiện tại | Ranh giới diễn giải |
|---|---|---|---|---|
| BQ1 | Tách tỷ lệ trễ theo tháng mua, bang khách hàng và ô bang–tháng; heatmap chỉ tô ô có từ 100 đơn. | `late_by_month.png`, `late_state_month_heatmap.png`; `bq1_late_month.csv`, `bq1_late_state.csv`, `bq1_late_state_month.csv` | Toàn bộ mẫu: 6,77% trễ. RJ 1.495/12.350 đơn (12,11%), BA 396/3.256 (12,16%), cao hơn SP 1.820/40.494 (4,49%). Tháng 3/2018: 1.328/7.003 (18,96%). | Bang là **địa chỉ khách**, không phải bang của seller hay carrier. So sánh tỷ lệ phải kèm mẫu số; tháng rìa rất ít đơn. |
| BQ2 | Review theo 5 nhóm độ trễ, có cỡ mẫu review và tỷ lệ 1–2 sao. | `review_by_delay_bucket.png`; `bq2_review_delay_bucket.csv` | Review trung bình 4,29 khi đúng hạn, 3,29 khi trễ 1–3 ngày, 2,10 khi trễ 4–7 ngày và 1,67 khi trễ 8–14 ngày. | Chỉ là liên hệ quan sát, không chứng minh giao trễ gây review thấp. Mỗi đơn lấy một review cuối cùng. |
| BQ3 | Phân bố GMV seller, Pareto, biểu đồ GMV–tỷ lệ trễ và danh sách sàng lọc. | `seller_gmv_pareto.png`, `seller_gmv_late_scatter.png`; `bq3_seller_gmv_quality.csv`, `bq3_seller_candidates.csv` | 31 seller đứng đầu (~1%) tạo khoảng 26,1% GMV. Chỉ 627/3.095 seller có ≥30 đơn đủ điều kiện. Seller `4869f7…` có GMV R$229.472,63 và tỷ lệ trễ 10,50% trên 1.124 đơn đủ điều kiện. | Danh sách ứng viên dùng ngưỡng khám phá: ≥100 đơn, GMV ≥R$100.000, và tỷ lệ trễ ≥10% **hoặc** review <4,0. Đơn nhiều seller có thể cùng xuất hiện ở nhiều seller; đây không phải bằng chứng seller gây trễ. |
| BQ4 | Tăng trưởng GMV theo cùng cửa sổ tháng 1–8 hai năm; review của tháng 1–8/2018; loại nhóm mẫu quá nhỏ. | `category_growth_review.png`; `bq4_category_growth_review.csv`, `bq4_screening_baseline.csv`, `bq4_category_candidates.csv` | GMV chung tăng 137,26%, review chung kỳ 2018 là 4,099. Bốn danh mục vượt mức tăng trưởng này nhưng review dưới 4,099 là `watches_gifts` (+237,15%; 4,027), `baby` (+262,77%; 3,998), `telephony` (+194,46%; 3,969) và `electronics` (+247,10%; 4,093). | Ngưỡng mẫu: GMV 2017 ≥R$10.000, GMV 2018 ≥R$20.000, ≥100 đơn có review. Một đơn đa danh mục có thể góp review vào nhiều danh mục. |
| BQ5 | Chuỗi số đơn và GMV theo tháng; giữ toàn bộ chuỗi trong CSV, hình tập trung 01/2017–08/2018. | `monthly_orders_gmv.png`; `bq5_monthly_orders_gmv_all.csv` | Tháng 11/2017 có 7.544 đơn, là đỉnh trong khoảng hiển thị. Rìa chuỗi rất thưa: 09/2016 có 4 đơn, 09/2018 có 16 đơn. | Hình EDA chỉ mô tả dữ liệu đầu vào. Giá trị dự báo, kiểm tra sai số và quyết định năng lực phải trình bày ở Chương DSS. |

Các đường dẫn hình ở `notebooks/eda_output/`; CSV ở `docs/evidence/mysql/eda/`. Có thể chèn Bảng 1.3 vào Chương 1 và đưa bảng ánh xạ vào đầu mục 3.2.3, sau đó đặt hình BQ1–BQ5 ở 3.2.3–3.2.5. Nếu dùng mục lục 6 chương mới, chuyển Bảng 1.3 sang mục 2.5 nhưng giữ nội dung.

## Kiểm tra nền dữ liệu cần viết trong mục 3.2.3–3.2.5

| Kiểm tra | Kết quả | Cách viết trong báo cáo |
|---|---:|---|
| `review_id` | 99.224 dòng, 98.410 ID khác nhau; cặp `(review_id, order_id)` có 99.224 giá trị khác nhau | Không viết “không trùng `review_id`”. Nêu rõ khóa ghép duy nhất trong bảng thô và logic chọn review cuối cùng ở cấp đơn. |
| Ngày giao/hẹn | 96.478 đơn nhãn `delivered`, 96.470 đủ ngày, 8 thiếu | Nêu mẫu số 96.470 của tỷ lệ trễ và lý do loại 8 đơn. |
| Thứ tự mốc thời gian | 0 trường hợp giao trước mua; 1.359 trường hợp ngày giao carrier trước ngày duyệt; 23 trường hợp giao khách trước ngày giao carrier | Gắn cờ để rà soát; không tự sửa hay kết luận toàn bộ là lỗi vì thời điểm ghi nhận có thể lệch quy trình. |
| Khách mua lại | 96.096 `customer_unique_id`; 2.997 người có trên một đơn (3,12%) | Không áp tỷ lệ mua lặp của thị trường Brazil lên Olist. Không khẳng định giao trễ làm mất khách mua lại từ dữ liệu này. |
| Khoảng ngày hẹn | Trung vị từ mua đến hẹn là 24 ngày; từ mua đến giao thực là 10 ngày | Cho thấy hẹn giao thường rộng hơn thời gian thực tế, nhưng chưa chứng minh lý do đặt ngày hẹn. |
| Khoảng cách và phí | Mẫu 94.722 đơn một seller có tọa độ zip; khoảng cách >2.000 km có phí vận chuyển tính cho khách trung bình R$39,52 và thời gian giao 21,15 ngày, so với R$13,26 và 6,46 ngày ở 0–100 km | Tọa độ là xấp xỉ tâm zip; phí tính cho khách không phải chi phí carrier; không suy quan hệ nhân quả. |

Nguồn kiểm tra: `eda_key_time_quality.csv`, `eda_repeat_customers.csv`, `eda_promise_actual_summary.csv`, `eda_distance_freight_delivery.csv` và hai hình `promise_vs_actual_days.png`, `distance_freight_delivery.png`.

## Đoạn viết đề xuất cho mục 3.2.3–3.2.5

**3.2.3. Mức độ giao trễ theo không gian và thời gian (BQ1).** Trên 96.470 đơn đã giao có đủ ngày giao và ngày dự kiến, 6.534 đơn giao trễ, tương đương 6,77%. Tỷ lệ toàn hệ thống che khuất khác biệt giữa các bang: RJ có 1.495/12.350 đơn trễ (12,11%), BA có 396/3.256 (12,16%), trong khi SP có 1.820/40.494 (4,49%). Theo tháng mua, tháng 3/2018 có 1.328/7.003 đơn trễ (18,96%). Hình `late_by_month.png` và `late_state_month_heatmap.png` cho phép chọn các ô bang–tháng để điều tra sâu; ô dưới 100 đơn được để trống nhằm tránh diễn giải tỷ lệ quá nhiễu. Bang trong phân tích là bang của khách nhận hàng.

**3.2.4. Giao trễ và phản hồi khách hàng (BQ2).** Điểm review trung bình của 89.443 đơn đúng hạn có review là 4,29; đối với 6.381 đơn trễ có review là 2,27. Khi chia theo mức trễ, điểm trung bình lần lượt là 3,29 ở nhóm 1–3 ngày, 2,10 ở nhóm 4–7 ngày, 1,67 ở nhóm 8–14 ngày và 1,72 ở nhóm trên 14 ngày. Tỷ lệ review 1–2 sao tăng từ 9,27% ở nhóm đúng hạn lên 67,68% ở nhóm trễ 4–7 ngày. Hình `review_by_delay_bucket.png` mô tả mối liên hệ quan sát; dữ liệu không đủ để quy toàn bộ thay đổi review cho việc giao trễ.

**Sàng lọc nhà bán và danh mục (BQ3–BQ4).** GMV tập trung: khoảng 1% seller đứng đầu (31/3.095) tạo 26,1% GMV. Chỉ 627 seller có từ 30 đơn đủ điều kiện trở lên, vì vậy việc xếp hạng tỷ lệ trễ cần ngưỡng cỡ mẫu. Danh sách điều tra ưu tiên trong `bq3_seller_candidates.csv` chọn seller có ít nhất 100 đơn đủ điều kiện, GMV từ R$100.000, đồng thời có tỷ lệ trễ từ 10% hoặc review dưới 4,0. Đây là bộ lọc khám phá, chưa phải quy định xử phạt seller. Ở cấp danh mục, so sánh tháng 1–8/2018 với cùng kỳ 2017 cho thấy GMV chung tăng 137,26%; review chung giai đoạn 2018 là 4,099. Bốn danh mục vừa tăng nhanh hơn mức chung vừa có review thấp hơn mức chung là `watches_gifts`, `baby`, `telephony` và `electronics`; kết quả chỉ ra nơi cần xem thêm chất lượng sản phẩm, xử lý đơn và giao vận. Hai biểu đồ `seller_gmv_late_scatter.png` và `category_growth_review.png` thể hiện các nhóm này.

**3.2.5. Chuỗi thời gian phục vụ dự báo (BQ5).** Hình `monthly_orders_gmv.png` đặt số đơn cạnh GMV theo tháng mua. Trong khoảng 01/2017–08/2018, tháng 11/2017 có 7.544 đơn và GMV R$1.010.271,37, là đỉnh số đơn của khoảng hiển thị và cần chú ý khi kiểm tra sai số dự báo. Tháng 09/2016 chỉ có 4 đơn, tháng 09/2018 có 16 đơn; do đó hình và cửa sổ huấn luyện loại các tháng rìa thưa. CSV `bq5_monthly_orders_gmv_all.csv` vẫn giữ toàn bộ lịch sử. EDA chỉ chứng minh dữ liệu và phạm vi chuỗi có thể dùng để thử mô hình; kết quả dự báo số đơn và GMV cùng sai số kiểm tra được trình bày ở phần DSS, không được coi là giá trị quan sát của các tháng tương lai.
