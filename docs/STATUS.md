# Trạng thái Atlas — 03/11/2026

## Đã lưu và đã triển khai

- Blueprint, quyết định kiến trúc và thứ tự triển khai nằm trong repo.
- Bản nền tảng mới: project, import TXT/MD/PDF, phiên bản nguồn, FTS5, xem context, demo adapter, lưu output và citation, chuyển context/phản hồi AI thủ công, chọn kết quả cũ, quyết định người dùng xác nhận.
- Source bytes/chunks/runs được giữ trong SQLite. Packet snapshot và hash bất biến theo lượt; phiên bản mới không đổi context cũ.
- Dữ liệu SQLite v1 là schema mới; chưa có source/schema database MVP để kiểm tra hay migrate.

## Bằng chứng kiểm tra

- 16 kiểm thử offline Python 3.12: lưu/mở lại, cô lập project, phiên bản, budget, citation, lỗi adapter, bàn giao, thao tác thủ công và PDF.
- Smoke test Streamlit AppTest: chọn nguồn, xem context, chạy demo, tạo lượt thủ công/dán phản hồi, lưu quyết định và mở lại app đều không có exception. Đây là kiểm tra luồng UI tự động, chưa phải kiểm tra giao diện trên trình duyệt Mac.
- Demo không gọi model. Chưa có bằng chứng kết nối AI thật hoặc thử trên Mac.
- CI cấu hình Python 3.10/3.12; cấu hình CI không phải bằng chứng CI đã chạy thành công.

## Việc tiếp theo

1. Probe một CLI trên Mac thực tế: binary/version, login, chế độ không tương tác, input/output, lỗi/timeout/hủy và quyền. Không ghi token hoặc nội dung riêng vào repo.
2. Chỉ sau probe mới viết adapter CLI cụ thể, giữ nguyên hợp đồng packet/run hiện có. Thử một tài liệu → một câu hỏi → một câu trả lời AI có nguồn.
3. Thêm runner draft → critique → revision, lưu từng bước và provenance.
4. Code/ZIP import, audit đề xuất và note NotebookLM import; không tự áp patch.
5. Worker nền, hủy/retry và backup/restore đầy đủ.

## Điểm cần nhớ khi sửa tiếp

- Tài liệu trong docs/reference chỉ là mô tả MVP được gửi, chưa phải source đã kiểm tra.
- Giữ đọc nguồn được chọn theo project và phiên bản. Không tự đưa tất cả run vào context.
- Không tự biến output AI thành decision. Chỉ xác nhận của người dùng mới làm điều đó.
- Ký tự không phải token. Citation ID tồn tại không chứng minh kết luận đúng.
- Manual run giữ snapshot từ lúc tạo lượt; dán phản hồi vào đúng lượt, không dựng lại packet từ nguồn hiện tại.
- Chưa có chỉnh/xóa project, xóa nguồn, sửa/supersede decision hoặc khôi phục job dở; thêm cùng kiểm thử migration khi cần.
