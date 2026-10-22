"""Checks that do not call Ollama or Oracle.

Run from the repo: python scripts/grh/eval/test_assistant.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docker" / "pythonpath_dev"))

from grh_portal.planner import (  # noqa: E402
    build_user_prompt,
    format_answer,
    load_examples,
    query_body,
    answer_question,
)
from grh_portal.retrieve import load_catalog, retrieve, search  # noqa: E402

EXAMPLES = [
    "Effectif actif par direction",
    "Pyramide des âges",
    "Masse salariale et coût employeur par direction (12 mois)",
    "Jours de congé par direction et par type (12 mois)",
    "Retraites prévues dans 5 ans par direction",
    "Taux d'absentéisme maladie par direction (12 mois)",
]
EXPECTED_TOP = [
    "effectif.extra1",
    "effectif.pyramide",
    "salaires.extra10",
    "conges.extra7",
    "departs.ret_direction",
    "sante.extra14",
]


class Scripted:
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return reply


def test_bubble_examples() -> None:
    for question, preset_id in zip(EXAMPLES, EXPECTED_TOP):
        top = search(question, 1)[0]
        assert top["id"] == preset_id, (question, top["id"], top["label"])


def test_company_and_active_filter() -> None:
    client = Scripted([
        '{"preset":"effectif.extra1","dataset":"salaires.paie","metrics":["masse_brute"],'
        '"filters":{"COD_SOC":["99"]},"clarify":null,"refuse":null}',
    ])
    result = answer_question(
        "Effectif actif par direction",
        client=client,
        use_examples=False,
        allowed_companies=["01"],
    )
    assert result.status == "ok", result.text
    assert result.plan is not None
    assert result.plan.dataset == "effectif.eff"
    assert result.plan.metrics == ["effectif"]
    assert result.plan.filters["COD_SOC"] == ["01"]
    assert result.plan.filters["ETAT"] == ["Actif"]
    assert client.calls == 0
    catalog = load_catalog()
    body = query_body(result.plan, catalog["datasets"][result.plan.dataset], 100000)
    query = body["queries"][0]
    assert query["row_limit"] == 500
    assert any(item["col"] == "COD_SOC" and item["val"] == ["01"] for item in query["filters"])
    assert "select" not in query["extras"]["where"].lower()


def test_sql_and_unknown_dataset_do_not_execute() -> None:
    client = Scripted([
        '{"dataset":"effectif.eff","metrics":["effectif"],"groupby":"DIRECTION; delete from dual","clarify":null}',
        '{"dataset":"not.a.dataset","metrics":["count(*)"],"clarify":null}',
    ])
    result = answer_question(
        "Pyramide des âges",
        client=client,
        use_examples=False,
        allowed_companies=["01"],
    )
    assert result.plan is not None
    assert result.plan.series == "SEXE"
    assert result.plan.groupby == "TRANCHE_AGE"
    assert client.calls == 0


def test_examples_toggle() -> None:
    catalog = load_catalog()
    bundle = retrieve("Effectif actif par direction", catalog)
    examples = load_examples(ROOT / "docker" / "pythonpath_dev" / "grh_portal" / "examples.json")
    without = build_user_prompt("Effectif actif par direction", bundle, catalog, None)
    with_examples = build_user_prompt("Effectif actif par direction", bundle, catalog, examples[:3])
    assert "Exemples vérifiés" not in without
    assert "preset effectif.extra1" in without
    assert len(without) <= 2800
    assert "Exemples vérifiés" in with_examples
    assert "preset=effectif.extra1" in with_examples


def test_catalog_sql_stays_server_side() -> None:
    client = Scripted([
        '{"preset":"conges.extra7","where":"1=1 OR COD_SOC = \'99\'","clarify":null,"refuse":null}',
    ])
    result = answer_question(
        "Jours de congé par direction et par type (12 mois)",
        client=client,
        use_examples=False,
        allowed_companies=["01"],
    )
    assert result.plan is not None
    catalog = load_catalog()
    where = query_body(result.plan, catalog["datasets"][result.plan.dataset], 500)["queries"][0]["extras"]["where"]
    assert "DAT_DEBUT" in where
    assert "99" not in where


def test_answer_uses_rows_not_the_model() -> None:
    catalog = load_catalog()
    client = Scripted(['{"preset":"effectif.extra1","clarify":null,"refuse":null}'])
    result = answer_question(
        "Effectif actif par direction",
        client=client,
        use_examples=True,
        allowed_companies=["01"],
        examples=load_examples(ROOT / "docker" / "pythonpath_dev" / "grh_portal" / "examples.json"),
    )
    assert result.plan is not None
    text = format_answer(result.plan, catalog["datasets"][result.plan.dataset], [{"DIRECTION": "Nord", "effectif": 12}])
    assert "12" in text
    assert "Nord" in text


def test_effectif_par_sexe_uses_catalog() -> None:
    assert search("effectif par sexe", 1)[0]["id"] == "effectif.sexe"
    client = Scripted(['not json', 'still not json'])
    result = answer_question(
        "effectif par sexe",
        client=client,
        use_examples=True,
        allowed_companies=["01"],
        examples=load_examples(ROOT / "docker" / "pythonpath_dev" / "grh_portal" / "examples.json"),
    )
    assert result.plan is not None
    assert result.plan.dataset == "effectif.eff"
    assert result.plan.metrics == ["effectif"]
    assert result.plan.groupby == "SEXE"
    assert result.plan.filters["ETAT"] == ["Actif"]
    assert result.plan.preset == "effectif.sexe"
    assert client.calls == 0
    catalog = load_catalog()
    prompt = build_user_prompt(
        "effectif par sexe",
        retrieve("effectif par sexe", catalog),
        catalog,
        [{"question": "effectif par sexe", "preset": "effectif.sexe"}],
    )
    assert "preset effectif.sexe" in prompt
    assert "Jeu de données:" in prompt
    assert "COUNT(" not in prompt


def test_loose_phrase_suggests_catalog_question() -> None:
    client = Scripted([
        '{"clarify":"Quels sont les agents en congé dans l\'organisation pour le mois de janvier 2026?"}',
    ])
    result = answer_question(
        "agent en congé janvier 2026",
        client=client,
        use_examples=True,
        allowed_companies=["01"],
        examples=load_examples(ROOT / "docker" / "pythonpath_dev" / "grh_portal" / "examples.json"),
    )
    assert result.plan is None
    assert result.status == "clarify"
    assert result.text.startswith("Voulez-vous dire :")
    assert "Quels sont les agents" not in result.text
    assert result.suggestions
    assert "mois" in result.suggestions[0].lower()
    assert "janvier 2026" in result.suggestions[0]
    assert client.calls == 2


def test_absence_day_lists_people() -> None:
    client = Scripted([
        '{"dataset":"conges.cng","detail":["MAT_PERS","NOM_PRENOM"],"metrics":[],'
        '"filters":[{"col":"DIRECTION","op":"==","val":"Nord"},{"col":"DAT_DEBUT","op":"==","val":"2026-01-20"}],'
        '"orderby":[["NOM_PRENOM", true]],"clarify":null}',
    ])
    result = answer_question(
        "employé absent 20/01/2026",
        client=client,
        use_examples=False,
        allowed_companies=["01"],
    )
    assert result.plan is not None
    assert result.plan.dataset == "conges.cng"
    assert result.plan.view == "detail"
    assert result.plan.metrics == []
    assert result.plan.detail == ["MAT_PERS", "NOM_PRENOM"]
    assert result.plan.orderby == [["NOM_PRENOM", True]]
    assert client.calls == 1
    catalog = load_catalog()
    query = query_body(result.plan, catalog["datasets"][result.plan.dataset], 500)["queries"][0]
    assert query["columns"] == ["MAT_PERS", "NOM_PRENOM"]
    assert query["metrics"] == []
    assert query["orderby"] == [["NOM_PRENOM", True]]
    filters = query["filters"]
    where = query["extras"]["where"]
    assert any(item["col"] == "DIRECTION" and item["op"] == "==" and item["val"] == "Nord" for item in filters)
    assert "DAT_DEBUT <= DATE '2026-01-20'" in where
    assert "DAT_FIN >= DATE '2026-01-20'" in where
    assert "DAT_DEBUT =" not in where
    assert any(item["col"] == "STATUT" and item["op"] == "!=" and item["val"] == "Annulé" for item in filters)
    assert any(item["col"] == "COD_SOC" and item["val"] == ["01"] for item in filters)


def test_unknown_filter_column_is_refused() -> None:
    client = Scripted([
        '{"dataset":"conges.cng","detail":["MAT_PERS","NOM_PRENOM"],"metrics":[],'
        '"filters":[{"col":"PAS_UNE_COLONNE","op":"==","val":"x"}]}',
        '{"dataset":"conges.cng","detail":["MAT_PERS","NOM_PRENOM"],"metrics":[],'
        '"filters":[{"col":"PAS_UNE_COLONNE","op":"==","val":"x"}]}',
    ])
    result = answer_question(
        "employé absent 20/01/2026",
        client=client,
        use_examples=False,
        allowed_companies=["01"],
    )
    assert result.plan is not None
    assert all(item.get("col") != "PAS_UNE_COLONNE" for item in result.plan.conditions)
    assert client.calls == 2


def test_unknown_detail_column_is_refused() -> None:
    client = Scripted([
        '{"dataset":"conges.cng","detail":["SALAIRE_SECRET"],"metrics":[]}',
        '{"dataset":"conges.cng","detail":["SALAIRE_SECRET"],"metrics":[]}',
    ])
    result = answer_question(
        "employé absent 20/01/2026",
        client=client,
        use_examples=False,
        allowed_companies=["01"],
    )
    assert result.plan is not None
    assert "SALAIRE_SECRET" not in result.plan.detail
    assert "MAT_PERS" in result.plan.detail
    assert "NOM_PRENOM" in result.plan.detail
    assert client.calls == 2


def test_agent_gross_pay() -> None:
    from grh_portal.retrieve import named_period

    assert named_period("salaire brut supérieur à 3000 en 2026") == "2026"
    client = Scripted(['{"clarify":"autre chose"}'])
    highest = answer_question(
        "l'agent a plus de salaire brut en 2026",
        client=client,
        use_examples=False,
        allowed_companies=["01"],
    )
    assert highest.plan is not None
    assert highest.plan.dataset == "salaires.paie"
    assert highest.plan.metrics == ["masse_brute"]
    assert highest.plan.groupby == "NOM_PRENOM"
    assert highest.plan.series == "MAT_PERS"
    assert highest.plan.filters["ANNEE"] == [2026]
    assert highest.plan.filters["COD_SOC"] == ["01"]
    assert highest.plan.row_limit == 1
    assert client.calls == 0
    catalog = load_catalog()
    query = query_body(highest.plan, catalog["datasets"]["salaires.paie"], 500)["queries"][0]
    assert query["row_limit"] == 1
    assert query["orderby"] == [["masse_brute", False]]
    assert any(item["col"] == "ANNEE" and item["val"] == 2026 for item in query["filters"])
    assert any(item["col"] == "COD_TYP_BUL" and item["val"] == "BN" for item in query["filters"])

    above = answer_question(
        "les agents salaire brut supérieur à 3000 en 2026",
        client=client,
        use_examples=False,
        allowed_companies=["01"],
    )
    assert above.plan is not None
    assert above.plan.metrics == ["salaire_moyen"]
    assert above.plan.having is not None
    assert "> 3000" in above.plan.having
    assert "3000 2026" not in (above.text or "")
    assert "SUM(BRUT)" in above.plan.having
    above_query = query_body(above.plan, catalog["datasets"]["salaires.paie"], 500)["queries"][0]
    assert above_query["extras"]["having"] == above.plan.having
    assert above_query["row_limit"] == 500


def test_absence_year_overlaps_the_year() -> None:
    client = Scripted([
        '{"dataset":"conges.cng","detail":["MAT_PERS","NOM_PRENOM"],"metrics":[],"clarify":null}',
    ])
    result = answer_question(
        "gents en congé en 2025",
        client=client,
        use_examples=False,
        allowed_companies=["01"],
    )
    assert result.plan is not None
    catalog = load_catalog()
    where = query_body(result.plan, catalog["datasets"]["conges.cng"], 500)["queries"][0]["extras"]["where"]
    assert "DAT_DEBUT <= DATE '2025-12-31'" in where
    assert "DAT_FIN >= DATE '2025-01-01'" in where
    assert "DAT_FIN IS NULL" in where
    text = format_answer(
        result.plan,
        catalog["datasets"]["conges.cng"],
        [{"MAT_PERS": "1", "NOM_PRENOM": "A"}, {"MAT_PERS": "1", "NOM_PRENOM": "A"}],
    )
    assert text.startswith("1 personne.")


def main() -> None:
    test_bubble_examples()
    test_company_and_active_filter()
    test_sql_and_unknown_dataset_do_not_execute()
    test_examples_toggle()
    test_catalog_sql_stays_server_side()
    test_effectif_par_sexe_uses_catalog()
    test_loose_phrase_suggests_catalog_question()
    test_absence_day_lists_people()
    test_absence_year_overlaps_the_year()
    test_unknown_filter_column_is_refused()
    test_unknown_detail_column_is_refused()
    test_agent_gross_pay()
    test_answer_uses_rows_not_the_model()
    print("ok")


if __name__ == "__main__":
    main()
