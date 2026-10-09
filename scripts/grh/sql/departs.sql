SELECT
    e.cod_soc,
    e.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.grade,
    e.fonction,
    NVL(e.type_depart, 'Non renseigné') AS type_depart,
    e.dat_depart,
    TO_CHAR(e.dat_depart, 'YYYY') AS annee,
    TRUNC(MONTHS_BETWEEN(e.dat_depart, e.dat_nais) / 12) AS age_depart,
    TRUNC(MONTHS_BETWEEN(e.dat_depart, e.dat_emb) / 12) AS anciennete_depart,
    CASE WHEN e.dat_depart BETWEEN ADD_MONTHS(TRUNC(SYSDATE), -12) AND SYSDATE THEN 1 ELSE 0 END AS dernier_12_mois,
    (SELECT COUNT(*) FROM personnel pa WHERE pa.etat_act = '0' AND pa.cod_soc = e.cod_soc) AS effectif_actif
FROM (
{personnel}
) e
WHERE e.dat_depart >= DATE '1980-01-01'
  AND e.dat_depart <= ADD_MONTHS(TRUNC(SYSDATE), 12)
