-- Model families named by the official archive (Source A). Only 'reyna' has a model so far:
-- the audit evidences the Reyna family for "For Reyna" documents but not which Reyna variant.
INSERT INTO model_family (slug, name) VALUES
    ('major-alpha-cello-x3-piano-xl-hdd', 'MAJOR/ALPHA/CELLO/X3/PIANO XL HDD'),
    ('flute-piano-piano-xl-sd-pk10', 'FLUTE/PIANO V1.5/PIANO XL SD/PK10'),
    ('ks-100-ks-10-mini-sd', 'KS-100 MINIBOX / KS-10 MINI SD'),
    ('reyna', 'REYNA SERIES'),
    ('t-x', 'T-X SERIES'),
    ('ks-40-kbox', 'KS-40 / KBOX-2 / KBOX-3'),
    ('ks-5-junior', 'KS-5 / JUNIOR LITE / KS-10 / JUNIOR 2'),
    ('bmb-x2-x1-hdd', 'BMB / X2 / X1 / HDD'),
    ('hermosa-n20-nano-plus', 'HERMOSA / N20 NANO PLUS'),
    ('home-40-nano-old', 'HOME 40 / NANO OLD'),
    ('bravo', 'BRAVO'),
    ('p-series', 'P-SERIES');

INSERT INTO model (family_id, slug, name, variant_group, notes)
SELECT id, 'reyna', 'Reyna (variant not specified)', NULL,
       'Header says "For Reyna"; Reyna 2/3C/SE vs Reyna 3/4 is not evidenced.'
FROM model_family WHERE slug = 'reyna';
