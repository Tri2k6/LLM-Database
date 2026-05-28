import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import QUERIES_PATH
from src.searcher import search


def run_test(idx: int | None = None):
    with open(QUERIES_PATH, encoding="utf-8") as f:
        queries = json.load(f)

    if idx is not None:
        queries = [queries[idx]]

    results = []
    for q in queries:
        doc_type = q.get("target_document_types", [None])[0] if q.get("target_document_types") else None
        metadata_filters = q.get("metadata_filters") or {}

        res = search(
            query_text=q["query"],
            role=q["role"],
            customer_id=q.get("customer_id"),
            branch_id=metadata_filters.get("branch_id") or q.get("branch_id"),
            document_type=doc_type,
            top_k=q.get("top_k", 5),
        )

        results.append({
            "query_id": q["query_id"],
            "role": q["role"],
            "query": q["query"],
            "num_results": len(res),
            "document_ids": [r["document_id"] for r in res],
            "document_types": list({r["document_type"] for r in res}),
        })

    return results


def print_report(results: list[dict]):
    total = len(results)
    empty = [r for r in results if r["num_results"] == 0]
    non_empty = [r for r in results if r["num_results"] > 0]

    print(f"{'='*60}")
    print(f"  Total queries:     {total}")
    print(f"  With results:      {len(non_empty)}")
    print(f"  Empty results:     {len(empty)}")
    print(f"{'='*60}")
    print()

    if empty:
        print(f"{'─'*60}")
        print(f"  Queries with 0 results ({len(empty)}):")
        print(f"{'─'*60}")
        for r in empty:
            print(f"  ❌ {r['query_id']} | role={r['role']} | \"{r['query'][:60]}\"")
        print()

    for r in results:
        icon = "✅" if r["num_results"] > 0 else "❌"
        print(f"  {icon} {r['query_id']} ({r['role']}, {r['num_results']} docs)")
        if r["num_results"] > 0:
            print(f"       ids:  {', '.join(r['document_ids'][:5])}")
            print(f"       types: {', '.join(r['document_types'])}")
        print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--idx", type=int, default=None, help="Run a single query by index")
    args = parser.parse_args()

    results = run_test(args.idx)
    print_report(results)

    if args.idx is None:
        out_path = Path(__file__).parent / "test_results.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"  Full results saved to {out_path}")
