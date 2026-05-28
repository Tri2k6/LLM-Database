# Banking Secure RAG Vector Search

Demo RAG ngan hang co kiem soat truy cap theo 2 lop:

- Document-level access control: role nao duoc retrieve tai lieu.
- Field-level masking: field nao role khong duoc xem se thanh `[MASKED]`.

He thong ho tro Local AI qua Ollama de:

- Chuyen cau hoi tieng Viet/Anh thanh structured query.
- Tong hop ket qua vector search thanh cau tra loi tu nhien bang tieng Viet.

Local AI chi nhan `safe_results` da mask, khong nhan raw content chua qua policy.

## Project Structure

```text
.
├── data/                         # Synthetic demo dataset and evaluation files
├── docs/                         # Demo guide, dataset notes, permission matrix
├── schemas/                      # Role, document type, schema, field policy definitions
├── src/                          # Application source code
│   ├── app.py                    # Streamlit UI
│   ├── config.py                 # Paths and constants
│   ├── indexer.py                # Build ChromaDB vector index
│   ├── searcher.py               # Vector search + document-level filtering
│   ├── nl_processor.py           # Deterministic fallback parser
│   ├── llm_services.py           # Ollama local AI parser/answer generator
│   └── answer_composer.py        # Masking and deterministic answer fallback
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
└── .dockerignore
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Optional Local AI

Install Ollama, then pull the lightweight Vietnamese-capable model:

```bash
ollama pull qwen2.5:3b-instruct
```

The app uses this model by default. To use another local model:

```bash
export LOCAL_LLM_MODEL="qwen2.5:7b-instruct"
export LOCAL_QUERY_MODEL="qwen2.5:7b-instruct"
export LOCAL_ANSWER_MODEL="qwen2.5:7b-instruct"
```

## Run

```bash
streamlit run src/app.py
```

Open:

```text
http://localhost:8501
```

The vector index is stored in `chroma_db/` and rebuilt automatically when missing.

## Test

Run one backend query:

```bash
python src/test_backend.py --idx 0
```

Run all predefined queries:

```bash
python src/test_backend.py
```

Parser smoke test:

```bash
python - <<'PY'
from src.nl_processor import parse_natural_language_query

q = parse_natural_language_query(
    "Khach C10002 co AML hay hoat dong dang ngo khong?",
    role="compliance_officer",
)
print(q.to_dict())
PY
```

## Demo Prompts

```text
Khach C10002 co AML hay hoat dong dang ngo khong?
```

Use role `compliance_officer`.

```text
Khach C10001 co diem tin dung va so lan no qua han nhu the nao?
```

Use role `risk_analyst`.

```text
Khach C10004 co muc rui ro cao hay can hanh dong khuyen nghi nao khong?
```

Use role `risk_analyst`.

## Security Notes

This is a seminar/demo implementation. It demonstrates the correct security shape:

```text
retrieve documents
-> check document-level access
-> mask unauthorized fields
-> send only safe_results to Local AI
```

For production, do not let users choose role from the UI. Role must come from trusted authentication/session data. Also avoid trusting policy embedded inside untrusted documents; use a trusted policy store or policy service.
