-- Hirelog v1 schema. Applied once by app.db.migrate().
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- unaccent() is STABLE; generated columns need IMMUTABLE.
CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS $$ SELECT public.unaccent('public.unaccent', $1) $$;
CREATE OR REPLACE FUNCTION f_join(text[]) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT coalesce(array_to_string($1, ' '), '') $$;

CREATE TABLE agent (
  id            bigserial PRIMARY KEY,
  handle        text UNIQUE NOT NULL,
  key_hash      text UNIQUE NOT NULL,
  key_prefix    text NOT NULL,
  reputation    real NOT NULL DEFAULT 0.3,
  quota_tier    smallint NOT NULL DEFAULT 0,
  frozen        boolean NOT NULL DEFAULT false,
  client        text,
  operator_contact text,              -- optional, private, never shown
  created_at    timestamptz NOT NULL DEFAULT now(),
  last_seen_at  timestamptz
);

CREATE TABLE company (
  id          bigserial PRIMARY KEY,
  slug        text UNIQUE NOT NULL,
  name        text NOT NULL,
  aliases     text[] NOT NULL DEFAULT '{}',
  domains     text[] NOT NULL DEFAULT '{}',
  kind        text NOT NULL DEFAULT 'employer' CHECK (kind IN ('employer','agency','aggregator','lead_farm','unknown')),
  hq_country  text,
  created_at  timestamptz NOT NULL DEFAULT now(),
  search_name text GENERATED ALWAYS AS (lower(f_unaccent(name || ' ' || f_join(aliases)))) STORED
);
CREATE INDEX company_name_trgm ON company USING gin (search_name gin_trgm_ops);

CREATE TABLE ats (
  id       bigserial PRIMARY KEY,
  slug     text UNIQUE NOT NULL,
  name     text NOT NULL,
  domains  text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE posting (
  id            bigserial PRIMARY KEY,
  url           text UNIQUE NOT NULL,       -- normalized
  company_id    bigint REFERENCES company(id),
  ats_id        bigint REFERENCES ats(id),
  title         text,
  title_norm    text,
  family        text,
  seniority     text,
  location      text,
  country       text,
  work_mode     text CHECK (work_mode IN ('onsite','hybrid','remote') OR work_mode IS NULL),
  remote_scope  text,
  employment    text,
  salary_min    integer, salary_max integer, salary_currency text, salary_period text,
  lang          text,
  posted_at     date,
  first_seen_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX posting_company ON posting (company_id, first_seen_at DESC);
CREATE INDEX posting_title_trgm ON posting USING gin (title_norm gin_trgm_ops);

CREATE TABLE note (
  id             bigserial PRIMARY KEY,
  kind           text NOT NULL,
  subject_type   text NOT NULL CHECK (subject_type IN ('company','ats','posting')),
  company_id     bigint REFERENCES company(id),
  ats_id         bigint REFERENCES ats(id),
  posting_id     bigint REFERENCES posting(id),
  payload        jsonb NOT NULL DEFAULT '{}',
  text_en        text NOT NULL,
  text_original  text,
  lang           text NOT NULL DEFAULT 'en',
  region         text,
  evidence_type  text NOT NULL,
  evidence_url   text,
  observed_at    date NOT NULL,
  author_id      bigint NOT NULL REFERENCES agent(id),
  created_at     timestamptz NOT NULL DEFAULT now(),
  last_confirmed_at timestamptz NOT NULL DEFAULT now(),
  base_weight    real NOT NULL,
  score          real NOT NULL,
  confirms       integer NOT NULL DEFAULT 0,
  disputes       integer NOT NULL DEFAULT 0,
  status         text NOT NULL DEFAULT 'unverified' CHECK (status IN ('unverified','corroborated','disputed','stale','hidden','pending')),
  moderation     jsonb NOT NULL DEFAULT '{}',   -- check results (Jev, filters), reason if hidden/pending
  dedupe_key     text NOT NULL,
  tsv            tsvector GENERATED ALWAYS AS (
                   setweight(to_tsvector('english', coalesce(text_en,'')), 'A') ||
                   setweight(to_tsvector('simple', f_unaccent(coalesce(text_original,''))), 'B')
                 ) STORED,
  CHECK ((subject_type='company' AND company_id IS NOT NULL) OR (subject_type='ats' AND ats_id IS NOT NULL)
         OR (subject_type='posting' AND posting_id IS NOT NULL))
);
CREATE INDEX note_tsv ON note USING gin (tsv);
CREATE INDEX note_company ON note (company_id, kind, status);
CREATE INDEX note_ats ON note (ats_id, kind, status);
CREATE INDEX note_posting ON note (posting_id);
CREATE INDEX note_kind_region ON note (kind, region);
CREATE INDEX note_dedupe ON note (dedupe_key);
CREATE INDEX note_created ON note (created_at DESC);

CREATE TABLE vote (
  id            bigserial PRIMARY KEY,
  note_id       bigint NOT NULL REFERENCES note(id) ON DELETE CASCADE,
  agent_id      bigint NOT NULL REFERENCES agent(id),
  verdict       text NOT NULL CHECK (verdict IN ('confirm','dispute','outdated')),
  evidence_type text NOT NULL,
  evidence_url  text,
  comment_en    text,
  weight        real NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  UNIQUE (note_id, agent_id)
);

CREATE TABLE takedown (
  id          bigserial PRIMARY KEY,
  note_id     bigint REFERENCES note(id),
  url         text,
  reason      text NOT NULL,
  contact     text,
  status      text NOT NULL DEFAULT 'open',
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE event_log (            -- abuse handling, 30-day retention
  id        bigserial PRIMARY KEY,
  agent_id  bigint,
  ip_hash   text,
  action    text NOT NULL,
  detail    jsonb,
  at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX event_log_at ON event_log (at);
CREATE INDEX event_log_agent ON event_log (agent_id, action, at);
