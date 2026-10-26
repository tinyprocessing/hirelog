CREATE TABLE feedback (
  id         bigserial PRIMARY KEY,
  message    text NOT NULL,
  contact    text,
  lang       text,
  ip_hash    text,
  status     text NOT NULL DEFAULT 'new',
  created_at timestamptz NOT NULL DEFAULT now()
);
