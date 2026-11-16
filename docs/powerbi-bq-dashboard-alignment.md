# Sửa dashboard Power BI để trả lời đủ BQ1–BQ5

## Trạng thái

`G8_Olist_BQ_Aligned.pbix` tạo bằng cách sửa trực tiếp kho lưu PBIX đã **không mở được** và đã được xóa ngày 15/11/2026. Bản chính hiện là `powerbi/pbip_project/G8_Olist_Overview_MySQL.pbip`; `powerbi/G8_Olist_Overview_MySQL.pbix` là snapshot cũ hơn. Không dùng bản PBIX lỗi hoặc snapshot cũ làm bằng chứng cho thay đổi PBIP chưa xuất lại.

Microsoft hỗ trợ chỉnh sửa bên ngoài với **Power BI Project (PBIP)** và định nghĩa báo cáo **PBIR**, không hỗ trợ quy trình tương tự với PBIX. Việc chuyển PBIX → PBIP phải thực hiện bằng **File → Save As** trong Power BI Desktop. Nguồn: [Microsoft Learn – Power BI Projects](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview), [Edit PBIP files outside Power BI Desktop](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-external-editing).

## Bước chuyển định dạng trong Power BI Desktop

1. Mở `powerbi/G8_Olist_Overview_MySQL.pbix`.
2. Chọn **File → Save As**; ở loại file chọn **Power BI project (*.pbip)**.
3. Lưu vào `D:\olist\olist-bidss-group08\powerbi\pbip_project`. Người dùng đã lưu với tên `G8_Olist_Overview_MySQL.pbip`; thư mục này có đủ `.pbip`, `.Report` và `.SemanticModel`.
4. Ngày 15/11/2026 đã chạy `python scripts/patch_pbir_bq_dashboard.py powerbi/pbip_project`: các visual BQ4/BQ5 và 5 measure BQ4 được chỉnh trực tiếp trong project. Bản sao các file trước sửa nằm ở `temp/pbip_bq_backup`.

## Mục tiêu sửa

| Trang | Thay đổi | Câu hỏi |
|---|---|---|
| Executive Overview | Thêm đường GMV thực tế/dự báo cạnh đường số đơn thực tế/dự báo. | BQ5 |
| Product/Category Analysis | Biểu đồ tăng trưởng GMV tháng 1–8/2018 so với cùng kỳ 2017 trên trục X và review cùng kỳ 2018 trên trục Y; bảng danh mục có GMV hai kỳ, tăng trưởng và review. | BQ4 |
| Delivery & Geography | Giữ bang–tháng và tỷ lệ trễ. | BQ1 |
| Executive Overview | Giữ review theo nhóm ngày trễ. | BQ2 |
| Seller Performance, Scorecard, Alerts | Giữ GMV, tỷ lệ trễ, review và ưu tiên điều tra seller. | BQ3 |

Khi sửa xong, mở lại `powerbi/pbip_project/G8_Olist_Overview_MySQL.pbip` trong Power BI Desktop (hoặc bấm **Apply external changes** nếu có banner), kiểm tra **Problems 0**, chạy `powerbi/Validate_BQ4_BQ5.dax` và Save As PBIX nếu cần nộp tệp PBIX. Kỳ vọng tăng trưởng GMV chung 137,26% và review chung kỳ 2018 là 4,099; đối chiếu thêm bốn danh mục `watches_gifts`, `baby`, `telephony`, `electronics` với CSV EDA. Kiểm tra cấu trúc project đã qua; cần xác nhận hiển thị thực tế trong Desktop.


Các nút trên đầu trang đã liên kết đúng: 4 trang đầu dùng Page Navigator, Scorecard và Alerts dùng nút PageNavigation. Trong Power BI Desktop ở chế độ chỉnh sửa, giữ Ctrl rồi nhấp để chuyển trang; trong chế độ đọc, nhấp bình thường.

**Đã kiểm tra trực tiếp trong Power BI Desktop:** tải lại project qua Desktop Bridge thành công, sau đó chụp [trang BQ4](evidence/powerbi/bq4_product_category_final.png) và [trang BQ5](evidence/powerbi/bq5_executive_overview_final.png). BQ4 hiển thị 53K đơn có review, tăng trưởng GMV 137,26%, GMV 2018 khoảng R$7,39 triệu và review 4,099; bảng danh mục và scatter có giá trị khác nhau theo nhóm. BQ5 hiển thị riêng hai đường dự báo **GMV** và **số đơn**. Header Product/Category và tiêu đề GMV đã được sửa. Chưa xuất lại PBIX cuối từ PBIP.

**Kiểm tra lưu 15/11/2026:** Power BI Desktop đã lưu project lúc 14:41:38. Desktop Bridge trả `hasUnsavedChanges=false`; project vẫn có 6 trang, 5 measure BQ4, hai đường dự báo BQ5 và các tiêu đề đã sửa. Bản PBIP trên đĩa đã hoàn tất; nếu cần nộp PBIX, xuất từ Power BI Desktop bằng File → Save As.
