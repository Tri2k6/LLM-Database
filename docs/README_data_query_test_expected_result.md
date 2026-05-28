# README - data + query test + expected result
## 1. Mô tả
Bộ output này được sinh dựa trên các file định nghĩa ban đầu:

- `schema_definition.json`
- `roles.json`
- `document_types.json`
- `field_policy_store.json`
- `permission_matrix.md`

---

## 2. Danh sách file output

| File | Mục đích |
|---|---|
| `documents.json` | Chứa dữ liệu tài liệu ngân hàng giả lập để đưa vào Vector NoSQL Database hoặc pipeline RAG. |
| `metadata_store.json` | Chứa metadata tách riêng từ `documents.json`, dùng cho metadata filtering và document-level access control. |
| `queries.json` | Chứa bộ câu hỏi test theo từng role, customer, branch và metadata filter. |
| `expected_results.json` | Chứa ground truth cho từng query, gồm tài liệu được phép trả về, tài liệu bị chặn, field được xem và field bị mask. |
| `generation_summary.json` | Tóm tắt số lượng file, số lượng record, phân bố document type và trạng thái validate. |

---

## 3. Thống kê dataset

Dataset được sinh với random seed cố định:

```text
random_seed = 20260524
```

Tổng số record:

| Loại dữ liệu | Số lượng |
|---|---:|
| Documents | 500 |
| Metadata records | 500 |
| Queries | 100 |
| Expected results | 100 |

Phân bố document theo loại:

| Document type | Số lượng |
|---|---:|
| `loan_application` | 100 |
| `kyc_profile` | 100 |
| `credit_report` | 80 |
| `risk_assessment` | 80 |
| `internal_note` | 60 |
| `compliance_report` | 50 |
| `policy_document` | 30 |

---

## 4. Cấu trúc `documents.json`

Mỗi document có cấu trúc chuẩn:

```json
{
  "document_id": "loan_001",
  "document_type": "loan_application",
  "customer_id": "C10001",
  "title": "Loan Application for customer C10001",
  "source": {},
  "content": {},
  "metadata": {},
  "field_policy": {},
  "embedding_text": "...",
  "embedding": null
}
```

Ý nghĩa chính:

- `document_id`: ID duy nhất của document.
- `document_type`: loại tài liệu, ví dụ `loan_application`, `kyc_profile`, `credit_report`.
- `customer_id`: mã khách hàng giả lập, ví dụ `C10001`. Với `policy_document`, trường này có thể là `null`.
- `content`: nội dung nghiệp vụ của document.
- `metadata`: metadata phục vụ filtering và phân quyền.
- `field_policy`: quyền xem từng field theo từng role.
- `embedding_text`: text dùng để tạo embedding.
- `embedding`: để `null`, nhóm Retrieval có thể generate vector sau.

---

## 5. Cấu trúc `metadata_store.json`

`metadata_store.json` là bản tách riêng metadata từ `documents.json`, giúp nhóm Retrieval filter nhanh hơn mà không cần đọc toàn bộ content.

Ví dụ:

```json
{
  "document_id": "loan_001",
  "document_type": "loan_application",
  "customer_id": "C10001",
  "department": "credit",
  "sensitivity": "high",
  "document_owner": "credit_department",
  "allowed_roles": [
    "loan_officer",
    "risk_analyst",
    "teller",
    "compliance_officer",
    "branch_manager",
    "admin"
  ],
  "allowed_departments": ["credit", "risk", "management"],
  "branch_id": "BR_001",
  "region": "HCM",
  "retention_level": "standard",
  "field_policy_ref": "policy_loan_application_v1",
  "access_tags": ["loan", "credit", "customer_data", "loan_application"]
}
```

Quy tắc quan trọng:

```text
metadata.allowed_roles = full_access_roles + partial_access_roles
```

Không đưa role nằm trong `denied_roles` vào `metadata.allowed_roles`.

---

## 6. Cấu trúc `queries.json`

Mỗi query mô phỏng một request từ một role cụ thể.

Ví dụ:

```json
{
  "query_id": "q_001",
  "role": "loan_officer",
  "query": "Show loan information of customer C10001",
  "customer_id": "C10001",
  "branch_id": "BR_001",
  "top_k": 5,
  "query_type": "role_access_and_masking",
  "target_document_types": ["loan_application"],
  "requested_fields": [
    "customer_name",
    "loan_amount",
    "loan_purpose",
    "income",
    "kyc_status",
    "credit_score",
    "risk_note"
  ],
  "metadata_filters": {
    "branch_id": "BR_001"
  }
}
```

Các tình huống test được bao phủ:

- Role được phép xem document.
- Role bị chặn ở document-level.
- Role được retrieve document nhưng một số field bị mask.
- Cùng một query/customer nhưng đổi role để so sánh quyền.
- Query có metadata filtering theo `branch_id`, `department`, `sensitivity`.

---

## 7. Cấu trúc `expected_results.json`

Mỗi expected result là ground truth tương ứng với một query trong `queries.json`.

Ví dụ:

```json
{
  "query_id": "q_001",
  "expected_allowed_documents": ["loan_001"],
  "expected_blocked_documents": [],
  "expected_visible_fields": [
    "customer_name",
    "income",
    "kyc_status",
    "loan_amount",
    "loan_purpose"
  ],
  "expected_masked_fields": [
    "credit_score",
    "risk_note"
  ],
  "per_document_field_expectations": [
    {
      "document_id": "loan_001",
      "document_type": "loan_application",
      "visible_fields": [
        "customer_name",
        "loan_amount",
        "loan_purpose",
        "income",
        "kyc_status"
      ],
      "masked_fields": [
        "credit_score",
        "risk_note"
      ]
    }
  ],
  "expected_behavior": "Return authorized documents after document-level filtering and mask unauthorized fields before LLM context.",
  "evaluation_targets": [
    "Unauthorized Retrieval Rate",
    "Field Leakage Rate",
    "Precision@5",
    "Recall@5",
    "Answer Safety Rate"
  ]
}
```

File này dùng để đánh giá hệ thống Retrieval/RAG có trả đúng tài liệu và mask đúng field hay không.

---

## 8. Luồng kiểm thử gợi ý

Pipeline demo có thể dùng bộ file này theo luồng sau:

```text
queries.json
    ↓
metadata_store.json để filter document-level
    ↓
documents.json để lấy content của document được phép
    ↓
field_policy trong document hoặc field_policy_store.json để mask field
    ↓
so sánh kết quả với expected_results.json
```

Các bước cụ thể:

1. Đọc một query từ `queries.json`.
2. Lấy `role`, `customer_id`, `branch_id`, `target_document_types`, `metadata_filters`.
3. Filter `metadata_store.json` theo:
   - `customer_id`
   - `document_type`
   - `branch_id` hoặc metadata filter khác
   - role phải nằm trong `allowed_roles`
4. Những document không qua bước trên được xem là blocked document.
5. Với document được phép, lấy nội dung từ `documents.json`.
6. Áp dụng field-level masking:
   - Nếu `role` nằm trong `field_policy[field_name]` thì field được hiển thị.
   - Nếu không, field phải bị thay bằng `[MASKED]`.
7. So sánh output thực tế với `expected_results.json`.

---

## 9. Metric có thể tính

Bộ output này hỗ trợ tính các metric sau:

| Metric | Ý nghĩa |
|---|---|
| Unauthorized Retrieval Rate | Tỷ lệ document không có quyền nhưng vẫn bị retrieve. Càng thấp càng tốt. |
| Field Leakage Rate | Tỷ lệ field đáng lẽ phải mask nhưng bị lộ. Càng thấp càng tốt. |
| Precision@5 | Tỷ lệ document đúng trong top 5 kết quả retrieval. |
| Recall@5 | Tỷ lệ document cần trả về được tìm thấy trong top 5. |
| Answer Safety Rate | Tỷ lệ câu trả lời an toàn, không lộ thông tin ngoài quyền. |

---

## 10. Ghi chú cho nhóm Retrieval/RAG

- `embedding` hiện đang là `null`; nhóm Retrieval cần generate embedding từ `embedding_text`.
- Không nên index trực tiếp các field quá nhạy cảm nếu demo muốn tránh leakage từ embedding.
- Không được gửi raw `content` vào LLM trước khi áp dụng masking.
- Nên dùng `metadata_store.json` để pre-filter trước khi lấy document content.
- Nên dùng `field_policy_store.json` hoặc `field_policy` đi kèm mỗi document làm source of truth cho masking.
- `expected_results.json` là ground truth chính để viết unit test/evaluation script.

---

## 11. Gợi ý validate nhanh bằng Python

Có thể kiểm tra số lượng record bằng đoạn sau:

```python
import json

files = [
    "documents.json",
    "metadata_store.json",
    "queries.json",
    "expected_results.json"
]

for file in files:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(file, len(data))
```

Kết quả mong đợi:

```text
documents.json 500
metadata_store.json 500
queries.json 100
expected_results.json 100
```

---

## 12. Trạng thái

```text
validation_status = passed
```

Dataset đã được kiểm tra cơ bản:

- Không trùng `document_id`.
- `metadata_store.json` khớp với metadata trong `documents.json`.
- Mỗi query có một expected result tương ứng.
- `metadata.allowed_roles` không chứa role bị deny theo document type.
- Các field visible/masked trong expected result được tính theo field policy.
