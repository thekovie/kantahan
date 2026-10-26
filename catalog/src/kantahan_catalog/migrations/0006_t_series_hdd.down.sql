DELETE FROM release_model WHERE model_id IN (SELECT id FROM model WHERE slug = 't-series-hdd');
DELETE FROM model WHERE slug = 't-series-hdd';
DELETE FROM model_family WHERE slug = 't-series-hdd';
