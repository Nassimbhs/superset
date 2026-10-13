"""Run every chart of every GRH dashboard and export each dashboard as a ZIP.

Usage: python verify_dashboard.py [--only effectif,conges]
"""
import argparse
import json
import sys

from grh_builder import HERE, load_ids
from superset_client import SupersetClient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    args = parser.parse_args()

    client = SupersetClient()
    ids = load_ids()
    keys = [k.strip() for k in args.only.split(",")] if args.only else list(ids)
    exports = HERE / "exports"
    exports.mkdir(exist_ok=True)
    failures = 0
    for key in keys:
        entry = ids[key]
        print(f"== {key} ({entry['slug']})")
        for chart_key, chart_id in entry["charts"].items():
            chart = client.get(f"/api/v1/chart/{chart_id}")["result"]
            qc = json.loads(chart["query_context"])
            qc["force"] = True
            res = client.session.post(f"{client.url}/api/v1/chart/data", json=qc)
            body = res.json()
            if res.status_code == 200:
                result = body["result"][0]
                status = "OK   " if result["rowcount"] else "EMPTY"
                sample = json.dumps(result["data"][:2], ensure_ascii=False, default=str)[:140]
                print(f"  {status} {chart['slice_name']}: {result['rowcount']} rows  {sample}")
            else:
                failures += 1
                print(f"  FAIL  {chart['slice_name']}: {res.status_code} "
                      f"{json.dumps(body, ensure_ascii=False)[:600]}")

        page = client.session.get(f"{client.url}/superset/dashboard/{entry['slug']}/")
        attached = client.get(f"/api/v1/dashboard/{entry['dashboard']}/charts")["result"]
        print(f"  page {page.status_code}, {len(attached)}/{len(entry['charts'])} charts attached")
        res = client.request("GET", "/api/v1/dashboard/export/", params={"q": f"!({entry['dashboard']})"})
        out = exports / f"{entry['slug']}.zip"
        out.write_bytes(res.content)
        print(f"  export: {out.name} ({len(res.content)} bytes)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
