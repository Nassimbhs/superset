SELECT 'Recrutement' AS type_mvt, v.dat_emb AS date_mvt, EXTRACT(YEAR FROM v.dat_emb) AS annee, v.*
FROM (
{personnel}
) v
WHERE v.dat_emb IS NOT NULL
UNION ALL
SELECT 'Départ' AS type_mvt, v.dat_depart AS date_mvt, EXTRACT(YEAR FROM v.dat_depart) AS annee, v.*
FROM (
{personnel}
) v
WHERE v.dat_depart IS NOT NULL
