"""One-off adjustments of the GRH content after restoring a Superset 4.1 metadata
database into Superset 6.1 (run after `superset db upgrade` / superset-init).

Superset 6 runs dataset SQL through sqlglot before sending it to Oracle, which
breaks two constructs of the GRH datasets:
  - TRUNC(<number>) is rewritten to TRUNC(<number>, 'DD')  -> ORA-01722
  - CROSS JOIN LATERAL (...) g is rewritten to ... AS g     -> ORA-00907
It also uses pandas 2, which cannot average the strings cx_Oracle returns for
Oracle NUMBER columns unless SQLAlchemy returns floats (coerce_to_decimal).

Dataset SQL is patched fragment by fragment instead of being regenerated from
sql/*.sql, so that edits made in the Superset UI are kept. The script is
idempotent. Dry run by default; pass --apply to write.

    SUPERSET_URL=http://localhost:8088 python migrate_to_6_1.py [--apply]
"""

import json
import re
import sys

from superset_client import SupersetClient

TRUNC_COMMENT = (
    "    -- No single-argument TRUNC on numbers: Superset 6 (sqlglot) rewrites TRUNC(n) to TRUNC(n, 'DD').\n"
)

# (old, new) fragments, matching sql/*.sql of the 4.1 and 6.1 trees line for line.
PATCHES = [
    (
        "    TRUNC(MONTHS_BETWEEN(SYSDATE, p.dat_nais) / 12) AS age,",
        TRUNC_COMMENT + "    FLOOR(MONTHS_BETWEEN(SYSDATE, p.dat_nais) / 12) AS age,",
    ),
    (
        "    TRUNC(MONTHS_BETWEEN(SYSDATE, p.dat_emb) / 12) AS anciennete,",
        "    SIGN(MONTHS_BETWEEN(SYSDATE, p.dat_emb)) * FLOOR(ABS(MONTHS_BETWEEN(SYSDATE, p.dat_emb)) / 12) AS anciennete,",
    ),
    (
        "    TRUNC(MONTHS_BETWEEN(f.dat_creat_fiche, f.dat_nais) / 12) AS age_candidature,",
        "    FLOOR(MONTHS_BETWEEN(f.dat_creat_fiche, f.dat_nais) / 12) AS age_candidature,",
    ),
    (
        "    TRUNC(MONTHS_BETWEEN(e.dat_depart, e.dat_nais) / 12) AS age_depart,",
        "    FLOOR(MONTHS_BETWEEN(e.dat_depart, e.dat_nais) / 12) AS age_depart,",
    ),
    (
        "    TRUNC(MONTHS_BETWEEN(e.dat_depart, e.dat_emb) / 12) AS anciennete_depart,",
        "    SIGN(MONTHS_BETWEEN(e.dat_depart, e.dat_emb)) * FLOOR(ABS(MONTHS_BETWEEN(e.dat_depart, e.dat_emb)) / 12) AS anciennete_depart,",
    ),
    (
        "    TRUNC(MONTHS_BETWEEN(e.dat_emb, e.dat_nais) / 12) AS age_recrutement",
        "    FLOOR(MONTHS_BETWEEN(e.dat_emb, e.dat_nais) / 12) AS age_recrutement",
    ),
    (
        "    TRUNC(MONTHS_BETWEEN(r.date_retraite, TRUNC(SYSDATE))) AS mois_restants,",
        TRUNC_COMMENT
        + "    SIGN(MONTHS_BETWEEN(r.date_retraite, TRUNC(SYSDATE)))\n"
        "        * FLOOR(ABS(MONTHS_BETWEEN(r.date_retraite, TRUNC(SYSDATE)))) AS mois_restants,",
    ),
    (
        "    CASE WHEN g.accorde = 1 THEN d.mnt_acc END AS mnt_accorde,\n"
        "    g.accorde,",
        "    CASE WHEN d.accorde = 1 THEN d.mnt_acc END AS mnt_accorde,\n"
        "    d.accorde,",
    ),
    (
        "        WHEN g.accorde = 1 AND TRUNC(SYSDATE) BETWEEN d.dat_debut AND d.dat_fin THEN 1 ELSE 0",
        "        WHEN d.accorde = 1 AND TRUNC(SYSDATE) BETWEEN d.dat_debut AND d.dat_fin THEN 1 ELSE 0",
    ),
    (
        "FROM demande_pret d\n"
        "CROSS JOIN LATERAL (\n"
        "    -- Since 2025 granted loans stay in status 'S' but carry an amount and a repayment start date.\n"
        "    SELECT CASE\n"
        "        WHEN d.cod_etat_pret = 'A' OR (d.mnt_acc > 0 AND d.dat_debut IS NOT NULL) THEN 1 ELSE 0\n"
        "    END AS accorde\n"
        "    FROM dual\n"
        ") g",
        "-- No LATERAL join: Superset 6 (sqlglot) renders its alias as \"AS g\", which Oracle rejects.\n"
        "FROM (\n"
        "    SELECT\n"
        "        dp.*,\n"
        "        -- Since 2025 granted loans stay in status 'S' but carry an amount and a repayment start date.\n"
        "        CASE\n"
        "            WHEN dp.cod_etat_pret = 'A' OR (dp.mnt_acc > 0 AND dp.dat_debut IS NOT NULL) THEN 1 ELSE 0\n"
        "        END AS accorde\n"
        "    FROM demande_pret dp\n"
        ") d",
    ),
]

# Ages from a birth date, also used by datasets written by hand in the UI.
# The value is never negative, so FLOOR gives the same result as TRUNC.
REGEX_PATCHES = [
    (
        re.compile(r"TRUNC\((\s*MONTHS_BETWEEN\(\s*SYSDATE\s*,\s*\w+\.dat_nais\s*\)\s*/\s*12\s*)\)"),
        r"FLOOR(\1)",
    ),
]

# Constructs that still fail under Superset 6 if a dataset was not covered above.
SUSPICIOUS = ("TRUNC(MONTHS_BETWEEN", "CROSS JOIN LATERAL")


def list_all(client: SupersetClient, resource: str, columns: str) -> list[dict]:
    rows, page = [], 0
    while True:
        q = f"(columns:!({columns}),page:{page},page_size:100)"
        chunk = client.get(f"/api/v1/{resource}/", params={"q": q})["result"]
        rows += chunk
        if len(chunk) < 100:
            return rows
        page += 1


def migrate_databases(client: SupersetClient, apply: bool) -> None:
    for db in list_all(client, "database", "id,database_name,backend"):
        if db["backend"] != "oracle":
            continue
        # GET /api/v1/database/<id> omits `extra` in 6.1; /connection returns it.
        conn = client.get(f"/api/v1/database/{db['id']}/connection")["result"]
        extra = json.loads(conn.get("extra") or "{}")
        if extra.get("engine_params", {}).get("coerce_to_decimal") is False:
            print(f"database {db['database_name']:26} unchanged")
            continue
        extra.setdefault("engine_params", {})["coerce_to_decimal"] = False
        if apply:
            try:
                client.put(f"/api/v1/database/{db['id']}", {"extra": json.dumps(extra)})
            except RuntimeError as exc:
                # Superset tests the connection before saving and refuses unreachable databases.
                print(f"database {db['database_name']:26} NOT UPDATED, set it in the UI once reachable: {exc}")
                continue
        print(f"database {db['database_name']:26} {'updated' if apply else 'would update'}: {json.dumps(extra)}")


def migrate_datasets(client: SupersetClient, apply: bool) -> None:
    for ds in list_all(client, "dataset", "id,table_name,kind"):
        if ds.get("kind") != "virtual":
            continue
        raw = client.get(f"/api/v1/dataset/{ds['id']}")["result"]["sql"] or ""
        sql = raw.replace("\r\n", "\n")
        patched, hits = sql, 0
        for old, new in PATCHES:
            hits += patched.count(old)
            patched = patched.replace(old, new)
        for pattern, repl in REGEX_PATCHES:
            patched, count = pattern.subn(repl, patched)
            hits += count
        leftover = [frag for frag in SUSPICIOUS if frag in patched]
        warning = f"  CHECK BY HAND, still contains {leftover}" if leftover else ""
        if patched == sql:
            if warning:
                print(f"dataset  {ds['table_name']:26} unchanged{warning}")
            continue
        if apply:
            client.put(f"/api/v1/dataset/{ds['id']}", {"sql": patched})
        print(f"dataset  {ds['table_name']:26} {'updated' if apply else 'would update'}: {hits} fragment(s){warning}")


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    client = SupersetClient()
    migrate_databases(client, apply)
    migrate_datasets(client, apply)
    if not apply:
        print("dry run, pass --apply to write")
