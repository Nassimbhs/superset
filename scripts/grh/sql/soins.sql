SELECT
    b.cod_soc,
    b.num_soins,
    b.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.tranche_age,
    b.dat_soins,
    TO_CHAR(b.dat_soins, 'YYYY') AS annee,
    DECODE(b.typ_parent, 'A', 'Agent', 'C', 'Conjoint', 'E', 'Enfant', 'Non renseigné') AS beneficiaire,
    DECODE(b.etat_bult,
           'R', 'Remboursé',
           'E', 'Transmis à l''assureur',
           'S', 'Saisi',
           NULL, 'Non renseigné',
           'Clôturé (code ' || b.etat_bult || ')') AS etat,
    NVL(b.tot_honor, 0) AS frais_engages,
    NVL(b.tot_net, 0) AS montant_rembourse,
    CASE WHEN b.date_recp - b.dat_soins BETWEEN 0 AND 365 THEN b.date_recp - b.dat_soins END AS delai_reception,
    CASE WHEN b.dat_soins > ADD_MONTHS(mx.dernier_jour, -12) THEN 1 ELSE 0 END AS dernier_12_mois
FROM bult_soin b
CROSS JOIN (SELECT MAX(dat_soins) AS dernier_jour FROM bult_soin WHERE dat_soins <= SYSDATE) mx
LEFT JOIN (
{personnel}
) e ON e.cod_soc = b.cod_soc AND e.mat_pers = b.mat_pers
WHERE b.dat_soins >= DATE '2014-01-01'
  AND b.dat_soins <= SYSDATE
