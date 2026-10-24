DELETE FROM release_model WHERE model_id IN (SELECT id FROM model WHERE slug <> 'reyna');
DELETE FROM model WHERE slug <> 'reyna';
