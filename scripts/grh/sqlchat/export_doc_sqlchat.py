"""Word documentation of the GRH data chat (architecture, security, installation, user
guide, available views, evaluation results, limits).

Usage: python sqlchat/export_doc_sqlchat.py [--out exports/Documentation_Chatbot_SQL_GRH.docx]
Reads docker/pythonpath_dev/grh_sql_chat/schema.json and exports/eval_sql.json (eval_sql.py).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GRH_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GRH_DIR))

from docx import Document  # noqa: E402
from docx.shared import Pt  # noqa: E402

from export_doc import add_table, set_landscape  # noqa: E402

ROOT = GRH_DIR.parent.parent
SCHEMA = ROOT / "docker" / "pythonpath_dev" / "grh_sql_chat" / "schema.json"
EVAL = GRH_DIR / "exports" / "eval_sql.json"
DEFAULT_OUT = GRH_DIR / "exports" / "Documentation_Chatbot_SQL_GRH.docx"

PIPELINE = [
    ("1. Choix des vues", "retrieve.py",
     "Les mots de la question (accents, pluriels et synonymes normalisés) sont comparés aux noms des vues, "
     "indicateurs, libellés de colonnes et valeurs. Les 3 vues les plus proches au maximum sont retenues ; "
     "la vue du dashboard ouvert est favorisée."),
    ("2. Écriture du SQL", "generate.py",
     "Le modèle local (Ollama) reçoit les règles Oracle, la description des vues retenues (colonnes, libellés, "
     "valeurs possibles, formules des indicateurs), la date du jour et des exemples question → SQL. "
     "« cette année », « le mois dernier »… sont remplacés par la date exacte avant l'envoi. Une question "
     "identique à un exemple réutilise directement son SQL."),
    ("3. Contrôle", "guard.py",
     "Analyse syntaxique (sqlglot, dialecte Oracle) : une seule requête SELECT, aucune écriture (INSERT, UPDATE, "
     "DELETE, DDL, PL/SQL), aucun objet système (SYS, DBA_, ALL_, USER_, V$, DBMS_, UTL_), aucun lien de base "
     "(@), uniquement les vues GRH et leurs colonnes. Limite de 200 lignes ajoutée si absente."),
    ("4. Droits", "run.py",
     "Chaque vue correspond à un dataset Superset : l'utilisateur doit avoir accès à tous les datasets "
     "utilisés (même règle que pour les dashboards)."),
    ("5. Exécution", "run.py",
     "Chaque vue est remplacée par le SQL de son dataset (filtré sur la société si l'URL contient cod_soc), "
     "puis la requête est exécutée sur ENDADB via la connexion Superset (délai maximal 30 s, 200 lignes)."),
    ("6. Correction", "run.py",
     "Si Oracle ou le contrôle refuse la requête, l'erreur est renvoyée une fois au modèle pour correction."),
    ("7. Réponse", "answer.py",
     "Phrase construite par un modèle de texte fixe (jamais rédigée par le modèle), tableau formaté en français "
     "(50 lignes affichées), CSV complet, requête SQL, vues utilisées et durée."),
]

SECURITY = [
    ("Lecture seule", "Seules les requêtes SELECT passent le contrôle ; une seule instruction par question."),
    ("Périmètre", "Uniquement les 33 vues GRH plates et leurs colonnes ; tout autre objet est refusé."),
    ("Droits Superset", "Accès vérifié par dataset pour l'utilisateur connecté ; les anonymes n'ont pas la bulle."),
    ("Société", "Le paramètre cod_soc de l'URL filtre toutes les vues sur la société."),
    ("Volume et durée", "200 lignes au maximum, 30 s d'exécution au maximum côté Oracle."),
    ("Confidentialité", "Le modèle tourne en local (Ollama) : ni question ni donnée ne sort du serveur. "
                        "Les noms, matricules et numéros de décision ne sont jamais envoyés au modèle "
                        "(seuls les noms de colonnes le sont)."),
    ("Traçabilité", "Chaque réponse affiche la requête SQL exécutée ; les erreurs sont journalisées par Superset."),
]

LIMITS = [
    "Le modèle (1,5 milliard de paramètres) peut se tromper d'indicateur ou de filtre : vérifier la requête "
    "SQL affichée pour les chiffres sensibles, et préférer les dashboards pour les indicateurs officiels.",
    "Une question à la fois (verrou) : les autres utilisateurs attendent jusqu'à 20 s, puis reçoivent un message.",
    "Les questions qui demandent de croiser beaucoup de vues ou des calculs complexes (taux sur plusieurs "
    "périodes, cumuls) réussissent moins souvent : les découper en questions simples.",
    "Pas de mémoire de conversation : chaque question doit être complète (indicateur, période, filtre).",
    "Les valeurs proposées au modèle sont limitées aux 15 premières par colonne ; une valeur rare doit être "
    "écrite exactement comme dans les données.",
]


def build(out: Path) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    evaluation = json.loads(EVAL.read_text(encoding="utf-8")) if EVAL.exists() else None

    doc = Document()
    set_landscape(doc)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    doc.add_heading("Chatbot SQL GRH : interroger les données en français", 0)
    doc.add_paragraph(
        "La bulle « Données GRH », en bas à droite de Superset, répond à une question écrite en français en "
        "interrogeant directement la base GRH (ENDADB). Un modèle de langage local écrit la requête SQL, qui est "
        "contrôlée puis exécutée avec les droits de l'utilisateur ; le résultat s'affiche en tableau, avec la "
        "requête utilisée et un export CSV.")

    doc.add_heading("1. Architecture", 1)
    doc.add_paragraph(
        "Paquet Python docker/pythonpath_dev/grh_sql_chat chargé par Superset (blueprint Flask /grh-sql-chat), "
        "widget JavaScript injecté dans toutes les pages pour les utilisateurs connectés, modèle "
        f"{evaluation['model'] if evaluation else 'qwen2.5-coder:1.5b'} servi par Ollama.")
    add_table(doc, ["Étape", "Module", "Fonctionnement"], [list(p) for p in PIPELINE], [4, 3, 18.5])
    doc.add_paragraph(
        "Points d'accès : POST /grh-sql-chat/api/ask {question, slug, cod_soc} renvoie la réponse, le tableau, "
        "la requête et les durées ; GET /grh-sql-chat/api/examples?slug= renvoie les exemples de questions du "
        "dashboard ouvert.")

    doc.add_heading("2. Sécurité", 1)
    add_table(doc, ["Règle", "Mise en œuvre"], [list(s) for s in SECURITY], [5, 20.5])

    doc.add_heading("3. Installation et exploitation", 1)
    for title, text in [
        ("Modèle", "Variables OLLAMA_URL et OLLAMA_MODEL (docker/.env, docker/.env-local). Télécharger le modèle : "
                   "ollama pull qwen2.5-coder:1.5b (ou service ollama-pull de docker compose). Licence Apache 2.0."),
        ("Superset", "superset_config.py : BLUEPRINTS = [grh_sql_chat_bp] et init_grh_sql_chat(app) dans "
                     "FLASK_APP_MUTATOR. Redémarrer le conteneur superset_app après modification de docker/.env."),
        ("Schéma", "Après une modification des datasets GRH : python sqlchat/build_schema.py (régénère "
                   "schema.json : colonnes, libellés, valeurs, indicateurs, SQL des datasets, exemples)."),
        ("Exemples", "sqlchat/examples.py : exemples question → SQL montrés au modèle et questions proposées par "
                     "dashboard. Vérifier qu'ils s'exécutent : python sqlchat/eval_sql.py --examples."),
        ("Évaluation", "python sqlchat/eval_sql.py : pose 30 questions et compare les résultats à des requêtes de "
                       "référence (exports/eval_sql.json)."),
        ("Options", "GRH_SQL_CHAT_LLM_TIMEOUT (60 s), GRH_SQL_CHAT_LOCK_WAIT (20 s), GRH_SQL_CHAT_KEEP_ALIVE (24h). "
                    "Les requêtes réussies sont gardées 1 h en cache Redis."),
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"{title} : ").bold = True
        p.add_run(text)

    doc.add_heading("4. Guide d'utilisation", 1)
    for text in [
        "Cliquer sur la bulle en bas à droite, écrire la question et appuyer sur Entrée (Maj+Entrée pour aller à "
        "la ligne). La flèche ↑ rappelle les questions précédentes.",
        "Une bonne question précise l'indicateur, le découpage et la période : « Jours de maladie par direction "
        "en 2025 », « Top 10 des agents en retard en mars 2026 », « Net à payer moyen par sexe le dernier mois ».",
        "Pour un agent, écrire son nom en majuscules : « Retards de l'agent BEN SALAH par mois ».",
        "Sous chaque réponse : « Voir la requête SQL » (avec bouton Copier), « Télécharger CSV » (toutes les "
        "lignes, séparateur point-virgule, compatible Excel) et le lien vers le dashboard concerné.",
        "Sur un dashboard, la bulle propose des exemples adaptés et privilégie ses données.",
    ]:
        doc.add_paragraph(text, style="List Bullet")
    rows = [[d["title"], " · ".join(d["suggestions"])] for d in schema["dashboards"].values()]
    add_table(doc, ["Dashboard", "Exemples de questions"], rows, [5.5, 20])

    doc.add_heading("5. Vues interrogeables", 1)
    doc.add_paragraph("Chaque vue correspond à un dataset des dashboards GRH ; elle est décrite au modèle avec "
                      "ses colonnes et les formules de ses indicateurs.")
    rows = []
    for name, view in schema["views"].items():
        dash = next(d for d in schema["dashboards"].values() if d["key"] == view["dashboard"])
        rows.append([name, dash["title"], str(len(view["columns"])),
                     ", ".join(m["label"] for m in view["metrics"])])
    add_table(doc, ["Vue", "Dashboard", "Colonnes", "Indicateurs"], rows, [5, 4.5, 2, 14], mono_cols={0})

    doc.add_heading("6. Résultats de l'évaluation", 1)
    if evaluation:
        doc.add_paragraph(
            f"Évaluation du {evaluation['date']} avec {evaluation['model']} : {evaluation['questions']} questions "
            f"couvrant les {len(schema['dashboards'])} dashboards. Une réponse est exacte quand son résultat "
            "contient les mêmes lignes et les mêmes valeurs que la requête de référence (colonnes "
            "supplémentaires, ordre et arrondis à 0,5 près tolérés).")
        add_table(doc, ["Mesure", "Valeur"], [
            ["Résultats exacts", f"{evaluation['exact']} / {evaluation['questions']} "
                                 f"({evaluation['accuracy']:.0%})".replace(".", ",")],
            ["Résultats différents", str(evaluation["different"])],
            ["Requêtes refusées par le contrôle", str(evaluation["refused"])],
            ["Erreurs d'exécution", str(evaluation["errors"])],
            ["Requêtes corrigées automatiquement", str(evaluation["retried"])],
            ["Durée médiane par question", f"{evaluation['median_seconds']} s".replace(".", ",")],
        ], [9, 6])
        rows = [[r["question"], r["status"], f"{r['seconds']} s".replace(".", ","), r.get("sql") or r.get("error", "")]
                for r in evaluation["results"]]
        add_table(doc, ["Question", "Résultat", "Durée", "Requête générée"], rows, [6.5, 2.2, 1.8, 15],
                  mono_cols={3})
    else:
        doc.add_paragraph("Évaluation non lancée : python sqlchat/eval_sql.py.")

    doc.add_heading("7. Limites", 1)
    for text in LIMITS:
        doc.add_paragraph(text, style="List Bullet")

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    print(f"-> {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    build(parser.parse_args().out)


if __name__ == "__main__":
    main()
