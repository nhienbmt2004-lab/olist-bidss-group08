# Streamlit RouteOps

## Chạy trong terminal

```powershell
cd D:\olist\olist-bidss-group08
python -m pip install -r requirements-forecast.txt
python -m streamlit run scripts/streamlit_late_risk_demo.py
```

Mở `http://localhost:8501`. Giữ terminal mở; nhấn `Ctrl+C` để dừng. MySQL phải chạy và `.mysql-password` phải có mật khẩu. Đồng hồ tự phát từ **01/10/2017 đến 31/08/2018** (20 giây = 1 ngày), có thể tạm dừng, tiếp tục, đặt lại và đổi tốc độ.

## Backend

1. `streamlit_dss_data.py` đọc `stg_Orders`, gom `stg_OrderItems` về một dòng mỗi `OrderId`; `GMV` là tổng `price`. `route_lookup()` nối dimension seller/khách để lấy bang và tọa độ. Olist không có Carrier ID.
2. App ghép dữ liệu theo `OrderId`. Tại ngày mô phỏng T, đơn đã giao khi `DeliveredAt ≤ T`; mọi đơn đã đặt nhưng chưa quan sát được mốc giao tại T thuộc nhóm chưa giao, không lọc theo ngày đặt 30 ngày. App tách đơn có `CarrierAt ≤ T` (đã bàn giao cho vận chuyển) với đơn chưa có mốc bàn giao. Olist has no cancellation timestamp. The app excludes final-status canceled orders; it cannot reconstruct cancellation state at T.
3. Tuyến là `SellerState → CustomerState`; đơn nhiều seller/thiếu bang bị loại khỏi KPI tuyến. OTD tính trên đơn đã giao trong 30 ngày đến T và có ngày hẹn để xác định đúng/trễ. Hàng đợi hiện tại là tập riêng: mọi đơn đã đặt đến T nhưng chưa giao tại T, bất kể ngày mua; trong đó “đang vận chuyển” chỉ là các đơn đã có `CarrierAt ≤ T`. GMV phơi nhiễm hiện tính từ đơn mở trễ ít nhất 3 ngày.
4. Route Overview: KPI OTD dùng toàn bộ đơn đã giao có ngày hẹn trong 30 ngày kết thúc tại T; KPI toàn sàn không loại đơn chỉ vì thiếu tuyến. Open GMV at Risk gồm đơn chưa giao đã quá hẹn ít nhất 3 ngày; mẫu số phần trăm là GMV của mọi đơn chưa giao. GMV đơn đã giao trễ trong 30 ngày hiển thị riêng. Seller-origin chỉ lọc hàng đợi và bản đồ. Bản đồ Leaflet/OpenStreetMap gom vị trí khách vào geohash precision 4; ô chỉ là vị trí, màu lấy từ OTD tuyến seller → bang khách (xanh >=90%, vàng 85-<90%, đỏ <85%, xám dưới 30 đơn giao). Vùng địa lý là đường bao xấp xỉ suy ra từ mã bang và tọa độ vì DW không có polygon ranh giới.
5. DimGeography trong MySQL không có cột Region, chỉ có StateCode và tọa độ. Năm vùng nền Norte, Nordeste, Centro-Oeste, Sudeste, Sul được suy ra theo phân vùng địa lý Brazil từ StateCode; đường bao hiển thị là xấp xỉ từ tọa độ bang, không phải ranh giới hành chính chính xác.
6. What-if dùng đơn đã giao; seller được đánh giá riêng bằng `CarrierAt` so với `ShippingLimitAt`. Nút hành động chỉ ghi nhận lựa chọn mô phỏng; không sửa đơn hoặc gửi thông báo.

## Luồng người dùng

1. **Route Overview:** chọn Seller origin (bang seller) để lọc map; bộ chọn **Tuyến đang xem** hiển rõ cặp Seller → Khách, OTD 30 ngày, số đơn giao/đang mở và GMV rủi ro. KPI phía trên gom các tuyến từ origin; map hiện các ô khách nhận và OTD cấp tuyến Seller → buyer state. Bảng bên cạnh xếp các tuyến cần chú ý theo trạng thái và GMV rủi ro. Màu xanh ≥90%, vàng 85–<90%, đỏ <85%, xám nếu tuyến dưới 30 đơn giao.
2. **Route Detail:** hai khối độc lập. Khối hiệu suất hiển thị OTD theo ngày, thời gian giao/ngày hẹn/thời gian sau bàn giao, cùng hai kịch bản riêng: rút ngắn giao 0/3/6/9/12 ngày và nới ngày hẹn 0/2/4/6 ngày. Khối cứu đơn lấy mọi đơn chưa giao tại T (không giới hạn ngày mua), tách đơn có mốc bàn giao khỏi đơn chưa có mốc bàn giao; lọc đơn trễ từ 3 ngày hoặc 4+ ngày. Nới hẹn chỉ đổi cách chấm OTD; không làm hàng đến nhanh hơn. Tác vụ CSKH chỉ mô phỏng, không gửi thông báo thật.
3. **Seller Performance:** Bảng hiển thị seller có bàn giao trên tuyến đang chọn. Seller Score là tổng điểm chuẩn hóa: Review 30%, OTD 25%, bàn giao đúng hạn 25%, số ngày trễ 10%, tỷ lệ hủy 10%; hạng A >=85, B 70-<85, C 50-<70, D <50. Chuẩn hóa dùng cùng bounds trong `scripts/mysql_dss.py`; chỉ chấm hạng khi có >=30 đơn giao và đủ dữ liệu. Seller Score và hạng dùng thông tin quan sát tới ngày mô phỏng. Olist không có thời điểm hủy nên chỉ số hủy dùng trạng thái cuối nguồn. Priority Score riêng: 60% rủi ro bàn giao trên tuyến + 40% tỷ trọng GMV trên tuyến.

**Tóm tắt:** chọn tuyến → xem bằng chứng và thử phương án → xem seller liên quan. Các con số What-if là giả định, không phải tiền tiết kiệm thực tế.


## Thao tác Route Overview

- Chọn **Seller origin** để lọc tuyến xuất phát từ bang đó. Mỗi cặp bang seller → bang khách chỉ xuất hiện một lần trong hàng đợi.
- Các ô geohash có thể lặp cùng tên tuyến vì đó là những vị trí khách khác nhau của cùng tuyến. Màu ô lấy từ OTD của tuyến, không phải OTD tính riêng trong ô.
- Chọn tuyến trong hàng đợi để đồng bộ tuyến đang xem và làm nổi bật các ô tương ứng. Hàng đợi chỉ hiện tuyến đỏ/vàng đủ mẫu, xếp theo mức cảnh báo rồi GMV at Risk.
- **Nhận xử lý** mở xác nhận cho đúng tuyến đang chọn. Xác nhận ghi nhận người phụ trách trong phiên mô phỏng rồi chuyển sang Route Detail; không sửa đơn hay liên hệ hãng vận chuyển thật.
- `OTD 30 ngày = đơn giao đúng hẹn / mọi đơn đã giao đủ ngày hẹn` trong cửa sổ 30 ngày kết thúc tại T. Nhóm chưa giao là tập riêng gồm các đơn đặt đến T chưa quan sát thấy giao hàng, bất kể ngày đặt; nhóm này không vào mẫu số OTD.
- Ví dụ tại T: 200 đơn đã giao trong 30 ngày, có ngày hẹn; 168 đơn đúng hẹn → OTD = 168/200 = 84%. Riêng tại T có thể còn 40 đơn chưa giao (28 đã bàn giao, 12 chưa có mốc bàn giao), trong đó 8 đơn đang vận chuyển đã quá hẹn. Các số 40/28/12/8 là hàng đợi tại T; chúng không cộng vào mẫu số 200 của OTD.
- Đối chiếu dữ liệu thật ngày 15/03/2018, tuyến SP → RJ: 402/498 đơn giao đúng hẹn → OTD 80,72%; riêng tại T có 724 đơn chưa giao, gồm 640 đã bàn giao và 84 chưa có mốc bàn giao. Có 212 đơn chưa giao đã quá hẹn (181 trong nhóm đã bàn giao); số quá hẹn ít nhất 3 ngày là 189 (158 đã bàn giao). Vì vậy GMV rủi ro của mọi đơn chưa giao là R$27.216,11; phần thuộc đơn đã bàn giao là R$18.675,42. Đây là hai nhóm số liệu khác nhau, được ghi riêng để tránh gọi toàn bộ đơn chưa giao là “đang vận chuyển”.
- `Open GMV at Risk` là GMV của nhóm chưa giao đã quá hẹn ít nhất 3 ngày. GMV đơn đã giao trễ trong 30 ngày là chỉ số lịch sử riêng, không cộng vào rủi ro hiện tại. Do không có timestamp hủy, nhóm chưa giao có thể gồm đơn được ghi nhận hủy về sau.


## Cancellation filter and What-if updates

- Route Overview, Route Detail, and Seller Performance exclude records whose final source status is `canceled`; `invoiced` records remain. Olist has no cancellation timestamp, so this is a final-status cleanup and cannot establish whether cancellation had occurred at the simulated date.
- Route Detail distinguishes the rolling 30-day delivered cohort used for OTD from the open-order queue at the simulated date. The KPI row shows on-time, late, and total delivered counts alongside open-order counts.
- The delivered-order scenario shortens the promise date for orders originally delivered on time and compares OTD, newly late orders, and GMV newly classified as at least 3 days late. The in-transit scenario extends the promise date only for orders currently 1?2 days overdue and compares remaining overdue orders and GMV before/after. Promise-date changes do not change actual delivery time; deltas describe hypothetical reclassification only.
