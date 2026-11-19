# Kịch bản demo RouteOps

Chạy `python -m streamlit run scripts/streamlit_late_risk_demo.py`. App mặc định tạm dừng ở **15/03/2018**; nhấn **Tiếp tục** nếu muốn xem ngày mô phỏng chạy. 20 giây thực = 1 ngày Olist.

1. **Route Overview:** chọn tuyến mẫu. Map tô từng ô vị trí khách theo OTD 30 ngày của tuyến seller-state → buyer-state. Màu KPI thuộc tuyến, không thuộc riêng ô; không có đường nối.
2. **Route Detail:** xem lịch sử OTD, thử giao sớm hoặc nới ngày hẹn; rồi kiểm tra đơn chưa giao trễ từ 3 ngày.
3. **Seller Performance:** xem riêng tỷ lệ seller bàn giao đúng hạn trên tuyến và chọn hỗ trợ mô phỏng.

Olist không có Carrier ID. Hành động trên app là mô phỏng, không sửa đơn và không gửi thông báo.
