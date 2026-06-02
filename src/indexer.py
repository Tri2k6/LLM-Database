import json
import shutil

import chromadb
from chromadb.api.shared_system_client import SharedSystemClient

from src.config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    DOCUMENTS_PATH,
)
from src.embedder import encode


EXPECTED_COUNT = 500


def _reset_chroma_dir():
    SharedSystemClient.clear_system_cache()
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    SharedSystemClient.clear_system_cache()


def load_documents():
    with open(DOCUMENTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_index(force: bool = False):
    if force:
        _reset_chroma_dir()
    else:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        existing = client.get_collection(COLLECTION_NAME)
        existing_count = existing.count()
        if not force and existing_count >= EXPECTED_COUNT:
            print(f"Index already exists ({existing_count} docs). Skipping.")
            return existing
        client.delete_collection(COLLECTION_NAME)
    except Exception as exc:
        print(f"Existing Chroma index is unavailable; rebuilding. Reason: {exc}")
        _reset_chroma_dir()
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    docs = load_documents()
    ids = []
    embeddings = []
    metadatas = []
    documents_store = []

    embedding_texts = [d["embedding_text"] for d in docs]

    print(f"Encoding {len(docs)} documents...")
    vectors = encode(embedding_texts)

    for i, doc in enumerate(docs):
        doc_id = doc["document_id"]
        meta = doc["metadata"]
        ids.append(doc_id)

        embeddings.append(vectors[i].tolist())

        allowed_roles_str = ",".join(meta["allowed_roles"])

        metadatas.append({
            "document_id": doc_id,
            "document_type": doc["document_type"],
            "customer_id": doc.get("customer_id") or "",
            "department": meta["department"],
            "sensitivity": meta["sensitivity"],
            "allowed_roles": allowed_roles_str,
            "branch_id": meta.get("branch_id") or "",
            "region": meta["region"],
            "retention_level": meta["retention_level"],
            "field_policy_ref": meta["field_policy_ref"],
        })

        documents_store.append(json.dumps({
            "title": doc["title"],
            "source": doc["source"],
            "content": doc["content"],
            "field_policy": doc["field_policy"],
        }))

    print("Adding to ChromaDB...")
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents_store,
    )

    print(f"Done. Indexed {collection.count()} documents.")
    return collection


if __name__ == "__main__":
    build_index(force=True)
