# ◈ Atlas — AI Project Workspace

Workspace cục bộ để giữ tài liệu, ngữ cảnh và kết quả theo project, rồi chuyển phần cần thiết giữa các AI.

**Trạng thái: bản nền tảng v0.1.dev1.** Repo ban đầu chưa có source MVP. Mô tả MVP được cung cấp nằm trong [tài liệu tham chiếu](docs/reference/MVP_README.md); các tính năng trong đó chưa mặc nhiên tồn tại trong bản này.

## Chạy trên Mac / Linux

Python 3.10+ có SQLite FTS5.

```bash
git clone https://github.com/NgDuonq/atlas.git
cd atlas
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m streamlit run app.py --server.address 127.0.0.1
```

Mở http://127.0.0.1:8501. Dữ liệu mặc định ở `~/Documents/Atlas/atlas.sqlite3`; đổi bằng `ATLAS_HOME`. Không lưu dữ liệu cá nhân vào repo. Chưa có migration từ database MVP cũ.

## Luồng dùng được hiện tại

1. Tạo project với mục tiêu và quy tắc.
2. Nhập TXT/Markdown UTF-8 hoặc PDF có text; cùng tên tạo phiên bản mới, cùng bytes dùng lại phiên bản cũ.
3. Chọn nguồn, nhập nhiệm vụ, chọn kết quả trước cần bàn giao.
4. Xem context packet: đoạn nguồn, trang/dòng, quyết định đã xác nhận, kết quả trước, độ phủ và giới hạn ký tự.
5. Chạy **demo offline** để kiểm tra lưu trữ. Demo chỉ trả trích đoạn, không gọi AI.
6. Hoặc xuất prompt sang AI bạn chọn, tạo lượt thủ công để giữ context, rồi dán phản hồi vào đúng lượt trong tab Kết quả. Có thể tải lại prompt gốc từ lượt đó.
7. Xem kết quả và các đoạn nguồn đã gửi, tải Markdown; xác nhận quyết định ở tab riêng. Mở lại app vẫn giữ dữ liệu.

Kết quả trước chỉ đi vào nhiệm vụ sau khi được chọn. Nó vẫn là đầu ra AI chưa xác nhận. Quyết định chỉ được thêm khi người dùng bấm xác nhận.

## Có gì trong code

- `storage/`: SQLite schema v1, foreign keys, project, source versions, FTS5, quyết định, runs và snapshot context.
- `ingest/`: TXT/MD, PDF theo trang, giới hạn 20 MiB/500 trang; cảnh báo trang không trích được text.
- `context/`: truy xuất FTS5 trong project, packet giới hạn ký tự JSON, provenance và kiểm tra citation IDs.
- `adapters/`: adapter demo, không giả lập khả năng trả lời AI.
- `services/`: nhập nguồn, chạy demo và lưu phản hồi thủ công theo context gốc.
- `ui/`: Streamlit, xem context và nguồn của từng kết quả.

Bản nền tảng lưu bytes nguồn, chunks và outputs trong cùng SQLite để việc import/run nhất quán trong một transaction. Đây là bước đơn giản hóa so với thiết kế file store trong blueprint; tách bytes ra file khi thêm backup/nguồn lớn. Context của run lưu nguyên text nên vẫn kiểm tra được nguồn cũ sau khi import phiên bản mới.

Citation `[S:source-id@version-id#chunk-id]` chỉ được kiểm tra có nằm trong packet hay không. Điều này không chứng minh nội dung câu trả lời đúng. Không có tokenizer: giới hạn hiện tại là ký tự JSON, không phải token. Retrieval không tương đương đọc toàn bộ tài liệu. PDF scan cần OCR ngoài ứng dụng.

## Chưa có

- Gọi CLI/API/local model tự động, worker nền, timeout/hủy/retry, restore backup.
- Review ba bước tự động, code/ZIP audit, DOCX, import note NotebookLM riêng, Unified Mission.
- Đồng bộ trực tiếp NotebookLM/Drive hoặc đọc lịch sử AI web.

Cả bốn workflow vẫn thuộc phạm vi đã chốt; triển khai trên cùng lõi theo [kế hoạch](docs/IMPLEMENTATION_PLAN.md). [Blueprint](docs/ATLAS_BLUEPRINT.md) mô tả hợp đồng và hướng phát triển. [Trạng thái kiểm tra](docs/STATUS.md) ghi bằng chứng và điểm tiếp tục.

CLI và API là hai adapter riêng; 9Router thuộc nhánh API. Cần probe CLI trên Mac có binary/login thật trước khi triển khai. Chưa kiểm tra CLI trên Mac trong phiên này.

## Kiểm thử

```bash
python -m unittest discover -s tests -v
```

Tests chạy offline: cô lập project, source version, độ phủ/budget, citation, lưu/mở lại, bàn giao kết quả được chọn, adapter lỗi, phản hồi thủ công, PDF có text/trang trống/mã hóa. GitHub Actions cấu hình Python 3.10 và 3.12.

Chỉ bind localhost; UI chưa có đăng nhập. Khi xuất context sang nhà cung cấp AI, các đoạn tài liệu trong packet được chia sẻ với nhà cung cấp đó. Nội dung nguồn không được thực thi; app chưa chạy shell hay áp patch vào repo của người dùng.
