SELECT
    a.cod_soc,
    a.num_aut,
    a.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.service,
    e.categorie,
    e.tranche_age,
    a.dat_debut_aut,
    TO_CHAR(a.dat_debut_aut, 'YYYY') AS annee,
    TO_CHAR(a.dat_debut_aut, 'YYYY-MM') AS mois,
    DECODE(a.etat_aut, 'V', 'Validée', 'R', 'Refusée', 'I', 'En instance', 'S', 'Saisie', 'Non renseigné') AS etat,
    NVL(a.duree, 0) * 60 + NVL(a.duree_m, 0) AS minutes_sortie,
    CASE WHEN a.heur_s BETWEEN 6 AND 20 THEN LPAD(a.heur_s, 2, '0') || 'h' ELSE 'Non renseignée' END AS heure_sortie,
    CASE WHEN a.dat_debut_aut > ADD_MONTHS(mx.dernier_jour, -12) AND a.dat_debut_aut <= mx.dernier_jour THEN 1 ELSE 0 END AS dernier_12_mois
FROM autorisation_sort a
CROSS JOIN (SELECT MAX(dat_debut_aut) AS dernier_jour FROM autorisation_sort WHERE dat_debut_aut <= SYSDATE) mx
LEFT JOIN (
{personnel}
) e ON e.cod_soc = a.cod_soc AND e.mat_pers = a.mat_pers
WHERE a.dat_debut_aut >= DATE '2015-01-01'
  AND a.dat_debut_aut < ADD_MONTHS(TRUNC(SYSDATE), 12)
