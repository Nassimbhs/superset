"""Run a read-only SQL query through SQL Lab: python sql.py <db_id> "<sql>" """
import sys

from superset_client import SupersetClient


def run_sql(client: SupersetClient, db_id: int, sql: str, limit: int = 1000) -> dict:
    return client.post(
        "/api/v1/sqllab/execute/",
        {
            "database_id": db_id,
            "sql": sql,
            "runAsync": False,
            "queryLimit": limit,
            "select_as_cta": False,
            "json": True,
        },
    )


if __name__ == "__main__":
    res = run_sql(SupersetClient(), int(sys.argv[1]), sys.argv[2])
    cols = [c["column_name"] for c in res.get("columns", [])]
    print(" | ".join(cols))
    for row in res.get("data", []):
        print(" | ".join(str(row.get(c)) for c in cols))
