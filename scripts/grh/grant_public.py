"""Donne au rôle Public l'accès en lecture à tous les datasets GRH, le limite à la
consultation des tableaux de bord (ni modification de graphique, ni Explore, ni SQL Lab,
ni affichage des requêtes ; téléchargement CSV/Excel autorisé) et génère les liens de
partage (tableaux de bord + graphiques) dans exports/public_links.csv.

Usage : python scripts/grh/grant_public.py [--base-url http://localhost:8088] [--cod-soc 01]
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
IDS_FILE = HERE / "grh_ids.json"
LINKS_FILE = HERE / "exports" / "public_links.csv"
DB_CONTAINER = "superset_db"

PUBLIC_READ_ONLY = [
    ("can_read", "Dashboard"), ("can_read", "Chart"),
    ("can_dashboard", "Superset"), ("can_dashboard_permalink", "Superset"), ("can_share_dashboard", "Superset"),
    ("can_explore_json", "Superset"), ("can_log", "Superset"), ("can_csv", "Superset"),
    ("can_read", "DashboardFilterStateRestApi"), ("can_write", "DashboardFilterStateRestApi"),
    ("can_read", "DashboardPermalinkRestApi"), ("can_write", "DashboardPermalinkRestApi"),
    ("can_read", "EmbeddedDashboard"), ("can_get_embedded", "Dashboard"),
    ("can_drill", "Dashboard"), ("can_view_chart_as_table", "Dashboard"),
    ("can_time_range", "Api"), ("can_query", "Api"), ("can_query_form_data", "Api"),
    ("can_read", "AdvancedDataType"), ("can_read", "AvailableDomains"), ("can_list", "AsyncEventsRestApi"),
    ("can_list", "DynamicPlugin"), ("can_show", "DynamicPlugin"), ("can_get", "MenuApi"),
    ("can_get_value", "KV"), ("can_store", "KV"),
    ("menu_access", "Dashboards"), ("menu_access", "Home"),
]


def psql(sql: str) -> str:
    out = subprocess.run(
        ["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", "superset", "-d", "superset",
         "-At", "-v", "ON_ERROR_STOP=1"],
        input=sql, capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return out.stdout.strip()


def grant(dataset_ids: list[int]) -> str:
    patterns = ",".join(f"'%(id:{i})'" for i in dataset_ids)
    return psql(f"""
\\set QUIET on
INSERT INTO ab_permission_view_role (id, permission_view_id, role_id)
SELECT nextval('ab_permission_view_role_id_seq'), pv.id, r.id
FROM ab_permission_view pv
JOIN ab_permission p ON p.id = pv.permission_id AND p.name = 'datasource_access'
JOIN ab_view_menu v ON v.id = pv.view_menu_id
CROSS JOIN ab_role r
WHERE r.name = 'Public'
  AND v.name LIKE '[ENDADB].%'
  AND v.name LIKE ANY (ARRAY[{patterns}])
  AND NOT EXISTS (
    SELECT 1 FROM ab_permission_view_role x
    WHERE x.permission_view_id = pv.id AND x.role_id = r.id);
SELECT count(*) FROM ab_permission_view_role x
JOIN ab_role r ON r.id = x.role_id AND r.name = 'Public'
JOIN ab_permission_view pv ON pv.id = x.permission_view_id
JOIN ab_view_menu v ON v.id = pv.view_menu_id
WHERE v.name LIKE ANY (ARRAY[{patterns}]);
""")


def restrict_to_read_only() -> str:
    """Replace every non-datasource permission of Public with PUBLIC_READ_ONLY."""
    pairs = ",".join(f"('{p}', '{v}')" for p, v in PUBLIC_READ_ONLY)
    return psql(f"""
\\set QUIET on
CREATE TEMP TABLE keep (perm text, view text);
INSERT INTO keep VALUES {pairs};
DELETE FROM ab_permission_view_role x
USING ab_role r, ab_permission_view pv, ab_permission p, ab_view_menu v
WHERE r.id = x.role_id AND r.name = 'Public'
  AND pv.id = x.permission_view_id AND p.id = pv.permission_id AND v.id = pv.view_menu_id
  AND p.name NOT IN ('datasource_access', 'schema_access', 'database_access')
  AND NOT EXISTS (SELECT 1 FROM keep k WHERE k.perm = p.name AND k.view = v.name);
INSERT INTO ab_permission_view_role (id, permission_view_id, role_id)
SELECT nextval('ab_permission_view_role_id_seq'), pv.id, r.id
FROM keep k
JOIN ab_permission p ON p.name = k.perm
JOIN ab_view_menu v ON v.name = k.view
JOIN ab_permission_view pv ON pv.permission_id = p.id AND pv.view_menu_id = v.id
CROSS JOIN ab_role r
WHERE r.name = 'Public'
  AND NOT EXISTS (
    SELECT 1 FROM ab_permission_view_role x
    WHERE x.permission_view_id = pv.id AND x.role_id = r.id);
SELECT count(*) FROM ab_permission_view_role x
JOIN ab_role r ON r.id = x.role_id AND r.name = 'Public'
JOIN ab_permission_view pv ON pv.id = x.permission_view_id
JOIN ab_permission p ON p.id = pv.permission_id
WHERE p.name NOT IN ('datasource_access', 'schema_access', 'database_access');
""")


def write_links(ids: dict, base: str, cod_soc: str | None) -> tuple[Path, int]:
    LINKS_FILE.parent.mkdir(exist_ok=True)
    out = LINKS_FILE.with_name(f"public_links_{cod_soc}.csv") if cod_soc else LINKS_FILE
    soc = f"&cod_soc={quote(cod_soc)}" if cod_soc else ""
    rows = 0
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["tableau_de_bord", "type", "cle", "id", "lien", "lien_standalone"])
        for key, d in ids.items():
            dash = f"{base}/superset/dashboard/{d['slug']}/"
            w.writerow([key, "dashboard", d["slug"], d["dashboard"],
                        f"{dash}?{soc[1:]}" if soc else dash, f"{dash}?standalone=1{soc}"])
            for name, cid in d["charts"].items():
                w.writerow([key, "chart", name, cid,
                            f"{base}/explore/?slice_id={cid}{soc}",
                            f"{base}/explore/?slice_id={cid}&standalone=1{soc}"])
                rows += 1
    return out, rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8088")
    ap.add_argument("--cod-soc", help="limite les liens générés à une société (?cod_soc=XX)")
    args = ap.parse_args()
    ids = json.loads(IDS_FILE.read_text(encoding="utf-8"))
    dataset_ids = sorted({i for d in ids.values() for i in d["datasets"].values()})
    granted = grant(dataset_ids)
    print(f"Public : datasource_access sur {granted}/{len(dataset_ids)} datasets GRH")
    kept = restrict_to_read_only()
    print(f"Public : lecture seule, {kept}/{len(PUBLIC_READ_ONLY)} permissions de consultation")
    out, n = write_links(ids, args.base_url.rstrip("/"), args.cod_soc)
    print(f"{len(ids)} tableaux de bord, {n} graphiques -> {out}")


if __name__ == "__main__":
    main()
