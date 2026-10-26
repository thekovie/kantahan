-- A machine the publisher lists inside its T-X SERIES section but whose own documents (Volumes 58
-- and 60) say "For T-Series, HDD" in their page header. Their numbers overlap the T-Series DVD
-- volumes (63 to 76), so keeping both in one model made 205 numbers conflict and left them out.
-- A document joins this model only when its own header says so (see mapping.HEADER_SPLITS).
INSERT INTO model_family (slug, name) VALUES ('t-series-hdd', 'T-SERIES HDD');
INSERT INTO model (family_id, slug, name, variant_group, notes)
SELECT id, slug, name, NULL,
       'Named by the page header of its own documents ("For T-Series, HDD"); the publisher lists '
       || 'them under T-X SERIES.'
FROM model_family WHERE slug = 't-series-hdd';
