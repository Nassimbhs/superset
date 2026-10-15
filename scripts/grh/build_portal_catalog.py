"""Generate the Bulle RH catalog (docker/pythonpath_dev/grh_portal/catalog.json).

The catalog lists, for every GRH domain, its datasets (Superset ids, columns,
metrics, filters, dimensions), the business questions offered by the search
(one per dashboard chart + portal_presets.EXTRA_PRESETS) and the KPI dictionary.

Usage:
    python build_portal_catalog.py
Env: SUPERSET_URL, SUPERSET_USER, SUPERSET_PASSWORD (to read dataset columns)
Run it again after build_dashboards.py whenever a spec changes.
"""
from __future__ import annotations

import importlib
import json
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import export_guide
import grh_builder
import portal_presets as pp
from superset_client import SupersetClient

OUT_FILE = grh_builder.HERE.parents[1] / "docker" / "pythonpath_dev" / "grh_portal" / "catalog.json"
STATUS_COLUMN = "ETAT"
ACTIVE_FLAG = "EST_ACTIF"
TEMPORAL_PREFIXES = ("DAT_", "DT_", "DATE_")


def column_label(name: str, filter_labels: dict[str, str]) -> str:
    return pp.COLUMN_LABELS.get(name) or filter_labels.get(name) or name.replace("_", " ").capitalize()


def is_temporal(col: dict[str, Any]) -> bool:
    name = col["column_name"]
    return bool(col.get("is_dttm")) or name.startswith(TEMPORAL_PREFIXES) or name == "JOUR"


def filter_constants(spec: ModuleType) -> list[tuple[str, dict]]:
    return [(name, value) for name, value in vars(spec).items()
            if name.isupper() and isinstance(value, dict) and "expressionType" in value]


def condition_label(domain: str, flt: dict, constants: list[tuple[str, dict]]) -> str:
    for name, value in constants:
        if value == flt:
            return pp.CONDITION_LABELS.get(f"{domain}.{name}") or pp.CONDITION_LABELS.get(name) \
                or name.replace("_", " ").capitalize()
    if flt["expressionType"] == "SQL":
        return flt["sqlExpression"]
    return f"{flt['subject']} {flt['operator']} {flt['comparator']}"


# --------------------------------------------------------------------------- datasets


def build_dataset(domain: str, spec: ModuleType, ds: grh_builder.Dataset, ds_id: int,
                  api_columns: list[dict[str, Any]], chart_specs: dict[str, grh_builder.Chart]) -> dict[str, Any]:
    names = [c["column_name"] for c in api_columns]
    present = set(names)
    domain_filters = [f for f in spec.FILTERS if isinstance(f, grh_builder.Filter) and f.dataset == ds.key]
    filter_labels = {f.column: f.label for f in spec.FILTERS if isinstance(f, grh_builder.Filter)}
    temporal = [c["column_name"] for c in api_columns if is_temporal(c)]
    has_status = ACTIVE_FLAG in present and STATUS_COLUMN in present

    filters: list[str] = []
    if has_status:
        filters.append(STATUS_COLUMN)
    for col in [f.column for f in domain_filters] + pp.STANDARD_FILTERS:
        if col in present and col not in filters and not (col == STATUS_COLUMN and not has_status):
            filters.append(col)

    dims: list[str] = []
    own_charts = [c for c in chart_specs.values() if c.dataset == ds.key]
    for chart in own_charts:
        p = chart.params
        if p.get("query_mode") == "raw":
            continue
        candidates = [*p.get("groupby", []), p.get("source"), p.get("target")]
        if not p.get("x_axis_is_time"):
            candidates.insert(0, p.get("x_axis"))
        dims.extend(c for c in candidates if c)
    dims.extend(f.column for f in domain_filters)
    dims.extend(pp.STANDARD_DIMENSIONS)
    if has_status:
        dims.append(STATUS_COLUMN)
    dimensions = [d for i, d in enumerate(dims) if d in present and d not in dims[:i] and d not in temporal]

    raw_tables = [c for c in own_charts if c.params.get("query_mode") == "raw"]
    detail = raw_tables[0].params["all_columns"] if raw_tables else pp.DEFAULT_DETAIL_COLUMNS
    detail = [c for c in detail if c in present]
    if not detail:
        detail = (["MAT_PERS", "NOM_PRENOM"] if "MAT_PERS" in present else []) + dimensions[:6]
        detail = [c for c in detail if c in present]

    default_label = ds.name.removeprefix("v_").removeprefix("grh_").removesuffix("_grh").replace("_", " ").capitalize()
    return {
        "id": ds_id,
        "domain": domain,
        "name": ds.name,
        "label": pp.DATASET_LABELS.get(f"{domain}.{ds.key}", default_label),
        "main_dttm_col": ds.main_dttm_col,
        "has_status": has_status,
        "has_company": "COD_SOC" in present,
        "columns": {n: column_label(n, filter_labels) for n in names},
        "temporal": temporal,
        "metrics": [
            {"name": m.name, "label": m.verbose, "expression": m.expression, "format": m.d3format}
            for m in ds.metrics
        ],
        "filters": filters,
        "dimensions": dimensions,
        "detail_columns": detail,
    }


# --------------------------------------------------------------------------- presets


def chart_preset(domain: str, key: str, chart: grh_builder.Chart, dataset: dict[str, Any],
                 constants: list[tuple[str, dict]]) -> dict[str, Any] | None:
    p = chart.params
    viz = p["viz_type"]
    preset: dict[str, Any] = {
        "id": f"{domain}.{key}", "domain": domain, "label": chart.name, "keywords": [],
        "dataset": f"{domain}.{chart.dataset}", "metrics": [], "groupby": None, "series": None,
        "grain": None, "time_column": None, "filters": {}, "conditions": [], "view": "bar",
        "subheader": p.get("subheader") or "",
    }
    if viz == "big_number_total":
        preset.update(metrics=[p["metric"]], view="kpi")
    elif viz in ("echarts_timeseries_bar", "echarts_timeseries_line"):
        preset["metrics"] = list(p["metrics"])
        if p.get("x_axis_is_time"):
            preset["grain"] = p.get("time_grain_sqla") or "P1Y"
            if p["x_axis"] != dataset["main_dttm_col"]:
                preset["time_column"] = p["x_axis"]
        else:
            preset["groupby"] = p["x_axis"]
        preset["series"] = (p.get("groupby") or [None])[0]
        preset["view"] = "line" if viz == "echarts_timeseries_line" else "bar"
    elif viz == "pie":
        preset.update(metrics=[p["metric"]], groupby=p["groupby"][0], view="pie")
    elif viz == "sankey_v2":
        preset.update(metrics=[p["metric"]], groupby=p["source"], series=p["target"], view="table")
    elif viz == "table" and p.get("query_mode") == "aggregate":
        groupby = p["groupby"]
        preset.update(metrics=list(p["metrics"]), groupby=groupby[0],
                      series=groupby[1] if len(groupby) > 1 else None, view="table")
    elif viz == "table":
        preset.update(metrics=[dataset["metrics"][0]["name"]], view="detail",
                      detail_columns=[c for c in p["all_columns"] if c in dataset["columns"]])
    else:
        return None

    apply_filters(preset, p.get("adhoc_filters", []), domain, dataset, constants)
    return preset


def apply_filters(preset: dict[str, Any], adhoc_filters: list[dict], domain: str, dataset: dict[str, Any],
                  constants: list[tuple[str, dict]]) -> None:
    """Equality filters on filter-bar columns pre-fill the bar; the others stay as fixed conditions."""
    for flt in adhoc_filters:
        if flt.get("operator") == "TEMPORAL_RANGE":
            continue
        if flt["expressionType"] == "SIMPLE" and flt["operator"] == "==":
            col, val = flt["subject"], flt["comparator"]
            if col == ACTIVE_FLAG and val == 1 and dataset["has_status"]:
                preset["filters"][STATUS_COLUMN] = ["Actif"]
                continue
            if col in dataset["filters"]:
                preset["filters"][col] = [val]
                continue
        cond = ({"sql": flt["sqlExpression"]} if flt["expressionType"] == "SQL"
                else {"col": flt["subject"], "op": flt["operator"], "val": flt["comparator"]})
        preset["conditions"].append({"label": condition_label(domain, flt, constants), **cond})


def extra_preset(index: int, extra: pp.Preset, dataset: dict[str, Any]) -> dict[str, Any]:
    preset = {
        "id": f"{extra.domain}.extra{index}", "domain": extra.domain, "label": extra.label,
        "keywords": extra.keywords, "dataset": f"{extra.domain}.{extra.dataset}", "metrics": extra.metrics,
        "groupby": extra.groupby, "series": extra.series, "grain": extra.grain, "time_column": None,
        "filters": dict(extra.filters), "conditions": [], "view": extra.view, "subheader": "",
    }
    spec = importlib.import_module(f"dashboards.{extra.domain}")
    constants = filter_constants(spec)
    unknown = [name for name in extra.conditions if not isinstance(getattr(spec, name, None), dict)]
    if unknown:
        raise SystemExit(f"Preset '{extra.label}': conditions inconnues dans dashboards/{extra.domain}.py {unknown}")
    apply_filters(preset, [getattr(spec, name) for name in extra.conditions], extra.domain, dataset, constants)
    return preset


# --------------------------------------------------------------------------- KPI dictionary


def guide_kpi_rows() -> list[list[str]]:
    for block in export_guide.KPIS:
        if block[0] == "table":
            return block[2]
    return []


def build_kpis(domains: dict[str, Any], datasets: dict[str, Any],
               usage: dict[tuple[str, str], list[dict[str, str]]]) -> list[dict[str, Any]]:
    kpis: list[dict[str, Any]] = []
    linked: set[tuple[str, str]] = set()
    for label, formula, dashboard in guide_kpi_rows():
        ds_key, metric_name = pp.KPI_METRICS.get(label, (None, None))
        entry: dict[str, Any] = {
            "label": label, "definition": formula, "dashboard": dashboard, "source": "guide",
            "domain": None, "dataset": ds_key, "metric": metric_name, "expression": None, "format": None,
            "used_in": [],
        }
        if ds_key and ds_key in datasets:
            ds = datasets[ds_key]
            metric = next((m for m in ds["metrics"] if m["name"] == metric_name), None)
            if metric:
                entry.update(domain=ds["domain"], expression=metric["expression"], format=metric["format"],
                             used_in=usage.get((ds_key, metric_name), []))
                linked.add((ds_key, metric_name))
        kpis.append(entry)

    for ds_key, ds in datasets.items():
        domain = domains[ds["domain"]]
        for m in ds["metrics"]:
            if (ds_key, m["name"]) in linked:
                continue
            used = usage.get((ds_key, m["name"]), [])
            subheaders = sorted({u["subheader"] for u in used if u["subheader"]})
            definition = f"{m['label']} ({', '.join(subheaders)})" if subheaders else m["label"]
            kpis.append({
                "label": m["label"], "definition": definition, "dashboard": domain["title"], "source": "metric",
                "domain": ds["domain"], "dataset": ds_key, "metric": m["name"], "expression": m["expression"],
                "format": m["format"], "used_in": used,
            })
    return kpis


# --------------------------------------------------------------------------- main


def main() -> None:
    client = SupersetClient()
    ids = grh_builder.load_ids()
    domains: dict[str, Any] = {}
    datasets: dict[str, Any] = {}
    presets: list[dict[str, Any]] = []
    usage: dict[tuple[str, str], list[dict[str, str]]] = {}

    for key, nav_label, slug in grh_builder.SUITE:
        spec = importlib.import_module(f"dashboards.{key}")
        if key not in ids:
            print(f"!! {key}: absent de grh_ids.json, lancer build_dashboards.py --only {key}")
            continue
        domains[key] = {
            "key": key, "title": spec.TITLE, "nav_label": nav_label, "slug": slug,
            "question": export_guide.DASHBOARD_QUESTIONS.get(key, ""),
            "synonyms": pp.DOMAIN_SYNONYMS.get(key, []),
        }
        chart_specs = spec.charts(ids[key]["datasets"])
        for ds in spec.DATASETS:
            ds_id = ids[key]["datasets"][ds.key]
            api = client.get(f"/api/v1/dataset/{ds_id}")["result"]
            datasets[f"{key}.{ds.key}"] = build_dataset(key, spec, ds, ds_id, api["columns"], chart_specs)
        constants = filter_constants(spec)
        for chart_key, chart in chart_specs.items():
            ds_key = f"{key}.{chart.dataset}"
            preset = chart_preset(key, chart_key, chart, datasets[ds_key], constants)
            if not preset:
                continue
            presets.append(preset)
            for metric in preset["metrics"]:
                usage.setdefault((ds_key, metric), []).append(
                    {"chart": chart.name, "subheader": preset["subheader"]})
        print(f"{key}: {len(spec.DATASETS)} datasets, {len(chart_specs)} questions")

    for i, extra in enumerate(pp.EXTRA_PRESETS, start=1):
        ds = datasets.get(f"{extra.domain}.{extra.dataset}")
        if not ds:
            raise SystemExit(f"Preset '{extra.label}': dataset inconnu {extra.domain}.{extra.dataset}")
        missing = [m for m in extra.metrics if m not in {x["name"] for x in ds["metrics"]}]
        cols = [c for c in (extra.groupby, extra.series, *extra.filters) if c]
        missing += [c for c in cols if c not in ds["columns"]]
        if missing:
            raise SystemExit(f"Preset '{extra.label}': champs inconnus {missing}")
        presets.append(extra_preset(i, extra, ds))

    catalog = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "default_company": pp.DEFAULT_COMPANY,
        "domains": list(domains.values()),
        "datasets": datasets,
        "presets": presets,
        "word_synonyms": pp.WORD_SYNONYMS,
        "kpis": build_kpis(domains, datasets, usage),
        "glossary": [{"term": t, "definition": d} for t, d in export_guide.GLOSSARY],
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(domains)} domaines, {len(datasets)} datasets, {len(presets)} questions, "
          f"{len(catalog['kpis'])} KPI -> {OUT_FILE}")


if __name__ == "__main__":
    main()
