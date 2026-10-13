SELECT
    d.cod_soc,
    d.num_don,
    d.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.tranche_age,
    d.dat_dem_don,
    TO_CHAR(NVL(d.annee, EXTRACT(YEAR FROM d.dat_dem_don))) AS annee,
    NVL(TRIM(n.lib_nat_don), 'Nature ' || d.nat_don) AS nature_don,
    DECODE(d.etat_dem, 'A', 'Accordée', 'V', 'Validée', 'I', 'En instance', 'N', 'Refusée',
           'Autre (code ' || d.etat_dem || ')') AS etat,
    NVL(d.mnt_dem_don, 0) AS montant_demande,
    NVL(d.mnt_acc_don, 0) AS montant_accorde,
    CASE WHEN d.etat_dem IN ('A', 'V') THEN 1 ELSE 0 END AS accordee
FROM demande_dons d
LEFT JOIN nature_don n ON n.nat_don = d.nat_don
LEFT JOIN (
{personnel}
) e ON e.cod_soc = d.cod_soc AND e.mat_pers = d.mat_pers
