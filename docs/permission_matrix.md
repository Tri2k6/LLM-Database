# Permission Matrix

Đề tài: Document-Level and Field-Level Access Control for Vector NoSQL Databases in RAG Systems  
Case study: Banking RAG Assistant for Loan and KYC Document Retrieval

Ma trận này mô tả quyền truy cập theo 2 cấp:

1. Document-level access control: role nào được retrieve loại tài liệu nào.
2. Field-level access control: role nào được xem field nào, role nào bị mask.

Ký hiệu:

| Ký hiệu | Ý nghĩa |
|---|---|
| allow | Role được phép truy cập tài liệu ở cấp document |
| partial | Role có thể truy cập tài liệu nhưng một số field sẽ bị mask |
| deny | Role không được truy cập tài liệu |
| policy_only | Role chủ yếu được xem metadata/policy, không mặc định được xem raw customer content |
| view | Field được hiển thị |
| masked | Field bị thay bằng [MASKED] |
| partial | Chỉ được xem trong một số document hoặc theo điều kiện metadata |

---

## 1. Document-Level Access Control Matrix

| Role | loan_application | kyc_profile | credit_report | risk_assessment | internal_note | compliance_report | policy_document |
|---|---|---|---|---|---|---|---|
| teller | partial | allow | deny | deny | deny | deny | partial |
| loan_officer | allow | allow | partial | deny | deny | deny | partial |
| risk_analyst | allow | partial | allow | allow | partial | deny | partial |
| compliance_officer | partial | allow | partial | partial | partial | allow | allow |
| branch_manager | partial | partial | partial | partial | deny | partial | partial |
| admin | partial/policy_only | partial/policy_only | partial/policy_only | partial/policy_only | partial/policy_only | partial/policy_only | allow |

---

## 2. Document-Level Explanation by Role

### 2.1 Teller

Teller là nhân viên giao dịch tại quầy. Role này chỉ cần xem thông tin cơ bản của khách hàng và trạng thái KYC.

| Document Type | Access | Explanation |
|---|---|---|
| loan_application | partial | Có thể xem thông tin cơ bản nếu cần hỗ trợ khách hàng, nhưng không xem số tiền vay, thu nhập, credit score hoặc risk note |
| kyc_profile | allow | Được xem thông tin KYC cơ bản |
| credit_report | deny | Không được xem báo cáo tín dụng |
| risk_assessment | deny | Không được xem đánh giá rủi ro |
| internal_note | deny | Không được xem ghi chú nội bộ |
| compliance_report | deny | Không được xem báo cáo tuân thủ |
| policy_document | partial | Có thể xem tên chính sách và ngày hiệu lực |

### 2.2 Loan Officer

Loan Officer là nhân viên tín dụng, cần xem thông tin hồ sơ vay và thông tin thu nhập để xử lý khoản vay.

| Document Type | Access | Explanation |
|---|---|---|
| loan_application | allow | Được xem hồ sơ vay |
| kyc_profile | allow | Được xem trạng thái KYC để kiểm tra điều kiện vay |
| credit_report | partial | Có thể xem một số thông tin tín dụng tổng quan, nhưng không xem toàn bộ chi tiết nhạy cảm |
| risk_assessment | deny | Không được xem báo cáo rủi ro nội bộ |
| internal_note | deny | Không được xem ghi chú nội bộ |
| compliance_report | deny | Không được xem báo cáo tuân thủ |
| policy_document | partial | Có thể xem chính sách liên quan đến xử lý khoản vay |

### 2.3 Risk Analyst

Risk Analyst là nhân viên phân tích rủi ro, cần xem dữ liệu tín dụng và rủi ro.

| Document Type | Access | Explanation |
|---|---|---|
| loan_application | allow | Được xem hồ sơ vay để phân tích rủi ro |
| kyc_profile | partial | Chỉ cần xem một phần thông tin KYC |
| credit_report | allow | Được xem báo cáo tín dụng |
| risk_assessment | allow | Được xem báo cáo đánh giá rủi ro |
| internal_note | partial | Có thể xem một số ghi chú liên quan đến rủi ro |
| compliance_report | deny | Không mặc định được xem báo cáo tuân thủ |
| policy_document | partial | Có thể xem chính sách liên quan đến risk/credit |

### 2.4 Compliance Officer

Compliance Officer là nhân viên tuân thủ, cần xem KYC, AML, audit và báo cáo tuân thủ.

| Document Type | Access | Explanation |
|---|---|---|
| loan_application | partial | Có thể xem một số thông tin phục vụ kiểm tra tuân thủ |
| kyc_profile | allow | Được xem hồ sơ KYC |
| credit_report | partial | Có thể xem một phần nếu phục vụ kiểm tra |
| risk_assessment | partial | Có thể xem fraud signal nhưng không xem toàn bộ risk note |
| internal_note | partial | Có thể xem một số ghi chú liên quan đến audit/compliance |
| compliance_report | allow | Được xem báo cáo tuân thủ |
| policy_document | allow | Được xem chính sách nội bộ |

### 2.5 Branch Manager

Branch Manager là quản lý chi nhánh, cần xem thông tin tổng quan của khách hàng trong chi nhánh.

| Document Type | Access | Explanation |
|---|---|---|
| loan_application | partial | Xem tổng quan hồ sơ vay trong chi nhánh |
| kyc_profile | partial | Xem trạng thái KYC cơ bản |
| credit_report | partial | Xem tổng quan, không xem chi tiết nhạy cảm |
| risk_assessment | partial | Xem risk level, không xem risk note chi tiết |
| internal_note | deny | Không được xem ghi chú nội bộ |
| compliance_report | partial | Xem trạng thái tuân thủ tổng quan |
| policy_document | partial | Xem chính sách liên quan đến quản lý chi nhánh |

### 2.6 Admin

Admin là quản trị hệ thống. Trong mô hình zero-trust, admin không mặc định được xem toàn bộ nội dung khách hàng.

| Document Type | Access | Explanation |
|---|---|---|
| loan_application | policy_only | Quản lý schema, metadata, policy; không mặc định xem raw content |
| kyc_profile | policy_only | Quản lý metadata/policy; không mặc định xem dữ liệu cá nhân |
| credit_report | policy_only | Quản lý metadata/policy; không mặc định xem điểm tín dụng |
| risk_assessment | policy_only | Quản lý metadata/policy; không mặc định xem risk note |
| internal_note | policy_only | Quản lý metadata/policy; không mặc định xem ghi chú nội bộ |
| compliance_report | policy_only | Quản lý metadata/policy; không mặc định xem audit note |
| policy_document | allow | Được xem tài liệu chính sách hệ thống |

---

## 3. Field-Level Access Control Matrix

| Field | Teller | Loan Officer | Risk Analyst | Compliance Officer | Branch Manager | Admin |
|---|---|---|---|---|---|---|
| customer_name | view | view | view | view | view | masked |
| national_id_masked | view | view | masked | view | masked | masked |
| date_of_birth | masked | view | masked | view | masked | masked |
| address | masked | view | masked | view | masked | masked |
| phone_masked | view | view | masked | view | masked | masked |
| email_masked | masked | view | masked | view | masked | masked |
| kyc_status | view | view | view | view | view | masked |
| aml_status | masked | masked | masked | view | masked | masked |
| loan_amount | masked | view | view | masked | view | masked |
| loan_purpose | masked | view | view | masked | view | masked |
| income | masked | view | view | masked | masked | masked |
| employment_status | masked | view | view | masked | masked | masked |
| requested_term_months | masked | view | view | masked | view | masked |
| collateral_type | masked | view | view | masked | masked | masked |
| application_status | masked | view | view | masked | view | masked |
| credit_score | masked | masked | view | masked | masked | masked |
| debt_ratio | masked | view | view | masked | masked | masked |
| overdue_count | masked | masked | view | masked | masked | masked |
| credit_history_summary | masked | masked | view | masked | masked | masked |
| active_loans | masked | view | view | masked | view | masked |
| total_debt | masked | masked | view | masked | masked | masked |
| risk_level | masked | masked | view | masked | view | masked |
| risk_score | masked | masked | view | masked | masked | masked |
| risk_note | masked | masked | view | masked | masked | masked |
| fraud_signal | masked | masked | view | view | masked | masked |
| analyst_comment | masked | masked | view | masked | masked | masked |
| recommended_action | masked | masked | view | masked | view | masked |
| staff_note | masked | masked | view | view | masked | masked |
| escalation_reason | masked | masked | view | view | masked | masked |
| internal_decision | masked | masked | view | masked | masked | masked |
| follow_up_required | masked | masked | view | view | masked | masked |
| compliance_status | masked | masked | masked | view | view | masked |
| suspicious_activity_flag | masked | masked | masked | view | masked | masked |
| audit_note | masked | masked | masked | view | masked | masked |
| review_result | masked | masked | masked | view | view | masked |
| policy_title | view | view | view | view | view | view |
| effective_date | view | view | view | view | view | view |
| policy_content | masked | view | view | view | view | view |
| department_owner | masked | view | view | view | view | view |
| policy_version | masked | view | view | view | view | view |
| review_cycle | masked | masked | masked | view | view | view |
| related_document_types | masked | view | view | view | view | view |

---

## 4. Example Access Scenarios

### Scenario 1: Teller hỏi KYC status

Query:

```text
Show KYC status of customer C10001