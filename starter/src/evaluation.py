"""Evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def _normalize_for_match(text: str) -> str:
    """Normalize typography and whitespace for robust evidence substring matching."""
    if not text:
        return ""
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("—", "-").replace("–", "-")
    return " ".join(text.split()).lower()


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check if retrieved top hits contain gold evidence and correct page."""
    gold_page = question["gold_page"]
    gold_quote_norm = _normalize_for_match(question["evidence_quote"])

    annotated_hits = []
    has_hit_1 = False
    has_hit_3 = False

    for rank, hit in enumerate(hits):
        hit_page = hit["metadata"].get("page")
        hit_text_norm = _normalize_for_match(hit.get("text", ""))

        # Check page match and evidence containment
        page_match = (hit_page == gold_page)
        evidence_found = gold_quote_norm in hit_text_norm
        is_hit = page_match and evidence_found

        annotated_hits.append(
            {
                "rank": rank + 1,
                "chunk_id": hit.get("chunk_id"),
                "score": hit.get("score"),
                "page": hit_page,
                "page_match": page_match,
                "evidence_found": evidence_found,
                "is_hit": is_hit,
                "text": hit.get("text"),
                "metadata": hit.get("metadata"),
            }
        )

        if rank == 0 and is_hit:
            has_hit_1 = True
        if is_hit:
            has_hit_3 = True

    return {
        "question_id": question["id"],
        "split": question["split"],
        "type": question.get("type", "direct"),
        "question": question["question"],
        "expected_answer": question.get("expected_answer", ""),
        "gold_page": gold_page,
        "evidence_quote": question["evidence_quote"],
        "filter": question.get("filter"),
        "hit_at_1": has_hit_1,
        "hit_at_3": has_hit_3,
        "top_hits": annotated_hits,
    }


def summarize(traces_by_strategy: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    summary: dict[str, Any] = {}

    for strat, traces in traces_by_strategy.items():
        dev_traces = [t for t in traces if t["split"] == "dev"]
        test_traces = [t for t in traces if t["split"] == "test"]

        def calc_metrics(sub_traces):
            total = len(sub_traces)
            if total == 0:
                return {"total": 0, "hit1_count": 0, "hit1_rate": 0.0, "hit3_count": 0, "hit3_rate": 0.0}
            h1 = sum(1 for t in sub_traces if t["hit_at_1"])
            h3 = sum(1 for t in sub_traces if t["hit_at_3"])
            return {
                "total": total,
                "hit1_count": h1,
                "hit1_rate": round(h1 / total, 4),
                "hit3_count": h3,
                "hit3_rate": round(h3 / total, 4),
            }

        summary[strat] = {
            "dev": calc_metrics(dev_traces),
            "test": calc_metrics(test_traces),
            "overall": calc_metrics(traces),
        }

    return summary
