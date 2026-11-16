# Mô phỏng vận hành Olist bằng micro-batch trên MySQL

## Phạm vi và cách gọi trong báo cáo

Đây là **phát lại dữ liệu lịch sử theo lô nhỏ**, không phải luồng đơn hàng thật đang phát sinh. Nguồn là `stg_Orders` trong schema `olist_bi_group08`. Chỉ lấy các đơn đã giao và có mốc giao khách, vì Olist không cung cấp thời điểm hủy đơn để phát lại trạng thái hủy một cách trung thực. Mặc định chọn đơn được đặt trong tháng 7/2018.

`EventAt` giữ giờ sự kiện lịch sử; `IngestedAtUtc` và `LastBatchAtUtc` ghi giờ nạp thực tế của phiên mô phỏng. KPI “quá ngày dự kiến” dùng **đồng hồ sự kiện mới nhất**, không dùng ngày hiện tại của máy. Chỉ tính là giao trễ sau khi có mốc giao khách, và so sánh theo **ngày** như kho dữ liệu chính.

Với cohort mặc định 07/2018: 6.156 đơn nguồn đã giao có ngày giao; 26 đơn bị loại vì mốc giao không hợp lệ; còn 6.130 đơn phát lại. Mỗi đơn tối đa bốn sự kiện. Trong 6.130 đơn, 537 mốc bàn giao sai thứ tự bị bỏ, nên **6.130 đặt + 6.130 duyệt + 5.593 bàn giao + 6.130 giao = 23.983 sự kiện**. Lô tối đa 500 sự kiện: 47 lô đủ 500 và lô cuối 483. Số `skipped carrier = 563` khi chuẩn bị nguồn tính trên toàn bộ 6.156 đơn, gồm cả 26 đơn bị loại; chỉ 537 ảnh hưởng đến tổng sự kiện của 6.130 đơn giữ lại.

```text
MySQL stg_Orders (đã giao, có ngày giao)
  → replay_olist_mysql.py: sắp sự kiện theo EventAt, 500 sự kiện/lô, nghỉ 5 giây
  → DemoOrderEvent + DemoReplayCheckpoint + DemoReplayBatch (cùng giao dịch mỗi lô)
  → vw_DemoOrderCurrent + vw_DemoOperationalKPI
  → tab Micro-batch MySQL của Streamlit, tự hỏi lại mỗi 5 giây
```

Các bảng `Demo*` là phần mô phỏng riêng. Việc tạo và phát lại không ghi vào `stg_*`, `Dim*`, `Fact*` hay sáu trang Power BI lịch sử. Giao diện hiện dùng Streamlit cục bộ ở `http://localhost:8501`.

## Chạy demo

Tại thư mục gốc project, đảm bảo MySQL Server cổng 3306 đang chạy và schema `olist_bi_group08` đã có kho dữ liệu:

```powershell
python -m pip install -r requirements-forecast.txt
python scripts/replay_olist_mysql.py --dry-run
python scripts/replay_olist_mysql.py --init-only
```

Script đọc mật khẩu từ biến môi trường `OLIST_MYSQL_PASSWORD`, hoặc tệp `.mysql-password` ở thư mục gốc (một dòng, tệp đã được Git bỏ qua), hoặc hỏi trong terminal tương tác. Không đưa mật khẩu vào tham số dòng lệnh và không chụp ảnh mật khẩu.

Mở **hai cửa sổ PowerShell** tại thư mục project. Cửa sổ 1:

```powershell
python -m streamlit run scripts/streamlit_late_risk_demo.py
```

Mở `http://localhost:8501` trong trình duyệt, chọn tab **Micro-batch MySQL**. Ở cửa sổ 2, phát ba lô đầu để xem KPI thay đổi:

```powershell
python scripts/replay_olist_mysql.py --batch-size 500 --interval-seconds 5 --max-batches 3 --reset
```

Sau đó chạy tiếp mà **không dùng `--reset`**:

```powershell
python scripts/replay_olist_mysql.py --batch-size 500 --interval-seconds 5
```

### Chạy dashboard lặp chu kỳ để demo liên tục

Mở Streamlit bằng `python -m streamlit run scripts/streamlit_late_risk_demo.py` ở terminal thứ nhất. Ở terminal thứ hai chạy:

```powershell
python scripts/run_mysql_demo_cycle.py --batch-size 500 --interval-seconds 5 --pause-seconds 20
```

Mỗi chu kỳ phát lại 23.983 sự kiện tháng 07/2018 theo các lô tối đa 500 sự kiện, cách nhau 5 giây; sau khi phát hết, chờ 20 giây rồi bắt đầu lại. Đầu mỗi chu kỳ chỉ đặt lại các bảng `Demo*`, còn kho lịch sử `stg_*`, `Dim*`, `Fact*` và Power BI không thay đổi. Streamlit đọc lại MySQL mỗi 5 giây. Hai tiến trình chạy cho đến khi dừng bằng `Ctrl+C` ở từng terminal. Không chạy đồng thời `run_mysql_demo_cycle.py` và `replay_olist_mysql.py` vì chúng dùng cùng các bảng Demo.

Phiên kiểm thử HTML/API ngày 15/11/2026 được lưu ở [bằng chứng cũ](evidence/mysql/micro_batch_live_2026-11-15.md). Giao diện chính hiện là Streamlit; nếu khởi động lại máy hoặc đóng tiến trình nền, dùng hai lệnh trên để bật lại.

Checkpoint gắn với chữ ký của đúng tập dữ liệu nguồn và khoảng ngày. Nếu thay đổi nguồn hoặc ngày, dùng `--reset` để xóa **chỉ ba bảng Demo** rồi phát lại. Không chạy hai tiến trình replay đồng thời. Dừng dashboard bằng `Ctrl+C`.

## Kiểm tra trong Workbench

```sql
USE olist_bi_group08;
SELECT * FROM DemoReplayCheckpoint;
SELECT * FROM vw_DemoOperationalKPI;
SELECT COUNT(*) AS EventRows FROM DemoOrderEvent;
SELECT * FROM DemoReplayBatch ORDER BY BatchId DESC LIMIT 5;
SELECT * FROM vw_DemoOrderCurrent
WHERE PastEstimate=1 OR CurrentStage='Awaiting carrier'
ORDER BY PastEstimate DESC,MinutesInCurrentStage DESC LIMIT 20;
```

Sau khi phát hết, `NextEventIndex = TotalEvents = COUNT(*) FROM DemoOrderEvent` là đối soát sự kiện của demo. `VisibleOrders` bằng số đơn nguồn còn lại sau kiểm tra thứ tự mốc. Trong lần chạy hiện tại, 26/6.156 đơn bị loại do mốc giao không hợp lệ; [bằng chứng chạy](evidence/mysql/micro_batch_run.md) ghi rõ số này. KPI của demo là một **cohort tháng 7/2018**, nên không so trực tiếp với KPI toàn bộ 99.441 đơn của Power BI.

## Giới hạn khi biện luận

- Khoảng thời gian duyệt → bàn giao và bàn giao → giao khách chỉ là thời gian trôi qua giữa hai mốc. Olist không có giờ pick/pack, quét kho, năng lực nhân sự hoặc chi phí từng công đoạn; không thể kết luận chính xác khâu nào trong kho làm lãng phí tiền nhất.
- Dashboard hỏi MySQL mỗi 5 giây; thời gian sự kiện gốc không trở thành dữ liệu 5 giây. Muốn chứng minh độ trễ, ghi `LastBatchAtUtc`, thời điểm màn hình nhìn thấy lô, rồi tính chênh lệch.
- MySQL và dashboard hiện chạy cục bộ, chưa phải triển khai cloud. Sáu trang Power BI lịch sử vẫn dùng Import và cần refresh riêng.
