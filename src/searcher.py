import json
from typing import Any

import chromadb

from src.config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    DEFAULT_TOP_K,
)
from src.embedder import encode


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


def build_where_filter(
    customer_id: str | None = None,
    branch_id: str | None = None,
    document_type: str | None = None,
    sensitivity: str | None = None,
) -> dict[str, Any] | None:
    clauses = []

    if customer_id:
        clauses.append({"customer_id": {"$eq": customer_id}})
    if branch_id:
        clauses.append({"branch_id": {"$eq": branch_id}})
    if document_type:
        clauses.append({"document_type": {"$eq": document_type}})
    if sensitivity:
        clauses.append({"sensitivity": {"$eq": sensitivity}})

    if len(clauses) == 0:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _role_is_allowed(role: str, allowed_roles_str: str) -> bool:
    return role in allowed_roles_str.split(",")


def search(
    query_text: str,
    role: str | None = None,
    customer_id: str | None = None,
    branch_id: str | None = None,
    document_type: str | None = None,
    sensitivity: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    collection = get_collection()

    query_vector = encode(query_text).tolist()
    where = build_where_filter(customer_id, branch_id, document_type, sensitivity)

    fetch_k = min(top_k * 3, 100)
    query_kwargs = {
        "query_embeddings": [query_vector],
        "n_results": fetch_k,
        "include": ["documents", "metadatas", "distances"],
    }
    if where is not None:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)

    output = []
    if not results["ids"] or not results["ids"][0]:
        return output

    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        allowed_roles_str = meta.get("allowed_roles", "")

        if role and not _role_is_allowed(role, allowed_roles_str):
            continue

        doc_store = json.loads(results["documents"][0][i])
        output.append({
            "document_id": results["ids"][0][i],
            "document_type": meta["document_type"],
            "customer_id": meta["customer_id"],
            "score": 1 - results["distances"][0][i],
            "title": doc_store["title"],
            "source": doc_store["source"],
            "content": doc_store["content"],
            "field_policy": doc_store["field_policy"],
            "metadata": {k: meta[k] for k in [
                "department", "sensitivity", "allowed_roles", "branch_id",
                "region", "retention_level", "field_policy_ref",
            ]},
        })

        if len(output) >= top_k:
            break

    return output


def search_many(
    query_text: str,
    role: str | None = None,
    customer_id: str | None = None,
    branch_id: str | None = None,
    document_types: list[str] | None = None,
    sensitivity: str | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    if not document_types:
        return search(
            query_text=query_text,
            role=role,
            customer_id=customer_id,
            branch_id=branch_id,
            sensitivity=sensitivity,
            top_k=top_k,
        )

    merged: dict[str, dict[str, Any]] = {}
    per_type_top_k = max(top_k, 3)

    for document_type in document_types:
        results = search(
            query_text=query_text,
            role=role,
            customer_id=customer_id,
            branch_id=branch_id,
            document_type=document_type,
            sensitivity=sensitivity,
            top_k=per_type_top_k,
        )
        for result in results:
            existing = merged.get(result["document_id"])
            if existing is None or result["score"] > existing["score"]:
                merged[result["document_id"]] = result

    return sorted(
        merged.values(),
        key=lambda item: item["score"],
        reverse=True,
    )[:top_k]
