# CHƯƠNG 1. TỔNG QUAN DỰ ÁN VÀ PHÂN TÍCH YÊU CẦU NGHIỆP VỤ

> **Lưu ý cấu trúc:** Bản thảo này viết theo mục lục 5 chương trước đó. Với [mục lục 6 chương mới](muc-luc-bao-cao-olist-6-chuong.md), phần 1.4–1.5 bên dưới chuyển sang **Chương 2: Objectives, Business Requirements và KPI Specification**; Chương 1 cần tách lại thành các mục 1.1–1.6 theo mục lục mới. Giữ nội dung làm nguồn biên tập, không dán nguyên số mục cũ vào báo cáo.

**Tên đề tài đề xuất:** Phân tích tình trạng giao trễ và hỗ trợ ưu tiên điều tra bằng BI & DSS (ca nghiên cứu trên bộ dữ liệu Olist).

**Hình thức:** Đề tài tự chọn theo Đề tài 11; phạm vi tập trung vào phân tích giao vận và đánh giá của khách hàng. Scorecard người bán là phân tích hỗ trợ. Đề tài 7 là chủ đề tham khảo, không phải cam kết triển khai Cloud BI.

**Cách gọi trong báo cáo:** Olist là **nguồn dữ liệu của ca nghiên cứu**, không phải khách hàng đặt hàng giải pháp hay đơn vị đã xác nhận vấn đề với nhóm. Các vai trò quản lý và quyết định dưới đây là tình huống mô phỏng dựa trên dữ liệu công khai.

Chương này trình bày nhu cầu quản trị và tiêu chí đánh giá giải pháp. Phân tích chi tiết dữ liệu nằm ở Chương 2; kiến trúc, ETL và mô hình dữ liệu nằm ở Chương 3; kết quả và kiểm thử nằm ở Chương 4–5.

## 1.1. Bối cảnh nghiệp vụ giao vận thương mại điện tử

Trong thương mại điện tử, việc hoàn tất đơn hàng đi qua nhiều mốc từ đặt mua đến nhận hàng. Người quản lý vận hành cần theo dõi đơn được giao so với ngày hẹn như thế nào, mức trễ khác nhau ra sao giữa thời kỳ và khu vực, và các đơn giao trễ có đi kèm đánh giá thấp hay không. Các thông tin này giúp thu hẹp phạm vi cần điều tra trước khi lựa chọn một biện pháp vận hành. Tình huống nghiệp vụ này được nghiên cứu trên bộ dữ liệu công khai Olist; nhóm không đại diện cho Olist để mô tả chính sách hay kết quả kinh doanh hiện tại của công ty.

Olist công bố bộ dữ liệu giao dịch thương mại điện tử Brazil gồm khoảng 100 nghìn đơn hàng trong giai đoạn 2016–2018. Dữ liệu liên kết đơn hàng, các mặt hàng trong đơn, người bán, khách hàng, thanh toán, sản phẩm, vị trí địa lý và đánh giá sau mua. Đây là dữ liệu lịch sử đã ẩn danh, phù hợp để xây dựng một tình huống phân tích BI/DSS; kết quả nghiên cứu không đại diện cho tình hình vận hành hiện tại của Olist. [Nguồn dữ liệu Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

Chuỗi sự kiện có thể quan sát trong dữ liệu là **đặt hàng → phê duyệt → bàn giao cho đơn vị vận chuyển → giao khách → đánh giá**. Dữ liệu có ngày giao dự kiến và ngày giao thực tế nên có thể xác định đơn giao sau hẹn. Các mốc này là dấu thời gian của đơn hàng, không phải nhật ký đầy đủ của mọi công đoạn kho vận.

Phân tích sơ bộ trên bản CSV của nhóm cho thấy 96.470 đơn có trạng thái đã giao và đủ ngày giao thực tế, ngày dự kiến; trong đó 6.534 đơn giao sau ngày dự kiến, tương đương 6,77%. Đây là dấu hiệu để đặt câu hỏi về nơi tập trung giao trễ và mối liên hệ với điểm đánh giá. Không suy ra chỉ từ chỉ số này rằng giao trễ gây ra đánh giá thấp, mất khách hàng hay tổn thất doanh thu.

**Đầu ra nên có:** một sơ đồ dòng sự kiện đơn hàng và bảng ba chỉ số sơ bộ: đơn đủ điều kiện, đơn trễ, tỷ lệ trễ. Quy tắc lọc và đối soát số liệu trình bày ở Chương 2 và Chương 4.

## 1.2. Stakeholder Analysis và nhu cầu ra quyết định

Vì nhóm sử dụng dữ liệu công khai, các vai trò dưới đây là **người dùng giả định của giải pháp**, không phải kết quả phỏng vấn nhân sự Olist hay mô tả chính sách nội bộ của công ty.

| Vai trò giả định | Quyết định cần hỗ trợ | Thông tin cần xem | Chu kỳ dự kiến |
|---|---|---|---|
| Quản lý vận hành marketplace | Chọn khu vực và giai đoạn cần điều tra giao trễ | Số đơn đủ điều kiện, tỷ lệ giao đúng hẹn, số ngày trễ, xu hướng theo tháng và bang | Tuần/tháng |
| Quản lý người bán | Chọn người bán cần kiểm tra hoặc hỗ trợ trước | Quy mô đơn và GMV, điểm đánh giá, tỷ lệ giao đúng hẹn, chỉ số bàn giao mang tính đại diện | Tháng |
| Quản lý trải nghiệm khách hàng | Ưu tiên nhóm đơn có đánh giá thấp hoặc giao trễ để tìm hiểu thêm | Phân bố điểm đánh giá, tỷ lệ đánh giá 1–2 sao, mức trễ và khu vực | Tuần/tháng |

Dashboard BI giúp người dùng **nhìn thấy và lọc** nơi phát sinh bất thường. Thành phần DSS như Seller Scorecard, quy tắc cảnh báo và What-if giúp **sắp thứ tự điều tra hoặc so sánh kịch bản**. Quyết định can thiệp thực tế vẫn cần xác minh nguyên nhân bằng dữ liệu vận hành bổ sung.

**Các quyết định cần hỗ trợ:** (1) chọn bang và tháng có giao trễ đáng chú ý để phân tích trước; (2) chọn nhóm đơn có trễ và điểm đánh giá thấp để rà soát; (3) nếu cần đi sâu, chọn nhóm người bán có nhiều giao dịch và chỉ số chất lượng cần kiểm tra. Hệ thống không tự động kết luận nguyên nhân hay áp dụng biện pháp đối với người bán.

## 1.3. Xác định vấn đề, câu hỏi quản trị và phạm vi dự án

### 1.3.1. Problem Statement

Trong tập dữ liệu lịch sử được khảo sát, 6.534 trong 96.470 đơn đã giao đủ mốc ngày đến sau ngày dự kiến (6,77%). Với một marketplace có nhiều khu vực giao nhận, người quản lý vận hành giả định cần quyết định **bang và giai đoạn nào nên được điều tra trước**. Tổng số đơn hoặc GMV riêng lẻ không cho biết điểm nóng giao trễ có đi kèm đánh giá thấp hay không; các mốc giao vận và đánh giá cũng có mức chi tiết khác nhau nên việc xếp thứ tự ưu tiên cần quy tắc đo nhất quán. Nếu không nhìn được các nhóm đơn bất thường, nguồn lực điều tra có thể bị phân tán và nhóm có quy mô ảnh hưởng lớn có thể bị bỏ sót. Đây là **tình huống quản trị do nhóm xây dựng từ dữ liệu công khai**, không phải khẳng định Olist hiện thiếu hệ thống này hoặc đã chịu một khoản thiệt hại được đo lường.

Giải pháp được đề xuất sau khi xác định vấn đề trên: tích hợp dữ liệu vào kho phân tích, theo dõi KPI giao trễ và đánh giá theo thời gian/địa lý, rồi dùng Scorecard và cảnh báo để gợi ý thứ tự điều tra. Các hành động thực tế cần được kiểm chứng bằng dữ liệu vận hành bổ sung.

**Câu hỏi quản trị trung tâm:** Giao trễ trong dữ liệu Olist tập trung ở thời điểm và khu vực nào, và có liên hệ thế nào với điểm đánh giá của khách hàng?

**Câu hỏi hỗ trợ:** Với các điểm nóng đã nhận diện, nhóm người bán nào cần được kiểm tra thêm theo Scorecard? Việc kiểm tra không đồng nghĩa với quy trách nhiệm giao trễ cho người bán.

### 1.3.2. Phạm vi

**Trong phạm vi:** giao dịch lịch sử Olist; phân tích đơn đã giao, thời gian giao, ngày hẹn, đánh giá, người bán, sản phẩm và địa lý; ETL vào MySQL Data Warehouse; dashboard Power BI; Seller Scorecard, cảnh báo, dự báo và What-if ở mức hỗ trợ quyết định. Micro-batch chỉ là mô phỏng phát lại các sự kiện lịch sử theo đợt nếu được port và kiểm chứng trên MySQL.

**Ngoài phạm vi:** dự đoán churn/giữ chân khách, phân khúc RFM, tối ưu tuyến xe theo GPS, xác định nguyên nhân nội bộ của từng công đoạn kho, tính lợi nhuận hoặc chi phí vận chuyển thực của Olist, kết luận tác động nhân quả và hệ thống thời gian thực trên đơn hàng phát sinh thật. Triển khai Cloud BI không thuộc mục tiêu bắt buộc của đề tài tự chọn này.

**Giới hạn quan trọng:** dữ liệu không có mốc nhặt hàng/đóng gói, mã hãng vận chuyển và chi phí từng công đoạn. `freight_value` là phí vận chuyển ghi trên giao dịch, không đủ để suy ra chi phí nội bộ. Đơn hàng có nhiều người bán khiến việc gán toàn bộ ngày giao hoặc điểm đánh giá của đơn cho từng người bán có thể gây sai lệch; chỉ số ở cấp người bán phải ghi rõ quy tắc quy thuộc. `order_delivered_carrier_date` là mốc cấp đơn, nên so với `shipping_limit_date` cấp item chỉ tạo **chỉ số đại diện** cho việc bàn giao đúng hạn, không chứng minh người bán cụ thể giao chậm. Dữ liệu lịch sử đã ẩn danh và các kết luận không đại diện cho hoạt động hiện tại của Olist.

### 1.3.3. Project Charter tóm tắt

| Thành phần | Nội dung của ca nghiên cứu |
|---|---|
| Bối cảnh | Phân tích hoàn tất đơn hàng trên dữ liệu thương mại điện tử lịch sử |
| Vấn đề | Có đơn giao sau hẹn; cần biết điểm nóng giao trễ và mối liên hệ với điểm đánh giá để ưu tiên điều tra |
| Người dùng giả định | Quản lý vận hành và quản lý trải nghiệm khách hàng; quản lý người bán sử dụng phân tích hỗ trợ |
| Quyết định | Chọn khu vực, thời kỳ và nhóm đơn cần rà soát trước; kiểm tra thêm người bán khi phù hợp |
| Phạm vi | Dữ liệu Olist 2016–2018, BI theo thời gian/địa lý/review, DSS ưu tiên điều tra |
| Tiêu chí thành công | KPI đối soát được, người dùng hoàn thành các nhiệm vụ quyết định, quy tắc DSS giải thích được |

## 1.4. Project Objectives, Key Results và Success Criteria

**Objective:** Xây dựng giải pháp BI/DSS có thể tái lập để người dùng giả định xác định điểm nóng giao trễ, xem mối liên hệ giữa giao trễ và đánh giá, và lập danh sách người bán cần điều tra theo quy tắc minh bạch.

Các KR dưới đây là **tiêu chí đánh giá đề xuất**, không phải kết quả đã đạt. Chương 4–5 sẽ báo cáo bằng chứng và trạng thái đạt/chưa đạt cho từng KR.

| Mã | Key Result đề xuất | Bằng chứng cần nộp |
|---|---|---|
| KR1 | 100% chỉ số đối soát trọng yếu được định nghĩa trước có chênh lệch bằng 0 giữa nguồn và kho dữ liệu theo cùng quy tắc lọc | Log ETL, bảng reconciliation, truy vấn SQL |
| KR2 | Người dùng tìm đúng bang và tháng có tỷ lệ giao trễ cao nhất, kèm cỡ mẫu, trong tối đa ba thao tác lọc hoặc drill | Kịch bản kiểm thử trên Power BI, ảnh kết quả |
| KR3 | Người dùng xem được chênh lệch điểm đánh giá giữa nhóm giao đúng hẹn và giao trễ, kèm số đơn của từng nhóm | KPI Dictionary, truy vấn đối chiếu, dashboard |
| KR4 | Người bán đủ ngưỡng mẫu được chấm điểm và xếp hạng theo quy tắc công khai; danh sách ưu tiên có giải thích từng chỉ số | Notebook/scorecard, bảng kết quả, kiểm thử ngưỡng |
| KR5 | Ít nhất 80% nhiệm vụ quyết định theo kịch bản được hoàn thành đúng, có ghi thời gian/thao tác và phản hồi | Test cases và UAT theo vai trò giả định; không gọi là nghiệm thu với Olist |

**Success Criteria:** (1) dữ liệu đúng và đối soát được; (2) dashboard trả lời được các câu hỏi nghiệp vụ bằng KPI có định nghĩa; (3) quy tắc DSS giúp giải thích thứ tự ưu tiên; (4) kết quả kiểm thử và giới hạn được trình bày trung thực. Không đặt mục tiêu “giảm X% giao trễ” vì dự án chưa triển khai can thiệp ngoài thực tế.

## 1.5. Business Requirements, Business Questions và KPI Framework

### 1.5.1. Business Questions

| Mã | Câu hỏi cần trả lời | Hướng ra quyết định |
|---|---|---|
| BQ1 | Tỷ lệ giao trễ và quy mô đơn thay đổi thế nào theo tháng và bang của khách hàng? | Khoanh vùng thời điểm và khu vực cần điều tra |
| BQ2 | Điểm đánh giá phân bố khác nhau ra sao giữa đơn đúng hẹn và đơn giao trễ? | Ưu tiên xem nhóm đơn có đồng thời trễ và đánh giá thấp |
| BQ3 | Người bán nào có quy mô giao dịch lớn nhưng các chỉ số chất lượng thấp? | Lập danh sách người bán cần kiểm tra hoặc hỗ trợ |
| BQ4 | Nhóm sản phẩm nào có GMV cao nhưng điểm đánh giá hoặc hiệu suất giao thấp? | Xác định danh mục cần phân tích sâu |
| BQ5 | Số đơn và giá trị hàng bán biến động theo thời gian ra sao; dự báo thử cho kỳ tiếp theo có sai số thế nào? | Thảo luận nhu cầu nguồn lực, có nêu sai số và giới hạn dữ liệu |
| BQ6 | Nếu thay đổi ngưỡng cảnh báo hoặc trọng số Scorecard, thứ tự ưu tiên người bán thay đổi thế nào? | Kiểm tra độ nhạy của khuyến nghị, không xem là tác động thực tế |

### 1.5.2. KPI cốt lõi

| KPI | Định nghĩa nghiệp vụ | Mức chi tiết và lưu ý |
|---|---|---|
| Số đơn | Đếm đơn hàng không trùng `order_id` | Cấp đơn; nêu rõ tập trạng thái được lọc |
| Tỷ lệ giao trễ | Số đơn `delivered` có ngày giao thực tế sau **ngày** hẹn / số đơn `delivered` đủ cả hai ngày | Cấp đơn; lọc theo tháng đặt hàng và bang khách |
| Tỷ lệ giao đúng hẹn | 1 − tỷ lệ giao trễ trên cùng tập đơn đủ điều kiện | Không tính đơn chưa giao là đúng hẹn |
| Số ngày trễ | Ngày giao thực tế − ngày hẹn với đơn trễ | Báo cáo cả cỡ mẫu; không gộp với lead time |
| Điểm đánh giá trung bình | Trung bình `review_score` theo quy tắc chọn một review đại diện cho mỗi đơn | Cấp đơn; chỉ dùng đơn có review hợp lệ |
| GMV | Tổng `price` ở cấp order item theo quy tắc trạng thái đã nêu | Là giá trị hàng bán trong dữ liệu, không phải lợi nhuận của Olist |
| Seller Scorecard | Tổng trọng số của các thành phần chất lượng đã chuẩn hóa | Chỉ chấm người bán đủ ngưỡng mẫu; cần kiểm tra quy thuộc KPI cấp đơn |

KPI Dictionary đầy đủ cần bổ sung công thức SQL/DAX, đơn vị, bộ lọc, cách xử lý null, mức chi tiết, nơi triển khai và cách giải thích. Các KPI đang ở notebook nhưng chưa có trên Power BI phải ghi đúng trạng thái.

### 1.5.3. Requirement Traceability Matrix

| Requirement | BQ | KPI | Nguồn dữ liệu chính | Sản phẩm phân tích | Kiểm thử |
|---|---|---|---|---|---|
| BR01: xem giao trễ theo thời gian/địa lý | BQ1 | Số đơn, tỷ lệ giao trễ | Orders, Customers | Delivery & Geography | Đối soát SQL và lọc dashboard |
| BR02: so sánh giao trễ với đánh giá | BQ2 | Điểm đánh giá, số đơn theo nhóm | Orders, Reviews | Delivery & Geography / notebook | So nhóm cùng quy tắc lọc |
| BR03: ưu tiên người bán | BQ3 | GMV, Seller Scorecard | Order Items, Sellers, Orders, Reviews | Seller Scorecard, Alerts | Kiểm tra ngưỡng mẫu và độ nhạy |
| BR04: phân tích danh mục | BQ4 | GMV, điểm đánh giá | Products, Order Items, Reviews | Product/Category | Đối soát giá trị item và quy thuộc review |
| BR05: dự báo thử | BQ5 | Số đơn, GMV theo tháng | Orders, Order Items | MySQL DSS, Power BI | Backtest, báo sai số |

**Yêu cầu phi chức năng tối thiểu:** có thể chạy lại ETL và đối soát; ghi rõ chu kỳ cập nhật của dữ liệu lịch sử; không công bố thông tin nhạy cảm; trang dashboard có tên KPI, đơn vị và bộ lọc rõ ràng; tài liệu hướng dẫn nêu khác biệt giữa dữ liệu quan sát, dự báo và giả định What-if.

---

**Liên kết với mục lục sáu chương hiện dùng:** Chương 2 đặt Objective, BQ và KPI; Chương 3 kiểm tra dữ liệu và EDA; Chương 4 trình bày MySQL staging, 6 dimension, 4 fact, ETL và semantic model; Chương 5 trình bày Power BI, Streamlit và kiểm thử; Chương 6 trả lời câu hỏi quản trị, đánh giá KR và nêu giới hạn.

**Nguồn phương pháp:** [BI & DSS Project Handbook Student Edition](https://drive.google.com/file/d/1reaEaULuSF6H-kz5cUGZQrdNWEVLaxRL/view?usp=sharing), đặc biệt các mục Business Understanding, Objectives/OKRs/KPIs, Requirements và yêu cầu truy vết từ business need đến validation.
