"""List databases, schemas and tables in Superset; optionally dump columns.

Usage:
    python discover.py                      # databases + schemas
    python discover.py <db_id> <schema>     # tables in schema
    python discover.py <db_id> <schema> <table> [<table> ...]  # columns
"""
import json
import sys

from superset_client import SupersetClient


def main() -> None:
    client = SupersetClient()
    args = sys.argv[1:]
    if not args:
        for db in client.get("/api/v1/database/", params={"q": "(page_size:100)"})["result"]:
            print(f"[{db['id']}] {db['database_name']} ({db.get('backend')})")
            try:
                schemas = client.get(f"/api/v1/database/{db['id']}/schemas/")["result"]
                print("    schemas:", ", ".join(schemas))
            except RuntimeError as ex:
                print("    schemas: ERROR", ex)
        return

    db_id, schema = args[0], args[1]
    if len(args) == 2:
        q = f"(schema_name:'{schema}',force:!f)"
        res = client.get(f"/api/v1/database/{db_id}/tables/", params={"q": q})
        for t in res["result"]:
            print(t["type"], t["value"])
        return

    for table in args[2:]:
        meta = client.get(
            f"/api/v1/database/{db_id}/table_metadata/",
            params={"name": table, "schema": schema},
        )
        print(f"== {schema}.{table}")
        for col in meta.get("columns", []):
            print(f"   {col['name']:<35} {col.get('type')}")
        print("   pk:", json.dumps(meta.get("primaryKey")), "fk:", json.dumps(meta.get("foreignKeys")))


if __name__ == "__main__":
    main()
