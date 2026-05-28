import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from functools import cache
from typing import Any

from src.config import DEFAULT_TOP_K, DOCUMENT_TYPES, QUERIES_PATH, ROLES, SENSITIVITY_LEVELS


CUSTOMER_ID_PATTERNS = [
    re.compile(r"\bC[\s_-]?(\d{4,})\b", re.IGNORECASE),
    re.compile(r"\bcustomer\s*(?:id)?\s*(\d{4,})\b", re.IGNORECASE),
    re.compile(r"\bkhach\s*(?:hang)?\s*(?:ma\s*)?(\d{4,})\b", re.IGNORECASE),
]

BRANCH_ID_PATTERNS = [
    re.compile(r"\bBR[\s_-]?(\d{3})\b", re.IGNORECASE),
    re.compile(r"\bbranch\s*(?:id)?\s*(\d{3})\b", re.IGNORECASE),
    re.compile(r"\bchi\s*nhanh\s*(\d{3})\b", re.IGNORECASE),
]

TOP_K_PATTERNS = [
    re.compile(r"\btop\s*k?\s*(\d{1,2})\b", re.IGNORECASE),
    re.compile(r"\b(\d{1,2})\s*(?:tai lieu|ket qua|documents?|results?)\b", re.IGNORECASE),
]

ROLE_KEYWORDS = {
    "teller": ["teller", "giao dich vien", "nhan vien giao dich"],
    "loan_officer": ["loan officer", "nhan vien tin dung", "can bo tin dung"],
    "risk_analyst": ["risk analyst", "phan tich rui ro", "nhan vien rui ro"],
    "compliance_officer": ["compliance officer", "nhan vien tuan thu", "aml officer"],
    "branch_manager": ["branch manager", "quan ly chi nhanh", "giam doc chi nhanh"],
    "admin": ["admin", "administrator", "quan tri", "quan tri vien"],
}

DOCUMENT_TYPE_KEYWORDS = {
    "loan_application": [
        "loan",
        "khoan vay",
        "ho so vay",
        "vay von",
        "dang ky vay",
        "loan application",
        "loan info",
    ],
    "kyc_profile": [
        "kyc",
        "xac minh",
        "dinh danh",
        "ho so dinh danh",
        "identity",
        "verified",
        "verification",
    ],
    "credit_report": [
        "credit",
        "diem tin dung",
        "bao cao tin dung",
        "no qua han",
        "overdue",
        "debt",
        "credit report",
    ],
    "risk_assessment": [
        "risk",
        "rui ro",
        "fraud",
        "gian lan",
        "risk assessment",
        "khuyen nghi",
        "recommended action",
    ],
    "internal_note": [
        "internal",
        "noi bo",
        "ghi chu noi bo",
        "staff note",
        "internal note",
        "internal decision",
    ],
    "compliance_report": [
        "compliance",
        "tuan thu",
        "aml",
        "suspicious",
        "dang ngo",
        "audit",
        "bao cao tuan thu",
    ],
    "policy_document": [
        "policy",
        "chinh sach",
        "quy dinh",
        "policy document",
        "quy trinh",
    ],
}

FIELD_KEYWORDS = {
    "customer_name": ["customer name", "ten khach", "ten khach hang", "ho ten"],
    "national_id_masked": ["national id", "cccd", "cmnd", "so dinh danh"],
    "date_of_birth": ["date of birth", "ngay sinh", "dob"],
    "address": ["address", "dia chi"],
    "phone_masked": ["phone", "so dien thoai", "sdt"],
    "email_masked": ["email"],
    "kyc_status": ["kyc status", "trang thai kyc", "xac minh", "verified"],
    "aml_status": ["aml", "aml status", "chong rua tien"],
    "loan_amount": ["loan amount", "so tien vay", "khoan vay", "han muc vay"],
    "loan_purpose": ["loan purpose", "muc dich vay", "vay de lam gi"],
    "income": ["income", "thu nhap", "luong"],
    "employment_status": ["employment", "viec lam", "nghe nghiep"],
    "requested_term_months": ["term", "thoi han vay", "ky han", "so thang vay"],
    "collateral_type": ["collateral", "tai san dam bao", "the chap"],
    "application_status": ["application status", "trang thai ho so", "tinh trang ho so"],
    "credit_score": ["credit score", "diem tin dung"],
    "debt_ratio": ["debt ratio", "ty le no"],
    "overdue_count": ["overdue", "no qua han", "so lan qua han"],
    "credit_history_summary": ["credit history", "lich su tin dung"],
    "active_loans": ["active loans", "khoan vay dang hoat dong"],
    "total_debt": ["total debt", "tong no"],
    "risk_level": ["risk level", "muc rui ro", "cap do rui ro"],
    "risk_score": ["risk score", "diem rui ro"],
    "risk_note": ["risk note", "ghi chu rui ro"],
    "fraud_signal": ["fraud", "fraud signal", "tin hieu gian lan", "gian lan"],
    "analyst_comment": ["analyst comment", "nhan xet phan tich"],
    "recommended_action": ["recommended action", "khuyen nghi", "hanh dong de xuat"],
    "staff_note": ["staff note", "ghi chu nhan vien"],
    "escalation_reason": ["escalation", "ly do leo thang"],
    "internal_decision": ["internal decision", "quyet dinh noi bo"],
    "follow_up_required": ["follow up", "can theo doi"],
    "follow_up_date": ["follow up date", "ngay theo doi"],
    "compliance_status": ["compliance status", "trang thai tuan thu"],
    "suspicious_activity_flag": ["suspicious", "hoat dong dang ngo"],
    "audit_note": ["audit note", "ghi chu audit", "ghi chu kiem toan"],
    "review_result": ["review result", "ket qua review", "ket qua danh gia"],
    "policy_title": ["policy title", "ten chinh sach"],
    "effective_date": ["effective date", "ngay hieu luc"],
    "policy_content": ["policy content", "noi dung chinh sach"],
    "department_owner": ["department owner", "phong ban so huu"],
    "policy_version": ["policy version", "phien ban chinh sach"],
    "review_cycle": ["review cycle", "chu ky review"],
    "related_document_types": ["related document", "tai lieu lien quan"],
}

FIELD_DOCUMENT_TYPES = {
    "customer_name": ["loan_application", "kyc_profile", "credit_report", "risk_assessment", "compliance_report"],
    "national_id_masked": ["kyc_profile"],
    "date_of_birth": ["kyc_profile"],
    "address": ["kyc_profile"],
    "phone_masked": ["kyc_profile"],
    "email_masked": ["kyc_profile"],
    "kyc_status": ["loan_application", "kyc_profile"],
    "aml_status": ["kyc_profile", "compliance_report"],
    "loan_amount": ["loan_application"],
    "loan_purpose": ["loan_application"],
    "income": ["loan_application"],
    "employment_status": ["loan_application"],
    "requested_term_months": ["loan_application"],
    "collateral_type": ["loan_application"],
    "application_status": ["loan_application"],
    "credit_score": ["credit_report", "loan_application"],
    "debt_ratio": ["credit_report"],
    "overdue_count": ["credit_report"],
    "credit_history_summary": ["credit_report"],
    "active_loans": ["credit_report"],
    "total_debt": ["credit_report"],
    "risk_level": ["risk_assessment"],
    "risk_score": ["risk_assessment"],
    "risk_note": ["risk_assessment", "loan_application"],
    "fraud_signal": ["risk_assessment", "compliance_report"],
    "analyst_comment": ["risk_assessment"],
    "recommended_action": ["risk_assessment"],
    "staff_note": ["internal_note"],
    "escalation_reason": ["internal_note"],
    "internal_decision": ["internal_note"],
    "follow_up_required": ["internal_note"],
    "follow_up_date": ["internal_note"],
    "compliance_status": ["compliance_report"],
    "suspicious_activity_flag": ["compliance_report"],
    "audit_note": ["compliance_report"],
    "review_result": ["compliance_report"],
    "policy_title": ["policy_document"],
    "effective_date": ["policy_document"],
    "policy_content": ["policy_document"],
    "department_owner": ["policy_document"],
    "policy_version": ["policy_document"],
    "review_cycle": ["policy_document"],
    "related_document_types": ["policy_document"],
}

DEFAULT_FIELDS_BY_DOCUMENT_TYPE = {
    "loan_application": ["customer_name", "loan_amount", "loan_purpose", "income", "kyc_status", "application_status"],
    "kyc_profile": ["customer_name", "national_id_masked", "phone_masked", "kyc_status", "aml_status", "last_verified_at"],
    "credit_report": ["customer_name", "credit_score", "overdue_count", "credit_history_summary", "total_debt"],
    "risk_assessment": ["customer_name", "risk_level", "risk_score", "risk_note", "fraud_signal", "recommended_action"],
    "internal_note": ["customer_name", "staff_note", "escalation_reason", "internal_decision", "follow_up_required"],
    "compliance_report": ["customer_name", "compliance_status", "suspicious_activity_flag", "audit_note", "aml_status", "review_result"],
    "policy_document": ["policy_title", "effective_date", "policy_content", "department_owner", "policy_version"],
}

BROAD_QUERY_KEYWORDS = [
    "show",
    "xem",
    "cho toi",
    "thong tin",
    "tong quan",
    "summary",
    "tom tat",
    "kiem tra",
    "check",
]

SUMMARY_DOCUMENT_TYPES = [
    "loan_application",
    "kyc_profile",
    "credit_report",
    "risk_assessment",
    "compliance_report",
]

COMPOSITE_INTENTS = [
    {
        "keywords": ["aml", "suspicious", "dang ngo", "hoat dong dang ngo", "chong rua tien"],
        "document_types": ["kyc_profile", "compliance_report", "risk_assessment"],
        "fields": [
            "aml_status",
            "suspicious_activity_flag",
            "fraud_signal",
            "audit_note",
            "compliance_status",
            "review_result",
        ],
    }
]

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "about",
    "cho",
    "cua",
    "co",
    "customer",
    "hang",
    "khach",
    "la",
    "of",
    "show",
    "the",
    "toi",
    "ve",
    "xem",
}


@dataclass
class StructuredQuery:
    original_text: str
    role: str
    customer_id: str | None
    branch_id: str | None
    top_k: int
    query_type: str
    target_document_types: list[str]
    requested_fields: list[str]
    metadata_filters: dict[str, str]
    retrieval_text: str
    confidence: float
    notes: list[str]
    template_query_id: str | None = None
    template_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_natural_language_query(
    text: str,
    role: str,
    default_branch_id: str | None = None,
    selected_document_type: str | None = None,
    selected_sensitivity: str | None = None,
    top_k: int | None = None,
) -> StructuredQuery:
    if role not in ROLES:
        raise ValueError(f"Unknown role: {role}")

    normalized = normalize_text(text)
    notes: list[str] = []

    mentioned_roles = _detect_role_mentions(normalized)
    ignored_roles = [r for r in mentioned_roles if r != role]
    if ignored_roles:
        notes.append(
            "Ignored role mentioned in the question; the trusted role comes from the current session."
        )

    customer_id = _extract_customer_id(text)
    branch_id = _extract_branch_id(text) or default_branch_id
    requested_top_k = _extract_top_k(normalized) or top_k or DEFAULT_TOP_K
    requested_top_k = max(1, min(10, requested_top_k))

    requested_fields = _infer_requested_fields(normalized)
    target_document_types = _infer_document_types(normalized, requested_fields)
    composite_document_types, composite_fields = _infer_composite_intent(normalized)
    target_document_types.extend(composite_document_types)
    requested_fields.extend(composite_fields)

    template_query, template_score = _match_query_template(normalized)
    if template_query:
        if not target_document_types:
            target_document_types = list(template_query.get("target_document_types") or [])
            notes.append(f"Used nearest query template {template_query['query_id']} for document types.")
        if not requested_fields:
            requested_fields = list(template_query.get("requested_fields") or [])
            notes.append(f"Used nearest query template {template_query['query_id']} for requested fields.")

    if selected_document_type:
        target_document_types = [selected_document_type]
        notes.append("Sidebar document type filter overrides document types inferred from text.")

    target_document_types = _unique_valid(target_document_types, DOCUMENT_TYPES)
    requested_fields = _unique(requested_fields)

    if _is_broad_query(normalized) and target_document_types and not requested_fields:
        requested_fields = _default_fields_for(target_document_types)

    if _is_summary_query(normalized) and not selected_document_type:
        target_document_types = SUMMARY_DOCUMENT_TYPES.copy()
        requested_fields = _unique(requested_fields + _default_fields_for(target_document_types))

    metadata_filters: dict[str, str] = {}
    if branch_id:
        metadata_filters["branch_id"] = branch_id
    if selected_sensitivity:
        if selected_sensitivity in SENSITIVITY_LEVELS:
            metadata_filters["sensitivity"] = selected_sensitivity
        else:
            notes.append(f"Ignored invalid sensitivity filter: {selected_sensitivity}")

    if not customer_id:
        notes.append("No customer_id detected. Retrieval may return broader results.")
    if not target_document_types:
        notes.append("No document type detected. Retrieval will search all allowed document types.")
    if not requested_fields:
        notes.append("No specific field detected. The answer will summarize visible fields from retrieved documents.")

    retrieval_text = _build_retrieval_text(text, customer_id, target_document_types, requested_fields)
    confidence = _estimate_confidence(
        customer_id=customer_id,
        branch_id=branch_id,
        target_document_types=target_document_types,
        requested_fields=requested_fields,
        template_score=template_score,
    )

    return StructuredQuery(
        original_text=text,
        role=role,
        customer_id=customer_id,
        branch_id=branch_id,
        top_k=requested_top_k,
        query_type="natural_language_structured_query",
        target_document_types=target_document_types,
        requested_fields=requested_fields,
        metadata_filters=metadata_filters,
        retrieval_text=retrieval_text,
        confidence=confidence,
        notes=notes,
        template_query_id=template_query["query_id"] if template_query else None,
        template_score=round(template_score, 3),
    )


def normalize_text(text: str) -> str:
    text = text.replace("Đ", "D").replace("đ", "d")
    decomposed = unicodedata.normalize("NFD", text)
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r"[_/\-]+", " ", ascii_text)
    ascii_text = re.sub(r"\s+", " ", ascii_text)
    return ascii_text.strip()


def _extract_customer_id(text: str) -> str | None:
    for pattern in CUSTOMER_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"C{match.group(1)}"
    return None


def _extract_branch_id(text: str) -> str | None:
    for pattern in BRANCH_ID_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"BR_{match.group(1)}"
    return None


def _extract_top_k(normalized_text: str) -> int | None:
    for pattern in TOP_K_PATTERNS:
        match = pattern.search(normalized_text)
        if match:
            return int(match.group(1))
    return None


def _detect_role_mentions(normalized_text: str) -> list[str]:
    roles = []
    for role, keywords in ROLE_KEYWORDS.items():
        if _contains_any(normalized_text, keywords):
            roles.append(role)
    return roles


def _infer_requested_fields(normalized_text: str) -> list[str]:
    fields = []
    for field, keywords in FIELD_KEYWORDS.items():
        if _contains_any(normalized_text, keywords):
            fields.append(field)
    return fields


def _infer_document_types(normalized_text: str, requested_fields: list[str]) -> list[str]:
    document_types = []
    for document_type, keywords in DOCUMENT_TYPE_KEYWORDS.items():
        if _contains_any(normalized_text, keywords):
            document_types.append(document_type)

    if document_types:
        return document_types

    for field in requested_fields:
        document_types.extend(FIELD_DOCUMENT_TYPES.get(field, []))

    return document_types


def _is_broad_query(normalized_text: str) -> bool:
    return _contains_any(normalized_text, BROAD_QUERY_KEYWORDS)


def _is_summary_query(normalized_text: str) -> bool:
    return _contains_any(normalized_text, ["tong quan", "tom tat", "summary", "branch summary"])


def _infer_composite_intent(normalized_text: str) -> tuple[list[str], list[str]]:
    document_types: list[str] = []
    fields: list[str] = []
    for intent in COMPOSITE_INTENTS:
        if _contains_any(normalized_text, intent["keywords"]):
            document_types.extend(intent["document_types"])
            fields.extend(intent["fields"])
    return document_types, fields


def _default_fields_for(document_types: list[str]) -> list[str]:
    fields = []
    for document_type in document_types:
        fields.extend(DEFAULT_FIELDS_BY_DOCUMENT_TYPE.get(document_type, []))
    return _unique(fields)


def _build_retrieval_text(
    original_text: str,
    customer_id: str | None,
    document_types: list[str],
    requested_fields: list[str],
) -> str:
    parts = [original_text]
    if customer_id:
        parts.append(customer_id)
    parts.extend(document_types)
    parts.extend(requested_fields)
    return " ".join(parts)


def _estimate_confidence(
    customer_id: str | None,
    branch_id: str | None,
    target_document_types: list[str],
    requested_fields: list[str],
    template_score: float,
) -> float:
    score = 0.15
    if customer_id:
        score += 0.25
    if branch_id:
        score += 0.1
    if target_document_types:
        score += 0.25
    if requested_fields:
        score += 0.15
    score += min(template_score, 0.5) * 0.2
    return round(min(score, 0.95), 2)


def _contains_any(normalized_text: str, keywords: list[str]) -> bool:
    return any(normalize_text(keyword) in normalized_text for keyword in keywords)


def _unique(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _unique_valid(values: list[str], allowed_values: list[str]) -> list[str]:
    allowed = set(allowed_values)
    return [value for value in _unique(values) if value in allowed]


def _tokens(normalized_text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalized_text)
        if len(token) > 1 and token not in STOPWORDS
    }


@cache
def _load_query_templates() -> list[dict[str, Any]]:
    if not QUERIES_PATH.exists():
        return []
    with open(QUERIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _match_query_template(normalized_text: str) -> tuple[dict[str, Any] | None, float]:
    input_tokens = _tokens(normalized_text)
    if not input_tokens:
        return None, 0.0

    best_query = None
    best_score = 0.0
    for query in _load_query_templates():
        template_tokens = _tokens(normalize_text(query.get("query", "")))
        if not template_tokens:
            continue

        overlap = len(input_tokens & template_tokens)
        union = len(input_tokens | template_tokens)
        score = overlap / union if union else 0.0

        if score > best_score:
            best_query = query
            best_score = score

    if best_score < 0.18:
        return None, best_score
    return best_query, best_score
