SELECT
    f.cod_soc,
    f.num_fiche,
    TRIM(f.nom_cand) || ' ' || TRIM(f.pren_cand) AS nom_prenom,
    DECODE(f.sexe, 'M', 'Homme', 'F', 'Femme', 'Non renseigné') AS sexe,
    TRUNC(MONTHS_BETWEEN(f.dat_creat_fiche, f.dat_nais) / 12) AS age_candidature,
    CASE
        WHEN f.dat_nais IS NULL THEN 'Non renseigné'
        WHEN MONTHS_BETWEEN(f.dat_creat_fiche, f.dat_nais) / 12 < 25 THEN '1. Moins de 25 ans'
        WHEN MONTHS_BETWEEN(f.dat_creat_fiche, f.dat_nais) / 12 < 30 THEN '2. 25-29 ans'
        WHEN MONTHS_BETWEEN(f.dat_creat_fiche, f.dat_nais) / 12 < 35 THEN '3. 30-34 ans'
        WHEN MONTHS_BETWEEN(f.dat_creat_fiche, f.dat_nais) / 12 < 40 THEN '4. 35-39 ans'
        ELSE '5. 40 ans et plus'
    END AS tranche_age,
    NVL(TRIM(c.lib_concours), 'Hors concours') AS concours,
    NVL(TRIM(nr.lib_nat_recr), 'Non renseigné') AS mode_recrutement,
    CASE
        WHEN f.etat_fiche = '9' THEN 'Recruté'
        WHEN f.etat_fiche IN ('6', '8') THEN 'Admis'
        WHEN f.etat_fiche IN ('2', '3', '4') THEN 'En évaluation'
        WHEN f.etat_fiche = '1' THEN 'Candidature enregistrée'
        WHEN f.etat_fiche = '0' THEN 'Brouillon'
        ELSE 'Autre (code ' || f.etat_fiche || ')'
    END AS statut,
    CASE WHEN f.mat_pers IS NOT NULL THEN 1 ELSE 0 END AS recrute,
    f.moyen_final,
    f.classement,
    f.dat_creat_fiche,
    TO_CHAR(f.dat_creat_fiche, 'YYYY') AS annee
FROM fiche_candidat f
LEFT JOIN concours c ON c.code_concours = f.code_concours
LEFT JOIN nature_recrut nr ON nr.typ_cand = f.typ_cand
WHERE f.dat_creat_fiche IS NOT NULL
