"""Pipeline orchestrator for Day 06 Data Ingestion Benchmark."""
import json
import time
from pathlib import Path
from .ingestion import load_pdf
from .chunking import fixed_size, by_paragraph
from .embeddings import LocalEmbedder
from .store import QdrantVectorStore
from .evaluation import evaluate_query, summarize


def find_file(relative_paths: list[str]) -> Path:
    """Resolve file from multiple potential base paths."""
    for p in relative_paths:
        path_obj = Path(p).resolve()
        if path_obj.exists():
            return path_obj
    raise FileNotFoundError(f"Could not find file in any of: {relative_paths}")


def main() -> None:
    print("=" * 65)
    print(" DAY 06: DATA INGESTION ENGINEERING PIPELINE ")
    print("=" * 65)

    # 1. Locate and load PDF
    pdf_path = find_file([
        "data/international_debt_report_2026.pdf",
        "data/9781464823558.pdf",
        "../data/international_debt_report_2026.pdf",
        "../../data/international_debt_report_2026.pdf",
        "D:/VinAI/prj/Day6/9781464823558.pdf",
    ])
    print(f"\n[1/5] Loading PDF corpus from: {pdf_path}")
    pages = load_pdf(
        path=pdf_path,
        document_id="worldbank-idr-2026",
        source="data/international_debt_report_2026.pdf",
        start_page=21,
        end_page=55,
    )
    valid_pages = [p for p in pages if len(p.text) >= 50]
    print(f"Loaded {len(pages)} physical pages ({len(valid_pages)} valid content pages >= 50 chars).")
    if len(valid_pages) < 30:
        raise ValueError(f"Corpus must have at least 30 content pages, got {len(valid_pages)}")

    # 2. Chunking for Strategy A and B
    print("\n[2/5] Chunking documents...")
    # Strategy A: Fixed-size (500 chars, overlap 50)
    chunks_a = []
    for page in pages:
        chunks_a.extend(fixed_size(page, size=500, overlap=50))
    print(f"Strategy A (Fixed-size 500/50): {len(chunks_a)} chunks generated.")

    # Strategy B: Paragraph-aware (max 800 chars)
    chunks_b = []
    for page in pages:
        chunks_b.extend(by_paragraph(page, max_size=800))
    print(f"Strategy B (Paragraph/Semantic): {len(chunks_b)} chunks generated.")

    # 3. Embedding and Indexing into Qdrant
    print("\n[3/5] Initializing Embedder and Local Qdrant Store...")
    embedder = LocalEmbedder(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Place Qdrant DB at project root or starter root
    qdrant_dir = Path("qdrant_db").resolve()
    store = QdrantVectorStore(storage_path=str(qdrant_dir), dimensions=embedder.dimensions)

    print("Embedding Strategy A chunks...")
    t0 = time.time()
    texts_a = [c.text for c in chunks_a]
    vectors_a = embedder.embed_documents(texts_a)
    store.upsert(strategy="config_a", chunks=chunks_a, vectors=vectors_a)
    time_a = time.time() - t0
    print(f"Config A indexed in {time_a:.2f}s.")

    print("Embedding Strategy B chunks...")
    t0 = time.time()
    texts_b = [c.text for c in chunks_b]
    vectors_b = embedder.embed_documents(texts_b)
    store.upsert(strategy="config_b", chunks=chunks_b, vectors=vectors_b)
    time_b = time.time() - t0
    print(f"Config B indexed in {time_b:.2f}s.")
    print("Config C reuses Config B index (will apply metadata filtering during retrieval).")

    # 4. Load Benchmark Questions
    print("\n[4/5] Running Benchmark Retrieval...")
    benchmark_path = find_file([
        "benchmark/questions.json",
        "../benchmark/questions.json",
        "../../benchmark/questions.json",
    ])
    with open(benchmark_path, "r", encoding="utf-8") as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} questions from {benchmark_path.name}.")

    traces_by_strategy = {"config_a": [], "config_b": [], "config_c": []}

    for q in questions:
        q_text = q["question"]
        q_vec = embedder.embed_query(q_text)

        # Config A: Search config_a, no filter
        hits_a = store.search(strategy="config_a", query_vector=q_vec, top_k=3, filters=None)
        traces_by_strategy["config_a"].append(evaluate_query(q, hits_a))

        # Config B: Search config_b, no filter
        hits_b = store.search(strategy="config_b", query_vector=q_vec, top_k=3, filters=None)
        traces_by_strategy["config_b"].append(evaluate_query(q, hits_b))

        # Config C: Search config_b, apply filter if provided
        q_filter = q.get("filter")
        hits_c = store.search(strategy="config_b", query_vector=q_vec, top_k=3, filters=q_filter)
        traces_by_strategy["config_c"].append(evaluate_query(q, hits_c))

    # 5. Summarize and Save Results
    print("\n[5/5] Benchmark Results & Metrics Summary:")
    summary = summarize(traces_by_strategy)

    print("\n" + "=" * 70)
    print(f"{'Strategy':<12} | {'Split':<6} | {'Total':<6} | {'Hit@1':<12} | {'Hit@3':<12}")
    print("-" * 70)
    for strat in ["config_a", "config_b", "config_c"]:
        strat_display = {
            "config_a": "Config A (Fixed)",
            "config_b": "Config B (Para)",
            "config_c": "Config C (B+Filter)"
        }[strat]
        for sp in ["dev", "test", "overall"]:
            m = summary[strat][sp]
            h1_str = f"{m['hit1_count']}/{m['total']} ({m['hit1_rate']*100:.1f}%)"
            h3_str = f"{m['hit3_count']}/{m['total']} ({m['hit3_rate']*100:.1f}%)"
            print(f"{strat_display:<20} | {sp:<6} | {m['total']:<6} | {h1_str:<12} | {h3_str:<12}")
        print("-" * 70)

    # Save results
    results_dir = Path("results").resolve()
    results_dir.mkdir(parents=True, exist_ok=True)

    trace_file = results_dir / "retrieval_trace.json"
    with open(trace_file, "w", encoding="utf-8") as f:
        json.dump(traces_by_strategy, f, indent=2, ensure_ascii=False)

    summary_file = results_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nTrace log saved to: {trace_file}")
    print(f"Summary saved to: {summary_file}")

    # Update artifacts/experiment_log.csv
    exp_log_path = Path("artifacts/experiment_log.csv").resolve()
    if exp_log_path.parent.exists():
        with open(exp_log_path, "w", encoding="utf-8") as f:
            f.write("strategy,description,chunk_count,embed_time_sec,dev_hit1,dev_hit3,test_hit1,test_hit3\n")
            f.write(f"Config A,Fixed-size 500/50,{len(chunks_a)},{time_a:.2f},{summary['config_a']['dev']['hit1_rate']},{summary['config_a']['dev']['hit3_rate']},{summary['config_a']['test']['hit1_rate']},{summary['config_a']['test']['hit3_rate']}\n")
            f.write(f"Config B,Paragraph-aware max 800,{len(chunks_b)},{time_b:.2f},{summary['config_b']['dev']['hit1_rate']},{summary['config_b']['dev']['hit3_rate']},{summary['config_b']['test']['hit1_rate']},{summary['config_b']['test']['hit3_rate']}\n")
            f.write(f"Config C,Paragraph-aware with filter,{len(chunks_b)},0.00,{summary['config_c']['dev']['hit1_rate']},{summary['config_c']['dev']['hit3_rate']},{summary['config_c']['test']['hit1_rate']},{summary['config_c']['test']['hit3_rate']}\n")
        print(f"Updated experiment log at: {exp_log_path}")

    print("\n Pipeline run successfully completed! ")


if __name__ == "__main__":
    main()
