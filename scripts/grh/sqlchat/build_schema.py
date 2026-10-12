"""Build the schema shown to the GRH SQL chatbot: one flat view per GRH dataset.

For every dataset of the dashboard suite: its view name (v_grh_*), dashboard, columns
(Oracle type, French label, sample values of low-cardinality text columns), the
dashboard metrics as SQL expressions, the SQL substituted for the view at run time and
the Superset dataset id used for the access check. Names of employees are never listed.

Usage: python sqlchat/build_schema.py [--out ../../docker/pythonpath_dev/grh_sql_chat/schema.json]
Env: SUPERSET_URL, SUPERSET_USER, SUPERSET_PASSWORD
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from urllib.parse import quote

GRH_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GRH_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from examples import EXAMPLES, SUGGESTIONS  # noqa: E402
from export_doc import CONVENTIONS, DESCRIPTIONS, RULES, col_label  # noqa: E402
from grh_builder import DATABASE_NAME, SUITE, find_database, load_ids, render_sql  # noqa: E402
from superset_client import SupersetClient  # noqa: E402
from view_docs import VIEW_DOCS  # noqa: E402

DEFAULT_OUT = GRH_DIR.parent.parent / "docker" / "pythonpath_dev" / "grh_sql_chat" / "schema.json"

MAX_VALUES = 15
MAX_DISTINCT = 60
NUMERIC_TYPES = ("INT", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "NUMBER", "LONG", "BIGINT", "REAL")
TEXT_WITHOUT_TYPE = {"OBJET_PRET"}
PRIVATE_COLUMNS = {"NOM_PRENOM", "MAT_PERS", "MAT_PERS_INT", "NUM_DECISION", "CIRCONSTANCES", "NUM_ACC", "NUM_FICHE"}


def oracle_type(col: dict) -> str:
    name = col["column_name"]
    col_type = (col.get("type") or "").upper()
    if col.get("is_dttm") or name.startswith(("DAT_", "DATE_", "DT_")) or col_type.startswith(("DATE", "TIMESTAMP")):
        return "DATE"
    if col_type.startswith(NUMERIC_TYPES) or (not col_type and name not in TEXT_WITHOUT_TYPE):
        return "NUMBER"
    return "VARCHAR2"


def column_values(client: SupersetClient, ds_id: int, column: str) -> tuple[list[str], int]:
    try:
        res = client.get(f"/api/v1/datasource/table/{ds_id}/column/{quote(column)}/values/")
    except RuntimeError as exc:
        print(f"    valeurs indisponibles pour {column}: {str(exc)[:120]}")
        return [], 0
    values = sorted({str(v) for v in res.get("result", []) if v is not None and str(v).strip()}, key=str.lower)
    return values, len(values)


def build_view(client: SupersetClient, dash_key: str, ds, ds_id: int) -> dict:
    detail = client.get(f"/api/v1/dataset/{ds_id}")["result"]
    columns = []
    for col in detail["columns"]:
        name = col["column_name"]
        entry = {"name": name, "type": oracle_type(col), "label": col_label(name)}
        if entry["type"] == "VARCHAR2" and name not in PRIVATE_COLUMNS:
            values, count = column_values(client, ds_id, name)
            if 0 < count <= MAX_DISTINCT:
                entry["values"] = values[:MAX_VALUES]
                entry["distinct"] = count
        columns.append(entry)
    metrics = [{"name": m.name, "label": m.verbose, "sql": m.expression,
                "rule": RULES.get((dash_key, m.name), "")} for m in ds.metrics]
    print(f"  {ds.name}: {len(columns)} colonnes, {len(metrics)} indicateurs")
    return {
        "name": ds.name.lower(),
        "dataset_id": ds_id,
        "dashboard": dash_key,
        "date_col": ds.main_dttm_col,
        "columns": columns,
        "metrics": metrics,
        "sql": render_sql(ds.sql_file),
    }


def attach_docs(views: dict) -> None:
    """Merge the fiche of every view; a missing fiche or an unknown column is an error."""
    errors = [f"{name} : fiche absente de view_docs.py" for name in views if name not in VIEW_DOCS]
    errors += [f"{name} : fiche sans vue" for name in VIEW_DOCS if name not in views]
    for name, doc in VIEW_DOCS.items():
        if name not in views:
            continue
        columns = {c["name"] for c in views[name]["columns"]}
        cited = list(doc["measures"]) + list(doc["dimensions"])
        errors += [f"{name} : colonne inconnue {c}" for c in cited if c not in columns]
        missing = {"description", "grain", "measures", "dimensions", "rules", "not_for"} - set(doc)
        errors += [f"{name} : champ manquant {m}" for m in sorted(missing)]
        views[name]["doc"] = doc
    if errors:
        raise SystemExit("fiches des vues invalides :\n  " + "\n  ".join(errors))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--docs-only", action="store_true",
                        help="met à jour les fiches et les exemples du schema.json existant, sans appeler Superset")
    args = parser.parse_args()

    if args.docs_only:
        schema = json.loads(args.out.read_text(encoding="utf-8"))
        attach_docs(schema["views"])
        schema["examples"] = EXAMPLES
        args.out.write_text(json.dumps(schema, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(VIEW_DOCS)} fiches, {len(EXAMPLES)} exemples -> {args.out}")
        return

    client = SupersetClient()
    ids = load_ids()
    schema: dict = {"database": DATABASE_NAME, "database_id": find_database(client, DATABASE_NAME),
                    "dashboards": {}, "views": {}}
    for key, label, slug in SUITE:
        spec = importlib.import_module(f"dashboards.{key}")
        print(f"== {spec.TITLE}")
        ds_ids = ids.get(key, {}).get("datasets", {})
        views = []
        for ds in spec.DATASETS:
            if ds.key not in ds_ids:
                print(f"  {ds.name}: absent de grh_ids.json, ignoré")
                continue
            view = build_view(client, key, ds, ds_ids[ds.key])
            schema["views"][view["name"]] = view
            views.append(view["name"])
        schema["dashboards"][slug] = {"key": key, "label": label, "title": spec.TITLE,
                                      "description": DESCRIPTIONS.get(key, ""), "views": views,
                                      "suggestions": SUGGESTIONS.get(key, [])}

    unknown = {e["view"] for e in EXAMPLES} - set(schema["views"])
    if unknown:
        raise SystemExit(f"exemples sur des vues inconnues : {sorted(unknown)}")
    attach_docs(schema["views"])
    schema["examples"] = EXAMPLES
    schema["conventions"] = [{"term": t, "definition": d} for t, d in CONVENTIONS]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(schema, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(schema['dashboards'])} dashboards, {len(schema['views'])} vues, "
          f"{len(EXAMPLES)} exemples -> {args.out}")


if __name__ == "__main__":
    main()
