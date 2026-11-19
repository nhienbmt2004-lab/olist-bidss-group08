# Thử nghiệm dự báo rủi ro giao trễ Olist

Ngày chạy: 16/11/2026. Nguồn: MySQL `olist_bi_group08`, các đơn đã giao và có đủ ngày hẹn/ngày giao. Đây là **backtest trên Olist lịch sử**, chưa phải mô hình vận hành trên đơn hàng phát sinh mới.

## Bài toán và giá trị quyết định

**Câu hỏi:** Khi đơn vừa được duyệt hoặc vừa được bàn giao cho vận chuyển, đơn nào nên được ưu tiên theo dõi vì có nguy cơ giao sau ngày hẹn?

- **Lần 1 — sau duyệt đơn:** dùng ngày đặt/duyệt, ngày hẹn, bang khách/người bán, danh mục, số sản phẩm/người bán, giá, phí vận chuyển, trọng lượng/kích thước và thanh toán. Không dùng ngày bàn giao, ngày giao, số ngày trễ hoặc review của chính đơn đó.
- **Lần 2 — lúc bàn giao:** cập nhật với số ngày còn lại trước hạn hẹn, thời gian từ duyệt đến bàn giao và chênh lệch so với `shipping_limit_date`. Chỉ xét đơn một sản phẩm để một mốc bàn giao không bị gán cho nhiều người bán.
- **Đầu ra quản trị:** xếp hạng 10% đơn rủi ro cao nhất để kiểm tra tuyến, làm việc với đối tác vận chuyển hoặc chủ động thông báo khách. Không tự động quy lỗi hay xử phạt seller.

## Cách kiểm tra

Script: [`scripts/forecast_late_delivery.py`](../../../../scripts/forecast_late_delivery.py). Chạy `python -m pip install -r requirements-forecast.txt` rồi `python scripts/forecast_late_delivery.py` tại thư mục gốc. Script chỉ đọc MySQL, xuất các CSV ở thư mục này. Hình vẽ tạo bằng `python scripts/plot_late_forecast.py`.

**Demo Streamlit:** chạy `python -m streamlit run scripts/streamlit_late_risk_demo.py` tại thư mục gốc. Ứng dụng có ba màn: Route Overview, Route Detail và Seller Performance; xem [hướng dẫn demo](../../../streamlit-rehearsal.md). Đây là phát lại Olist lịch sử, không phải hệ thống đơn hàng trực tiếp.

- Huấn luyện: đơn mua trong 2017 có nhãn giao hàng trước 01/04/2018.
- Chọn mô hình: đơn mua 01–02/2018 có nhãn trước 01/04/2018. Tháng 3/2018 là khoảng chờ nhãn.
- Kiểm tra tương lai: đơn mua 04–08/2018. Mọi phép biến đổi dữ liệu được fit trên tập huấn luyện.
- So sánh Logistic Regression với Random Forest bằng Average Precision (AP) trên tập chọn mô hình. Isotonic calibration được kiểm tra riêng, không mặc định dùng. Chia ngẫu nhiên 15% chỉ là đối chứng hồi cứu.
- Chỉ số: AP, AP lift so với tỷ lệ trễ nền, ROC-AUC, Brier, tỷ lệ đơn trễ trong top 10% rủi ro và phần đơn trễ mà top 10% thu được.

## Kết quả chính

**Bản kiểm toán phương pháp và các số liệu cập nhật:** xem [methodology_audit.md](methodology_audit.md). Bảng trong tệp này là nguồn diễn giải chính cho phép so sánh hai thời điểm. Đây là **so sánh hồi cứu có điều kiện trên cùng nhóm đơn về sau có mốc bàn giao hợp lệ**; lúc duyệt chưa thể biết toàn bộ nhóm này. Định nghĩa “còn ít nhất 3 ngày” tính theo **ngày lịch tại lúc bàn giao**, không phải khoảng 72 giờ.

| Mẫu kiểm tra | Cách xếp hạng | AP | Phần đơn trễ tìm được khi kiểm tra 10% đơn |
| --- | --- | ---: | ---: |
| 27.639 đơn được bàn giao **trước** ngày hẹn; 1.100 đơn sau đó giao trễ | Điểm lúc duyệt | 0,0721 | 20,55% |
| Cùng 27.639 đơn | Điểm cập nhật lúc bàn giao | **0,1570** | **33,09%** |
| 27.272 đơn còn **ít nhất 3 ngày lịch** trước hạn hẹn lúc bàn giao; 1.004 đơn sau đó giao trễ | Điểm lúc duyệt | 0,0693 | 21,51% |
| Cùng 27.272 đơn | Điểm cập nhật lúc bàn giao | **0,1271** | **30,18%** |

Chọn ngẫu nhiên 10% đơn sẽ thu được khoảng 10% đơn trễ. Như vậy lần cập nhật lúc bàn giao giúp hàng đợi điều tra tập trung hơn **ngay cả khi đơn chưa tới hạn**. Trên toàn bộ tập tương lai của lần dự báo lúc duyệt, AP là 0,0790 so với tỷ lệ trễ nền 0,0442; top 10% thu được 19,44% đơn trễ. AP thay đổi theo tháng, và đến tháng 8/2018 top 10% chỉ thu được khoảng 10,20% đơn trễ: phải giám sát và đánh giá lại theo thời gian.

Thử hiệu chỉnh isotonic bằng nhãn 01–02/2018 làm Brier trên 04–08/2018 tăng từ 0,0419 lên 0,0603. Vì vậy bản thử dùng **điểm xếp hạng rủi ro thô**, không giới thiệu điểm này như xác suất giao trễ đã được hiệu chuẩn. Kết quả này cũng phù hợp bài học phương pháp của bài `s41598-026-80365-9_reference.pdf`: đánh giá ngẫu nhiên và tương lai, khả năng xếp hạng và độ tin cậy xác suất là các vấn đề khác nhau. Con số của bài báo không phải kết quả đồ án này.

## Gợi ý trình bày để hỗ trợ quyết định

Giữ dự báo số đơn và GMV theo tháng cho BQ5. Bổ sung phần **Cảnh báo giao trễ sớm** vào DSS: (1) thẻ số đơn cần kiểm tra trong top 10%; (2) bảng đơn rủi ro kèm bang gửi–nhận, danh mục, số ngày còn trước hạn và thời điểm chấm; (3) biểu đồ so hai lần cảnh báo trên cùng nhóm đơn; (4) biểu đồ hiệu quả theo từng tháng để thấy mô hình suy giảm; (5) dòng giải thích “dữ liệu lịch sử mô phỏng, điểm để xếp ưu tiên, không phải xác suất đã hiệu chuẩn”. Lần bàn giao là tín hiệu cập nhật; không được dùng thông tin chỉ có sau khi khách nhận hàng để chấm đơn đang vận chuyển.

## Tệp đầu ra

- `metrics.csv`: đối chứng nền, validation, test tương lai, hiệu chỉnh và chia ngẫu nhiên.
- `monthly_metrics.csv`: khả năng xếp hạng từng tháng của lần dự báo lúc duyệt.
- `two_stage_comparison.csv`: hai lần cảnh báo trên cùng toàn bộ tập đơn một sản phẩm.
- `actionable_comparison.csv`: so sánh chỉ trên đơn chưa tới hạn, và đơn còn từ 3 ngày trước hạn.
- `test_risk_queue.csv`, `handover_risk_queue.csv`: hàng đợi lịch sử kèm nhãn thực tế để **kiểm thử**. Khi trình bày màn hình mô phỏng tại thời điểm dự báo, phải ẩn cột `Late`.
- `two_stage_temporal_validation.png`: hình tóm tắt cho báo cáo.

## Giới hạn

Olist không lưu bản lịch sử của mọi thuộc tính tĩnh và không ghi chính xác thời điểm từng bản ghi được hệ thống nhận. Đề tài giả định thông tin sản phẩm, thanh toán và ngày hẹn trong CSV đã có tại thời điểm duyệt/bàn giao. Mẫu chỉ gồm **đơn cuối cùng được giao**; đơn hủy hoặc chưa có ngày giao không được gán nhãn “đúng hạn”. Mô hình không có định danh carrier, log quét từng chặng, thời tiết hay nguyên nhân chậm; điểm rủi ro không chứng minh nguyên nhân. Chưa có đánh giá trên đơn phát sinh sau 2018, thử nghiệm can thiệp thực tế hoặc kiểm tra chi phí triển khai.
