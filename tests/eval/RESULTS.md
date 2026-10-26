# Search evals — results

Golden set: `search_golden.json`, 36 queries (12 lexical, 12 paraphrase, 12 cross-lingual ru/es) over 74 public facts.
Run: `docker compose exec app_a python -m tests.eval.search_eval`.

## 2026-10-26 — semantic search launch
Embeddings: `paraphrase-multilingual-MiniLM-L12-v2` (384-d) in pgvector (HNSW, cosine). Reranker: `ms-marco-MiniLM-L-6-v2`
(English only → applied to English queries only). Fusion: Reciprocal Rank Fusion, k = 60.

| mode | recall@5 | MRR@10 | hit@1 | cross-lingual hit@1 | ms / query |
|---|---|---|---|---|---|
| fts (before) | 0.57 | 0.50 | 0.39 | 0.00 | 2 |
| vector | 0.89 | 0.90 | 0.83 | 0.75 | 13 |
| hybrid (equal weights, no language gate) | 0.88 | 0.79 | 0.67 | 0.33 | 15 |
| hybrid_rerank (rerank on every query) | 0.80 | 0.74 | 0.64 | 0.08 | 271 |
| hybrid, full text off for non-English | 0.94 | 0.89 | 0.81 | 0.75 | 15 |
| **hybrid_rerank, rerank English only, full text off for non-English (default)** | **0.95** | **0.91** | **0.86** | 0.75 | 186 |

Lessons: an English cross-encoder scrambles Russian/Spanish queries; full-text matches of non-English words against English
facts are noise; vectors alone already fix cross-lingual search. Caveat: 36 queries, tuned on the same set — grow the set
from real agent queries before trusting second-decimal differences.
