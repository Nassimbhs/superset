SELECT
    a.cod_soc,
    a.num_attest,
    a.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    a.date_edition,
    TO_CHAR(a.date_edition, 'YYYY') AS annee,
    TO_CHAR(a.date_edition, 'YYYY-MM') AS mois,
    'Modèle n°' || a.typ_att AS modele_attestation,
    CASE WHEN a.date_edition > ADD_MONTHS(mx.dernier_jour, -12) THEN 1 ELSE 0 END AS dernier_12_mois
FROM attest_trav a
CROSS JOIN (SELECT MAX(date_edition) AS dernier_jour FROM attest_trav WHERE date_edition <= SYSDATE) mx
LEFT JOIN (
{personnel}
) e ON e.cod_soc = a.cod_soc AND e.mat_pers = a.mat_pers
WHERE a.date_edition BETWEEN DATE '2014-01-01' AND SYSDATE
