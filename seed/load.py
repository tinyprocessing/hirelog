"""Load the reviewed seed notes as the founder agent. Idempotent: skips notes whose text already exists.

    docker compose exec app python -m seed.load
Prints the founder key once (first run) — store it, it is the operator's own agent key.
"""
import asyncio
import json
from pathlib import Path

from app import db, service


async def main() -> None:
    await db.pool.open()
    await db.migrate()
    founder = await db.fetchone("SELECT * FROM agent WHERE handle='hirelog-founder'")
    if not founder:
        key = await service.register_agent("seed", None, None)
        await db.execute("UPDATE agent SET handle='hirelog-founder', reputation=1.0, quota_tier=2 WHERE handle=%s", key["handle"])
        founder = await db.fetchone("SELECT * FROM agent WHERE handle='hirelog-founder'")
        print("FOUNDER_KEY", key["api_key"])
    items = json.loads((Path(__file__).parent / "seed.json").read_text())
    added = 0
    for it in items:
        if await db.fetchone("SELECT 1 FROM note WHERE text_en=%s", it["text_en"]):
            continue
        data = {**it, "evidence": {"type": it.pop("evidence"), "observed_at": it.pop("observed_at")}}
        try:
            r = await service.contribute(founder, data)
        except service.Rejected as e:
            print("REJECTED", it["text_en"][:60], "→", e)
            continue
        if r.get("accepted") and r["status"] == "pending":   # seed was reviewed by hand: place names, not people
            await db.execute("UPDATE note SET status='unverified' WHERE id=%s", r["note_id"])
        added += bool(r.get("accepted"))
        print(r.get("note_id"), r.get("status"), it["kind"], it["subject"].get("name") or it["subject"].get("slug"))
    print("added", added)
    await db.pool.close()


if __name__ == "__main__":
    asyncio.run(main())
