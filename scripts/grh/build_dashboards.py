"""Build or update the GRH dashboards suite.

Usage:
    python build_dashboards.py                     # all dashboards
    python build_dashboards.py --only conges,prets # a subset
Env: SUPERSET_URL, SUPERSET_USER, SUPERSET_PASSWORD
"""
import argparse
import importlib
import sys

import grh_builder
from superset_client import SupersetClient


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma-separated keys: " + ",".join(k for k, *_ in grh_builder.SUITE))
    parser.add_argument("--database", default=grh_builder.DATABASE_NAME)
    args = parser.parse_args(argv)

    keys = [k for k, *_ in grh_builder.SUITE]
    if args.only:
        wanted = [k.strip() for k in args.only.split(",")]
        unknown = set(wanted) - set(keys)
        if unknown:
            sys.exit(f"Unknown dashboards: {', '.join(sorted(unknown))}")
        keys = [k for k in keys if k in wanted]

    client = SupersetClient()
    db_id = grh_builder.find_database(client, args.database)
    ids = grh_builder.load_ids()
    print(f"css template '{grh_builder.THEME_NAME}': id={grh_builder.upsert_css_template(client)}")
    for key in keys:
        spec = importlib.import_module(f"dashboards.{key}")
        ids[key] = grh_builder.build(client, spec, db_id)
        grh_builder.save_ids(ids)
    print("done")


if __name__ == "__main__":
    main()
