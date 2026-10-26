"""Search evals: recall@5, MRR@10 and hit@1 per mode and query type, on the live database.

  docker compose exec app_a python -m tests.eval.search_eval            # all modes
  docker compose exec app_a python -m tests.eval.search_eval hybrid     # one mode

recall@5 — share of relevant facts found in the top 5; MRR@10 — 1/rank of the first relevant hit (0 if not in top 10);
hit@1 — first result is relevant. Same filters as production (public notes only).
"""
import asyncio
import json
import pathlib
import sys
import time

from app import db, service

GOLDEN = json.loads((pathlib.Path(__file__).parent / "search_golden.json").read_text())["queries"]
MODES = sys.argv[1:] or ["fts", "vector", "hybrid", "hybrid_rerank"]


async def run(mode: str) -> dict:
    rows, t0 = [], time.perf_counter()
    for g in GOLDEN:
        ids = (await service.search_ids(g["q"], [service.PUBLIC], [], mode))[:10]
        rel = set(g["relevant"])
        recall = len(rel & set(ids[:5])) / len(rel)
        rr = next((1 / (k + 1) for k, i in enumerate(ids) if i in rel), 0.0)
        rows.append((g["type"], recall, rr, 1.0 if ids and ids[0] in rel else 0.0, g["q"], ids[:5]))
    ms = (time.perf_counter() - t0) * 1000 / len(GOLDEN)
    out = {"mode": mode, "ms_per_query": round(ms)}
    for typ in ("all", "lexical", "paraphrase", "cross"):
        sel = [r for r in rows if typ == "all" or r[0] == typ]
        out[typ] = {m: round(sum(r[i] for r in sel) / len(sel), 2) for m, i in (("recall@5", 1), ("mrr@10", 2), ("hit@1", 3))}
    out["misses"] = [(r[4], r[5]) for r in rows if r[1] == 0]
    return out


async def main():
    await db.pool.open()
    for mode in MODES:
        r = await run(mode)
        print(json.dumps({k: v for k, v in r.items() if k != "misses"}, ensure_ascii=False))
        for q, got in r["misses"]:
            print(f"   miss [{mode}] {q!r} → {got}")
    await db.pool.close()


asyncio.run(main())
