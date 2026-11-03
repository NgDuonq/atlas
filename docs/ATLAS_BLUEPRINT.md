# Atlas — Bộ khung triển khai v0.1

Ngày: 02/11/2026. Trạng thái: thiết kế đề xuất, chưa phải tính năng đã triển khai.
Nguồn kiểm tra: README.md do người dùng gửi. Chưa kiểm tra ZIP/source, chưa chạy MVP và chưa xác minh giao diện các CLI trên máy người dùng.

## 1. Mục tiêu và phạm vi

Atlas là workspace chạy trên máy cá nhân: một project chứa nguồn tài liệu, mục tiêu, quyết định và kết quả; nhiều AI nhận ngữ cảnh có kiểm soát để làm việc nối tiếp trên cùng project.

Người dùng thao tác chính: tạo project → thêm nguồn → giao nhiệm vụ → chọn AI/vai trò → xem ngữ cảnh sẽ gửi → chạy → kiểm tra nguồn và kết quả → lưu quyết định hoặc giao bước kế tiếp.

Bốn workflow đều là phạm vi sản phẩm: Study & Knowledge, Multi-AI Review, Project Development, NotebookLM Research. Cùng một lõi thực thi phục vụ cả bốn. Hoàn thiện dần từng luồng, không xây bốn ứng dụng riêng.

Một model không tự nhìn thấy lịch sử hay suy nghĩ riêng của model khác. Atlas chuyển giao những nội dung đã lưu và được chọn vào ngữ cảnh. Không hứa đọc trực tiếp lịch sử ChatGPT/Claude web hay toàn bộ NotebookLM.

## 2. Chọn kiến trúc

- Bản đầu: Python, Streamlit, SQLite + FTS5, file trên đĩa. Giữ stack README để tránh viết lại UI trước khi lõi chạy được.
- UI gọi service; service gọi kho dữ liệu và bộ thực thi. Không đặt SQL, prompt, subprocess trong callback giao diện.
- CLI và API là hai loại adapter độc lập. 9Router là gateway tùy chọn cho nhánh API, không phải kho ngữ cảnh chung và không phải cầu nối mặc định tới mọi CLI.
- Model local đi qua adapter có giao thức được xác minh sau. Không bắt buộc để hoàn thành bản đầu.
- Chưa cần React, FastAPI, Docker, Redis, vector database hay workflow builder kéo thả. Chỉ thêm khi có nhu cầu đo được.

## 3. Các khối lõi và hợp đồng

| Khối | Nhận | Trả | Trách nhiệm |
|---|---|---|---|
| Project service | Tên, mục tiêu, quy tắc | Project ID | Cô lập dữ liệu giữa project |
| Source importer | File hoặc note | Source version + chunks | Lưu bản nguồn, hash, metadata, trạng thái trích xuất |
| Context builder | Nhiệm vụ, nguồn được chọn, giới hạn | Context packet | Tìm đoạn liên quan, chọn kết quả trước, ghi thiếu sót |
| Execution adapter | Request + context packet | Output + trạng thái | Gọi CLI/API, timeout, hủy, chuẩn hóa lỗi |
| Workflow runner | Workflow + vai trò | Run + steps | Truyền đầu ra giữa các bước, lưu tiến độ |
| Result & memory service | Kết quả và quyết định người dùng | Artifact, decision | Giữ lịch sử và trí nhớ đã xác nhận |

## 4. Dữ liệu và vị trí lưu

Mặc định đề xuất: ~/Documents/Atlas; thay đổi được bằng ATLAS_HOME. Đây là đường dẫn thiết kế trên máy người dùng, chưa được tạo ở phiên này.

```text
Atlas/
  atlas.sqlite3
  projects/<project-id>/
    project.md
    sources/<source-id>/<version>/original.ext
    extracted/<source-id>/<version>/content.md
    artifacts/<artifact-id>/result.md
    runs/<run-id>/context.json
    runs/<run-id>/events.jsonl
  exports/
  backups/
```

DB là nguồn chính cho ID, quan hệ, trạng thái và quyết định. File dùng cho bytes nguồn và artifact; tránh hai bản metadata cùng được sửa độc lập. project.md là bản xuất để đọc, không phải DB thứ hai.

Đường dẫn lưu tương đối dưới ATLAS_HOME để sao lưu/di chuyển dễ hơn. Repo code người dùng chọn được tham chiếu riêng; không sao chép toàn bộ repo vào DB.

Các bảng tối thiểu:

| Bảng | Trường và quan hệ chính |
|---|---|
| projects | id, name, goal, instructions, created_at |
| sources | id, project_id, kind, title, origin, active_version_id |
| source_versions | id, source_id, sha256, relative_path, extraction_status, imported_at |
| chunks | id, project_id, source_version_id, text, page, line_start, line_end |
| chunks_fts | Chỉ mục FTS5 phục vụ tìm kiếm văn bản |
| tasks | id, project_id, goal, workflow_type, selected_source_ids |
| runs | id, task_id, state, context_hash, started_at, finished_at |
| run_steps | id, run_id, role, adapter_id, state, input_ref, output_ref, error |
| artifacts | id, project_id, run_step_id, kind, relative_path, status |
| decisions | id, project_id, text, evidence_ref, confirmed_at, supersedes_id |
| adapters | id, kind, display_name, config_without_secrets, capabilities |

Mọi truy vấn tìm kiếm phải lọc project_id trước. SQLite bật foreign keys; dùng migration có phiên bản. Upload cùng hash có thể tái sử dụng bản đã trích xuất; nguồn đổi nội dung tạo phiên bản mới. Kết quả cũ tiếp tục tham chiếu phiên bản cũ.

PDF lưu trang khi trích xuất được; text/code lưu dòng. DOCX chỉ gắn cấu trúc đoạn khi không có trang đáng tin cậy. File không trích được phải hiện lỗi, không giả vờ đã đọc. Chưa OCR trong mốc đầu.

## 5. Context packet: trung tâm của bộ nhớ chung

Mỗi lần gọi AI tạo một packet bất biến gồm:

1. Mục tiêu nhiệm vụ và quy tắc project.
2. Quyết định đã được người dùng xác nhận, có mức ưu tiên và giới hạn dung lượng.
3. Các đoạn nguồn liên quan: source ID, version, chunk ID, vị trí, nội dung.
4. Artifact/kết quả trước được chọn hoặc đầu ra bước ngay trước.
5. Chỉ dẫn vai trò và cấu trúc đầu ra.
6. Danh sách nguồn bỏ qua, lỗi trích xuất và giới hạn độ phủ.

Không đưa toàn bộ lịch sử vào mọi lần gọi. Dùng truy vấn FTS5 + lựa chọn nguồn thủ công trước; nếu chất lượng tìm kiếm không đạt bộ câu hỏi kiểm thử mới cân nhắc embeddings.

Giới hạn ngữ cảnh cấu hình theo adapter/model, chừa dung lượng cho đầu ra. Khi chưa có tokenizer phù hợp, ghi rõ phép ước lượng; không gọi số ký tự là số token chính xác. Packet có hash và được lưu cùng run để biết AI đã được xem gì.

Citation dùng dạng [S:<source-id>@<version>#<chunk-id>]. Bộ kiểm tra xác nhận ID tồn tại trong packet và phiên bản đúng; việc đó chưa chứng minh câu kết luận được nguồn hỗ trợ. UI mở đoạn dẫn để người dùng kiểm tra. Không tìm thấy chứng cứ thì yêu cầu model nói thiếu dữ liệu.

Trí nhớ chia thành: nguồn gốc; kết quả AI chưa xác nhận; quyết định đã xác nhận. AI không được tự nâng kết luận của nó thành quyết định của project.

## 6. Adapter CLI/API

Giao diện đề xuất:

```python
class ExecutionAdapter:
    def probe(self) -> Capabilities: ...
    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...
    def cancel(self, execution_id: str) -> None: ...
```

Request: task, context packet, model/profile, working directory, timeout, output limit, execution mode.
Result: text, raw output reference, adapter/model identity nếu biết, duration, usage nếu provider cung cấp, exit/status, normalized error. Usage không biết hiển thị unknown; không quy đổi thành chi phí giả.

Trước khi hỗ trợ một CLI phải thử: binary tồn tại; cách đăng nhập; gọi không tương tác; đưa prompt bằng cơ chế nào; định dạng đầu ra; timeout; hủy tiến trình; quyền đọc/sửa file; cách giới hạn công cụ. Không viết cờ lệnh dựa trên phỏng đoán. Một adapter capability quyết định UI cho phép việc gì.

Thứ tự: mock adapter → một CLI người dùng đang có và vượt qua probe → CLI thứ hai → API gateway nếu cần → model local. Nếu CLI chỉ có chế độ tương tác hoặc không hạn chế được ghi file, đánh dấu chưa hỗ trợ chạy tự động; vẫn có đường xuất context packet để sử dụng thủ công.

CLI đăng nhập riêng; không giả định gói thuê bao tương đương API hay mọi công cụ Google có cùng giao diện. Cần kiểm tra chính thức khi triển khai adapter cụ thể.

Chạy subprocess bằng danh sách đối số, không shell=True; không ghép lệnh từ nội dung tài liệu. Không nạp bí mật vào log. Chỉ bind localhost. Chế độ đọc phải được adapter thực sự bảo đảm bằng quyền/công cụ hoặc vùng thực thi giới hạn; lời nhắc “đừng sửa file” không đủ.

## 7. Bốn workflow

### Study & Knowledge
Chọn nguồn + mục tiêu học → tìm/tóm tắt đoạn phù hợp → giải thích/lời giải/lộ trình → lưu artifact. Nếu yêu cầu đọc toàn bộ tài liệu phải có lượt quét theo từng phần, thống kê độ phủ và phần thất bại; không đánh đồng top-k retrieval với đọc hết.

### Multi-AI Review
Solver tạo bản nháp → Reviewer nhận cùng nguồn và nháp, ghi lỗi/chứng cứ → Solver nhận phản biện để sửa. Bản đầu một vòng; giữ riêng cả ba đầu ra. Đánh dấu khi hai vai dùng cùng model. Đồng thuận giữa model không phải bằng chứng đúng.

### Project Development
Chọn thư mục/ZIP, lọc file → lập bản đồ repo có giới hạn → audit câu hỏi cụ thể → tạo đề xuất Markdown/unified diff. Loại .env, private keys, .git, node_modules, build output khỏi import mặc định. ZIP kiểm tra đường dẫn và giới hạn giải nén.
Mốc đầu không áp patch và không chạy code từ repo. Mốc sau dùng git worktree, xem diff, cho phép áp dụng theo thao tác người dùng, test trong môi trường giới hạn và giữ đường rollback.

### NotebookLM Research
Import tài liệu gốc hoặc note đã xuất/copy → giữ provenance nguồn → hỏi/tổng hợp có citation tới file đã import. Phân biệt note do AI sinh với tài liệu gốc. Không coi URL notebook là nội dung đã đọc. Đồng bộ trực tiếp là nhánh nghiên cứu riêng sau này.

### Unified Mission
Một nhiệm vụ chọn các workflow cần chạy, xem trước thứ tự và nguồn. Ví dụ nghiên cứu có thể dùng NotebookLM Research → Review; nhiệm vụ code có thể dùng Development → Review. Preset “chạy cả 4” vẫn có khi người dùng muốn và có đủ nguồn. Bước không liên quan hoặc thiếu nguồn phải báo/skip rõ, không tự tạo nội dung cho đủ bốn tab.

## 8. Điều phối và lỗi

Run state: queued → running → completed/failed/cancelled. Các step có trạng thái riêng. Ghi output mỗi bước trước khi chuyển bước kế tiếp. Lỗi reviewer giữ lại draft; retry tạo attempt mới và lưu quan hệ. Timeout không biến thành “hoàn thành”.

Một tiến trình worker cục bộ lấy job từ SQLite; UI đọc tiến độ, tránh việc Streamlit rerun tạo job trùng. Tách worker từ mốc chạy tác vụ dài; bản mock có thể thực thi đồng bộ. Bản đầu một job chạy đồng thời. Khi khởi động lại, job bị ngắt được nhận diện; người dùng chọn retry, không tự gửi lại yêu cầu có thể đã tính phí.

Cho phép hủy, giới hạn số bước/lượt gọi, timeout và độ dài đầu ra. Budget theo tiền chỉ thực thi khi có dữ liệu giá/usage đủ tin cậy; nếu không dùng giới hạn lượt và hiện unknown.

## 9. Giao diện

| Khu vực | Hiển thị / thao tác |
|---|---|
| Danh sách project | Tạo/mở project, mục tiêu và hoạt động gần nhất |
| Sources | Upload, chọn nguồn, trạng thái trích xuất, phiên bản, xem nội dung |
| Task | Ô giao việc, workflow, vai trò AI, xem context, nút chạy/hủy |
| Runs | Tiến trình theo bước, lỗi, retry, kết quả từng AI |
| Memory & Results | Kết quả đã lưu, quyết định đã xác nhận, xuất Markdown |
| Connections | Probe CLI/API, năng lực, lỗi cấu hình; không hiện bí mật |

Sources và Task là đường đi chính. Chọn project/nguồn phải rõ trước khi chạy. Kết quả có nút mở nguồn dẫn và “lưu thành quyết định”; không tự ghi mọi output vào trí nhớ quan trọng.

## 10. Cấu trúc source đề xuất

```text
atlas/
  app.py
  worker.py
  pyproject.toml
  README.md
  src/atlas/
    config.py
    domain/          # models, states, contracts
    storage/         # schema, migrations, repositories
    ingest/          # text, pdf, docx, zip, code filters
    context/         # search, packet, citations, coverage
    adapters/        # base, mock, cli_verified, openai_compatible
    workflows/       # study, review, development, notebook, mission
    services/        # projects, sources, tasks, runs, memory
    ui/              # projects, sources, task, results, settings
  tests/
    fixtures/
    test_project_isolation.py
    test_source_versions.py
    test_context_provenance.py
    test_workflow_handoff.py
    test_adapter_failures.py
```

Tên cli_verified là vị trí minh họa, thay bằng tên CLI sau khi xác minh. Không tạo hàng loạt module rỗng trước khi có lát cắt chạy được. Khi nhận source MVP: chạy baseline offline, kiểm tra schema thực tế rồi mới quyết định tái sử dụng/tách core.py; không ghi đè database cũ.

## 11. Thứ tự làm và điều kiện hoàn thành

| Mốc | Việc làm | Bằng chứng hoàn thành |
|---|---|---|
| 0 — Chốt đường chạy AI | Kiểm tra source hiện có; probe một CLI trên Mac; chốt input/output/quyền | Một yêu cầu nhỏ trả kết quả, có log lỗi và cách hủy |
| 1 — Xương sống dữ liệu | Project, import TXT/MD/PDF có text, phiên bản, search, packet, mock | Tạo project, thêm nguồn, hỏi, đóng/mở lại vẫn giữ dữ liệu; không lẫn project |
| 2 — Một luồng thật | Nối CLI đã probe với Study; nguồn dẫn và run history | Câu trả lời có đoạn nguồn mở được, thấy được context đã gửi |
| 3 — Hai AI tiếp nối | Thêm adapter thứ hai và review ba bước | Reviewer thấy draft và nguồn; bản sửa giữ provenance; lỗi không mất bước trước |
| 4 — Đủ bốn workflow | Thêm code import/audit, note NotebookLM, mission presets | Cùng dữ liệu dùng qua bốn workflow và tái sử dụng artifact có chọn lọc |
| 5 — Tiện dùng hằng ngày | Worker, hủy/retry, export/backup, thử restore | Job dài không mất theo UI; khôi phục đủ nguồn/kết quả/quyết định |
| Sau v0.1 | Model local, Drive sync, code editing, embeddings, UI nâng cấp | Từng nhánh có nhu cầu và kiểm thử riêng |

Không ấn ngày giao khi chưa kiểm tra source và CLI. Ước lượng sau mốc 0. Cả bốn workflow vẫn là đích v0.1; các mốc là thứ tự triển khai phụ thuộc nhau.

## 12. Kịch bản nghiệm thu

1. Tạo “Ôn thi Hệ điều hành”, thêm tài liệu TXT/MD và PDF có text.
2. Hỏi một câu trả lời có trong nguồn; mở citation đúng đoạn và phiên bản.
3. AI thứ hai phản biện; bản sửa có liên kết tới draft/review.
4. Xác nhận một quyết định; nhiệm vụ sau có thể dùng quyết định đó.
5. Thêm file code và note NotebookLM; chạy hai workflow tương ứng trên cùng project.
6. Tạo project khác với đoạn nguồn tương tự; không được truy xuất chéo.
7. Thay nội dung nguồn; run cũ vẫn chỉ đúng phiên bản cũ.
8. Giả lập CLI lỗi/timeout/hủy; giữ output đã hoàn thành và hiển thị trạng thái đúng.
9. Khởi động lại và thử khôi phục backup; kiểm tra DB, source, artifacts và đường dẫn cùng hoạt động.

## 13. Việc bắt đầu ngay

Đầu tiên lấy source ZIP MVP và xác định CLI thực tế có trên máy. Chỉ đọc README chưa đủ để kết luận chất lượng code hoặc mức tái sử dụng.
Đầu ra đầu tiên cần đạt: một project, một tài liệu, một câu hỏi, một AI thật, một kết quả lưu được và mở lại được kèm nguồn. Sau đó thêm AI phản biện và mở rộng bốn workflow trên cùng lõi.
