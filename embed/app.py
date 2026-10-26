"""Embedding + reranking service. One process holds the models; app replicas call it over HTTP.

POST /embed  {"texts": [...]}                  -> {"vectors": [[384 floats], ...]}
POST /rerank {"query": "...", "docs": [...]}  -> {"scores": [float, ...]}  (higher = more relevant)
"""
import os

from fastapi import FastAPI
from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from pydantic import BaseModel, Field

EMBED_MODEL = os.environ.get("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
RERANK_MODEL = os.environ.get("RERANK_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2")
CACHE = os.environ.get("MODEL_CACHE", "/models")

embedder = TextEmbedding(EMBED_MODEL, cache_dir=CACHE, threads=2)
reranker = TextCrossEncoder(RERANK_MODEL, cache_dir=CACHE, threads=2)
app = FastAPI(title="hirelog-embed", docs_url=None, redoc_url=None)


class EmbedIn(BaseModel):
    texts: list[str] = Field(max_length=64)


class RerankIn(BaseModel):
    query: str
    docs: list[str] = Field(max_length=50)


@app.get("/health")
def health():
    return {"ok": True, "embed": EMBED_MODEL, "rerank": RERANK_MODEL}


@app.post("/embed")
def embed(body: EmbedIn):
    vecs = embedder.embed([t[:2000] for t in body.texts], batch_size=16)
    return {"vectors": [v.round(6).tolist() for v in vecs]}


@app.post("/rerank")
def rerank(body: RerankIn):
    return {"scores": [float(s) for s in reranker.rerank(body.query[:500], [d[:1500] for d in body.docs])]}
