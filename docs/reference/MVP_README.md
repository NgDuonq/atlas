> Tài liệu MVP do người dùng cung cấp; chưa có source kèm theo để xác minh các tính năng mô tả dưới đây.

# ◈ Atlas — AI Project Workspace (MVP)

Một ứng dụng chạy trên máy cá nhân cho **4 workflow dùng chung một project**:

1. **Study & Knowledge** — tóm tắt lần lượt nội dung trích xuất từ tài liệu rồi tạo lộ trình ôn tập / lời giải.
2. **Multi-AI Review** — model A giải → model B phản biện → model A sửa.
3. **Project Development** — đọc source (ZIP hoặc file), audit, đề xuất patch ở dạng Markdown/unified diff.
4. **NotebookLM Research** — đọc các nguồn/notes được **import từ** NotebookLM, rồi tổng hợp báo cáo dẫn theo tên file.

Mọi workflow dùng chung các document chunks + lịch sử kết quả (SQLite) trong cùng project. AI có thể tiếp tục từ kết quả workflow trước.

## 1. Yêu cầu

- Python 3.10+ (khuyên dùng 3.11/3.12).
- 9Router đã cài và chạy ở `http://127.0.0.1:20128` với ít nhất 1 provider đã cấu hình.
- Model có hỗ trợ OpenAI-compatible `/v1/chat/completions`.

9Router: <https://docs.9router.com/> · GitHub: <https://github.com/decolua/9router>

## 2. Chạy trên macOS (M1 Pro được)

```bash
cd ai-workspace-mvp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.address 127.0.0.1
```

Streamlit thường mở **http://127.0.0.1:8501**. Nếu cần cài 9Router riêng:

```bash
npm install -g 9router
9router
```

Tại dashboard 9Router, kết nối provider, tạo/copy API key phù hợp (nếu cần), rồi trong sidebar Atlas bấm **Lấy danh sách model**. Chọn **AI chính** và **AI phản biện**. Nếu không tải được danh sách, nhập đúng model ID mà 9Router cung cấp.

**Lưu ý:** Gói đăng ký ChatGPT/Claude không mặc định cấp quyền API; tuân thủ điều khoản từng provider khi kết nối qua gateway.

## 3. Cách dùng bốn workflow

1. **Tạo project** (ví dụ: `Ôn thi Hệ điều hành` hoặc `Portfolio`).
2. Import PDF, DOCX, TXT/MD hoặc source ZIP ở thanh bên. Dán note NotebookLM qua mục riêng hoặc nhập file với loại nguồn **NotebookLM**.
3. Chọn model từ 9Router.
4. Chuyển qua bốn tab, nhập mục tiêu và chạy. Kết quả được lưu trong **Shared Memory**.
5. Tải kết quả từng tab / từng lần chạy dưới dạng `.md`.

Dữ liệu SQLite nằm ở `~/.ai-workspace/workspace.sqlite3` (có thể thay bằng biến môi trường `AI_WORKSPACE_DATA` trỏ vào thư mục dữ liệu). Bản đầu không tự ghi đè mã nguồn gốc.

## 4. NotebookLM: giới hạn và phương án hiện có

**Đã hỗ trợ:** upload tài liệu nguồn từng dùng trong notebook, xuất note qua Google Docs rồi tải DOCX, copy-paste câu trả lời/notes thành `.md`.

**Chưa hỗ trợ:** đăng nhập trực tiếp tài khoản NotebookLM, tự liệt kê notebooks, sync thay đổi trong NotebookLM, tái hiện chính xác hệ thống citation nội bộ của NotebookLM. Không coi link notebook là khả năng truy cập nội dung.

- Google hỗ trợ nguồn Google Drive được đồng bộ trong NotebookLM: <https://support.google.com/gemininotebook/answer/16215270>
- Google hỗ trợ xuất Note thành Google Docs: <https://support.google.com/gemininotebook/answer/16262519>
- API Notebook Enterprise chính thức áp dụng ở sản phẩm enterprise: <https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks>

**Bước nâng cấp khả thi:** adapter Google Drive OAuth chỉ đọc (đồng bộ file gốc), không lưu token trong browser. Có thể cân nhắc MCP NotebookLM bên thứ ba nhưng *không bật mặc định* vì phụ thuộc UI/browser và chứa rủi ro thông tin đăng nhập.

## 5. Kiến trúc

```
Browser (Streamlit, localhost:8501)
    ├─ Project / Source Import ─────────── SQLite: documents, chunks
    ├─ Shared Memory ──────────────────── SQLite: workflow runs
    ├─ Workflow 1 Study  ──────────────── Document summarization → final plan
    ├─ Workflow 2 Review ──────────────── Model A → Model B → Model A
    ├─ Workflow 3 Dev    ──────────────── Code retrieval → audit/patch suggestion
    └─ Workflow 4 NLM    ──────────────── Imported notebook docs → report
                       ↓
          9Router /v1/chat/completions
                       ↓
             GPT / Claude / Gemini / ...
```

- `core.py`: SQLite, import ZIP + PDF/DOCX/text, token-budgeted retrieval, 9Router client, workflow orchestration.
- `app.py`: giao diện điều khiển.
- `tests/`: unit tests chạy offline (mock router).

## 6. Bảo mật & hạn chế minh bạch

- Chỉ nên chạy trên `127.0.0.1`, đừng public port; UI **không có đăng nhập riêng**.
- API key 9Router nhập trong session Streamlit; không persist vào SQLite, nhưng vẫn cần tin tưởng máy và provider.
- Chọn rõ nguồn trước khi gửi: tài liệu sẽ được chuyển tới model provider qua 9Router. Tránh tài liệu nhạy cảm.
- Ngữ cảnh file có thể chứa prompt injection. Có chỉ thị phòng vệ nhưng **không đảm bảo tuyệt đối**.
- Không chạy shell, không sửa file thật, không tự commit/push GitHub. Bản audit chỉ tạo patch *đề xuất*; phải review rồi áp dụng thủ công.
- `Project Development` truy xuất các đoạn source tối đa 38.000 ký tự mỗi lượt; với repo lớn cần phân tích nhiều vòng. `Study` và `NotebookLM` tóm tắt lần lượt các đoạn text trích xuất (tối đa 60 lượt tóm tắt mỗi lần chạy), có thể phát sinh chi phí API đáng kể.
- PDF dạng ảnh/scan sẽ không trích text được nếu chưa OCR. Không hỗ trợ hình ảnh, audio, PPTX, video, Google Docs trực tiếp trong bản này.
- Citation hiện mới ở mức tên file/chunk được trích xuất, chưa đảm bảo trích đúng dòng/trang hoặc kiểm chứng tự động nội dung AI sinh ra.
- Kết nối trực tiếp Drive, NotebookLM MCP, multi-user auth, vector database, terminal sandbox và auto-edit source nằm trong roadmap, **chưa có** ở MVP.

## 7. Roadmap lên phiên bản đầy đủ

- **v0.2**: đồng bộ Google Drive OAuth read-only, gắn citation theo chunk (và trang PDF nếu có); làm mới nguồn tự động.
- **v0.3**: code-agent dựa trên git worktree, patch preview/approval, chạy test trong sandbox; rollback.
- **v0.4**: DAG workflow builder (chạy tuần tự, song song, review chéo), đánh giá kết quả, hỗ trợ RAG embedding & memory có phân quyền.
- **v0.5**: adapter NotebookLM được tùy chọn nếu có integration đáng tin cậy được xác thực, event log, budget/rate caps theo từng provider.

## 8. Test offline

```bash
python -m unittest discover -s tests -v
```

Test không gọi model thật. Muốn end-to-end phải chạy 9Router với provider hoạt động.

### Chạy bốn workflow bằng một nút

Tab **🚀 Chạy cả 4** là một **Unified Mission**: hệ thống lần lượt chạy Study, Multi-AI Review, Project Development, NotebookLM Research và tạo báo cáo tổng hợp cuối. Các bước đều lưu kết quả riêng. Yêu cầu có nguồn project, file code và nguồn NotebookLM; chọn hai model khác nhau, đánh dấu xác nhận chi phí rồi bấm chạy. Các tab riêng vẫn hoạt động độc lập.
