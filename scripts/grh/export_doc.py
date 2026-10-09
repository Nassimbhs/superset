"""Generate a Word document describing every GRH dashboard from its spec:
dashboards summary, all metric formulas, datasets and one chart table per dashboard.

Usage: python export_doc.py [--out exports/Documentation_Dashboards_GRH.docx]
Requires: pip install python-docx
"""
from __future__ import annotations

import argparse
import importlib
import json
import re
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

import grh_builder
from grh_builder import HERE, SUITE, TimeFilter, render_sql

DEFAULT_OUT = HERE / "exports" / "Documentation_Dashboards_GRH.docx"

DESCRIPTIONS = {
    "synthese": "Vue mensuelle de synthèse : effectif payé, entrées/sorties, turnover, rétention, encadrement, "
                "absentéisme toutes causes et masse salariale rapportée à l'effectif.",
    "effectif": "Photographie de l'effectif actif : répartition par direction, sexe, âge, ancienneté, catégorie, "
                "grade, région, fonction et mouvements annuels.",
    "conges": "Suivi des demandes de congés et absences : volumes, types, motifs, statuts et agents absents ce jour.",
    "formation": "Activité de formation : actions, heures, coûts, domaines et agents formés.",
    "departs": "Départs définitifs par motif, taux de départ et projection des départs à la retraite.",
    "prets": "Prêts et avances au personnel : demandes, montants accordés, prêts en cours et mensualités.",
    "mobilite": "Mutations entre directions, demandes de mutation et promotions de grade.",
    "recrutement": "Recrutements par nature, direction et catégorie, et suivi des candidatures et concours.",
    "sante": "Absences pour maladie, maternité et accidents : jours, taux d'absentéisme maladie, indemnités CNAM.",
    "salaires": "Masse salariale, coût employeur, salaires moyens par catégorie, grade et ancienneté.",
    "presence": "Ponctualité et présence : retards, pointages et autorisations de sortie.",
    "budget": "Comparaison du budget de la masse salariale avec le réalisé de la paie.",
    "rendement": "Campagnes d'évaluation : notes de rendement, distribution et lien avec la promotion.",
    "soins": "Couverture médicale : bulletins de soins, frais engagés, remboursements et délais.",
    "social": "Œuvres sociales : aides et dons accordés, primes de scolarité.",
    "endettement": "Cessions sur salaire et taux d'endettement des agents.",
    "services": "Services RH rendus : attestations, demandes de service et intérims.",
}

VIZ_TYPES = {
    "big_number_total": "Indicateur clé",
    "echarts_timeseries_bar": "Barres",
    "echarts_timeseries_line": "Courbe",
    "pie": "Anneau",
    "table": "Tableau",
    "sankey_v2": "Flux (Sankey)",
}

GRAINS = {"P1D": "par jour", "P1M": "par mois", "P3M": "par trimestre", "P1Y": "par année"}

FORMATS = {
    "SMART_NUMBER": "nombre",
    ",.0f": "montant / entier",
    ",.1f": "nombre à 1 décimale",
    ",.2f": "nombre à 2 décimales",
    ".1%": "pourcentage (1 décimale)",
    ".2%": "pourcentage (2 décimales)",
}

SIMPLE_FILTERS = {
    ("DERNIER_12_MOIS", 1): "12 derniers mois",
    ("DOUZE_MOIS", 1): "12 derniers mois",
    ("DERNIER_MOIS", 1): "dernier mois de paie",
    ("EST_ACTIF", 1): "agents actifs",
    ("COD_TYP_BUL", "BN"): "paie mensuelle (bulletins BN)",
    ("EN_COURS", 1): "en cours",
    ("DERNIERE_SIMULATION", 1): "dernière simulation",
    ("CHANGE_DIRECTION", 1): "changement de direction",
    ("DERNIERE_ANNEE", 1): "dernière année / campagne",
    ("ANNEE_PRECEDENTE", 1): "année / campagne précédente",
    ("ACCORDE", 1): "prêts accordés",
    ("RUBRIQUE_PAIE", 1): "rubriques rattachées à la paie",
}

SQL_FILTERS = {
    "ANNEE = TO_CHAR(SYSDATE, 'YYYY')": "année en cours",
    "NATURE_ABSENCE <> 'Jours théoriques'": "hors lignes de jours théoriques",
    "DT_BUL >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -36)": "36 derniers mois",
    "DAT_DEM >= ADD_MONTHS(TRUNC(SYSDATE), -12)": "12 derniers mois",
    "DAT_DEBUT >= ADD_MONTHS(TRUNC(SYSDATE), -12) AND DAT_DEBUT <= TRUNC(SYSDATE)": "12 derniers mois",
    "DAT_DEBUT >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -24)": "24 derniers mois",
    "MOIS_RESTANTS BETWEEN 0 AND 12": "retraite dans les 12 mois",
    "MOIS_RESTANTS BETWEEN 0 AND 60": "retraite dans les 5 ans",
    "MOIS_RESTANTS BETWEEN 0 AND 120": "retraite dans les 10 ans",
    "MOIS_RESTANTS <= 24": "retraite dans les 24 mois",
    "DAT_DEBUT >= ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), -48)": "5 dernières années",
    "DAT_DEBUT >= ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), -108)": "10 dernières années",
    "DAT_EMB >= ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), -48)": "5 dernières années",
    "DAT_EMB >= ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), -228)": "20 dernières années",
}

COLUMN_LABELS = {
    "MAT_PERS": "Matricule", "NOM_PRENOM": "Nom et prénom", "DT_BUL": "Date du bulletin", "DT_MOIS": "Mois",
    "NUM_MOIS": "Mois", "DAT_EMB": "Date d'embauche", "DAT_DEM": "Date de demande", "DAT_ACC": "Date de l'accident",
    "DAT_MUT": "Date de mutation", "DAT_GRAD": "Date de promotion", "DAT_DEB_ACTION": "Début de l'action",
    "DAT_FIN_ACTION": "Fin de l'action", "DAT_DEBUT_AUT": "Date de l'autorisation", "DAT_ARRET_TRAV": "Date d'arrêt",
    "DATE_MVT": "Date du mouvement", "NBR_ECH": "Nombre d'échéances", "NBR_JOURS": "Nombre de jours",
    "MNT_ACCORDE": "Montant accordé", "REM_MEN": "Remboursement mensuel", "TAUX_IPP": "Taux d'IPP",
    "FLUX_ORIGINE": "Direction d'origine", "FLUX_DESTINATION": "Direction d'accueil",
    "MOIS_RESTANTS": "Mois restants avant la retraite", "NUM_DECISION": "Numéro de décision",
    "NIVEAU_ESTIME": "Niveau scolaire estimé", "BENEFICIAIRE": "Bénéficiaire",
}

COLUMN_WORDS = {
    "DAT": "date", "DATE": "date", "ANNEE": "année", "AGE": "âge", "ANCIENNETE": "ancienneté",
    "CATEGORIE": "catégorie", "DEBUT": "début", "DEPART": "départ", "ETAT": "état", "DEM": "demande",
    "SOINS": "soins", "ACTE": "acte", "ARRIVEE": "arrivée", "ESTIME": "estimé", "REMUNERATION": "rémunération",
    "PRET": "prêt", "DESTINATION": "destination", "ORIGINE": "origine", "REGION": "région", "RETRAITE": "retraite",
    "RECRUTEMENT": "recrutement", "INTITULE": "intitulé", "PARTICIPANTS": "participants", "COUT": "coût",
    "ACCIDENT": "accident", "CONGE": "congé", "MVT": "mouvement", "RETARD": "retard", "ENDETTEMENT": "endettement",
    "SEMAINE": "semaine", "OBTENU": "obtenu",
}

OPERATORS = {"==": "=", "!=": "≠", ">": ">", "<": "<", ">=": "≥", "<=": "≤", "IN": "dans", "NOT IN": "hors"}

CONVENTIONS = [
    ("EST_ACTIF", "1 si l'agent est en activité (PERSONNEL.ETAT_ACT = '0')."),
    ("DERNIER_12_MOIS / DOUZE_MOIS", "1 si la ligne tombe dans les 12 derniers mois (par rapport à la date du jour "
                                    "ou au dernier mois de paie selon le dataset)."),
    ("DERNIER_MOIS", "1 pour le dernier mois de paie mensuelle disponible."),
    ("Pôle / Direction / Service", "Niveaux 2 et 3 de l'arborescence SERVICE (SER_COD_SERV) ; le service est "
                                   "l'affectation réelle de l'agent."),
    ("Effectif payé", "Agents distincts ayant un bulletin de paie mensuel (BULLETINH, COD_TYP_BUL = 'BN')."),
    ("Entrée", "Agent payé dans le mois sans l'avoir été le mois précédent."),
    ("Sortie", "Agent payé dans le mois sans l'être le mois suivant."),
    ("REF_M12 / RETENU", "Agents payés 12 mois avant le dernier mois / parmi eux, ceux encore payés le dernier mois "
                         "(taux de rétention = RETENU / REF_M12)."),
    ("Turnover", "(entrées + sorties) / 2 / effectif moyen de la période."),
    ("Responsable", "Agent ayant une fonction (FONCTION <> 'Sans fonction') : chef de service, chef d'agence, "
                    "directeur, etc. Photo à la date du jour."),
    ("Jours théoriques", "230 / 12 jours ouvrés par agent payé et par mois (230 jours par an)."),
    ("Absentéisme toutes causes", "Congés maladie (type 02), exceptionnels (03) et sanctions (05), hors congé "
                                  "annuel (01) et autres absences (08 : formation, mission, badge)."),
    ("Coût employeur", "Brut (rubrique 50000) + charges patronales (rubriques 81%)."),
]


# --------------------------------------------------------------------------- spec reading


def col_label(name: str) -> str:
    if name in COLUMN_LABELS:
        return COLUMN_LABELS[name]
    words = [COLUMN_WORDS.get(w, w.lower()) for w in name.split("_")]
    if words[0] in {"type", "nature", "tranche", "famille", "groupe", "mode", "objet", "statut", "niveau",
                    "modele", "heure", "jour"} and len(words) > 1:
        words.insert(1, "de" if words[1][0] not in "aeiouéâ" else "d'")
    text = " ".join(words).replace("d' ", "d'").replace("modele", "modèle")
    return text[:1].upper() + text[1:]


def fmt_label(fmt: str | None) -> str:
    return FORMATS.get(fmt or "SMART_NUMBER", fmt or "nombre")


def describe_filter(f: dict) -> str:
    if f["expressionType"] == "SQL":
        return SQL_FILTERS.get(f["sqlExpression"], f["sqlExpression"])
    if f["operator"] == "TEMPORAL_RANGE":
        return ""
    known = SIMPLE_FILTERS.get((f["subject"], f["comparator"]))
    if known and f["operator"] == "==":
        return known
    return f"{f['subject']} {OPERATORS.get(f['operator'], f['operator'])} {f['comparator']}"


def chart_metrics(params: dict) -> list[str]:
    if "metric" in params:
        return [params["metric"]]
    return list(params.get("metrics", []))


def chart_type(params: dict) -> str:
    viz = params["viz_type"]
    label = VIZ_TYPES.get(viz, viz)
    if viz == "echarts_timeseries_bar":
        if params.get("orientation") == "horizontal":
            label += " horizontales"
        if params.get("stack"):
            label += " empilées"
    if viz == "table":
        label += " agrégé" if params.get("query_mode") == "aggregate" else " détaillé"
    return label


def chart_axes(params: dict) -> str:
    viz = params["viz_type"]
    col = col_label
    if viz == "sankey_v2":
        return f"{col(params['source'])} → {col(params['target'])}"
    if viz == "pie":
        return ", ".join(col(c) for c in params["groupby"])
    if viz == "table":
        cols = params.get("groupby") or params.get("all_columns") or []
        return ", ".join(col(c) for c in cols)
    if viz.startswith("echarts_timeseries"):
        axis = col(params["x_axis"])
        if params.get("x_axis_is_time"):
            axis += f" ({GRAINS.get(params.get('time_grain_sqla'), params.get('time_grain_sqla'))})"
        groups = params.get("groupby") or []
        if groups:
            axis += " ; séries : " + ", ".join(col(g) for g in groups)
        return axis
    return ""


def chart_meaning(params: dict, measures: list[str], filters: list[str]) -> str:
    viz = params["viz_type"]
    col = lambda c: col_label(c).lower()
    what = " et ".join(m.lower() for m in measures) if measures else ""
    if viz == "big_number_total":
        text = f"Valeur unique : {what}"
        if params.get("subheader"):
            text += f" ({params['subheader']})"
    elif viz == "pie":
        text = f"Part de chaque {col(params['groupby'][0])} dans le total : {what}"
    elif viz == "sankey_v2":
        text = f"Flux de {what} de {col(params['source'])} vers {col(params['target'])}"
    elif viz == "table" and params.get("query_mode") != "aggregate":
        text = f"Liste détaillée ({len(params.get('all_columns', []))} colonnes), " \
               f"triée par {col(json_order(params))}"
    elif viz == "table":
        text = f"Tableau de {what} par {', '.join(col(c) for c in params['groupby'])}"
    else:
        grain = GRAINS.get(params.get("time_grain_sqla"), "") if params.get("x_axis_is_time") else ""
        axis = grain if grain else f"par {col(params['x_axis'])}"
        text = f"{what[:1].upper() + what[1:]} {axis}"
        if params.get("groupby"):
            text += ", ventilé par " + ", ".join(col(g) for g in params["groupby"])
        if viz == "echarts_timeseries_line":
            text += " (évolution)"
    if filters:
        text += " — périmètre : " + ", ".join(filters)
    return text[:1].upper() + text[1:] + "."


def json_order(params: dict) -> str:
    order = params.get("order_by_cols") or []
    return json.loads(order[0])[0] if order else ""


def source_tables(sql: str) -> list[str]:
    ctes = {m.lower() for m in re.findall(r"(?:WITH|,)\s*(\w+)\s+AS\s*\(", sql, re.I)}
    tables = []
    for name in re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_][\w$#]*)\b(?!\.)", sql, re.I):
        low = name.lower()
        if low in ctes or low in {"select", "dual", "table", "lateral"} or low in tables:
            continue
        tables.append(low)
    return [t.upper() for t in tables]


class FakeIds(dict):
    def __missing__(self, key):
        return 0


def load_dashboards() -> list[dict]:
    result = []
    for key, label, slug in SUITE:
        spec = importlib.import_module(f"dashboards.{key}")
        datasets = {ds.key: ds for ds in spec.DATASETS}
        metrics = {(ds.key, m.name): m for ds in spec.DATASETS for m in ds.metrics}
        charts = spec.charts(FakeIds({k: 0 for k in datasets}))
        order = [k for row in spec.LAYOUT for k, *_ in row]
        order += [k for k in charts if k not in order]
        rows = []
        for ck in order:
            chart = charts[ck]
            p = chart.params
            names = chart_metrics(p)
            measures = [metrics[(chart.dataset, n)].verbose if (chart.dataset, n) in metrics else n for n in names]
            filters = [t for t in (describe_filter(f) for f in p.get("adhoc_filters", [])) if t]
            rows.append({
                "key": ck,
                "name": chart.name,
                "dataset": datasets[chart.dataset].name,
                "type": chart_type(p),
                "measures": measures,
                "formulas": [metrics[(chart.dataset, n)].expression for n in names if (chart.dataset, n) in metrics],
                "axes": chart_axes(p),
                "filters": filters,
                "meaning": chart_meaning(p, measures, filters),
            })
        filters = []
        for f in spec.FILTERS:
            if isinstance(f, TimeFilter):
                filters.append({"label": f.label, "column": "Période (filtre de temps)",
                                "scope": ", ".join(charts[c].name for c in f.charts if c in charts)})
            else:
                note = "dépend du filtre Pôle" if f.column == "DIRECTION" and any(
                    getattr(o, "column", None) == "POLE" for o in spec.FILTERS) else ""
                if f.exclude:
                    excl = ", ".join(charts[c].name for c in f.exclude if c in charts)
                    note = (note + " ; " if note else "") + f"sans effet sur : {excl}"
                filters.append({"label": f.label, "column": f.column, "scope": note or "tous les graphiques concernés"})
        result.append({
            "key": key, "label": label, "title": spec.TITLE, "slug": spec.SLUG,
            "description": DESCRIPTIONS.get(key, ""),
            "datasets": [{
                "name": ds.name, "sql_file": ds.sql_file, "date_col": ds.main_dttm_col or "",
                "tables": source_tables(render_sql(ds.sql_file)),
                "metrics": ds.metrics,
            } for ds in spec.DATASETS],
            "charts": rows,
            "filters": filters,
        })
    return result


# --------------------------------------------------------------------------- docx helpers


HEADER_FILL = "1E3A8A"


def set_landscape(doc: Document) -> None:
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Cm(1.5))


def shade(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    tr_pr.append(el)


def write_cell(cell, text: str, bold: bool = False, mono: bool = False, color: RGBColor | None = None) -> None:
    cell.text = ""
    run = cell.paragraphs[0].add_run(text)
    run.font.size = Pt(8 if mono else 9)
    run.bold = bold
    if mono:
        run.font.name = "Consolas"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    if color:
        run.font.color.rgb = color


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float],
              mono_cols: set[int] = frozenset()) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    header = table.rows[0]
    repeat_header(header)
    for i, h in enumerate(headers):
        write_cell(header.cells[i], h, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
        shade(header.cells[i], HEADER_FILL)
    for values in rows:
        cells = table.add_row().cells
        for i, v in enumerate(values):
            write_cell(cells[i], v, mono=i in mono_cols)
    for row in table.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    doc.add_paragraph()


# --------------------------------------------------------------------------- document


def build_document(dashboards: list[dict], out: Path) -> dict[str, int]:
    doc = Document()
    set_landscape(doc)
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    n_charts = sum(len(d["charts"]) for d in dashboards)
    n_metrics = sum(len(ds["metrics"]) for d in dashboards for ds in d["datasets"])
    n_datasets = sum(len(d["datasets"]) for d in dashboards)

    doc.add_heading("Documentation des tableaux de bord GRH", 0)
    doc.add_paragraph(f"Généré le {datetime.now():%d/%m/%Y à %H:%M} à partir des spécifications "
                      f"scripts/grh/dashboards (Superset, base {grh_builder.DATABASE_NAME}).")
    doc.add_paragraph(f"{len(dashboards)} dashboards · {n_datasets} datasets · {n_charts} graphiques · "
                      f"{n_metrics} métriques (formules).")

    doc.add_heading("1. Récapitulatif des dashboards", 1)
    add_table(doc, ["N°", "Dashboard", "Lien", "Objectif", "Datasets", "Graphiques", "Filtres disponibles"], [
        [str(i), d["title"], f"/superset/dashboard/{d['slug']}/", d["description"], str(len(d["datasets"])),
         str(len(d["charts"])), ", ".join(f["label"] for f in d["filters"])]
        for i, d in enumerate(dashboards, start=1)
    ], [1, 3.5, 4.5, 8, 1.6, 1.8, 5.5])

    doc.add_heading("2. Formules : toutes les métriques", 1)
    doc.add_paragraph("Chaque métrique est une expression SQL agrégée, évaluée par Superset sur le dataset, "
                      "après application des filtres du graphique et du dashboard.")
    add_table(doc, ["Dashboard", "Dataset", "Métrique", "Libellé", "Formule SQL", "Format"], [
        [d["title"], ds["name"], m.name, m.verbose, m.expression, fmt_label(m.d3format)]
        for d in dashboards for ds in d["datasets"] for m in ds["metrics"]
    ], [3.2, 3.8, 3.2, 4.5, 9.5, 2.5], mono_cols={2, 4})

    doc.add_heading("3. Datasets et tables sources", 1)
    add_table(doc, ["Dashboard", "Dataset Superset", "Fichier SQL", "Tables Oracle sources", "Colonne date"], [
        [d["title"], ds["name"], f"sql/{ds['sql_file']}", ", ".join(ds["tables"]), ds["date_col"]]
        for d in dashboards for ds in d["datasets"]
    ], [3.5, 4.5, 4, 11, 3.2], mono_cols={1, 2})

    doc.add_heading("4. Détail des graphiques par dashboard", 1)
    for i, d in enumerate(dashboards, start=1):
        doc.add_heading(f"4.{i} {d['title']}", 2)
        p = doc.add_paragraph()
        p.add_run("Lien : ").bold = True
        p.add_run(f"/superset/dashboard/{d['slug']}/")
        p = doc.add_paragraph()
        p.add_run("Objectif : ").bold = True
        p.add_run(d["description"])
        add_table(doc, ["N°", "Graphique", "Type", "Mesure", "Axe / regroupement", "Filtres fixes",
                        "Ce que représente le graphique"], [
            [str(n), c["name"], c["type"], ", ".join(c["measures"]) or "Liste détaillée", c["axes"] or "—",
             ", ".join(c["filters"]) or "—", c["meaning"]]
            for n, c in enumerate(d["charts"], start=1)
        ], [0.9, 4.2, 2.6, 3.6, 4, 3.2, 7.6])
        doc.add_paragraph().add_run("Filtres du dashboard").bold = True
        add_table(doc, ["Filtre", "Colonne", "Portée / remarque"], [
            [f["label"], f["column"], f["scope"]] for f in d["filters"]
        ], [5, 5, 16])

    doc.add_heading("Annexe : conventions et définitions", 1)
    add_table(doc, ["Terme / colonne", "Définition"], [[t, v] for t, v in CONVENTIONS], [6, 20])

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return {"dashboards": len(dashboards), "datasets": n_datasets, "charts": n_charts, "metrics": n_metrics}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    dashboards = load_dashboards()
    stats = build_document(dashboards, args.out)
    print(", ".join(f"{v} {k}" for k, v in stats.items()))
    print(f"document: {args.out}")


if __name__ == "__main__":
    main()
