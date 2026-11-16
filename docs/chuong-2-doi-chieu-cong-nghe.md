# Đối chiếu Chương 2 với hệ thống Olist đang chạy

Nguồn đối chiếu: bản Chương 2 người dùng gửi ngày 15/11/2026; chỉ xét pipeline MySQL hiện tại. Tài liệu SQL Server cũ đã được chuyển sang bản sao lưu cục bộ, không phải kiến trúc đang trình bày.

## 1. Công nghệ thực sự dùng

| Thành phần | Công nghệ và bằng chứng | Cách viết trong báo cáo |
| --- | --- | --- |
| Dữ liệu nguồn | 9 CSV lịch sử Olist trong `data/raw/` | Dữ liệu lịch sử, không phải luồng đơn mới trực tiếp |
| ETL và EDA | Python (`scripts/build_mysql_dw.py`, `scripts/run_mysql_eda.py`, notebook), pandas, NumPy, SQL MySQL | Python đọc/nạp CSV; SQL trong MySQL làm sạch, biến đổi, đối soát; notebook phân tích |
| Lưu trữ | MySQL schema `olist_bi_group08`; 9 bảng `stg_*`, 6 bảng Dim, 4 bảng Fact; `sql/mysql/` | Staging và kho chiều là **các nhóm bảng trong cùng một schema**, không phải hai database |
| BI | Power BI Desktop, semantic model Import, Power Query M, DAX; `powerbi/pbip_project/` | 6 trang dashboard quản trị lịch sử; refresh thủ công sau ETL |
| DSS | Python/SQL và DAX; `scripts/mysql_dss.py`, `scripts/publish_mysql_forecast.py`, TMDL | Scorecard, cảnh báo, forecast và What-if có code; ghi đúng nơi hiển thị của từng tính năng |
| Dự báo | Python `statsmodels` Simple Exponential Smoothing (SES), bảng `PowerBIForecastMonthly`; backtest MAE/MAPE | Dự báo số đơn và GMV theo tháng; các giả định/độ bất định là đầu ra phân tích |
| Demo vận hành | Python `replay_olist_mysql.py`, MySQL `Demo*`, web server Python `http.server`, HTML/JavaScript | Micro-batch phát lại lịch sử; web dashboard hỏi MySQL mỗi 5 giây, tách khỏi 6 trang Power BI |
| Tài liệu thiết kế | draw.io `.drawio` | Sơ đồ hệ thống và mô hình dữ liệu, không phải công cụ xử lý dữ liệu |

## 2. Những chỗ trong bản Chương 2 phải bỏ hoặc sửa

| Vị trí | Bản cũ | Sửa cho đúng |
| --- | --- | --- |
| 2.1.3 | `SSIS, SQL Server`, `Olist_Staging → Olist_DW` | Python/SQL → MySQL `olist_bi_group08` (`stg_*` → Dim/Fact) |
| 2.1.3, 2.3.4, 2.4.8 | `SSAS Tabular` như dịch vụ đã triển khai | Semantic model **tích hợp trong Power BI Desktop**; không có server SSAS riêng |
| 2.3.1 | Hai database SQL Server | Một schema MySQL, staging và kho phân biệt bằng nhóm bảng |
| 2.3.2 và bảng 2.6 | `FactOrder`, `DimOrderStatus`, `DimRoute` | `FactOrderDelivery`, `FactOrderItem`, `FactPayment`, `FactReview`; `DimDate`, `DimGeography`, `DimCustomer`, `DimSeller`, `DimCategory`, `DimProduct`. Tuyến seller → customer được suy ra khi nối địa lý, không có `DimRoute` vật lý |
| 2.3.3, 2.4.8 | SSIS, Control Flow/Data Flow/Derived Column/Lookup và kiểu `nvarchar` | Bỏ phần SSIS và các chi tiết SQL Server; mô tả Python loader, staging VARCHAR, SQL Transform và bảng `ETLRun`, `ETLStepLog`, `ETLReconciliation`, `DataQualityIssues` |
| 2.3.4 | MDX, SSAS Multidimensional, kết nối Power BI đến SSAS | Chỉ giữ khái niệm OLAP cần thiết và cách lọc/nhóm/drill trong Power BI; bỏ MDX và SSAS |
| 2.3.5 | Khẳng định mọi KPI trong từ điển có đúng một measure | Viết là các KPI chính được định nghĩa bằng DAX/SQL và đối chiếu; không khẳng định 1:1 khi chưa có bảng mapping đầy đủ |
| Bảng 2.8–2.9 | Các cột vật lý `FactOrder.is_late`, `FactOrder.promise_buffer_days`, `FactOrderItem.handover_on_time`, `DimProduct.category_name_en`, `DimCustomer.latitude` | Dùng tên thực: `FactOrderDelivery.IsOnTime`, `DelayDays`, `DeliveryDays`, `ReviewScore`; `FactOrderItem.ShippingLimitDate`; `DimCategory.CategoryName`; `DimGeography.Latitude/Longitude`. `Promise Buffer` là measure/cột tính trong Power BI; `HandoverOnTime` được tạo trong truy vấn M/SQL của semantic model, không phải cột vật lý của fact MySQL |
| 2.4, bảng 2.10, 2.4.1, 2.4.8 | 5 trang, trang “Dự báo và cảnh báo” | 6 trang: Executive Overview; Delivery & Geography; Seller Performance Analysis; Product/Category Analysis; Seller Scorecard; Seller Alerts & Prioritization. Forecast số đơn và GMV ở Executive Overview; alert ở trang Seller Alerts |
| 2.4.2 | Khẳng định có drill-through riêng qua trang chi tiết | Có slicer, tooltip và nút điều hướng trang; chỉ ghi drill-through nếu bổ sung và kiểm tra chức năng thật. PBIR hiện không chứa cấu hình drill-through |
| 2.4.6 | Khẳng định What-if có slider và kết quả ngay trên dashboard | Có bảng tham số và DAX trong semantic model, cùng kết quả kịch bản ở notebook/CSV; chưa thấy visual sử dụng tham số What-if trong 6 trang PBIR |
| 2.4.7 | Khuyến nghị “hạn chế/tạm ngưng” seller như quyết định tự động | Scorecard chỉ **ưu tiên điều tra/hỗ trợ**; không đủ bằng chứng quy lỗi hay tự động xử phạt seller |
| 2.4.8 | UAT 80% đạt như kết quả đã kiểm chứng | Nếu chưa có biên bản thử nghiệm, viết là **tiêu chí dự kiến**, không phải kết quả |
| 2.2.2–2.2.4 | Gán toàn bộ khoảng duyệt → bàn giao cho seller, bàn giao → giao khách cho carrier | Gọi đó là **khoảng thời gian giữa các mốc quan sát được**. Olist không có log pick/pack/scan hoặc định danh carrier nên chưa đủ bằng chứng quy trách nhiệm từng bên |

## 3. Đoạn thay thế có thể dán vào Chương 2

**2.1.3. Kiến trúc hệ thống BI/DSS.** Chín tệp CSV lịch sử Olist được Python nạp vào các bảng `stg_*` trong MySQL `olist_bi_group08`. SQL trong MySQL làm sạch và biến đổi dữ liệu thành sáu bảng dimension, bốn bảng fact cùng các view KPI; Python ghi log và đối soát nguồn–đích. Power BI Desktop dùng chế độ Import để tải dữ liệu từ MySQL, xây dựng quan hệ và measure DAX cho sáu trang dashboard quản trị. Python, SQL và DAX tạo thẻ điểm người bán, cảnh báo, dự báo và kịch bản What-if. Nhánh micro-batch riêng phát lại sự kiện lịch sử vào bảng `Demo*` và hiển thị trên dashboard web cục bộ; đây là mô phỏng cập nhật theo chu kỳ, không phải dữ liệu giao dịch thời gian thực.

**2.3.1. Kho dữ liệu.** Đề tài dùng một schema MySQL tên `olist_bi_group08`. Chín bảng `stg_*` lưu nguồn CSV để kiểm tra và đối soát. Các bảng `Dim*` và `Fact*` là lớp dữ liệu phân tích trong cùng schema. Quy trình nạp, kiểm tra và đối soát được lưu trong `ETLRun`, `ETLStepLog`, `ETLReconciliation` và `DataQualityIssues`.

**2.3.2. Mô hình chiều.** Mô hình gồm sáu dimension (`DimDate`, `DimGeography`, `DimCustomer`, `DimSeller`, `DimCategory`, `DimProduct`) và bốn fact: `FactOrderDelivery` (một dòng/đơn), `FactOrderItem` (một dòng/item), `FactPayment` (một dòng/lần thanh toán) và `FactReview` (một dòng/review sau quy tắc làm sạch). Các phép tính theo người bán hoặc danh mục xuất phát từ item fact; số đơn dùng `DISTINCTCOUNT(OrderId)` khi ở grain item. Cặp bang người bán–khách được suy ra từ dimension địa lý, không được lưu thành `DimRoute`.

**2.3.3. ETL/ELT.** Script Python đọc 9 CSV, nạp vào staging và chạy các script SQL MySQL để chuẩn hóa, ánh xạ khóa, tạo dimension/fact và view. Việc đối soát số dòng và tổng giá trị được ghi lại; ETL hoàn tất khi các kiểm tra đạt. Đây là pipeline batch chạy theo lệnh, chưa có lịch tự động cho toàn bộ kho dữ liệu.

**2.3.4. OLAP và semantic model.** Power BI Desktop tạo semantic model Import từ MySQL. DAX định nghĩa các KPI như số đơn, tỷ lệ đúng hạn, review, GMV và điểm seller; slicer và visual cho phép lọc theo thời gian, bang, người bán và danh mục. Dự án không cài hoặc triển khai dịch vụ SSAS riêng.

**2.4. Kỹ thuật BI/DSS.** Sáu trang Power BI phục vụ theo dõi và đào sâu lịch sử. Scorecard và cảnh báo ưu tiên đối tượng để điều tra. Dự báo số đơn/GMV theo tháng dùng mô hình SES ở Python và được nạp vào Power BI; backtest có MAE/MAPE. What-if hiện có logic DAX và bảng kết quả notebook/CSV; nếu mô tả tương tác slider trên dashboard, cần thêm visual và kiểm tra trước. Dashboard web micro-batch là màn hình vận hành mô phỏng độc lập với báo cáo Power BI.

**Lưu ý về phạm vi:** Không trình bày SSIS, SSAS, MDX, SQL Server, Azure/AWS, Power BI Service hoặc dữ liệu giao dịch live như công nghệ đã triển khai trong phiên bản MySQL hiện tại. Nếu cần nhắc đến để so sánh phương án, đặt ở phần hướng phát triển và ghi rõ chưa sử dụng.
