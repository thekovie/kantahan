-- One model per machine group named by the publisher on Source A (its own song list page).
-- A volume joins a group only through a release_model evidence row (see mapping.py), never by
-- default. 'reyna' already exists from migration 0002 and keeps its strict header rule.
INSERT INTO model (family_id, slug, name, variant_group, notes)
SELECT id, slug, name, NULL,
       'Machine group as named by the publisher on Source A; which machines in the group use '
       || 'a list is the publisher''s statement, not verified here.'
FROM model_family WHERE slug <> 'reyna';
