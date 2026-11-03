# Atlas — Kế hoạch đang thực hiện

Cập nhật: 03/11/2026. Đây là điểm tiếp tục công việc, không phải danh sách tính năng đã hoàn thành.

## Quyết định đã chốt
- Trải nghiệm: mở Atlas → chọn project → thêm tài liệu/code → giao nhiệm vụ → chọn AI → xem context → chạy → xem kết quả và nguồn → giao bước tiếp.
- Stack đầu tiên: Python + Streamlit + SQLite; tách storage, ingest, context, adapters, workflows, services, ui khi có chức năng thực tế.
- Context Builder là trung tâm: chuyển nguồn, quyết định đã xác nhận và kết quả được chọn giữa các AI. Kết nối nhiều model không tự tạo bộ nhớ chung.
- Giữ cả bốn workflow trên cùng lõi: học tập, review nhiều AI, phát triển project, nghiên cứu từ nguồn/note NotebookLM import. Cho phép ghép workflow và preset cả bốn khi đủ nguồn.
- CLI và API dùng adapter riêng; 9Router chỉ thuộc nhánh API. Không đoán cờ CLI, không coi thuê bao web là API.
- Kết luận AI chưa xác nhận không trở thành quyết định của project.

## Mốc và nghiệm thu
0. Kiểm tra source MVP; thử CLI thật trên Mac: input/output, lỗi, timeout, hủy, quyền.
1. Project + import nguồn + phiên bản + lưu dữ liệu: khởi động lại vẫn giữ nguồn/kết quả.
2. Context Builder + AI thật: xem packet, truy về đoạn nguồn đúng phiên bản.
3. Hai AI: draft → critique → revision, lưu từng bước.
4. Code audit + NotebookLM import cùng lõi.
5. Tác vụ nền, hủy/retry, backup và restore.

## Phát hiện ban đầu
- Repo NgDuonq/atlas lúc bắt đầu chỉ có README một dòng.
- Hai file được cung cấp là tài liệu, không có core.py, app.py hay tests của MVP.
- Môi trường phát triển phiên này là Linux, không phải Mac của người dùng; chưa có binary codex/claude/gemini. Không thể báo đã probe CLI trên Mac.
- docs/ATLAS_BLUEPRINT.md giữ thiết kế chi tiết; docs/reference/MVP_README.md giữ mô tả MVP cũ, chưa được xác minh bằng source.

## Lát cắt triển khai đầu tiên
Tạo project → import TXT/MD/PDF có text → chọn đoạn nguồn → xem context packet → chạy adapter → lưu run/output/citation → mở lại dữ liệu.

Bắt đầu bằng adapter demo offline để kiểm tra lưu trữ/provenance. Adapter thật chỉ báo đã kiểm thử khi có provider/CLI thật. Không dựng lại hàng loạt tính năng dựa trên README cũ.

## Tiến độ lát cắt đầu
- Đã triển khai project, import TXT/MD/PDF, phiên bản, FTS5, packet xem được, demo/manual adapter và kết quả/decision lưu lại.
- 16 kiểm thử offline đã pass; smoke test Streamlit chạy luồng chính thành công.
- Mốc 1 có nền tảng dùng được; mốc 0 CLI trên Mac và mốc 2 AI tự động vẫn chưa hoàn thành.
- Chi tiết bằng chứng, giới hạn và việc sửa tiếp: [STATUS.md](STATUS.md).

## Việc tiếp theo sau lát cắt đầu
- Có source MVP thì kiểm tra baseline/schema rồi mới chọn phần tái sử dụng.
- Probe CLI trên Mac có binary và đăng nhập thực tế; lưu phiên bản và bằng chứng, không lưu token.
- Nối một AI thật, rồi thêm review ba bước trước khi mở rộng bốn workflow.
