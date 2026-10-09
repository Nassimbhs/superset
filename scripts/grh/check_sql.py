"""Run a summary query over a dataset SQL file before publishing it.

Usage: python check_sql.py <file.sql> ["<select over v>"]
Default summary: SELECT COUNT(*) FROM (<sql>) v
"""
import sys

from grh_builder import DATABASE_NAME, find_database, render_sql
from sql import run_sql
from superset_client import SupersetClient

if __name__ == "__main__":
    body = render_sql(sys.argv[1])
    outer = sys.argv[2] if len(sys.argv) > 2 else "SELECT COUNT(*) AS n FROM v"
    client = SupersetClient()
    sql = outer.replace("FROM v", f"FROM (\n{body}\n) v", 1)
    res = run_sql(client, find_database(client, DATABASE_NAME), sql)
    cols = [c["column_name"] for c in res.get("columns", [])]
    print(" | ".join(cols))
    for row in res.get("data", []):
        print(" | ".join(str(row.get(c)) for c in cols))
