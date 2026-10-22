"""Compare retrieval and plans on the question file.

A is the current bubble search. B asks Ollama without verified examples.
C asks Ollama with examples.json. Numeric gold values stay null until supplied:
a plan that matches the expected preset is a structural match, not a proof the
figure is right. Execution is recorded only inside a running Superset app
(``--execute``).

    python scripts/grh/eval/run_eval.py
    python scripts/grh/eval/run_eval.py --mode A
    python scripts/grh/eval/run_eval.py --mode C
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docker" / "pythonpath_dev"))

from grh_portal.ollama_client import OllamaClient, OllamaError, ollama_reachable  # noqa: E402
from grh_portal.planner import Plan, answer_question, load_examples, plan_for_preset  # noqa: E402
from grh_portal.retrieve import load_catalog, search  # noqa: E402

HERE = Path(__file__).parent
QUESTIONS = HERE / "questions.json"
REPORTS = HERE / "reports"
EXAMPLES = ROOT / "docker" / "pythonpath_dev" / "grh_portal" / "examples.json"


def percentile(values: list[float], percent: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(percent / 100 * len(ordered)) - 1))
    return ordered[index]


def signature(preset: dict[str, Any]) -> dict[str, Any]:
    groupby = f"time:{preset['grain']}" if preset.get("grain") else preset.get("groupby")
    return {
        "dataset": preset["dataset"],
        "metrics": list(preset.get("metrics") or []),
        "groupby": groupby,
        "series": preset.get("series"),
        "filters": preset.get("filters") or {},
    }


def plan_signature(plan: Plan) -> dict[str, Any]:
    filters = {key: values for key, values in plan.filters.items() if key not in {"COD_SOC", "EST_ACTIF"}}
    return {
        "dataset": plan.dataset,
        "metrics": list(plan.metrics),
        "groupby": plan.groupby,
        "series": plan.series,
        "filters": filters,
    }


def score_plan(plan: Plan | None, status: str, expected: dict[str, Any], catalog: dict[str, Any], top_ids: list[str]) -> dict[str, Any]:
    preset = catalog["presets_by_id"][expected["expected_preset"]]
    dataset = catalog["datasets"][preset["dataset"]]
    wanted = signature(preset)
    got = plan_signature(plan) if plan else None
    exact = bool(plan and (plan.preset == preset["id"] or got == wanted))
    dataset_ok = bool(plan and plan.dataset == preset["dataset"])
    metrics_ok = bool(plan and list(plan.metrics) == list(preset.get("metrics") or []))
    columns_ok = bool(plan and plan.groupby == wanted["groupby"] and plan.series == wanted["series"])
    wanted_filters = preset.get("filters") or {}
    got_filters = (plan.filters if plan else {}) or {}
    missing_filters = [key for key, value in wanted_filters.items() if got_filters.get(key) != value]
    wanted_conditions = [c.get("label") for c in preset.get("conditions") or [] if c.get("label")]
    got_conditions = [c.get("label") for c in (plan.conditions if plan else []) if c.get("label")]
    missing_conditions = [label for label in wanted_conditions if label not in got_conditions]
    return {
        "exact_plan": exact,
        "execution": None,
        "wrong_dataset": bool(plan) and not dataset_ok,
        "wrong_column": bool(plan) and dataset_ok and not columns_ok,
        "wrong_join": False,
        "kpi_or_aggregation_error": bool(plan) and dataset_ok and not metrics_ok,
        "missing_mandatory_filters": missing_filters + missing_conditions,
        "missing_company_filter": bool(dataset.get("has_company") and plan and "COD_SOC" not in plan.filters),
        "refusal": status in {"clarify", "refuse"} or plan is None,
        "empty_result": None,
        "retrieval_hit_at_3": expected["expected_preset"] in top_ids[:3],
        "expected_aggregate": expected.get("expected_aggregate"),
        "aggregate_correct": None if expected.get("expected_aggregate") is None else False,
    }


def run_mode(mode: str, questions: list[dict[str, Any]], catalog: dict[str, Any], client: OllamaClient | None, execute: bool) -> dict[str, Any]:
    examples = load_examples(EXAMPLES)
    rows = []
    for item in questions:
        started = time.perf_counter()
        top = search(item["question"], 12, catalog)
        top_ids = [preset["id"] for preset in top]
        plan: Plan | None = None
        status = "ok"
        error = None
        if mode == "A":
            if top:
                preset = top[0]
                dataset = catalog["datasets"][preset["dataset"]]
                plan = plan_for_preset(preset, dataset, item["question"], ["01"])
            else:
                status = "clarify"
        else:
            assert client is not None
            try:
                answer = answer_question(
                    item["question"],
                    client=client,
                    use_examples=mode == "C",
                    allowed_companies=["01"],
                    catalog=catalog,
                    examples=examples,
                )
                status = answer.status
                plan = answer.plan
            except OllamaError as ex:
                status = "error"
                error = str(ex)
        elapsed = time.perf_counter() - started
        scored = score_plan(plan, status, item, catalog, top_ids)
        execution = None
        empty = None
        if execute and plan is not None:
            execution, empty = execute_plan(plan, catalog)
            scored["execution"] = execution
            scored["empty_result"] = empty
        rows.append({
            "id": item["id"],
            "question": item["question"],
            "status": status,
            "error": error,
            "latency_s": round(elapsed, 3),
            "preset": plan.preset if plan else (top_ids[0] if mode == "A" and top_ids else None),
            "dataset": plan.dataset if plan else None,
            "metrics": plan.metrics if plan else None,
            "groupby": plan.groupby if plan else None,
            "filters": plan.public()["filters"] if plan else None,
            **scored,
        })
        if status == "error":
            break
    latencies = [row["latency_s"] for row in rows if row["status"] != "error"]
    def rate(key: str) -> float | None:
        usable = [row for row in rows if row["status"] != "error"]
        if not usable:
            return None
        return sum(1 for row in usable if row[key]) / len(usable)

    return {
        "mode": mode,
        "questions": len(rows),
        "exact_plan_rate": rate("exact_plan"),
        "execution_success_rate": None if not execute else rate("execution"),
        "wrong_dataset_rate": rate("wrong_dataset"),
        "wrong_column_rate": rate("wrong_column"),
        "wrong_join_rate": rate("wrong_join"),
        "kpi_or_aggregation_error_rate": rate("kpi_or_aggregation_error"),
        "missing_mandatory_filter_rate": rate("missing_mandatory_filters"),
        "missing_company_filter_rate": rate("missing_company_filter"),
        "refusal_rate": rate("refusal"),
        "empty_result_rate": None if not execute else rate("empty_result"),
        "retrieval_hit_at_3": rate("retrieval_hit_at_3"),
        "median_latency_s": statistics.median(latencies) if latencies else None,
        "p95_latency_s": percentile(latencies, 95),
        "note": "exact_plan is a structural match to the catalog preset. expected_aggregate is null, so business correctness is not scored.",
        "rows": rows,
    }


def execute_plan(plan: Plan, catalog: dict[str, Any]) -> tuple[bool | None, bool | None]:
    try:
        from flask import has_app_context
    except ImportError:
        return None, None
    if not has_app_context():
        return None, None
    from grh_portal.execute import ChatQueryError, run_plan

    try:
        data = run_plan(plan, catalog["datasets"][plan.dataset], 500)
    except ChatQueryError:
        return False, None
    return True, len(data) == 0


def regression(mode_a: dict[str, Any], mode_c: dict[str, Any]) -> list[str]:
    by_id = {row["id"]: row for row in mode_c["rows"]}
    lost = []
    for row in mode_a["rows"]:
        other = by_id.get(row["id"])
        if row.get("exact_plan") and other and not other.get("exact_plan"):
            lost.append(row["id"])
    return lost


def main() -> int:
    parser = argparse.ArgumentParser(description="GRH assistant benchmark")
    parser.add_argument("--mode", choices=("A", "B", "C", "all"), default="all")
    parser.add_argument("--execute", action="store_true", help="Run plans when a Superset app context is active")
    parser.add_argument("--ollama-url", default="http://host.docker.internal:11434")
    parser.add_argument("--model", default="qwen2.5:3b")
    args = parser.parse_args()
    payload = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    questions = payload["questions"]
    catalog = load_catalog()
    modes = ["A", "B", "C"] if args.mode == "all" else [args.mode]
    client = None
    if any(mode != "A" for mode in modes):
        if not ollama_reachable(args.ollama_url):
            print(f"Ollama is not reachable at {args.ollama_url}. Modes B and C were not run.")
            modes = [mode for mode in modes if mode == "A"]
            if not modes:
                return 2
        else:
            client = OllamaClient(args.ollama_url, args.model, 60)
    reports = []
    for mode in modes:
        print(f"mode {mode}...")
        reports.append(run_mode(mode, questions, catalog, client, args.execute))
    summary: dict[str, Any] = {"generated_at": datetime.now().isoformat(timespec="seconds"), "modes": reports}
    if any(item["mode"] == "A" for item in reports) and any(item["mode"] == "C" for item in reports):
        mode_a = next(item for item in reports if item["mode"] == "A")
        mode_c = next(item for item in reports if item["mode"] == "C")
        lost = regression(mode_a, mode_c)
        summary["regression_ids"] = lost
        summary["regression_rate"] = (len(lost) / len(mode_a["rows"])) if mode_a["rows"] else None
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out = REPORTS / f"{stamp}_{args.mode}.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    for item in reports:
        print(
            f"{item['mode']}: exact_plan={item['exact_plan_rate']} "
            f"retrieval@3={item['retrieval_hit_at_3']} "
            f"refusal={item['refusal_rate']} "
            f"median_s={item['median_latency_s']} p95_s={item['p95_latency_s']}"
        )
    if "regression_rate" in summary:
        print(f"regression C vs A: {summary['regression_rate']} ids={summary['regression_ids']}")
    print(f"report: {out}")
    print(summary["modes"][0]["note"] if reports else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
