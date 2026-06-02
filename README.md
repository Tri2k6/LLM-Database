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

Các thư mục như `.venv/`, `chroma_db/`, `Báo cáo/`, `scripts/` và cache Python là dữ liệu local hoặc artifact sinh ra khi chạy, nên không cần đưa lên GitHub.

## Yêu cầu môi trường

- Python 3.10 trở lên.
- Pip và virtual environment.
- Ollama nếu muốn dùng Local AI.

## Cài đặt

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
