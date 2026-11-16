# MỤC LỤC BÁO CÁO ĐỒ ÁN OLIST — BẢN 6 CHƯƠNG

**Tên đề tài:** Phân tích tình trạng giao trễ và hỗ trợ ưu tiên điều tra bằng BI & DSS (ca nghiên cứu trên bộ dữ liệu Olist).

**Phạm vi:** Đề tài tự chọn theo Đề tài 11. Olist là nguồn dữ liệu lịch sử công khai, không phải đơn vị đặt hàng hoặc xác nhận kết quả. Câu hỏi trung tâm là giao trễ tập trung theo thời gian/địa lý ở đâu và liên hệ thế nào với điểm đánh giá. Phân tích người bán là nhánh hỗ trợ điều tra; không quy nguyên nhân giao trễ cho người bán.

## PHẦN ĐẦU

- Trang bìa, tóm tắt, mục lục, danh mục hình/bảng, danh mục từ viết tắt.

## CHƯƠNG 1. PROJECT CHARTER VÀ BUSINESS PROBLEM

**1.1.** Bối cảnh nghiệp vụ giao vận thương mại điện tử và ca nghiên cứu Olist  
**1.2.** Vấn đề kinh doanh cần giải quyết  
**1.3.** Stakeholders giả định và người dùng chính  
**1.4.** Các quyết định cần hỗ trợ; vai trò của BI và DSS  
**1.5.** Phạm vi trong/ngoài dự án  
**1.6.** Giả định, ràng buộc và Project Charter tóm tắt

*Đầu ra:* Problem Statement, sơ đồ chuỗi thực hiện đơn hàng, bảng stakeholder → quyết định, Project Charter. Chương này không khẳng định Olist hiện thiếu hệ thống, không kết luận giao trễ gây đánh giá thấp.

## CHƯƠNG 2. OBJECTIVES, BUSINESS REQUIREMENTS VÀ KPI SPECIFICATION

**2.1.** Mục tiêu dự án (Objectives)  
**2.2.** Key Results gắn với từng mục tiêu  
**2.3.** Success Criteria của dữ liệu, giải pháp và nhiệm vụ ra quyết định  
**2.4.** Tóm tắt khả năng dữ liệu đáp ứng bài toán  
**2.5.** Business Questions: giao trễ, đánh giá, địa lý, người bán và kịch bản DSS  
**2.6.** KPI Dictionary và quy tắc tính  
**2.7.** Thuộc tính và chiều phân tích cần có  
&emsp;**2.7.1.** Thời gian đặt hàng, hẹn giao, giao thực tế  
&emsp;**2.7.2.** Địa lý khách hàng và người bán  
&emsp;**2.7.3.** Người bán  
&emsp;**2.7.4.** Sản phẩm và danh mục  
&emsp;**2.7.5.** Khách hàng, trạng thái đơn và điểm đánh giá  
&emsp;**2.7.6.** Mức chi tiết cần thiết cho từng KPI: order, item, payment, review  
**2.8.** Business Requirements, mức ưu tiên Must/Should/Could, yêu cầu chức năng và phi chức năng  
**2.9.** Requirement Traceability Matrix: BQ → KPI → nguồn → mô hình → dashboard/DSS → kiểm thử

*Đầu ra:* ít nhất 1 Objective, 3–5 KR, 5–10 BQ, KPI Dictionary có công thức và grain, ma trận truy vết. Các KR là tiêu chí dự kiến, chưa phải kết quả đã đạt.

## CHƯƠNG 3. DATA UNDERSTANDING VÀ QUALITY ASSESSMENT

**3.1.** Nguồn dữ liệu Olist và Data Source Inventory của 9 CSV  
**3.2.** Cấu trúc bảng, khóa, quan hệ và grain nguồn  
**3.3.** Data Profiling và EDA: số dòng, độ phủ thời gian, null, trùng, phân bố giao trễ/review  
**3.4.** Data Quality Assessment và Quality Log  
**3.5.** Field-source Mapping và quy tắc làm sạch  
**3.6.** Calculation Logic cho OTD, số ngày trễ, review, GMV và Scorecard  
**3.7.** Data Coverage và khả năng trả lời từng BQ/KPI; các câu hỏi không thể kết luận

*Đầu ra:* Data Dictionary, profiling, quality log, quy tắc loại/giữ bản ghi, bằng chứng cỡ mẫu. Phân biệt dữ liệu thiếu với giá trị bằng 0; kiểm soát đơn nhiều item/review/seller để tránh nhân số liệu.

## CHƯƠNG 4. SOLUTION ARCHITECTURE VÀ BI/DSS DESIGN

**4.1.** Kiến trúc đã triển khai: CSV → MySQL staging/clean layer → MySQL Data Warehouse → Power BI và Streamlit  
**4.2.** User Flow, Decision Flow và wireframe  
**4.3.** Thiết kế Data Warehouse/Data Mart  
&emsp;**4.3.1.** Bốn fact: giao đơn, item, thanh toán, đánh giá; sáu dimension dùng chung  
&emsp;**4.3.2.** Grain, khóa và quan hệ của từng fact  
&emsp;**4.3.3.** Bus Matrix và sơ đồ mô hình nhiều fact  
**4.4.** ETL Design and Implementation  
&emsp;**4.4.1.** Pipeline nạp snapshot lịch sử  
&emsp;**4.4.2.** Source-to-Target Mapping  
&emsp;**4.4.3.** Data Cleaning và Transformation  
&emsp;**4.4.4.** Data Reconciliation và log ETL  
&emsp;**4.4.5.** Micro-batch MySQL phát lại dữ liệu lịch sử và checkpoint  
**4.5.** Semantic Model và triển khai KPI trên Power BI  
&emsp;**4.5.1.** Quan hệ, filter và hierarchy  
&emsp;**4.5.2.** DAX Measures và đối chiếu với SQL  
&emsp;**4.5.3.** Thao tác lọc, drill-down và phân tích theo chiều  
**4.6.** DSS Design: Scorecard, cảnh báo, dự báo và What-if; quy tắc và quyết định hỗ trợ  
**4.7.** Quản trị dữ liệu, phân quyền, chu kỳ refresh và cách chạy lại  
**4.8.** Phương án bàn giao/vận hành tại chỗ và khả năng mở rộng trong tương lai

*Đầu ra:* sơ đồ kiến trúc, draw.io Data Warehouse, bus matrix, mapping, mã ETL, semantic model, mô tả DSS. Không gọi hệ thống là Cloud BI đã triển khai khi chưa có triển khai và bằng chứng tương ứng.

## CHƯƠNG 5. POC, DASHBOARD, ANALYTICS VÀ SYSTEM TESTING

**5.1.** POC: phạm vi thử, giả định cần kiểm tra, tiêu chí và kết quả đánh giá  
**5.2.** Dashboard Power BI: sáu trang hiện có và cách mỗi trang trả lời BQ  
&emsp;**5.2.1.** Executive Overview  
&emsp;**5.2.2.** Delivery & Geography  
&emsp;**5.2.3.** Seller Performance Analysis  
&emsp;**5.2.4.** Product/Category Analysis  
&emsp;**5.2.5.** Seller Scorecard  
&emsp;**5.2.6.** Seller Alerts & Prioritization  
&emsp;**5.2.7.** Demo Streamlit: hàng đợi cảnh báo, micro-batch và kiểm thử mô hình  
**5.3.** DSS trong Power BI, MySQL và Streamlit  
&emsp;**5.3.1.** Scorecard và quy tắc ưu tiên điều tra  
&emsp;**5.3.2.** Alert/exception và cỡ mẫu tối thiểu  
&emsp;**5.3.3.** Forecasting, phương pháp và backtest  
&emsp;**5.3.4.** What-if, giả định đầu vào và độ nhạy  
**5.4.** Kết quả phân tích  
&emsp;**5.4.1.** Giao trễ theo thời gian và địa lý  
&emsp;**5.4.2.** Khác biệt điểm đánh giá giữa nhóm giao đúng hẹn và giao trễ  
&emsp;**5.4.3.** Phân tích người bán và danh mục như nhánh hỗ trợ  
&emsp;**5.4.4.** Insights quan sát được và giới hạn diễn giải  
**5.5.** Kiểm thử và xác thực  
&emsp;**5.5.1.** Đối soát dữ liệu nguồn–DW–Power BI  
&emsp;**5.5.2.** Kiểm thử chức năng filter, drill và cảnh báo  
&emsp;**5.5.3.** Đo thời gian phản hồi/refresh nếu có bằng chứng  
&emsp;**5.5.4.** Kiểm thử nhiệm vụ quyết định với người dùng giả định; ghi phản hồi và issue log
&emsp;**5.5.5.** Backtest dự báo rủi ro theo thời gian, precision/recall/lift ở top 10% và giới hạn mẫu

*Đầu ra:* ảnh sáu trang Power BI, ảnh ba tab Streamlit, bảng KPI đối chiếu, log micro-batch, kết quả DSS/What-if từ MySQL, bảng backtest, test cases và kịch bản UAT nếu được thực hiện. Streamlit là màn hình mô phỏng riêng, không phải trang thứ bảy của PBIX.

## CHƯƠNG 6. MANAGEMENT INSIGHTS, EVALUATION VÀ CONCLUSION

**6.1.** Case Study: từ điểm nóng trên dashboard đến thứ tự ưu tiên điều tra  
**6.2.** Trả lời các Business Questions của đề tài tự chọn  
**6.3.** Trạng thái triển khai, hướng dẫn sử dụng và gói bàn giao  
**6.4.** Đánh giá từng Objective, KR và Success Criterion bằng bằng chứng  
**6.5.** Giá trị của giải pháp đối với việc phát hiện và giải thích bất thường  
**6.6.** Hạn chế dữ liệu/phương pháp/hệ thống và hướng phát triển  
**6.7.** Khuyến nghị quản trị có điều kiện và kết luận

*Đầu ra:* câu trả lời có số liệu cho BQ trung tâm, ví dụ quyết định và phần chưa thể kết luận; bảng KR đạt/một phần/chưa đạt; user guide, deployment status và known issues. Không biến GMV của đơn trễ thành doanh thu thất thoát hoặc kết luận khâu vận chuyển gây lãng phí chi phí nhiều nhất.

## TÀI LIỆU THAM KHẢO

## PHỤ LỤC

- Phân công công việc và lịch sử đóng góp.
- Data Dictionary, Data Source Inventory và Field-source Mapping.
- SQL, ETL, quy tắc làm sạch và Source-to-Target Mapping.
- Sơ đồ kho dữ liệu, grain, Bus Matrix, semantic model và DAX.
- Ảnh dashboard, bảng kết quả DSS, Forecast/What-if và backtest.
- Data Reconciliation, POC Evaluation, test logs, kịch bản UAT, feedback và user guide.

**Nguồn khung:** [BI & DSS Project Handbook Student Edition](https://drive.google.com/file/d/1reaEaULuSF6H-kz5cUGZQrdNWEVLaxRL/view?usp=sharing). Sáu chương ở đây gộp nội dung của 10 phase trong handbook; khi viết phải có bằng chứng cho từng phase, không chỉ có tiêu đề.
