"""Settings from environment. Secrets live only in the server .env."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    database_url: str = _env("HIRELOG_DATABASE_URL", "postgresql://hirelog:hirelog@localhost:5432/hirelog")
    base_url: str = _env("HIRELOG_BASE_URL", "http://localhost:8000")
    admin_token: str = _env("HIRELOG_ADMIN_TOKEN")
    ip_salt: str = _env("HIRELOG_IP_SALT", "dev-salt")
    typesafe_api_key: str = _env("TYPESAFE_API_KEY")
    jev_mode: str = _env("HIRELOG_JEV_MODE", "shadow")          # off | shadow | on
    allowed_hosts: tuple[str, ...] = tuple(h for h in _env("HIRELOG_ALLOWED_HOSTS", "localhost:*,127.0.0.1:*").split(",") if h)
    new_agent_notes_per_day: int = int(_env("HIRELOG_NEW_NOTES_PER_DAY", "20"))
    new_agent_votes_per_day: int = int(_env("HIRELOG_NEW_VOTES_PER_DAY", "50"))
    keys_per_ip_per_day: int = int(_env("HIRELOG_KEYS_PER_IP_PER_DAY", "3"))
    gsc_verify: str = _env("HIRELOG_GSC_VERIFY")            # Google Search Console meta token
    embed_url: str = _env("HIRELOG_EMBED_URL")              # embedding/rerank service; empty → full-text search only
    search_mode: str = _env("HIRELOG_SEARCH_MODE", "hybrid_rerank")  # fts | vector | hybrid | hybrid_rerank


settings = Settings()
