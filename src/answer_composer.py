from typing import Any


MASK_TOKEN = "[MASKED]"

AML_SUSPICIOUS_FIELDS = {
    "aml_status",
    "suspicious_activity_flag",
    "fraud_signal",
    "compliance_status",
    "review_result",
    "risk_level",
    "audit_note",
}


def mask_content(
    content: dict[str, Any],
    field_policy: dict[str, list[str]],
    role: str,
    requested_fields: list[str] | None = None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    fields = _select_fields(content, requested_fields)
    safe_content: dict[str, Any] = {}
    visible_fields: list[str] = []
    masked_fields: list[str] = []

    for field in fields:
        allowed_roles = field_policy.get(field, [])
        if role in allowed_roles:
            safe_content[field] = content[field]
            visible_fields.append(field)
        else:
            safe_content[field] = MASK_TOKEN
            masked_fields.append(field)

    return safe_content, visible_fields, masked_fields


def build_field_access_table(
    content: dict[str, Any],
    field_policy: dict[str, list[str]],
    role: str,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    rows: list[dict[str, Any]] = []
    visible_fields: list[str] = []
    masked_fields: list[str] = []

    for field, value in content.items():
        allowed_roles = field_policy.get(field, [])
        allowed = role in allowed_roles

        if allowed:
            visible_fields.append(field)
        else:
            masked_fields.append(field)

        rows.append({
            "field": field,
            "value": value if allowed else MASK_TOKEN,
            "access": "view" if allowed else "mask",
            "allowed": allowed,
            "allowed_roles": allowed_roles,
        })

    return rows, visible_fields, masked_fields


def build_safe_results(
    results: list[dict[str, Any]],
    role: str,
    requested_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    safe_results = []
    for result in results:
        content = result.get("content", {})
        field_policy = result.get("field_policy", {})
        field_access_table, all_visible_fields, all_masked_fields = build_field_access_table(
            content=content,
            field_policy=field_policy,
            role=role,
        )
        safe_content, visible_fields, masked_fields = mask_content(
            content=content,
            field_policy=field_policy,
            role=role,
            requested_fields=requested_fields,
        )

        safe_result = {
            key: value
            for key, value in result.items()
            if key not in {"content", "field_policy"}
        }
        safe_result["content"] = safe_content
        safe_result["visible_fields"] = visible_fields
        safe_result["masked_fields"] = masked_fields
        safe_result["field_access_table"] = field_access_table
        safe_result["document_access"] = role in str(
            safe_result.get("metadata", {}).get("allowed_roles", "")
        ).split(",")
        safe_result["access_summary"] = {
            "total_fields": len(content),
            "visible_fields": len(all_visible_fields),
            "masked_fields": len(all_masked_fields),
            "visible_field_names": all_visible_fields,
            "masked_field_names": all_masked_fields,
        }
        safe_results.append(safe_result)

    return safe_results


def compose_answer(
    structured_query: Any,
    safe_results: list[dict[str, Any]],
) -> str:
    query = structured_query.to_dict() if hasattr(structured_query, "to_dict") else structured_query

    if not safe_results:
        return (
            "Không tìm thấy tài liệu phù hợp với role và filter hiện tại.\n\n"
            f"Query đã hiểu: customer_id={query.get('customer_id') or 'N/A'}, "
            f"document_types={query.get('target_document_types') or 'all'}, "
            f"fields={query.get('requested_fields') or 'auto'}, "
            f"metadata_filters={query.get('metadata_filters') or {}}."
        )

    solved = solve_question(query, safe_results)
    lines = [
        f"**Câu trả lời:** {solved['answer']}",
    ]

    if solved["details"]:
        lines.append("")
        lines.append("**Lý do:**")
        lines.extend(f"- {detail}" for detail in solved["details"])

    lines.append("")
    lines.append(
        f"Đã hiểu câu hỏi thành structured query với confidence {query.get('confidence', 0):.2f}; "
        f"dùng {len(safe_results)} tài liệu làm bằng chứng."
    )

    sources = _source_summary(safe_results)
    if sources:
        lines.append("")
        lines.append("**Nguồn bằng chứng:**")
        lines.extend(f"- {source}" for source in sources)

    masked = solved["masked_fields"]
    if masked:
        lines.append("")
        lines.append(
            "Không thể dùng các field bị ẩn theo quyền truy cập: "
            + ", ".join(masked)
            + "."
        )

    notes = query.get("notes") or []
    if notes:
        lines.append("")
        lines.append("Ghi chú xử lý: " + " ".join(notes))

    return "\n".join(lines)


def solve_question(query: dict[str, Any], safe_results: list[dict[str, Any]]) -> dict[str, Any]:
    requested_fields = set(query.get("requested_fields") or [])
    original_text = str(query.get("original_text") or "").lower()

    if _is_aml_or_suspicious_question(original_text, requested_fields):
        return _solve_aml_or_suspicious(query, safe_results)

    return _solve_field_summary(query, safe_results)


def _solve_aml_or_suspicious(
    query: dict[str, Any],
    safe_results: list[dict[str, Any]],
) -> dict[str, Any]:
    records = _visible_records(safe_results, AML_SUSPICIOUS_FIELDS)
    masked_fields = _masked_fields(safe_results, AML_SUSPICIOUS_FIELDS)

    if not records:
        return {
            "answer": (
                f"Không thể kết luận khách hàng {query.get('customer_id') or ''} có AML "
                "hay hoạt động đáng ngờ hay không, vì các field cần thiết đều đang bị mask "
                "theo role hiện tại."
            ),
            "details": [],
            "masked_fields": masked_fields,
        }

    positive_details: list[str] = []
    negative_details: list[str] = []
    neutral_details: list[str] = []
    aml_warning = False
    suspicious_activity = False
    suspicious_activity_clear = False
    fraud_warning = False
    compliance_warning = False
    review_warning = False
    risk_warning = False

    for record in records:
        field = record["field"]
        value = record["value"]
        normalized = _normalize_value(value)
        source = f"{field}={value} trong {record['document_id']}"

        if field == "aml_status":
            if normalized in {"flagged", "under_review", "review", "pending"}:
                aml_warning = True
                positive_details.append(f"AML cần chú ý: {source}.")
            elif normalized in {"clear", "passed", "none"}:
                negative_details.append(f"AML không bị flag: {source}.")
            else:
                neutral_details.append(f"Có thông tin AML: {source}.")
        elif field == "suspicious_activity_flag":
            if _is_truthy(value):
                suspicious_activity = True
                positive_details.append(f"Có cờ hoạt động đáng ngờ: {source}.")
            else:
                suspicious_activity_clear = True
                negative_details.append(f"Không có cờ hoạt động đáng ngờ: {source}.")
        elif field == "fraud_signal":
            if normalized in {"high", "medium"}:
                fraud_warning = True
                positive_details.append(f"Fraud signal cần chú ý: {source}.")
            elif normalized in {"low", "none", "false"}:
                negative_details.append(f"Fraud signal thấp hoặc không có: {source}.")
            else:
                neutral_details.append(f"Có thông tin fraud signal: {source}.")
        elif field == "compliance_status":
            if normalized in {"non_compliant", "needs_review", "under_review"}:
                compliance_warning = True
                positive_details.append(f"Compliance cần xem xét: {source}.")
            elif normalized == "compliant":
                negative_details.append(f"Compliance đang compliant: {source}.")
            else:
                neutral_details.append(f"Có thông tin compliance: {source}.")
        elif field == "review_result":
            if normalized in {"escalated", "requires_follow_up", "follow_up"}:
                review_warning = True
                positive_details.append(f"Kết quả review cần xử lý tiếp: {source}.")
            elif normalized == "passed":
                negative_details.append(f"Kết quả review đã passed: {source}.")
            else:
                neutral_details.append(f"Có kết quả review: {source}.")
        elif field == "risk_level":
            if normalized in {"high", "critical"}:
                risk_warning = True
                positive_details.append(f"Mức rủi ro cao: {source}.")
            elif normalized in {"low", "medium"}:
                negative_details.append(f"Mức rủi ro không cao: {source}.")
            else:
                neutral_details.append(f"Có thông tin risk level: {source}.")
        elif field == "audit_note":
            neutral_details.append(f"Có audit note trong {record['document_id']}.")

    customer_id = query.get("customer_id") or "khách hàng này"
    if suspicious_activity:
        answer = (
            f"Có cờ hoạt động đáng ngờ với {customer_id}. "
            "Kết luận này được suy ra từ các field mà role hiện tại được phép xem."
        )
    elif aml_warning or fraud_warning or compliance_warning or review_warning or risk_warning:
        caveat = (
            " Tuy nhiên, field suspicious_activity_flag đang cho thấy không có cờ hoạt động đáng ngờ trực tiếp."
            if suspicious_activity_clear
            else ""
        )
        answer = (
            f"Có dấu hiệu cần chú ý với {customer_id}, chủ yếu ở AML/compliance/risk. "
            "Hệ thống đã đọc các field được phép xem để suy luận, không chỉ liệt kê vector."
            + caveat
        )
    elif negative_details:
        answer = (
            f"Không thấy dấu hiệu AML hoặc hoạt động đáng ngờ rõ ràng với {customer_id} "
            "trong các field mà role hiện tại được phép xem."
        )
    else:
        answer = (
            f"Có tài liệu liên quan đến AML/hoạt động đáng ngờ của {customer_id}, "
            "nhưng các field thấy được chưa đủ rõ để kết luận có hay không."
        )

    details = positive_details + negative_details + neutral_details
    return {
        "answer": answer,
        "details": details,
        "masked_fields": masked_fields,
    }


def _solve_field_summary(
    query: dict[str, Any],
    safe_results: list[dict[str, Any]],
) -> dict[str, Any]:
    requested_fields = set(query.get("requested_fields") or [])
    records = _visible_records(safe_results, requested_fields or None)
    masked_fields = _masked_fields(safe_results, requested_fields or None)

    if not records:
        return {
            "answer": (
                "Tìm thấy tài liệu liên quan, nhưng không có field nào đủ quyền hiển thị "
                "để trả lời trực tiếp câu hỏi."
            ),
            "details": [],
            "masked_fields": masked_fields,
        }

    customer_id = query.get("customer_id") or "khách hàng"
    details = [
        f"{record['field']}={record['value']} trong {record['document_id']}."
        for record in records[:8]
    ]
    return {
        "answer": f"Tìm thấy thông tin có thể trả lời cho {customer_id} từ các tài liệu được phép xem.",
        "details": details,
        "masked_fields": masked_fields,
    }


def _select_fields(content: dict[str, Any], requested_fields: list[str] | None) -> list[str]:
    if not requested_fields:
        return list(content.keys())

    selected = [field for field in requested_fields if field in content]
    if selected:
        return selected

    return list(content.keys())


def _is_aml_or_suspicious_question(original_text: str, requested_fields: set[str]) -> bool:
    if requested_fields & AML_SUSPICIOUS_FIELDS:
        return True
    return any(
        keyword in original_text
        for keyword in ["aml", "suspicious", "dang ngo", "đáng ngờ", "fraud", "gian lan"]
    )


def _visible_records(
    safe_results: list[dict[str, Any]],
    fields: set[str] | None,
) -> list[dict[str, Any]]:
    records = []
    for result in safe_results:
        for field, value in result.get("content", {}).items():
            if fields is not None and field not in fields:
                continue
            if value == MASK_TOKEN:
                continue
            records.append({
                "document_id": result["document_id"],
                "document_type": result["document_type"],
                "field": field,
                "value": value,
            })
    return records


def _masked_fields(
    safe_results: list[dict[str, Any]],
    fields: set[str] | None,
) -> list[str]:
    masked = []
    for result in safe_results:
        for field in result.get("masked_fields", []):
            if fields is not None and field not in fields:
                continue
            masked.append(f"{field} ({result['document_id']})")
    return _unique(masked)


def _source_summary(safe_results: list[dict[str, Any]]) -> list[str]:
    sources = []
    for result in safe_results:
        score = result.get("score")
        score_text = f", score={score:.3f}" if isinstance(score, float) else ""
        visible = result.get("visible_fields") or []
        masked = result.get("masked_fields") or []
        parts = [
            f"{result['document_id']} ({result['document_type']}{score_text})",
        ]
        if visible:
            parts.append("visible: " + ", ".join(visible))
        if masked:
            parts.append("masked: " + ", ".join(masked))
        sources.append("; ".join(parts))
    return sources


def _normalize_value(value: Any) -> str:
    return str(value).strip().lower()


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return _normalize_value(value) in {"true", "yes", "y", "1", "flagged"}


def _unique(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output
