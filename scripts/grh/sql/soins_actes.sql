SELECT
    l.cod_soc,
    l.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    l.dat_acte,
    TO_CHAR(l.dat_acte, 'YYYY') AS annee,
    NVL(TRIM(a.lib_act), NVL(l.abrv_act, 'Non renseigné')) AS type_acte,
    NVL(l.tot_honor, 0) AS frais_engages,
    NVL(l.tot_net, 0) AS montant_rembourse,
    CASE WHEN l.dat_acte > ADD_MONTHS(mx.dernier_jour, -12) THEN 1 ELSE 0 END AS dernier_12_mois
FROM lig_bult l
CROSS JOIN (SELECT MAX(dat_acte) AS dernier_jour FROM lig_bult WHERE dat_acte <= SYSDATE) mx
LEFT JOIN acte a ON a.type_act = l.type_act AND a.abrv_act = l.abrv_act
LEFT JOIN (
{personnel}
) e ON e.cod_soc = l.cod_soc AND e.mat_pers = l.mat_pers
WHERE l.dat_acte >= DATE '2014-01-01'
  AND l.dat_acte <= SYSDATE
