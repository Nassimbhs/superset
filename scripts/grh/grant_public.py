"""Donne au rôle Public l'accès en lecture à tous les datasets GRH et génère
les liens de partage (tableaux de bord + graphiques) dans exports/public_links.csv.

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
    out, n = write_links(ids, args.base_url.rstrip("/"), args.cod_soc)
    print(f"{len(ids)} tableaux de bord, {n} graphiques -> {out}")


if __name__ == "__main__":
    main()
