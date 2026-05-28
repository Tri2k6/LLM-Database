Người thứ 2 không cần định nghĩa lại role/schema/policy nữa. Người này chỉ cần **dựa trên 5 file của bạn để tạo dataset thật và bộ test**.

## Nhiệm vụ của người thứ 2

Người thứ 2 phụ trách phần **generate data + query test + expected result**.

Cụ thể cần làm 4 file chính:

```text
documents.json
metadata_store.json
queries.json
expected_results.json
```

## 1. Tạo `documents.json`

Dựa vào:

```text
schema_definition.json
document_types.json
field_policy_store.json
roles.json
```

để sinh dữ liệu giả lập ngân hàng.

Mỗi document phải có đủ:

```json
{
  "document_id": "...",
  "document_type": "...",
  "customer_id": "...",
  "title": "...",
  "source": {},
  "content": {},
  "metadata": {},
  "field_policy": {},
  "embedding_text": "...",
  "embedding": null
}
```

Số lượng nên làm:

```text
Tối thiểu: 200 documents
Tốt hơn: 300–500 documents
```

Phân bố theo `document_types.json`: loan, KYC, credit report, risk assessment, internal note, compliance report, policy document.

## 2. Tạo `metadata_store.json`

File này tách riêng metadata của từng document để nhóm retrieval dùng filter.

Ví dụ:

```json
{
  "document_id": "loan_001",
  "document_type": "loan_application",
  "customer_id": "C10001",
  "department": "credit",
  "sensitivity": "high",
  "allowed_roles": [
    "loan_officer",
    "risk_analyst",
    "teller",
    "compliance_officer",
    "branch_manager",
    "admin"
  ],
  "branch_id": "BR_001",
  "region": "HCM",
  "field_policy_ref": "policy_loan_application_v1"
}
```

Quy tắc quan trọng nhất:

```text
metadata.allowed_roles = full_access_roles + partial_access_roles
```

Không được đưa `denied_roles` vào `allowed_roles`.

## 3. Tạo `queries.json`

Tạo tập câu hỏi để test hệ thống RAG.

Mỗi query nên có:

```json
{
  "query_id": "q_001",
  "role": "loan_officer",
  "query": "Show loan information of customer C10001",
  "customer_id": "C10001",
  "branch_id": "BR_001",
  "top_k": 5
}
```

Nên có khoảng:

```text
Tối thiểu: 30–50 queries
Tốt hơn: 80–100 queries
```

Query phải có nhiều tình huống:

```text
Role được xem tài liệu
Role bị chặn tài liệu
Role được xem document nhưng bị mask field
Cùng một query nhưng role khác nhau
Query cần metadata filtering theo branch/department/sensitivity
```

## 4. Tạo `expected_results.json`

Đây là ground truth để nhóm demo đánh giá đúng/sai.

Mỗi query cần biết:

```json
{
  "query_id": "q_001",
  "expected_allowed_documents": ["loan_001", "kyc_001"],
  "expected_blocked_documents": ["risk_001", "internal_001"],
  "expected_visible_fields": ["customer_name", "loan_amount", "income", "kyc_status"],
  "expected_masked_fields": ["credit_score", "risk_note", "fraud_signal"],
  "expected_behavior": "Return loan and KYC information, but mask risk-related fields."
}
```

File này dùng để tính:

```text
Unauthorized Retrieval Rate
Field Leakage Rate
Precision@5
Recall@5
Answer Safety Rate
```

## 5. Có thể viết thêm script hỗ trợ

Nếu có thời gian, người thứ 2 nên viết thêm:

```text
generate_documents.py
validate_dataset.py
```

`generate_documents.py` dùng để sinh data tự động.

`validate_dataset.py` dùng để kiểm tra:

```text
document_id có trùng không
document_type có hợp lệ không
role có đúng không
field_policy_ref có tồn tại không
metadata.allowed_roles có đúng không
embedding_text có rỗng không
```

## Câu mô tả ngắn để gửi người thứ 2

Bạn có thể gửi nguyên đoạn này:

> Phần của bạn là tạo dataset thật dựa trên các file định nghĩa đã có. Cụ thể, bạn cần generate `documents.json`, tách metadata thành `metadata_store.json`, tạo bộ câu hỏi test trong `queries.json`, và tạo ground truth trong `expected_results.json`. Khi generate document, phải tuân theo `schema_definition.json`, lấy loại tài liệu từ `document_types.json`, lấy field policy từ `field_policy_store.json`, và lấy role/quyền từ `roles.json`. Quan trọng nhất là `metadata.allowed_roles` phải bằng `full_access_roles + partial_access_roles`, không được thêm `denied_roles`. Mục tiêu là tạo data đủ để test document-level access control và field-level masking trong RAG.
