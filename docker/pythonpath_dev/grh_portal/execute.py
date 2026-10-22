"""Execute a validated plan through Superset chart data, as the current user."""
from __future__ import annotations

import logging
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from grh_portal.planner import Plan, query_body

logger = logging.getLogger(__name__)


class ChatQueryError(Exception):
    def __init__(self, public: str) -> None:
        super().__init__(public)
        self.public = public


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    item = getattr(value, "item", None)
    if callable(item):
        try:
            return _plain(item())
        except Exception:  # noqa: BLE001 - numpy scalars vary
            pass
    if isinstance(value, dict):
        return {str(key): _plain(inner) for key, inner in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(inner) for inner in value]
    return str(value)


def run_plan(plan: Plan, dataset: dict[str, Any], configured_limit: int) -> list[dict[str, Any]]:
    from superset.charts.schemas import ChartDataQueryContextSchema
    from superset.commands.chart.data.get_data_command import ChartDataCommand
    from superset.exceptions import SupersetSecurityException

    body = query_body(plan, dataset, configured_limit)
    try:
        query_context = ChartDataQueryContextSchema().load(body)
        command = ChartDataCommand(query_context)
        command.validate()
        result = command.run()
    except SupersetSecurityException:
        logger.warning("grh chat access denied dataset=%s", plan.dataset)
        raise ChatQueryError("Accès refusé à ces données.") from None
    except Exception:
        logger.exception("grh chat execution failed dataset=%s", plan.dataset)
        raise ChatQueryError("La requête n'a pas abouti.") from None

    queries = result.get("queries") or []
    if not queries or queries[0].get("error"):
        logger.error("grh chat empty query result dataset=%s", plan.dataset)
        raise ChatQueryError("La requête n'a pas abouti.")
    data = queries[0].get("data") or []
    if not isinstance(data, list):
        raise ChatQueryError("La requête n'a pas abouti.")
    rows = []
    for row in data:
        if isinstance(row, dict):
            rows.append({str(key): _plain(value) for key, value in row.items()})
    return rows
