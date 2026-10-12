"""Evaluate the GRH data chat: each question is asked to the real pipeline (model, guard,
Oracle) and its result is compared with the result of a hand-written reference SQL.

    python sqlchat/eval_sql.py              # 30 questions -> exports/eval_sql.json
    python sqlchat/eval_sql.py --examples   # every example of examples.py must run
    python sqlchat/eval_sql.py --runs 2 --compare exports/eval_sql_baseline.json
                                            # each question twice, compared with the baseline
                                            # -> exports/eval_sql_comparaison.json
    python sqlchat/eval_sql.py --model qwen2.5-coder:7b
                                            # another Ollama model -> exports/eval_sql_qwen2.5-coder_7b.json

The script copies itself into the superset_app container and runs there (Superset app
context, admin user), because the views only exist as dataset SQL inside Superset.
"""
from __future__ import annotations

import json
import statistics
import subprocess
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

CONTAINER = "superset_app"
HERE = Path(__file__).resolve().parent
OUTPUT = HERE.parent / "exports" / "eval_sql.json"
COMPARISON = HERE.parent / "exports" / "eval_sql_comparaison.json"
MODEL_TIMEOUT = 300

QUESTIONS: list[dict] = [
    {"dashboard": "synthese", "question": "Nombre d'entrées et de sorties en 2025",
     "sql": "SELECT SUM(ENTREE) AS ENTREES, SUM(SORTIE) AS SORTIES FROM v_grh_effectif_mensuel WHERE ANNEE = '2025'"},
    {"dashboard": "synthese", "question": "Jours d'absence par nature d'absence sur les 12 derniers mois",
     "sql": "SELECT NATURE_ABSENCE, SUM(JOURS_ABSENCE) AS JOURS FROM v_grh_absenteisme_global WHERE DOUZE_MOIS = 1 "
            "GROUP BY NATURE_ABSENCE"},
    {"dashboard": "effectif", "question": "Nombre d'agents actifs par sexe",
     "sql": "SELECT SEXE, COUNT(DISTINCT MAT_PERS) AS EFFECTIF FROM v_effectif_grh WHERE EST_ACTIF = 1 GROUP BY SEXE"},
    {"dashboard": "effectif", "question": "Âge moyen des agents actifs par catégorie",
     "sql": "SELECT CATEGORIE, AVG(AGE) AS AGE_MOYEN FROM v_effectif_grh WHERE EST_ACTIF = 1 GROUP BY CATEGORIE"},
    {"dashboard": "effectif", "question": "Nombre d'agents actifs par tranche d'âge",
     "sql": "SELECT TRANCHE_AGE, COUNT(DISTINCT MAT_PERS) AS EFFECTIF FROM v_effectif_grh WHERE EST_ACTIF = 1 "
            "GROUP BY TRANCHE_AGE"},
    {"dashboard": "conges", "question": "Jours de congé annuel pris en 2025 par direction",
     "sql": "SELECT DIRECTION, SUM(NBR_JOURS) AS JOURS FROM v_grh_conges WHERE ANNEE = '2025' "
            "AND TYPE_CONGE = 'Congé annuel' GROUP BY DIRECTION"},
    {"dashboard": "conges", "question": "Combien d'agents sont en congé en ce moment ?",
     "sql": "SELECT COUNT(DISTINCT MAT_PERS) AS AGENTS FROM v_grh_conges WHERE EN_COURS = 1"},
    {"dashboard": "formation", "question": "Nombre d'actions de formation par année",
     "sql": "SELECT ANNEE, COUNT(DISTINCT NUM_ACTION) AS ACTIONS FROM v_grh_formation_actions GROUP BY ANNEE"},
    {"dashboard": "formation", "question": "Heures de formation par sexe",
     "sql": "SELECT SEXE, SUM(HEURES) AS HEURES FROM v_grh_formation_participants GROUP BY SEXE"},
    {"dashboard": "departs", "question": "Âge moyen au départ par type de départ",
     "sql": "SELECT TYPE_DEPART, AVG(AGE_DEPART) AS AGE_MOYEN FROM v_grh_departs GROUP BY TYPE_DEPART"},
    {"dashboard": "departs", "question": "Combien d'agents partent à la retraite en 2026 ?",
     "sql": "SELECT COUNT(DISTINCT MAT_PERS) AS AGENTS FROM v_grh_retraites WHERE ANNEE_RETRAITE = '2026'"},
    {"dashboard": "prets", "question": "Nombre de prêts par groupe de prêt",
     "sql": "SELECT GROUPE_PRET, COUNT(*) AS PRETS FROM v_grh_prets GROUP BY GROUPE_PRET"},
    {"dashboard": "prets", "question": "Montant accordé des prêts en cours par direction",
     "sql": "SELECT DIRECTION, SUM(MNT_ACCORDE) AS MONTANT FROM v_grh_prets WHERE EN_COURS = 1 GROUP BY DIRECTION"},
    {"dashboard": "mobilite", "question": "Nombre de mutations par raison",
     "sql": "SELECT RAISON, COUNT(*) AS MUTATIONS FROM v_grh_mutations GROUP BY RAISON"},
    {"dashboard": "mobilite", "question": "Nombre de promotions par année",
     "sql": "SELECT ANNEE, COUNT(*) AS PROMOTIONS FROM v_grh_promotions GROUP BY ANNEE"},
    {"dashboard": "recrutement", "question": "Nombre de candidats par sexe",
     "sql": "SELECT SEXE, COUNT(*) AS CANDIDATS FROM v_grh_candidats GROUP BY SEXE"},
    {"dashboard": "recrutement", "question": "Recrutements par nature de recrutement",
     "sql": "SELECT NATURE_RECRUTEMENT, COUNT(DISTINCT MAT_PERS) AS RECRUTEMENTS FROM v_grh_recrutements "
            "GROUP BY NATURE_RECRUTEMENT"},
    {"dashboard": "sante", "question": "Jours de maladie par nature d'absence en 2025",
     "sql": "SELECT NATURE_ABSENCE, SUM(NBR_JOURS) AS JOURS FROM v_grh_absences_maladie WHERE ANNEE = '2025' "
            "GROUP BY NATURE_ABSENCE"},
    {"dashboard": "sante", "question": "Nombre de demandes d'indemnités maladie par situation",
     "sql": "SELECT SITUATION, COUNT(*) AS DEMANDES FROM v_grh_indemnites_maladie GROUP BY SITUATION"},
    {"dashboard": "salaires", "question": "Coût employeur total en 2025",
     "sql": "SELECT SUM(COUT_EMPLOYEUR) AS COUT FROM v_grh_paie WHERE ANNEE = '2025' AND COD_TYP_BUL = 'BN'"},
    {"dashboard": "salaires", "question": "Net à payer moyen par sexe le dernier mois",
     "sql": "SELECT SEXE, AVG(NET_A_PAYER) AS NET_MOYEN FROM v_grh_paie WHERE DERNIER_MOIS = 1 AND COD_TYP_BUL = 'BN' "
            "GROUP BY SEXE"},
    {"dashboard": "presence", "question": "Nombre de retards par jour de la semaine en 2026",
     "sql": "SELECT JOUR_SEMAINE, COUNT(*) AS RETARDS FROM v_grh_retards WHERE ANNEE = '2026' GROUP BY JOUR_SEMAINE"},
    {"dashboard": "presence", "question": "Minutes de sortie autorisée par direction en 2025",
     "sql": "SELECT DIRECTION, SUM(MINUTES_SORTIE) AS MINUTES FROM v_grh_autorisations_sortie WHERE ANNEE = '2025' "
            "GROUP BY DIRECTION"},
    {"dashboard": "budget", "question": "Budget total et réalisé en 2025",
     "sql": "SELECT SUM(BUDGET) AS BUDGET, SUM(REALISE) AS REALISE FROM v_grh_budget WHERE ANNEE = 2025"},
    {"dashboard": "rendement", "question": "Nombre d'agents par tranche de note la dernière année",
     "sql": "SELECT TRANCHE_NOTE, COUNT(DISTINCT MAT_PERS) AS AGENTS FROM v_grh_notes_rendement "
            "WHERE DERNIERE_ANNEE = 1 GROUP BY TRANCHE_NOTE"},
    {"dashboard": "soins", "question": "Frais engagés et montant remboursé par bénéficiaire",
     "sql": "SELECT BENEFICIAIRE, SUM(FRAIS_ENGAGES) AS FRAIS, SUM(MONTANT_REMBOURSE) AS REMBOURSE FROM v_grh_soins "
            "GROUP BY BENEFICIAIRE"},
    {"dashboard": "social", "question": "Montant des primes de scolarité par année",
     "sql": "SELECT ANNEE, SUM(MONTANT_PRIME) AS MONTANT FROM v_grh_scolarite GROUP BY ANNEE"},
    {"dashboard": "endettement", "question": "Nombre d'agents par tranche d'endettement à la dernière simulation",
     "sql": "SELECT TRANCHE_ENDETTEMENT, COUNT(DISTINCT MAT_PERS) AS AGENTS FROM v_grh_capacite "
            "WHERE DERNIERE_SIMULATION = 1 GROUP BY TRANCHE_ENDETTEMENT"},
    {"dashboard": "services", "question": "Nombre d'attestations éditées par modèle",
     "sql": "SELECT MODELE_ATTESTATION, COUNT(*) AS ATTESTATIONS FROM v_grh_attestations GROUP BY MODELE_ATTESTATION"},
    {"dashboard": "services", "question": "Délai moyen de réponse aux demandes par type",
     "sql": "SELECT TYPE_DEMANDE, AVG(DELAI_REPONSE) AS DELAI FROM v_grh_demandes_service GROUP BY TYPE_DEMANDE"},
]


# --------------------------------------------------------------------------- comparison


def _value(v):
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, str):
        v = v.strip()
        return float(v) if v.isdigit() else v.upper()
    return v


def _sorted(column: list) -> list:
    return sorted(column, key=lambda v: (v is None, isinstance(v, str), v if isinstance(v, (int, float)) else str(v)))


def _same(a: list, b: list) -> bool:
    for x, y in zip(a, b):
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            if abs(x - y) > max(0.5, abs(x) * 0.001):
                return False
        elif x != y:
            return False
    return True


def same_result(ref_rows: list[tuple], got_rows: list[tuple]) -> bool:
    """Same row count, and every reference column found among the generated columns
    (order of rows and columns, aliases and extra columns do not matter)."""
    if len(ref_rows) != len(got_rows):
        return False
    if not ref_rows:
        return True
    got_cols = [_sorted([_value(v) for v in col]) for col in zip(*got_rows)]
    for col in zip(*ref_rows):
        wanted = _sorted([_value(v) for v in col])
        match = next((i for i, g in enumerate(got_cols) if _same(wanted, g)), None)
        if match is None:
            return False
        got_cols.pop(match)
    return True


# --------------------------------------------------------------------------- inside the container


def _app_context():
    from flask import g
    from flask_login import login_user
    from superset.app import create_app

    app = create_app()
    ctx = app.test_request_context()
    ctx.push()
    from superset import security_manager

    user = security_manager.find_user(username="admin")
    login_user(user)
    g.user = user
    return ctx


def _run_sql(sql: str, schema) -> list[tuple]:
    from grh_sql_chat.guard import check
    from grh_sql_chat.run import execute, wrap

    checked, used = check(sql, schema.catalog)
    return execute(wrap(checked, used, schema, None), schema)[1]


def inside_examples() -> dict:
    from grh_sql_chat.schema import get_schema

    schema = get_schema()
    queries = schema.examples + QUESTIONS
    failures = []
    for e in queries:
        try:
            rows = _run_sql(e["sql"], schema)
            print(f"ok   {len(rows):>4} lignes  {e['question']}", file=sys.stderr)
        except Exception as exc:  # noqa: BLE001
            failures.append({"question": e["question"], "error": str(exc)[:300]})
            print(f"FAIL {e['question']}: {str(exc)[:200]}", file=sys.stderr)
    return {"examples": len(queries), "failures": failures}


def _ask_once(q: dict, ref: list[tuple], schema, slug: str | None) -> dict:
    from grh_sql_chat.guard import Refused
    from grh_sql_chat.run import ask

    item: dict = {}
    started = time.monotonic()
    try:
        res = ask(q["question"], schema, slug, use_cache=False)
        item.update(sql=res.sql, rows=len(res.rows), retried=res.retried,
                    status="exact" if same_result(ref, res.rows) else "différent")
    except Refused as exc:
        item.update(status="refusé", error=str(exc)[:300], sql=exc.sql)
    except Exception as exc:  # noqa: BLE001
        item.update(status="erreur", error=str(exc)[:300], sql=getattr(exc, "sql", ""))
    item["seconds"] = round(time.monotonic() - started, 1)
    return item


def summary(results: list[dict]) -> dict:
    def count(status: str) -> int:
        return sum(r["status"] == status for r in results)

    seconds = sorted(r["seconds"] for r in results)
    return {
        "questions": len(results),
        "exact": count("exact"),
        "different": count("différent"),
        "refused": count("refusé"),
        "errors": count("erreur"),
        "retried": sum(bool(r.get("retried")) for r in results),
        "accuracy": round(count("exact") / len(results), 3),
        "median_seconds": statistics.median(seconds),
        "p90_seconds": seconds[min(len(seconds) - 1, int(len(seconds) * 0.9))],
    }


def inside_questions(runs: int) -> dict:
    """Every question is asked ``runs`` times: the first run gives the status, the others reveal
    unstable answers (same question, different outcome)."""
    from grh_sql_chat.generate import OLLAMA_MODEL
    from grh_sql_chat.schema import get_schema

    schema = get_schema()
    slugs = {d["key"]: slug for slug, d in schema.dashboards.items()}
    results = []
    for q in QUESTIONS:
        ref = _run_sql(q["sql"], schema)
        attempts = [_ask_once(q, ref, schema, slugs.get(q["dashboard"])) for _ in range(runs)]
        item = {"dashboard": q["dashboard"], "question": q["question"], "reference": q["sql"],
                "reference_rows": len(ref), **attempts[0],
                "seconds": statistics.median(a["seconds"] for a in attempts),
                "runs": [a["status"] for a in attempts], "run_seconds": [a["seconds"] for a in attempts]}
        item["unstable"] = len(set(item["runs"])) > 1
        if item["unstable"]:
            item["other_runs"] = [{k: a.get(k) for k in ("status", "sql", "error")} for a in attempts[1:]]
        print(f"{item['status']:<10} {item['seconds']:>5}s  {'/'.join(item['runs']):<20} {q['question']}",
              file=sys.stderr)
        results.append(item)
    return {"model": OLLAMA_MODEL, "date": date.today().isoformat(), "runs": runs, **summary(results),
            "median_first_run_seconds": statistics.median(r["run_seconds"][0] for r in results),
            "unstable": sum(r["unstable"] for r in results), "results": results}


def compare(before: dict, after: dict) -> dict:
    """Question-by-question comparison with an earlier evaluation (eval_sql_baseline.json)."""
    old = {r["question"]: r for r in before["results"]}
    rows = []
    for r in after["results"]:
        b = old.get(r["question"], {})
        rows.append({"question": r["question"], "before": b.get("status"), "after": r["status"],
                     "before_seconds": b.get("seconds"), "after_seconds": r["seconds"],
                     "runs": r.get("runs"), "unstable": r.get("unstable", False),
                     "change": ("gagné" if r["status"] == "exact" and b.get("status") != "exact" else
                                "perdu" if b.get("status") == "exact" and r["status"] != "exact" else "")})
    common = [r for r in before["results"] if r["question"] in {x["question"] for x in after["results"]}]
    return {"before": {"date": before.get("date"), **summary(common)},
            "after": {"date": after.get("date"), "unstable": after.get("unstable", 0),
                      "median_first_run_seconds": after.get("median_first_run_seconds"), **summary(after["results"])},
            "gained": [r["question"] for r in rows if r["change"] == "gagné"],
            "lost": [r["question"] for r in rows if r["change"] == "perdu"],
            "questions": rows}


# --------------------------------------------------------------------------- host side


def _option(args: list[str], name: str) -> str | None:
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else None


def main() -> None:
    args = sys.argv[1:]
    runs = int(_option(args, "--runs") or 1)
    if "--inside" in args:
        sys.path.insert(0, "/app/docker/pythonpath_dev")
        ctx = _app_context()
        try:
            out = inside_examples() if "--examples" in args else inside_questions(runs)
        finally:
            ctx.pop()
        print("@@RESULT@@" + json.dumps(out, ensure_ascii=False))
        return

    baseline = _option(args, "--compare")
    model = _option(args, "--model")
    output = OUTPUT.with_name(f"eval_sql_{model.replace(':', '_').replace('/', '_')}.json") if model else OUTPUT
    env = ["-e", f"OLLAMA_MODEL={model}", "-e", f"GRH_SQL_CHAT_LLM_TIMEOUT={MODEL_TIMEOUT}"] if model else []
    subprocess.run(["docker", "cp", str(Path(__file__).resolve()), f"{CONTAINER}:/tmp/eval_sql.py"], check=True)
    inside = ["--examples"] if "--examples" in args else ["--runs", str(runs)]
    proc = subprocess.run(
        ["docker", "exec", "-e", "PYTHONIOENCODING=utf-8", *env, CONTAINER, "python", "/tmp/eval_sql.py",
         "--inside", *inside],
        stdout=subprocess.PIPE, text=True, encoding="utf-8", check=False,
    )
    marker = next((line for line in proc.stdout.splitlines() if line.startswith("@@RESULT@@")), None)
    if marker is None:
        sys.exit(f"Évaluation interrompue (code {proc.returncode}).")
    out = json.loads(marker[len("@@RESULT@@"):])
    if "--examples" in args:
        print(f"{out['examples'] - len(out['failures'])}/{out['examples']} requêtes (exemples et références) "
              "exécutées sans erreur")
        sys.exit(1 if out["failures"] else 0)
    output.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{out['model']} : {out['exact']}/{out['questions']} résultats exacts ({out['accuracy']:.0%}), "
          f"{out['different']} différents, {out['refused']} refusés, {out['errors']} erreurs, "
          f"{out['retried']} corrigés, {out['unstable']} instables ; médiane {out['median_seconds']} s "
          f"(1re passe {out['median_first_run_seconds']} s), p90 {out['p90_seconds']} s -> {output}")
    if baseline:
        before = json.loads((HERE.parent / baseline if not Path(baseline).is_absolute() else Path(baseline))
                            .read_text(encoding="utf-8"))
        result = compare(before, out)
        COMPARISON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        b, a = result["before"], result["after"]
        print(f"Avant : {b['exact']} exacts, {b['different']} différents, {b['refused']} refusés, "
              f"{b['errors']} erreurs, médiane {b['median_seconds']} s")
        print(f"Après : {a['exact']} exacts, {a['different']} différents, {a['refused']} refusés, "
              f"{a['errors']} erreurs, médiane {a['median_seconds']} s")
        print(f"Gagnées : {result['gained']}\nPerdues : {result['lost']} -> {COMPARISON}")


if __name__ == "__main__":
    main()
