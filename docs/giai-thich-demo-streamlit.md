# Giải thích demo Streamlit Olist

## Một câu dễ nhớ

**Micro-batch cho biết đơn đang ở bước nào; mô hình dự báo xếp ưu tiên đơn nào nên kiểm tra trước.** Hai nhánh nối nhau bằng `OrderId`, nhưng việc phát một lô sự kiện không huấn luyện hay chạy lại mô hình.

```text
Olist lịch sử trong MySQL
  ├─ stg_Orders → phát lại bốn loại sự kiện → Demo* → KPI trạng thái
  │                                              └─ tab Micro-batch MySQL
  └─ Dim/Fact → huấn luyện + kiểm thử theo thời gian → hai bảng điểm rủi ro CSV
                                                 ├─ tab Hàng đợi cảnh báo
                                                 └─ ghép OrderId với đơn đang vận chuyển ở tab Micro-batch
```

## Micro-batch: input, xử lý, output

- **Input:** `stg_Orders` của những đơn mua trong 07/2018, cuối cùng có trạng thái delivered và ngày giao. Nguồn có mốc đặt, duyệt, bàn giao carrier, giao khách và ngày hẹn.
- **Xử lý:** `scripts/replay_olist_mysql.py` chuyển mỗi mốc hợp lệ thành một hàng `DemoOrderEvent`, xếp theo giờ sự kiện lịch sử và nạp tối đa 500 hàng mỗi lô, cách nhau 5 giây. `DemoReplayCheckpoint` ghi tiến độ; `DemoReplayBatch` ghi từng lô. Các view SQL suy ra trạng thái mới nhất của mỗi đơn và KPI vận hành.
- **Output:** số sự kiện đã phát, số đơn đang vận chuyển, đơn chưa giao đã quá ngày hẹn, và danh sách đơn đang ở từng bước. Đây là trạng thái **quan sát được trong mô phỏng**, không phải dự báo.
- **Hai đồng hồ:** `LastEventAt` là ngày giờ Olist năm 2018 đang được phát lại; `LastBatchAtUtc` là giờ máy thực sự nạp lô. Hai giờ này khác nhau.

### Vì sao tổng là 23.983?

Nguồn chọn 6.156 đơn; loại 26 đơn có mốc giao không hợp lệ, còn 6.130 đơn. Mỗi đơn tối đa bốn sự kiện. Trong những đơn giữ lại, 537 mốc bàn giao bị bỏ vì sai thứ tự. Do đó:

| Loại sự kiện | Số hàng |
| --- | ---: |
| Đặt hàng | 6.130 |
| Duyệt đơn | 6.130 |
| Bàn giao carrier | 5.593 |
| Giao khách | 6.130 |
| **Tổng** | **23.983** |

Đây là **số hàng sự kiện**, không phải 23.983 đơn. Có 47 lô đủ 500 sự kiện và lô cuối 483. Log chuẩn bị nguồn báo 563 mốc carrier bị bỏ trên 6.156 đơn ban đầu; 26 trong số đó thuộc các đơn bị loại hoàn toàn, nên phần thiếu trong 6.130 đơn giữ lại là 537.

Lệnh demo hiện dùng `run_mysql_demo_cycle.py`: khi đã phát hết 23.983 sự kiện, runner chờ 20 giây rồi **xóa và nạp lại chỉ các bảng `Demo*`** để bắt đầu vòng sau. Vì vậy tiến độ trên màn hình có thể quay về đầu; đây là hành vi mô phỏng, không phải dữ liệu kho chính bị mất.

## Mô hình: input, xử lý, output

- **Input lúc duyệt:** thông tin đơn, ngày hẹn, bang người bán/khách, sản phẩm, giá, phí vận chuyển và thanh toán đã ghi trong MySQL. Không dùng ngày giao, số ngày trễ hoặc review của chính đơn.
- **Input lúc bàn giao:** thêm mốc bàn giao, số ngày còn trước ngày hẹn và việc bàn giao có vượt `shipping_limit_date` hay không. Lần này chỉ tính trên đơn một sản phẩm để tránh gán nhầm mốc của đơn nhiều seller.
- **Xử lý:** script `scripts/forecast_late_delivery.py` huấn luyện trên dữ liệu cũ, chọn mô hình bằng giai đoạn 01–02/2018, rồi kiểm tra trên các đơn mua 04–08/2018 **đã giao và có nhãn**. Điểm rủi ro của tập kiểm tra được lưu sẵn ở `test_risk_queue.csv` và `handover_risk_queue.csv`. Đơn chưa có kết quả giao bị loại ngay từ truy vấn đầu vào, nên demo offline hiện chưa chấm điểm các đơn đó.
- **Output:** điểm để **xếp thứ tự điều tra** và các bảng kiểm thử. Điểm chưa được hiệu chuẩn tốt thành xác suất thực. Cột `Late` trong CSV là nhãn chỉ biết sau khi giao; Streamlit ẩn nó trong hàng đợi và chỉ cho hiện khi chọn xem kết quả kiểm thử. So sánh 226 với 364 đơn là **so sánh hồi cứu có điều kiện** trên cùng 27.639 đơn mà về sau có mốc bàn giao hợp lệ, còn trong hạn tại mốc đó. Người vận hành lúc duyệt chưa thể biết chính xác quần thể này.

## Hai nhánh gặp nhau ở đâu trong Streamlit?

| Tab | Đọc từ đâu? | Người xem làm gì? |
| --- | --- | --- |
| **Hàng đợi cảnh báo** | Hai CSV điểm đã tính trước | Chọn ngày lịch sử và giai đoạn. App chỉ hiện đơn đang mở tại cuối ngày đó: đã duyệt chưa bàn giao, hoặc đã bàn giao chưa giao. Lọc bang/danh mục và chọn top % đơn cần kiểm tra. Đồng hồ ở đây do người xem điều chỉnh bằng tay. |
| **Micro-batch MySQL** | Bảng `Demo*` và view KPI trong MySQL; nối `OrderId` với CSV điểm lúc bàn giao | Đồng hồ tự tiến khi runner nạp lô. App hỏi lại MySQL mỗi 5 giây và chỉ hiển thị điểm cho đơn **đã có sự kiện bàn giao, còn đang vận chuyển**, thuộc tập điểm đã tính và chưa quá hạn. |
| **Kiểm thử mô hình** | CSV metrics và so sánh hai giai đoạn | Xem trên dữ liệu lịch sử việc chọn top 10% có tìm được nhiều đơn giao trễ hơn chọn ngẫu nhiên không; xem hiệu quả thay đổi theo tháng. Đây là đánh giá sau khi nhãn đã biết. |

**Ví dụ:** Một đơn được duyệt nhưng chưa bàn giao sẽ xuất hiện ở trạng thái “chờ bàn giao” trong micro-batch; nếu thuộc tập kiểm thử, tab hàng đợi có thể xếp nó bằng điểm lúc duyệt. Khi sự kiện bàn giao được nạp, trạng thái thành “đang vận chuyển” và tab micro-batch có thể ghép điểm cập nhật lúc bàn giao theo `OrderId`. Khi sự kiện giao khách tới, đơn ra khỏi hàng đợi đang vận chuyển; lúc ấy mới biết nó có giao trễ thật hay không.

## Giới hạn cần nói khi thuyết trình

Đây là **hai cách phát lại cùng dữ liệu lịch sử**, không phải đơn hàng mới ngoài đời. Micro-batch nạp sự kiện vào MySQL theo chu kỳ; điểm mô hình đã được tính trước trên tập kiểm tra, chưa được chấm lại khi từng lô tới. Tab micro-batch mặc định phát lại các đơn mua trong **07/2018** (6.130 đơn đủ điều kiện phát lại, 537 mốc carrier bỏ qua), còn quần thể so sánh mô hình gồm **27.639 đơn mua 04–08/2018** đã giao, một sản phẩm, có mốc bàn giao hợp lệ và còn trong hạn lúc bàn giao. Hai con số có mẫu số khác nhau. Đơn nhiều sản phẩm và đơn thiếu/sai mốc bàn giao không có điểm lần hai; đơn cuối kỳ chưa có nhãn không được đưa vào cả bước chấm điểm offline lẫn đánh giá. Vì vậy không phải mọi đơn đang vận chuyển đều có điểm. Chọn top 10% là giả định về số đơn nhóm có thể kiểm tra, không phải số nhân viên thực tế hay mức tối ưu đã được chứng minh.
