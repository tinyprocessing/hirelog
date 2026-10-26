-- Index the text values inside payload too (symptom, workaround, question …), weight C.
ALTER TABLE note DROP COLUMN tsv;
ALTER TABLE note ADD COLUMN tsv tsvector GENERATED ALWAYS AS (
  setweight(to_tsvector('english', coalesce(text_en,'')), 'A') ||
  setweight(to_tsvector('simple', f_unaccent(coalesce(text_original,''))), 'B') ||
  setweight(jsonb_to_tsvector('english', payload, '["string"]'), 'C')
) STORED;
CREATE INDEX note_tsv ON note USING gin (tsv);
