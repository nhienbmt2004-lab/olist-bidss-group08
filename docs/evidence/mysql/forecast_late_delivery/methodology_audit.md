# Kiểm tra phương pháp: cảnh báo giao trễ hai thời điểm

Đây là **backtest trên dữ liệu Olist lịch sử**. Dashboard phát lại sự kiện theo lô và ghép điểm rủi ro đã tính trước theo `OrderId`; micro-batch không huấn luyện hay chấm điểm lại mô hình. Nhãn trễ là ngày giao thực tế sau ngày hẹn giao trong dữ liệu Olist.

| Điểm cần kiểm soát | Cách thực hiện và bằng chứng |
| --- | --- |
| Đơn còn trong hạn tại lúc bàn giao | Chỉ đưa vào hàng đợi nếu `date(CarrierAt) < date(EstimatedAt)`. Điều kiện này dùng hai mốc đã biết tại lúc bàn giao, không dùng kết quả giao hàng hay nhãn `Late`. Nhóm còn ít nhất ba ngày dùng chênh lệch ngày lịch `>= 3`. Đơn đã hết hạn khi bàn giao không tham gia phép so sánh chính. |
| Điểm ngoài mẫu | Mô hình học từ đơn mua năm 2017, kết quả giao đã quan sát trước 01/04/2018; chọn mô hình bằng đơn mua 01–02/2018 cũng đã có kết quả trước ngày đó. Tháng 3 là khoảng chờ nhãn. Tập kiểm thử là **cohort đơn mua 04–08/2018**, bao gồm các đơn tháng 7 được phát lại. Mọi phép biến đổi dữ liệu được fit trên tập huấn luyện. Điểm phát lại không được học từ nhãn của chính các đơn kiểm thử. |
| Năng lực kiểm tra | Top 10% là **giả định** người vận hành có thể kiểm tra 1 trong 10 đơn; không được tối ưu từ tập kiểm thử. `Precision@10% = đơn trễ trong nhóm chọn / số đơn được chọn`; `Recall@10% = đơn trễ trong nhóm chọn / tổng đơn trễ`; `Lift@10% = precision / tỷ lệ trễ nền`. |
| Nhãn cuối kỳ | Script hiện đọc `FactOrderDelivery` với `IsOnTime IS NOT NULL`, nên đơn hủy, chưa giao hoặc chưa có ngày giao bị loại **ngay trước cả bước tạo điểm kiểm thử và bước đánh giá**; không bị gán là đúng hạn. Đây là giới hạn của demo offline: nó chưa chấm điểm cho đơn chưa biết kết quả, dù một hệ thống triển khai thật sẽ phải làm việc đó. Kết quả có thiên lệch chọn mẫu và không suy rộng nguyên vẹn cho mọi đơn mới. Trong cohort mua tháng 8/2018 có 6.512 đơn, 6.351 đơn delivered/đủ nhãn và 70 đơn còn trạng thái mở theo kiểm tra nguồn; phần còn lại thuộc trạng thái khác. |
| Mốc carrier lỗi | Điểm lúc bàn giao chỉ tính trên đơn một sản phẩm có `CarrierAt` hợp lệ, không thiếu, không trước `ApprovedAt` và không sau `DeliveredAt`. Trong 28.958 đơn một sản phẩm đã giao/đủ mốc duyệt thuộc cohort 04–08/2018, có 1.106 mốc carrier trước duyệt; không có mốc sau giao và không thiếu carrier trong subset này. Những đơn lỗi carrier vẫn có thể có điểm lúc duyệt nếu các trường đầu vào ở mốc đó hợp lệ. Đây là quy tắc chất lượng dữ liệu, không phải đặc trưng của mô hình. |

## Kết quả so sánh có điều kiện trên cùng 27.639 đơn

Quần thể này được xác định **sau khi biết mốc bàn giao**: đơn một sản phẩm, chuỗi mốc hợp lệ, cuối cùng đã giao và `date(CarrierAt) < date(EstimatedAt)`. Tại thời điểm duyệt, người vận hành chưa thể biết chính xác đơn nào về sau thuộc quần thể này. Vì vậy hàng “Sau duyệt” là **so sánh hồi cứu trên cùng các đơn** để cô lập giá trị của thông tin bàn giao; 226 đơn **không phải** kết quả của một hàng đợi thực tế lúc duyệt. Tập có **1.100 đơn giao trễ**, tỷ lệ nền **3,98%**. Với năng lực kiểm tra **2.764 đơn**:

| Thời điểm chấm | Đơn trễ được chọn | Precision@10% | Recall@10% | Lift@10% | AP |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sau duyệt đơn | 226 | 8,18% | 20,55% | 2,05 lần | 0,0721 |
| Lúc bàn giao | 364 | 13,17% | 33,09% | 3,31 lần | 0,1570 |

Điểm cập nhật lúc bàn giao **đưa thêm 138 đơn thực tế giao trễ vào top 10%** trên cùng quy mô kiểm tra trong backtest. Đây là *khả năng phát hiện sớm*, không phải 138 đơn đã được cứu hay bằng chứng giảm tỷ lệ giao trễ. Muốn đo tác động can thiệp cần thí nghiệm vận hành và dữ liệu chi phí.

Nếu yêu cầu còn **ít nhất ba ngày lịch** trước hạn lúc bàn giao, mẫu còn 27.272 đơn với 1.004 đơn trễ (nền 3,68%). Top 10% sau duyệt tìm 216 đơn (precision 7,92%, recall 21,51%, lift 2,15); lúc bàn giao tìm 303 đơn (precision 11,11%, recall 30,18%, lift 3,02). Các số này dùng đúng định nghĩa ngày lịch, khác phiên bản cũ tính 72 giờ.

## Giới hạn cần nói khi bảo vệ

- Tỷ lệ trễ thay đổi theo tháng; bảng `monthly_metrics.csv` cho thấy hiệu quả xếp hạng không ổn định, đặc biệt gần cuối kỳ. Cần báo tỷ lệ nền cùng từng tháng khi diễn giải.
- Dữ liệu không ghi thời điểm mọi trường sản phẩm, thanh toán và ngày hẹn được hệ thống nhận. Backtest **giả định** các trường này đã sẵn có tại mốc chấm; cần xác thực giả định bằng log nguồn trước khi dùng thực tế.
- Mẫu bàn giao chỉ gồm đơn một sản phẩm có chuỗi mốc hợp lệ. Không được suy rộng trực tiếp kết quả 33,09% cho đơn nhiều sản phẩm hoặc đơn chưa giao.
- Số **537 mốc bàn giao bị bỏ** là thống kê của luồng micro-batch phát lại **tháng 7/2018**. Nó không phải số đơn bị loại khỏi quần thể kiểm thử mô hình 27.639 đơn của **tháng 4–8/2018**; hai phép lọc có phạm vi khác nhau.
- `Risk` là điểm **xếp hạng**; chưa được chứng minh là xác suất đã hiệu chuẩn. Không dùng để kết luận người bán hay carrier gây trễ.

Tái lập: `python scripts/forecast_late_delivery.py` rồi `python scripts/plot_late_forecast.py`. Số chi tiết nằm trong `actionable_comparison.csv`, hàng đợi kiểm thử trong `test_risk_queue.csv` và `handover_risk_queue.csv`.
