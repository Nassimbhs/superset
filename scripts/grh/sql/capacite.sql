SELECT
    s.cod_soc,
    s.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.tranche_age,
    e.est_actif,
    s.dat_saisie,
    TO_CHAR(s.dat_saisie, 'YYYY') AS annee,
    s.taux_actuel,
    s.taux_apres_pret,
    CASE
        WHEN s.taux_apres_pret IS NULL THEN 'Non calculé'
        WHEN s.taux_apres_pret < 20 THEN '1. Moins de 20 %'
        WHEN s.taux_apres_pret < 30 THEN '2. 20 à 30 %'
        WHEN s.taux_apres_pret < 40 THEN '3. 30 à 40 %'
        WHEN s.taux_apres_pret < 50 THEN '4. 40 à 50 %'
        ELSE '5. 50 % et plus'
    END AS tranche_endettement,
    CASE WHEN s.taux_apres_pret >= 40 THEN 1 ELSE 0 END AS au_dela_seuil,
    s.mensualite_demandee,
    s.derniere_simulation
FROM (
    SELECT
        c.cod_soc,
        c.mat_pers,
        c.dat_saisie,
        CASE WHEN c.end_taux1 BETWEEN 0 AND 100 THEN c.end_taux1 END AS taux_actuel,
        CASE WHEN c.end_taux2 BETWEEN 0 AND 100 THEN c.end_taux2 END AS taux_apres_pret,
        c.rem_men AS mensualite_demandee,
        CASE WHEN ROW_NUMBER() OVER (PARTITION BY c.cod_soc, c.mat_pers ORDER BY c.dat_saisie DESC NULLS LAST,
                                     c.num_cap DESC) = 1 THEN 1 ELSE 0 END AS derniere_simulation
    FROM capacite_end c
    WHERE c.dat_saisie >= DATE '2014-01-01'
) s
LEFT JOIN (
{personnel}
) e ON e.cod_soc = s.cod_soc AND e.mat_pers = s.mat_pers
