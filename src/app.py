import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.answer_composer import MASK_TOKEN, build_safe_results, compose_answer
from src.config import BRANCH_IDS, DOCUMENT_TYPES, ROLES, SENSITIVITY_LEVELS
from src.indexer import build_index
from src.llm_services import (
    generate_answer_with_llm,
    get_llm_runtime_label,
    llm_is_configured,
    parse_query_with_llm,
)
from src.nl_processor import parse_natural_language_query
from src.searcher import search_many

st.set_page_config(page_title="Banking RAG Vector Search", layout="wide")

st.title("🏦 Banking RAG — Vector Search")


def render_structured_query(structured_query: dict):
    with st.expander("Structured query", expanded=False):
        st.json(structured_query)


def render_retrieved_vectors(results: list[dict]):
    with st.expander("Retrieved vectors & access", expanded=True):
        rows = []
        for index, r in enumerate(results, start=1):
            meta = r["metadata"]
            summary = r.get("access_summary", {})
            rows.append({
                "Rank": index,
                "Document ID": r["document_id"],
                "Type": r["document_type"],
                "Score": f"{r['score']:.3f}",
                "Document Access": "✅" if r.get("document_access") else "🔴",
                "Sensitivity": meta["sensitivity"],
                "Branch": meta["branch_id"],
                "Visible Fields": summary.get("visible_fields", 0),
                "Masked Fields": summary.get("masked_fields", 0),
                "Visible Field Names": ", ".join(summary.get("visible_field_names", [])),
                "Masked Field Names": ", ".join(summary.get("masked_field_names", [])),
            })

        st.dataframe(rows, hide_index=True, use_container_width=True)


def render_results(results: list[dict]):
    for r in results:
        with st.expander(
            f"📄 {r['document_id']}  —  {r['title']}  "
            f"(score: {r['score']:.3f})",
            expanded=True,
        ):
            meta = r["metadata"]
            st.caption(
                f"Type: {r['document_type']}  |  "
                f"Branch: {meta['branch_id']}  |  "
                f"Sensitivity: {meta['sensitivity']}  |  "
                f"Allowed Roles: {meta['allowed_roles']}"
            )

            rows = []
            for field_access in r.get("field_access_table", []):
                rows.append({
                    "Field": field_access["field"],
                    "Value": str(field_access["value"]),
                    "Access": "✅" if field_access["allowed"] else "🔴",
                    "Allowed Roles": ", ".join(field_access["allowed_roles"]),
                })

            st.dataframe(rows, column_config={
                "Field": st.column_config.TextColumn("Field"),
                "Value": st.column_config.TextColumn("Value", width="large"),
                "Access": st.column_config.TextColumn("Access", width="small"),
                "Allowed Roles": st.column_config.TextColumn("Allowed Roles", width="large"),
            }, hide_index=True, use_container_width=True)

if "index_ready" not in st.session_state:
    with st.spinner("Building vector index..."):
        try:
            build_index()
            st.session_state.index_ready = True
        except FileNotFoundError as exc:
            st.session_state.index_ready = False
            st.warning(
                "Dataset file is missing, so the app will demo NL parsing only. "
                f"Index build error: {exc}"
            )
        except Exception as exc:
            st.session_state.index_ready = False
            st.warning(
                "Vector index is not ready, so the app will demo NL parsing only. "
                f"Index build error: {exc}"
            )

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("⚙️ Search Settings")

    role = st.selectbox("Role", ROLES, index=1)
    customer_id = st.text_input("Customer ID", placeholder="e.g. C10001")
    branch_id = st.selectbox("Branch", ["All"] + BRANCH_IDS, index=0)
    doc_type = st.selectbox("Document Type", ["All"] + DOCUMENT_TYPES, index=0)
    sensitivity = st.selectbox("Sensitivity", ["All"] + SENSITIVITY_LEVELS, index=0)
    top_k = st.slider("Top K", 1, 10, 5)
    use_llm = st.checkbox("Use local AI parser/answer", value=True)

    if use_llm and not llm_is_configured():
        st.caption(
            "Local AI disabled: start Ollama and pull qwen2.5:3b-instruct, "
            "or set LOCAL_LLM_MODEL to an installed model."
        )
    elif use_llm:
        st.caption(f"Local AI active: {get_llm_runtime_label()}")

    if st.button("🔄 Reset Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("structured_query"):
            render_structured_query(msg["structured_query"])
        if msg.get("results"):
            render_retrieved_vectors(msg["results"])
            render_results(msg["results"])

if prompt := st.chat_input("Ask about banking documents..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        default_branch = branch_id if branch_id != "All" else None
        selected_doc_type = doc_type if doc_type != "All" else None
        selected_sensitivity = sensitivity if sensitivity != "All" else None

        structured_query = None
        if use_llm:
            structured_query = parse_query_with_llm(
                text=prompt,
                role=role,
                default_branch_id=default_branch,
                selected_document_type=selected_doc_type,
                selected_sensitivity=selected_sensitivity,
                top_k=top_k,
            )

        if structured_query is None:
            structured_query = parse_natural_language_query(
                text=prompt,
                role=role,
                default_branch_id=default_branch,
                selected_document_type=selected_doc_type,
                selected_sensitivity=selected_sensitivity,
                top_k=top_k,
            )
            if use_llm:
                structured_query.notes.append(
                    "Local AI parser unavailable or failed; rule-based parser was used."
                )

        if customer_id:
            structured_query.customer_id = customer_id
            structured_query.notes.append("Sidebar customer_id overrides customer_id inferred from text.")
            structured_query.retrieval_text = " ".join([
                prompt,
                customer_id,
                *structured_query.target_document_types,
                *structured_query.requested_fields,
            ])

        if st.session_state.index_ready:
            raw_results = search_many(
                query_text=structured_query.retrieval_text,
                role=role,
                customer_id=structured_query.customer_id,
                branch_id=structured_query.metadata_filters.get("branch_id"),
                document_types=structured_query.target_document_types,
                sensitivity=structured_query.metadata_filters.get("sensitivity"),
                top_k=structured_query.top_k,
            )
            if not raw_results and structured_query.metadata_filters.get("sensitivity"):
                raw_results = search_many(
                    query_text=structured_query.retrieval_text,
                    role=role,
                    customer_id=structured_query.customer_id,
                    branch_id=structured_query.metadata_filters.get("branch_id"),
                    document_types=structured_query.target_document_types,
                    sensitivity=None,
                    top_k=structured_query.top_k,
                )
                if raw_results:
                    structured_query.notes.append(
                        "No results with sensitivity filter; retried without sensitivity filter."
                    )
                    structured_query.metadata_filters.pop("sensitivity", None)
            if not raw_results and use_llm:
                fallback_query = parse_natural_language_query(
                    text=prompt,
                    role=role,
                    default_branch_id=default_branch,
                    selected_document_type=selected_doc_type,
                    selected_sensitivity=selected_sensitivity,
                    top_k=top_k,
                )
                fallback_results = search_many(
                    query_text=fallback_query.retrieval_text,
                    role=role,
                    customer_id=fallback_query.customer_id,
                    branch_id=fallback_query.metadata_filters.get("branch_id"),
                    document_types=fallback_query.target_document_types,
                    sensitivity=fallback_query.metadata_filters.get("sensitivity"),
                    top_k=fallback_query.top_k,
                )
                if fallback_results:
                    raw_results = fallback_results
                    fallback_query.notes.append(
                        "Local AI retrieval returned no results; deterministic parser fallback was used."
                    )
                    structured_query = fallback_query
        else:
            raw_results = []
            structured_query.notes.append(
                "Vector index is not ready; only NL parsing was demonstrated."
            )
        results = build_safe_results(
            results=raw_results,
            role=role,
            requested_fields=structured_query.requested_fields,
        )
        text = None
        if use_llm and results:
            text = generate_answer_with_llm(structured_query, results)
            if text:
                structured_query.notes.append("Local AI answer generator used.")

        if text is None:
            text = compose_answer(structured_query, results)
            if use_llm and results:
                structured_query.notes.append(
                    "Local AI answer generator unavailable or failed; deterministic solver was used."
                )

        if not results:
            st.write(text)
            render_structured_query(structured_query.to_dict())
        else:
            st.markdown(text)
            render_structured_query(structured_query.to_dict())
            render_retrieved_vectors(results)
            render_results(results)

        st.session_state.messages.append({
            "role": "assistant",
            "content": text,
            "structured_query": structured_query.to_dict(),
            "results": results if results else [],
        })
