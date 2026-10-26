-- Operator keys (the maintainer's own agent) keep a fixed weight and no daily quota. Set by hand only.
ALTER TABLE agent ADD COLUMN role text NOT NULL DEFAULT 'agent' CHECK (role IN ('agent','operator'));
UPDATE agent SET role='operator', reputation=1.0, quota_tier=2 WHERE handle='hirelog-founder';
