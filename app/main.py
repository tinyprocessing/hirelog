"""ASGI entrypoint: FastAPI (web + REST) with the MCP streamable-HTTP route at /mcp."""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from mcp.server.transport_security import TransportSecuritySettings

from . import db, service
from .api import router as api_router
from .config import settings
from .guard import Guard
from .mcp_server import mcp
from .web import router as web_router, STATIC_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("hirelog")

ATS_SEED = [("workday", "Workday"), ("greenhouse", "Greenhouse"), ("ashby", "Ashby"), ("lever", "Lever"),
            ("teamtailor", "Teamtailor"), ("smartrecruiters", "SmartRecruiters"), ("workable", "Workable"),
            ("recruitee", "Recruitee"), ("hibob", "HiBob"), ("onlyfy", "onlyfy"), ("phenom", "Phenom"),
            ("avature", "Avature"), ("bamboohr", "BambooHR"), ("jazzhr", "JazzHR"), ("personio", "Personio"),
            ("linkedin_easy_apply", "LinkedIn Easy Apply"), ("oracle_hcm", "Oracle HCM"), ("successfactors", "SAP SuccessFactors"),
            ("icims", "iCIMS"), ("taleo", "Taleo"), ("breezy", "Breezy HR"), ("jobvite", "Jobvite"), ("join", "JOIN"),
            ("factorial", "Factorial"), ("headhunter", "HeadHunter (hh.ru)"), ("habr_career", "Habr Career"),
            ("superjob", "SuperJob"), ("infojobs", "InfoJobs"), ("tecnoempleo", "Tecnoempleo"), ("cornerstone", "Cornerstone OnDemand")]

mcp_http = mcp.streamable_http_app(
    streamable_http_path="/mcp", stateless_http=True, json_response=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                                 allowed_hosts=list(settings.allowed_hosts), allowed_origins=[]),
)


async def _refresher() -> None:
    while True:
        await asyncio.sleep(1800)
        try:
            n = await service.refresh_all()
            await db.execute("DELETE FROM event_log WHERE at < now() - interval '30 days'")
            log.info("refreshed %d notes", n)
        except Exception:  # noqa: BLE001
            log.exception("refresh failed")


async def _embedder() -> None:
    """Keep every note embedded: catches up after deploys or when the embed service was briefly down."""
    await asyncio.sleep(15)
    while True:
        try:
            while await service.backfill_embeddings():
                await asyncio.sleep(1)
        except Exception:  # noqa: BLE001
            log.exception("embedding backfill failed")
        await asyncio.sleep(120)


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    await db.pool.open()
    await db.migrate()
    for slug, name in ATS_SEED:
        await db.execute("INSERT INTO ats (slug, name) VALUES (%s,%s) ON CONFLICT (slug) DO NOTHING", slug, name)
    task = asyncio.create_task(_refresher())
    etask = asyncio.create_task(_embedder())
    async with mcp.session_manager.run():
        yield
    task.cancel()
    etask.cancel()
    await db.pool.close()


app = FastAPI(title="Hirelog", lifespan=lifespan, docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(api_router)
app.include_router(web_router)
app.router.routes.extend(mcp_http.routes)
app.add_middleware(Guard)


@app.get("/health")
async def health():
    if os.path.exists("/tmp/drain"):          # deploy.sh drains a replica before replacing it
        return JSONResponse({"ok": False, "draining": True}, status_code=503)
    r = await db.fetchone("SELECT 1 AS ok")
    return {"ok": bool(r), "service": "hirelog"}
