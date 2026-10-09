SELECT
    c.cod_soc,
    c.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.est_actif,
    NVL(TRIM(t.lib_pret), NVL2(c.typ_pret, 'Type ' || c.typ_pret, 'Objet non renseigné')) AS objet_cession,
    CASE
        WHEN UPPER(t.lib_pret) LIKE '%UGTT%' OR UPPER(t.lib_pret) LIKE '%COTISATION%'
             OR TRIM(UPPER(t.lib_pret)) = 'AMICALE BTE' THEN 'Cotisations (Amicale, UGTT)'
        WHEN REGEXP_LIKE(UPPER(t.lib_pret), 'GSM|INTERNET|BOX|3G|ADSL|ORANGE|RAPIDO') THEN 'Télécom via l''Amicale'
        WHEN UPPER(t.lib_pret) LIKE '%BUVETTE%' THEN 'Buvette'
        WHEN REGEXP_LIKE(UPPER(t.lib_pret), 'BANQUE|B\.I\.A\.T|BTEI|BCT|C N S S|CNRPS|FINANCES') THEN 'Organismes financiers et sociaux'
        WHEN REGEXP_LIKE(UPPER(t.lib_pret), 'SAISON|VOYAGE|EXCURSION') THEN 'Loisirs'
        ELSE 'Autres'
    END AS famille_cession,
    DECODE(c.typ_etat, 'C', 'En cours', 'P', 'Soldée', 'Non renseigné') AS etat,
    c.prt_dat_dem,
    TO_CHAR(c.prt_dat_dem, 'YYYY') AS annee,
    NVL(c.rem_men, 0) AS mensualite,
    NVL(c.prt_mnt_dem, 0) AS montant,
    CASE WHEN c.typ_etat = 'C' AND (c.prt_dat_fin IS NULL OR c.prt_dat_fin >= TRUNC(SYSDATE))
         THEN 1 ELSE 0 END AS en_cours
FROM cession_pers c
LEFT JOIN type_pret t ON t.cod_soc = c.cod_soc AND t.cod_grp_pret = c.cod_grp_pret AND t.typ_pret = c.typ_pret
LEFT JOIN (
{personnel}
) e ON e.cod_soc = c.cod_soc AND e.mat_pers = c.mat_pers
WHERE c.prt_dat_dem IS NULL OR c.prt_dat_dem >= DATE '2000-01-01'
