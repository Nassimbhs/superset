"""Shared helpers to build GRH dashboards in Superset through the REST API.

A dashboard spec is a module in ``dashboards/`` exposing:
    KEY, TITLE, SLUG
    DATASETS: list[Dataset]
    charts(ds: dict[str, int]) -> dict[str, Chart]
    LAYOUT: list[list[tuple[chart_key, width, height]]]
    FILTERS: list[Filter]
Everything is idempotent: objects are matched by name/slug and updated.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from superset_client import SupersetClient

HERE = Path(__file__).parent
SQL_DIR = HERE / "sql"
IDS_FILE = HERE / "grh_ids.json"
DATABASE_NAME = "ENDADB"

# Order defines the navigation row shown on top of every dashboard.
SUITE = [
    ("synthese", "Tableau de bord", "tableau-de-bord-rh"),
    ("effectif", "Effectif", "effectif-grh"),
    ("conges", "Congés", "conges-absences"),
    ("formation", "Formation", "formation"),
    ("departs", "Départs & retraites", "departs-retraites"),
    ("prets", "Prêts", "prets-avances"),
    ("mobilite", "Mobilité & carrière", "mobilite-carriere"),
    ("recrutement", "Recrutement", "recrutement"),
    ("sante", "Maladie & accidents", "maladie-accidents"),
    ("salaires", "Salaires", "salaires"),
    ("presence", "Présence", "presence-ponctualite"),
    ("budget", "Budget", "budget-masse-salariale"),
    ("rendement", "Rendement", "evaluation-rendement"),
    ("soins", "Soins", "couverture-medicale"),
    ("social", "Œuvres sociales", "oeuvres-sociales"),
    ("endettement", "Endettement", "endettement-cessions"),
    ("services", "Services RH", "services-rh"),
]

# Shared employee dimensions available in every dataset joined on PERSONNEL.
EMPLOYEE_FILTERS = [
    ("Pôle", "POLE"),
    ("Direction", "DIRECTION"),
    ("Catégorie", "CATEGORIE"),
    ("Sexe", "SEXE"),
]


# --------------------------------------------------------------------------- spec types


@dataclass
class Metric:
    name: str
    expression: str
    verbose: str
    d3format: str = "SMART_NUMBER"


@dataclass
class Dataset:
    key: str
    name: str
    sql_file: str
    metrics: list[Metric]
    main_dttm_col: str | None = None

    def sql(self) -> str:
        return company_scoped(render_sql(self.sql_file))


@dataclass
class Chart:
    name: str
    dataset: str
    params: dict[str, Any]


@dataclass
class Filter:
    label: str
    column: str
    dataset: str
    multi: bool = True
    exclude: list[str] = field(default_factory=list)


@dataclass
class TimeFilter:
    label: str
    charts: list[str]


SQL_INCLUDES = {
    "{personnel}": "_personnel_dims.sql",
    "{services}": "_services_dims.sql",
}


def render_sql(sql_file: str) -> str:
    """Load a SQL file, expanding ``{personnel}`` (one row per employee with
    labelled dimensions) and ``{services}`` (service -> pole/direction)."""
    sql = (SQL_DIR / sql_file).read_text(encoding="utf-8").strip().rstrip(";")
    while any(tag in sql for tag in SQL_INCLUDES):
        for tag, include in SQL_INCLUDES.items():
            if tag in sql:
                body = (SQL_DIR / include).read_text(encoding="utf-8").strip().rstrip(";")
                sql = sql.replace(tag, body)
    return sql


COMPANY_PARAM = "cod_soc"


def company_scoped(sql: str) -> str:
    """Restrict a dataset to one company when the URL carries ``?cod_soc=XX``
    (dashboard or explore link). Every dataset SQL must expose a COD_SOC column."""
    return (
        f"SELECT * FROM (\n{sql}\n) grh\n"
        f"{{% if url_param('{COMPANY_PARAM}') %}}"
        f"WHERE grh.cod_soc = '{{{{ url_param('{COMPANY_PARAM}') }}}}'"
        "{% endif %}"
    )


# --------------------------------------------------------------------------- chart params


def simple_filter(column: str, operator: str, value: Any) -> dict[str, Any]:
    return {
        "expressionType": "SIMPLE",
        "subject": column,
        "operator": operator,
        "comparator": value,
        "clause": "WHERE",
    }


def sql_filter(expression: str) -> dict[str, Any]:
    return {"expressionType": "SQL", "sqlExpression": expression, "clause": "WHERE"}


ACTIF = simple_filter("EST_ACTIF", "==", 1)


def big_number(dataset: str, name: str, metric: str, subheader: str = "",
               fmt: str = "SMART_NUMBER", filters: list | None = None) -> Chart:
    return Chart(name, dataset, {
        "viz_type": "big_number_total",
        "metric": metric,
        "adhoc_filters": filters or [],
        "subheader": subheader,
        "header_font_size": 0.4,
        "subheader_font_size": 0.15,
        "y_axis_format": fmt,
        "time_format": "smart_date",
    })


def bar(dataset: str, name: str, x_axis: str, metric: str | list[str], groupby: list[str] | None = None,
        horizontal: bool = False, sort_by_metric: bool = True, stack: bool = False,
        filters: list | None = None, fmt: str = "SMART_NUMBER", limit: int = 10000) -> Chart:
    metrics = metric if isinstance(metric, list) else [metric]
    # Superset can only sort the x axis by metric when there is a single series.
    sort_by_metric = sort_by_metric and not groupby and len(metrics) == 1
    return Chart(name, dataset, {
        "viz_type": "echarts_timeseries_bar",
        "x_axis": x_axis,
        "metrics": metrics,
        "groupby": groupby or [],
        "adhoc_filters": filters or [],
        "orientation": "horizontal" if horizontal else "vertical",
        "x_axis_sort": metrics[0] if sort_by_metric else x_axis,
        "x_axis_sort_asc": not sort_by_metric,
        "row_limit": limit,
        "truncate_metric": True,
        "show_value": len(metrics) == 1,
        "show_legend": bool(groupby) or len(metrics) > 1,
        "legendType": "scroll",
        "legendOrientation": "top",
        "rich_tooltip": True,
        "y_axis_format": fmt,
        "stack": "Stack" if stack else None,
        "color_scheme": "supersetColors",
        "zoomable": False,
        "sort_series_type": "sum",
    })


def timeseries(dataset: str, name: str, x_axis: str, metric: str | list[str],
               groupby: list[str] | None = None, grain: str = "P1Y", kind: str = "bar", stack: bool = True,
               filters: list | None = None, fmt: str = "SMART_NUMBER") -> Chart:
    time_format = {"P1Y": "%Y", "P1M": "%b %Y", "P3M": "%b %Y"}.get(grain, "smart_date")
    metrics = metric if isinstance(metric, list) else [metric]
    multi_series = bool(groupby) or len(metrics) > 1
    return Chart(name, dataset, {
        "viz_type": "echarts_timeseries_bar" if kind == "bar" else "echarts_timeseries_line",
        "x_axis": x_axis,
        "x_axis_is_time": True,
        "time_grain_sqla": grain,
        "metrics": metrics,
        "groupby": groupby or [],
        "adhoc_filters": [simple_filter(x_axis, "TEMPORAL_RANGE", "No filter"), *(filters or [])],
        "orientation": "vertical",
        "x_axis_time_format": time_format,
        "row_limit": 10000,
        "show_legend": multi_series,
        "legendType": "scroll",
        "legendOrientation": "top",
        "rich_tooltip": True,
        "show_value": False,
        "stack": "Stack" if stack and multi_series else None,
        "markerEnabled": kind == "line",
        "y_axis_format": fmt,
        "color_scheme": "supersetColors",
        "zoomable": True,
    })


def pie(dataset: str, name: str, groupby: str, metric: str, filters: list | None = None,
        fmt: str = "SMART_NUMBER") -> Chart:
    return Chart(name, dataset, {
        "viz_type": "pie",
        "groupby": [groupby],
        "metric": metric,
        "adhoc_filters": filters or [],
        "row_limit": 100,
        "sort_by_metric": True,
        "donut": True,
        "innerRadius": 40,
        "outerRadius": 70,
        "show_labels": True,
        "labels_outside": True,
        "label_line": True,
        "label_type": "key_percent",
        "show_legend": True,
        "legendType": "scroll",
        "legendOrientation": "top",
        "number_format": fmt,
        "color_scheme": "supersetColors",
    })


def table(dataset: str, name: str, columns: list[str], order_by: str, ascending: bool = True,
          filters: list | None = None, limit: int = 1000) -> Chart:
    return Chart(name, dataset, {
        "viz_type": "table",
        "query_mode": "raw",
        "all_columns": columns,
        "adhoc_filters": filters or [],
        "order_by_cols": [json.dumps([order_by, ascending])],
        "row_limit": limit,
        "server_pagination": False,
        "page_length": 20,
        "include_search": True,
        "show_cell_bars": False,
        "table_timestamp_format": "%d/%m/%Y",
        "allow_rearrange_columns": True,
    })


def summary_table(dataset: str, name: str, groupby: list[str], metrics: list[str],
                  filters: list | None = None, limit: int = 1000) -> Chart:
    """Aggregated table: one row per groupby value, sorted by the first metric."""
    return Chart(name, dataset, {
        "viz_type": "table",
        "query_mode": "aggregate",
        "groupby": groupby,
        "metrics": metrics,
        "adhoc_filters": filters or [],
        "timeseries_limit_metric": metrics[0],
        "order_desc": True,
        "row_limit": limit,
        "server_pagination": False,
        "page_length": 20,
        "include_search": True,
        "show_cell_bars": True,
        "allow_rearrange_columns": True,
    })


def sankey(dataset: str, name: str, source: str, target: str, metric: str,
           filters: list | None = None, limit: int = 40) -> Chart:
    return Chart(name, dataset, {
        "viz_type": "sankey_v2",
        "source": source,
        "target": target,
        "metric": metric,
        "adhoc_filters": filters or [],
        "row_limit": limit,
        "sort_by_metric": True,
        "color_scheme": "supersetColors",
    })


# --------------------------------------------------------------------------- query context


def _base_axis(column: str, time_grain: str | None = None) -> dict[str, Any]:
    col: dict[str, Any] = {
        "columnType": "BASE_AXIS",
        "sqlExpression": column,
        "label": column,
        "expressionType": "SQL",
    }
    if time_grain:
        col["timeGrain"] = time_grain
    return col


def query_context(ds_id: int, params: dict[str, Any]) -> dict[str, Any]:
    """Build a query context equivalent to what Explore would save."""
    viz = params["viz_type"]
    filters, where = [], []
    for f in params.get("adhoc_filters", []):
        if f["expressionType"] == "SQL":
            where.append(f"({f['sqlExpression']})")
        elif f["operator"] != "TEMPORAL_RANGE":
            filters.append({"col": f["subject"], "op": f["operator"], "val": f["comparator"]})
    query: dict[str, Any] = {
        "filters": filters,
        "extras": {"having": "", "where": " AND ".join(where)},
        "applied_time_extras": {},
        "columns": [],
        "metrics": [],
        "orderby": [],
        "annotation_layers": [],
        "row_limit": params.get("row_limit", 10000),
        "series_limit": 0,
        "order_desc": True,
        "url_params": {},
        "custom_params": {},
        "custom_form_data": {},
    }
    post_processing: list[dict[str, Any]] = []
    if viz == "big_number_total":
        query["metrics"] = [params["metric"]]
    elif viz == "pie":
        query["columns"] = params["groupby"]
        query["metrics"] = [params["metric"]]
        query["orderby"] = [[params["metric"], False]]
    elif viz == "sankey_v2":
        query["columns"] = [params["source"], params["target"]]
        query["metrics"] = [params["metric"]]
        query["orderby"] = [[params["metric"], False]]
    elif viz in ("echarts_timeseries_bar", "echarts_timeseries_line"):
        metrics = params["metrics"]
        grain = params.get("time_grain_sqla") if params.get("x_axis_is_time") else None
        query["columns"] = [_base_axis(params["x_axis"], grain), *params.get("groupby", [])]
        query["metrics"] = metrics
        if grain:
            query["time_range"] = "No filter"
            query["extras"]["time_grain_sqla"] = grain
        query["orderby"] = [[metrics[0], False]]
        post_processing.append({
            "operation": "pivot",
            "options": {
                "index": [params["x_axis"]],
                "columns": params.get("groupby", []),
                "aggregates": {m: {"operator": "mean"} for m in metrics},
                "drop_missing_columns": False,
            },
        })
        sort_key = params.get("x_axis_sort")
        if sort_key and not grain:
            by_index = sort_key == params["x_axis"]
            post_processing.append({
                "operation": "sort",
                "options": {
                    "is_sort_index": by_index,
                    "ascending": params.get("x_axis_sort_asc", True),
                    **({} if by_index else {"by": sort_key}),
                },
            })
        post_processing.append({"operation": "flatten"})
    elif viz == "table" and params.get("query_mode") == "aggregate":
        query["columns"] = params["groupby"]
        query["metrics"] = params["metrics"]
        query["orderby"] = [[params["timeseries_limit_metric"], False]]
    elif viz == "table":
        query["columns"] = params["all_columns"]
        query["orderby"] = [json.loads(o) for o in params.get("order_by_cols", [])]
    query["post_processing"] = post_processing
    return {
        "datasource": {"id": ds_id, "type": "table"},
        "force": False,
        "queries": [query],
        "form_data": params,
        "result_format": "json",
        "result_type": "full",
    }


# --------------------------------------------------------------------------- datasets


def find_database(client: SupersetClient, name: str = DATABASE_NAME) -> int:
    db = client.find("database", "database_name", name)
    if not db:
        raise SystemExit(f"Database '{name}' not found in Superset")
    return db["id"]


def upsert_dataset(client: SupersetClient, db_id: int, spec: Dataset) -> int:
    sql = spec.sql()
    existing = client.find("dataset", "table_name", spec.name)
    if existing:
        ds_id = existing["id"]
        client.put(f"/api/v1/dataset/{ds_id}", {"sql": sql})
    else:
        ds_id = client.post(
            "/api/v1/dataset/",
            {"database": db_id, "table_name": spec.name, "sql": sql, "schema": None},
        )["id"]
    client.request("PUT", f"/api/v1/dataset/{ds_id}/refresh")
    _configure_dataset(client, ds_id, spec)
    return ds_id


def _configure_dataset(client: SupersetClient, ds_id: int, spec: Dataset) -> None:
    ds = client.get(f"/api/v1/dataset/{ds_id}")["result"]
    columns = []
    for col in ds["columns"]:
        name = col["column_name"]
        col_type = (col.get("type") or "").upper()
        columns.append({
            "id": col["id"],
            "column_name": name,
            "type": col.get("type"),
            "is_dttm": col_type.startswith("DATE") or col_type.startswith("TIMESTAMP"),
            "groupby": True,
            "filterable": True,
            "verbose_name": name.replace("_", " ").capitalize(),
        })
    wanted = {m.name for m in spec.metrics}
    existing = {m["metric_name"]: m["id"] for m in ds["metrics"]}
    metrics: list[dict[str, Any]] = [
        {"id": m["id"], "metric_name": m["metric_name"], "expression": m["expression"]}
        for m in ds["metrics"]
        if m["metric_name"] not in wanted
    ]
    for m in spec.metrics:
        item: dict[str, Any] = {
            "metric_name": m.name,
            "expression": m.expression,
            "verbose_name": m.verbose,
            "d3format": m.d3format,
        }
        if m.name in existing:
            item["id"] = existing[m.name]
        metrics.append(item)
    client.put(f"/api/v1/dataset/{ds_id}", {
        "columns": columns,
        "metrics": metrics,
        "main_dttm_col": spec.main_dttm_col,
        "description": f"GRH - {spec.name} (généré par scripts/grh)",
    })


def dataset_columns(client: SupersetClient, ds_id: int) -> set[str]:
    ds = client.get(f"/api/v1/dataset/{ds_id}")["result"]
    return {c["column_name"] for c in ds["columns"]}


# --------------------------------------------------------------------------- charts & dashboard


def upsert_chart(client: SupersetClient, chart: Chart, ds_id: int, dashboard_id: int) -> int:
    params = {**chart.params, "datasource": f"{ds_id}__table"}
    payload = {
        "slice_name": chart.name,
        "viz_type": params["viz_type"],
        "datasource_id": ds_id,
        "datasource_type": "table",
        "params": json.dumps(params),
        "query_context": json.dumps(query_context(ds_id, params)),
        "dashboards": [dashboard_id],
    }
    q = {"filters": [
        {"col": "slice_name", "opr": "eq", "value": chart.name},
        {"col": "datasource_id", "opr": "eq", "value": ds_id},
    ]}
    found = client.get("/api/v1/chart/", params={"q": json.dumps(q)})["result"]
    if found:
        client.put(f"/api/v1/chart/{found[0]['id']}", payload)
        return found[0]["id"]
    return client.post("/api/v1/chart/", payload)["id"]


THEME_FILE = Path(__file__).parent / "theme" / "grh_modern.css"
THEME_NAME = "GRH moderne"


def theme_css() -> str:
    return THEME_FILE.read_text(encoding="utf-8")


def upsert_css_template(client: SupersetClient) -> int:
    """Publish the theme as a Superset CSS template so it can be picked in
    'Edit CSS' on any dashboard."""
    payload = {"template_name": THEME_NAME, "css": theme_css()}
    existing = client.find("css_template", "template_name", THEME_NAME)
    if existing:
        client.put(f"/api/v1/css_template/{existing['id']}", payload)
        return existing["id"]
    return client.post("/api/v1/css_template/", payload)["id"]


def nav_markdown(current_key: str) -> str:
    return " ".join(
        f"**{label}**" if key == current_key else f"[{label}](/superset/dashboard/{slug}/)"
        for key, label, slug in SUITE
    )


def position_json(title: str, layout: list, charts: dict[str, int], names: dict[str, str],
                  nav: str | None) -> dict[str, Any]:
    pos: dict[str, Any] = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
        "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": title}},
    }

    def add_row(row_id: str) -> dict[str, Any]:
        pos["GRID_ID"]["children"].append(row_id)
        pos[row_id] = {
            "type": "ROW", "id": row_id, "children": [],
            "parents": ["ROOT_ID", "GRID_ID"],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        return pos[row_id]

    if nav:
        row = add_row("ROW-grh-nav")
        row["children"].append("MARKDOWN-grh-nav")
        pos["MARKDOWN-grh-nav"] = {
            "type": "MARKDOWN", "id": "MARKDOWN-grh-nav", "children": [],
            "parents": ["ROOT_ID", "GRID_ID", "ROW-grh-nav"],
            "meta": {"width": 12, "height": 12, "code": nav},
        }
    for r, layout_row in enumerate(layout, start=1):
        row_id = f"ROW-grh-{r}"
        row = add_row(row_id)
        for key, width, height in layout_row:
            chart_key = f"CHART-grh-{key}"
            row["children"].append(chart_key)
            pos[chart_key] = {
                "type": "CHART", "id": chart_key, "children": [],
                "parents": ["ROOT_ID", "GRID_ID", row_id],
                "meta": {"width": width, "height": height,
                         "chartId": charts[key], "sliceName": names[key]},
            }
    return pos


def native_filters(filters: list, ds_ids: dict[str, int], charts: dict[str, int],
                   chart_datasets: dict[str, str], ds_columns: dict[str, set[str]]) -> list:
    """Select filters only apply to charts whose dataset has the filtered column."""
    result = []
    for f in filters:
        if isinstance(f, TimeFilter):
            in_scope = [charts[k] for k in f.charts]
            excluded = [cid for cid in charts.values() if cid not in in_scope]
            result.append({
                "id": f"NATIVE_FILTER-grh-time-{f.charts[0]}",
                "name": f.label,
                "filterType": "filter_time",
                "type": "NATIVE_FILTER",
                "targets": [{}],
                "controlValues": {"enableEmptyFilter": False},
                "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
                "cascadeParentIds": [],
                "scope": {"rootPath": ["ROOT_ID"], "excluded": excluded},
                "chartsInScope": in_scope,
                "tabsInScope": [],
                "description": "",
            })
            continue
        excluded = [
            cid for key, cid in charts.items()
            if key in f.exclude or f.column not in ds_columns[chart_datasets[key]]
        ]
        result.append({
            "id": f"NATIVE_FILTER-grh-{f.dataset}-{f.column.lower()}",
            "name": f.label,
            "filterType": "filter_select",
            "type": "NATIVE_FILTER",
            "targets": [{"datasetId": ds_ids[f.dataset], "column": {"name": f.column}}],
            "controlValues": {
                "enableEmptyFilter": False,
                "defaultToFirstItem": False,
                "multiSelect": f.multi,
                "searchAllOptions": False,
                "inverseSelection": False,
            },
            "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": excluded},
            "chartsInScope": [cid for cid in charts.values() if cid not in excluded],
            "tabsInScope": [],
            "description": "",
        })
    by_column = {f["targets"][0].get("column", {}).get("name"): f["id"] for f in result}
    for f in result:
        if f["filterType"] == "filter_select" and f["targets"][0]["column"]["name"] == "DIRECTION" \
                and "POLE" in by_column:
            f["cascadeParentIds"] = [by_column["POLE"]]
    return result


def remove_stale_charts(client: SupersetClient, dashboard_id: int, keep: set[int], ds_ids: set[int]) -> None:
    """Charts dropped from a spec are deleted if built on our datasets, else just detached."""
    for chart in client.get(f"/api/v1/dashboard/{dashboard_id}/charts")["result"]:
        chart_id = chart["id"]
        if chart_id in keep:
            continue
        detail = client.get(f"/api/v1/chart/{chart_id}")["result"]
        ds_id = json.loads(detail.get("params") or "{}").get("datasource", "").split("__")[0]
        if ds_id.isdigit() and int(ds_id) in ds_ids:
            client.request("DELETE", f"/api/v1/chart/{chart_id}")
            print(f"  removed stale chart {detail['slice_name']} (id={chart_id})")
        else:
            others = [d["id"] for d in detail.get("dashboards", []) if d["id"] != dashboard_id]
            client.put(f"/api/v1/chart/{chart_id}", {"dashboards": others})
            print(f"  detached chart {detail['slice_name']} (id={chart_id})")


def build(client: SupersetClient, spec: Any, db_id: int) -> dict[str, Any]:
    print(f"== {spec.TITLE}")
    ds_ids = {}
    for ds in spec.DATASETS:
        ds_ids[ds.key] = upsert_dataset(client, db_id, ds)
        print(f"  dataset {ds.name}: id={ds_ids[ds.key]}")
    ds_columns = {key: dataset_columns(client, ds_id) for key, ds_id in ds_ids.items()}

    existing = client.find("dashboard", "slug", spec.SLUG)
    dashboard_id = existing["id"] if existing else client.post(
        "/api/v1/dashboard/", {"dashboard_title": spec.TITLE, "slug": spec.SLUG, "published": True}
    )["id"]

    chart_specs: dict[str, Chart] = spec.charts(ds_ids)
    charts, names, chart_datasets = {}, {}, {}
    for key, chart in chart_specs.items():
        charts[key] = upsert_chart(client, chart, ds_ids[chart.dataset], dashboard_id)
        names[key] = chart.name
        chart_datasets[key] = chart.dataset
        print(f"  chart {chart.name}: id={charts[key]}")

    remove_stale_charts(client, dashboard_id, set(charts.values()), set(ds_ids.values()))

    metadata = {
        "native_filter_configuration": native_filters(
            spec.FILTERS, ds_ids, charts, chart_datasets, ds_columns
        ),
        "color_scheme": "supersetColors",
        "refresh_frequency": 0,
        "timed_refresh_immune_slices": [],
        "expanded_slices": {},
        "cross_filters_enabled": True,
        "default_filters": "{}",
        "chart_configuration": {},
        "global_chart_configuration": {
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "chartsInScope": list(charts.values()),
        },
    }
    nav = nav_markdown(spec.KEY)
    client.put(f"/api/v1/dashboard/{dashboard_id}", {
        "dashboard_title": spec.TITLE,
        "slug": spec.SLUG,
        "published": True,
        "css": theme_css(),
        "position_json": json.dumps(position_json(spec.TITLE, spec.LAYOUT, charts, names, nav)),
        "json_metadata": json.dumps(metadata),
    })
    print(f"  dashboard: {client.url}/superset/dashboard/{spec.SLUG}/")
    return {"slug": spec.SLUG, "dashboard": dashboard_id, "datasets": ds_ids, "charts": charts}


def load_ids() -> dict[str, Any]:
    if IDS_FILE.exists():
        return json.loads(IDS_FILE.read_text(encoding="utf-8"))
    return {}


def save_ids(ids: dict[str, Any]) -> None:
    IDS_FILE.write_text(json.dumps(ids, indent=2), encoding="utf-8")
