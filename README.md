# Banking Secure RAG Vector Search

Đây là đồ án demo hệ thống RAG cho dữ liệu ngân hàng, tập trung vào truy xuất tài liệu bằng vector search và kiểm soát truy cập theo vai trò người dùng.

Hệ thống có hai lớp bảo vệ chính:

- **Document-level access control**: chỉ truy xuất các tài liệu mà vai trò hiện tại được phép xem.
- **Field-level masking**: nếu người dùng được xem tài liệu nhưng không được xem một số trường dữ liệu, các trường đó sẽ được thay bằng `[MASKED]`.

Ứng dụng cũng hỗ trợ Local AI thông qua Ollama để:

- Chuyển câu hỏi tiếng Việt hoặc tiếng Anh thành truy vấn có cấu trúc.
- Tổng hợp kết quả truy xuất thành câu trả lời tự nhiên bằng tiếng Việt.

Local AI chỉ nhận dữ liệu đã qua bước kiểm soát truy cập và masking (`safe_results`). Dữ liệu gốc chưa qua policy không được gửi trực tiếp cho mô hình.

## Chức năng chính

- Giao diện demo bằng Streamlit.
- Tìm kiếm tài liệu ngân hàng bằng ChromaDB và embedding model.
- Lọc tài liệu theo vai trò, khách hàng, chi nhánh, loại tài liệu và mức độ nhạy cảm.
- Mask các trường dữ liệu không được phép xem theo field policy.
- Parser fallback theo luật nếu Local AI chưa sẵn sàng.
- Bộ dữ liệu giả lập, bộ câu hỏi kiểm thử và expected results phục vụ đánh giá đồ án.

## Cấu trúc thư mục

```text
.
├── data/
│   ├── documents.json              # Bộ tài liệu ngân hàng giả lập
│   ├── metadata_store.json         # Metadata tách riêng để filter khi retrieval
│   ├── queries.json                # Bộ câu hỏi dùng để kiểm thử hệ thống
│   └── expected_results.json       # Ground truth cho đánh giá retrieval/masking
├── docs/
│   ├── assignment.md               # Mô tả nhiệm vụ tạo dataset và bộ test
│   ├── NLP_DEMO_GUIDE.md           # Hướng dẫn demo xử lý ngôn ngữ tự nhiên
│   ├── permission_matrix.md        # Ma trận quyền truy cập theo vai trò
│   ├── README_dataset_definition.md
│   └── README_data_query_test_expected_result.md
├── schemas/
│   ├── schema_definition.json      # Định nghĩa schema tài liệu
│   ├── document_types.json         # Danh sách loại tài liệu
│   ├── roles.json                  # Danh sách vai trò người dùng
│   └── field_policy_store.json     # Chính sách truy cập theo từng trường dữ liệu
├── src/
│   ├── __init__.py
│   ├── app.py                      # Giao diện Streamlit
│   ├── answer_composer.py          # Masking và tạo câu trả lời fallback
│   ├── config.py                   # Đường dẫn, hằng số và cấu hình chung
│   ├── embedder.py                 # Tạo embedding cho văn bản
│   ├── indexer.py                  # Xây dựng ChromaDB vector index
│   ├── llm_services.py             # Tích hợp Ollama/OpenAI cho parser và trả lời
│   ├── nl_processor.py             # Parser rule-based khi không dùng Local AI
│   ├── searcher.py                 # Vector search và kiểm soát document-level access
│   └── test_backend.py             # Script kiểm thử backend retrieval
├── .dockerignore
├── .env.example                    # Mẫu biến môi trường
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Yêu cầu môi trường

- Python 3.10 trở lên.
- Pip và virtual environment.
- Ollama nếu muốn dùng Local AI.
- Docker Desktop hoặc Docker Engine nếu muốn chạy bằng Docker Compose.

## Chuẩn bị push GitHub

Các file/thư mục nên push:

```text
data/
docs/
schemas/
src/
scripts/setup.ps1
scripts/setup.sh
.dockerignore
.env.example
.gitignore
Dockerfile
docker-compose.yml
docker-compose.ollama.yml
pyproject.toml
requirements.txt
README.md
```

Các file/thư mục không nên push vì là dữ liệu local, cache, runtime artifact hoặc phần báo cáo riêng:

```text
.venv/
chroma_db/
Báo cáo/
__pycache__/
.env
*.sqlite
*.sqlite3
*.db
*.zip
```

Kiểm tra trước khi commit:

```bash
git status --short --ignored
```

Nếu chỉ muốn add phần source/app và các file setup Docker:

```bash
git add .dockerignore .env.example .gitignore Dockerfile docker-compose.yml docker-compose.ollama.yml README.md pyproject.toml requirements.txt data docs schemas src scripts/setup.ps1 scripts/setup.sh
```

Nếu lỡ add nhầm dữ liệu runtime, bỏ khỏi staging bằng:

```bash
git restore --staged .venv chroma_db Báo cáo
```

## Cài đặt

### Cài tự động

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

Linux/macOS:

```bash
bash scripts/setup.sh
```

Các script trên sẽ tạo `.venv`, cài package Python, tạo `.env`, kiểm tra/cài Ollama nếu có thể, tải model `qwen2.5:3b-instruct`, và kiểm tra import cơ bản. Nếu không muốn cài Ollama, dùng:

```powershell
.\scripts\setup.ps1 -SkipOllama
```

hoặc:

```bash
SKIP_OLLAMA=1 bash scripts/setup.sh
```

### Chạy bằng Docker Compose

Nếu đã cài Docker Desktop hoặc Docker Engine và đã có Ollama chạy trên máy host, dùng:

```bash
docker compose up --build
```

Lệnh này chỉ chạy Streamlit app trong Docker và kết nối tới Ollama trên máy host qua `http://host.docker.internal:11434`, nên không pull lại model trong Docker.

Trong lần `--build` đầu tiên, Docker image sẽ tải embedding model `all-MiniLM-L6-v2`. Sau khi app mở, màn hình `Building vector index...` là bước tạo Chroma index từ `data/documents.json`; bước này chỉ chạy khi volume `chroma_data` chưa có index.

Sau đó mở:

```text
http://localhost:8501
```

Nếu chưa cài Ollama trên máy host, hoặc muốn Ollama chạy hoàn toàn trong Docker, dùng thêm file compose Ollama:

```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build
```

Compose sẽ dựng các service:

- `app`: Streamlit app.
- `ollama`: Ollama server.
- `ollama-pull`: chỉ tải model `qwen2.5:3b-instruct` nếu model chưa tồn tại trong Docker volume.

Đổi model local AI:

```bash
LOCAL_LLM_MODEL=llama3.2:3b docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build
```

Xoá dữ liệu runtime của app để build lại Chroma index:

```bash
docker compose down -v
docker compose up --build
```

Nếu đang dùng Ollama trong Docker, lệnh `down -v` cũng xoá model đã pull trong Docker volume. Không dùng `-v` nếu muốn giữ model:

```bash
docker compose -f docker-compose.yml -f docker-compose.ollama.yml down
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up --build
```

### Cài thủ công

Tạo môi trường ảo:

```bash
python -m venv .venv
source .venv/bin/activate
```

Cài thư viện:

```bash
pip install -r requirements.txt
```

Nếu cần chỉnh đường dẫn dữ liệu hoặc cấu hình Local AI, tạo file `.env` dựa trên `.env.example`.

## Chạy ứng dụng

```bash
streamlit run src/app.py
```

Sau đó mở:

```text
http://localhost:8501
```

Khi chạy lần đầu, hệ thống sẽ tự xây dựng vector index từ `data/documents.json`. Index được lưu local trong thư mục `chroma_db/`.

## Lỗi thường gặp

Nếu trên Windows gặp lỗi dạng:

```text
[WinError 32] The process cannot access the file because it is being used by another process: '...\\chroma_db\\chroma.sqlite3'
```

Nguyên nhân thường là một process Streamlit/Python khác vẫn đang giữ file SQLite của ChromaDB. Hãy tắt các cửa sổ Streamlit/Python đang chạy, xoá thư mục `chroma_db/`, rồi chạy lại:

```bash
streamlit run src/app.py
```

Không cần push `chroma_db/` lên GitHub; thư mục này được build lại tự động từ dữ liệu trong `data/`.

## Dùng Local AI với Ollama

Cài Ollama, sau đó tải model mặc định:

```bash
ollama pull qwen2.5:3b-instruct
```

Các biến môi trường mặc định:

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LOCAL_LLM_MODEL=qwen2.5:3b-instruct
LOCAL_QUERY_MODEL=qwen2.5:3b-instruct
LOCAL_ANSWER_MODEL=qwen2.5:3b-instruct
```

Có thể đổi model bằng cách chỉnh `.env` hoặc export biến môi trường trước khi chạy app.

## Kiểm thử backend

Chạy một câu hỏi theo index trong `data/queries.json`:

```bash
python src/test_backend.py --idx 0
```

Chạy toàn bộ bộ câu hỏi:

```bash
python src/test_backend.py
```

Kiểm tra nhanh parser rule-based:

```bash
python - <<'PY'
from src.nl_processor import parse_natural_language_query

q = parse_natural_language_query(
    "Khách C10002 có AML hay hoạt động đáng ngờ không?",
    role="compliance_officer",
)
print(q.to_dict())
PY
```

## Câu hỏi demo

Vai trò `compliance_officer`:

```text
Khách C10002 có AML hay hoạt động đáng ngờ không?
```

Vai trò `risk_analyst`:

```text
Khách C10001 có điểm tín dụng và số lần nợ quá hạn như thế nào?
```

Vai trò `risk_analyst`:

```text
Khách C10004 có mức rủi ro cao hay cần hành động khuyến nghị nào không?
```

## Luồng xử lý bảo mật

```text
Câu hỏi người dùng
-> parser tạo structured query
-> vector search trong ChromaDB
-> lọc document-level access theo role
-> mask các field không được phép xem
-> tạo safe_results
-> Local AI hoặc fallback composer tạo câu trả lời cuối
```

Điểm quan trọng của đồ án là mô hình AI không được nhận dữ liệu thô chưa qua kiểm soát truy cập. Nếu một trường bị cấm theo policy, giá trị thật phải được thay bằng `[MASKED]` trước khi đưa vào câu trả lời hoặc gửi cho Local AI.

## Ghi chú

Đây là hệ thống demo phục vụ seminar/đồ án. Trong môi trường production, role không nên được chọn trực tiếp từ giao diện; role phải đến từ hệ thống xác thực hoặc session đáng tin cậy. Policy truy cập cũng nên được quản lý bởi policy store hoặc policy service đáng tin cậy thay vì phụ thuộc vào dữ liệu không kiểm chứng.
