# Banking Secure RAG Dataset Definition

## 1. Mục đích

Bộ file này dùng để định nghĩa dataset cho đề tài:

**Document-Level and Field-Level Access Control for Vector NoSQL Databases in RAG Systems**

Case study:

**Banking RAG Assistant for Loan and KYC Document Retrieval**

Mục tiêu là chuẩn bị dữ liệu JSON/BSON để đưa vào Vector Database, phục vụ RAG có kiểm soát quyền truy cập theo 2 cấp:

- **Document-level access control**: role nào được retrieve loại tài liệu nào.
- **Field-level masking**: field nào được xem, field nào phải che bằng `[MASKED]`.

---

## 2. Ý nghĩa từng file

| File | Vai trò |
|---|---|
| `roles.json` | Định nghĩa các role trong hệ thống như `teller`, `loan_officer`, `risk_analyst`, `compliance_officer`, `branch_manager`, `admin`. |
| `document_types.json` | Định nghĩa các loại tài liệu ngân hàng như `loan_application`, `kyc_profile`, `credit_report`, `risk_assessment`, `internal_note`, `compliance_report`, `policy_document`. |
| `schema_definition.json` | Định nghĩa schema chuẩn cho mỗi document: `document_id`, `document_type`, `content`, `metadata`, `field_policy`, `embedding_text`, `embedding`. |
| `field_policy_store.json` | Định nghĩa quyền xem từng field theo từng role. Nếu role không có quyền thì field phải bị mask. |
| `permission_matrix.md` | Bảng tổng hợp quyền truy cập theo role, dùng để đưa vào báo cáo hoặc slide. |

---

## 3. Luồng liên kết giữa các file

```text
roles.json
        ↓
document_types.json
        ↓
schema_definition.json
        ↓
field_policy_store.json
        ↓
permission_matrix.md
```

Cách hiểu:

- `roles.json` định nghĩa danh sách role hợp lệ.
- `document_types.json` dùng các role đó để khai báo role nào được `allow`, `partial`, hoặc `deny` với từng loại document.
- `schema_definition.json` quy định document thật phải có cấu trúc như thế nào.
- `field_policy_store.json` quy định field nào role nào được xem.
- `permission_matrix.md` là bản tóm tắt dễ đọc cho báo cáo.

---

## 4. Quy tắc quan trọng khi generate dataset

Khi tạo `documents.json`, mỗi document cần có:

```json
{
  "document_id": "loan_001",
  "document_type": "loan_application",
  "customer_id": "C10001",
  "title": "...",
  "source": {},
  "content": {},
  "metadata": {},
  "field_policy": {},
  "embedding_text": "...",
  "embedding": null
}
```

Quy tắc quan trọng nhất:

```text
metadata.allowed_roles = full_access_roles + partial_access_roles
```

Không đưa các role trong `denied_roles` vào `metadata.allowed_roles`.

Ví dụ:

```text
loan_application:
full_access_roles = loan_officer, risk_analyst
partial_access_roles = teller, compliance_officer, branch_manager, admin

=> metadata.allowed_roles gồm:
loan_officer, risk_analyst, teller, compliance_officer, branch_manager, admin
```

---

## 5. Quy tắc masking

Sau khi retrieve document:

```text
retrieved document
→ kiểm tra document-level access
→ áp dụng field-level masking
→ tạo safe context
→ gửi vào LLM
```

Không được gửi raw `content` trực tiếp vào LLM.

Quy tắc field:

```text
Nếu role nằm trong field_policy[field_name] → hiển thị field.
Nếu role không nằm trong field_policy[field_name] → thay bằng [MASKED].
Nếu field không được khai báo → mặc định mask.
```

---

## 6. File nào là nguồn chính?

| Nội dung cần lấy | File nguồn chính |
|---|---|
| Danh sách role | `roles.json` |
| Danh sách document type | `document_types.json` |
| Schema document | `schema_definition.json` |
| Quyền xem field | `field_policy_store.json` |
| Bảng trình bày trong báo cáo | `permission_matrix.md` |

Lưu ý: khi code masking, ưu tiên dùng `field_policy_store.json`, không dùng `permission_matrix.md`.

---

## 7. Output tiếp theo cần tạo

Sau bộ file định nghĩa này, người generate dataset cần tạo tiếp:

```text
documents.json
metadata_store.json
queries.json
expected_results.json
```

Trong đó:

- `documents.json`: dữ liệu document giả lập.
- `metadata_store.json`: metadata tách riêng để filter.
- `queries.json`: bộ câu hỏi test theo role.
- `expected_results.json`: ground truth để đánh giá retrieval và masking.

---

## 8. Ghi chú ngắn

Bộ file hiện tại đã đủ để bắt đầu generate dataset. Khi generate, cần đảm bảo:

- Tên role không đổi.
- Tên document type không đổi.
- Field trong `content` phải khớp với `schema_definition.json`.
- `field_policy_ref` phải trỏ đúng policy trong `field_policy_store.json`.
- `embedding` có thể để `null`, nhóm Retrieval sẽ tạo vector sau.
