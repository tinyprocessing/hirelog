-- Markets (segments like "iOS · Europe") as a fourth subject type, and a ban list for abuse handling.
CREATE TABLE market (
  id          bigserial PRIMARY KEY,
  slug        text UNIQUE NOT NULL,
  name        text NOT NULL,
  family      text,              -- ios, android, mobile, ai_eng, backend, platform, security, solutions, em, all
  region      text,              -- ES, UK, EU, EMEA, US, GLOBAL
  description text,
  created_at  timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE note ADD COLUMN market_id bigint REFERENCES market(id);
ALTER TABLE note DROP CONSTRAINT IF EXISTS note_subject_type_check;
ALTER TABLE note ADD CONSTRAINT note_subject_type_check CHECK (subject_type IN ('company','ats','posting','market'));
ALTER TABLE note DROP CONSTRAINT IF EXISTS note_check;
ALTER TABLE note ADD CONSTRAINT note_subject_ref_check CHECK (
  (subject_type='company' AND company_id IS NOT NULL) OR (subject_type='ats' AND ats_id IS NOT NULL) OR
  (subject_type='posting' AND posting_id IS NOT NULL) OR (subject_type='market' AND market_id IS NOT NULL));
CREATE INDEX note_market ON note (market_id, kind, status);

CREATE TABLE ban (
  id         bigserial PRIMARY KEY,
  kind       text NOT NULL CHECK (kind IN ('ip','agent')),
  value      text NOT NULL,          -- ip hash or agent id
  reason     text NOT NULL,
  until      timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ban_active ON ban (kind, value, until);
