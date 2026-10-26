# Search

Hirelog search is hybrid: full-text for exact words and names, vectors for meaning in any language.

```
write a fact ─► embed service ─► vector(384) in note.embedding (pgvector, HNSW, cosine)
                                 (a background task re-embeds anything missed)

query ─┬─► PostgreSQL full text (weighted tsvector) ─ top 50 ─┐
       └─► embed(query) → nearest vectors (distance < 0.75) ─ top 50 ─┤
                                       Reciprocal Rank Fusion (k = 60)
                                       English query → cross-encoder reorders the top 20
```

- **Embed service** (`embed/`): one process holds the models (`paraphrase-multilingual-MiniLM-L12-v2`,
  `ms-marco-MiniLM-L-6-v2`), baked into the image. App replicas call it over HTTP; if it is down, search falls back to
  full text.
- **Language gates:** the reranker is English-only, and full-text matches of non-English words against English facts are
  noise — both are switched off for non-English queries.
- **Modes** (`HIRELOG_SEARCH_MODE`): `fts`, `vector`, `hybrid`, `hybrid_rerank` (default).
- **Evals:** `tests/eval/search_golden.json` (36 queries: lexical, paraphrase, cross-lingual),
  `docker compose exec app_a python -m tests.eval.search_eval`. Results in `tests/eval/RESULTS.md`:
  recall@5 0.57 → 0.95, hit@1 0.39 → 0.86 versus full text alone.

To change the model: update `embed/app.py` and the migration's vector size, set `embedding = NULL`, deploy — the
background task re-embeds every note.
