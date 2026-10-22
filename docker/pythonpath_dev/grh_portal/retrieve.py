"""Keyword retrieval over the Bulle RH catalog.

The tokenizer and preset ranking match ``static/bubble.js`` (``search``).
KPI and glossary hits are extra context for the assistant prompt.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
CATALOG_FILE = HERE / "catalog.json"

STOP = {
    "le", "la", "les", "de", "des", "du", "par", "en", "et", "au", "aux", "un", "une", "pour",
    "sur", "dans", "quel", "quels", "quelle", "quelles", "est", "sont", "nos", "notre", "mes",
    "ma", "mon", "qui", "que", "quoi", "avec", "ce", "ces", "cette", "il", "ils", "on", "nous",
    "je", "veux", "voir", "afficher", "donne", "moi", "svp", "chaque", "tous", "toutes", "tout",
}
GRAINS = {"P1Y": "Année", "P3M": "Trimestre", "P1M": "Mois", "P1D": "Jour"}
MONTHS = {
    "janvier", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
}
FILLER = {"top", "ont", "plus", "grand", "meilleur", "classement", "avoir", "ete"}
_TOKEN_RE = re.compile(r"[^a-z0-9%]+")

_cache: dict[str, Any] = {"mtime": None, "catalog": None}


def norm(value: Any) -> str:
    text = str(value or "").replace("œ", "oe").replace("Œ", "oe")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()


def stem(token: str) -> str:
    if len(token) > 4:
        return re.sub(r"(es|s|x)$", "", token)
    return token


def tokenize(text: Any) -> list[str]:
    return [stem(token) for token in _TOKEN_RE.split(norm(text)) if len(token) > 1 and token not in STOP]


def load_catalog() -> dict[str, Any]:
    mtime = CATALOG_FILE.stat().st_mtime if CATALOG_FILE.exists() else None
    if mtime != _cache["mtime"]:
        catalog = json.loads(CATALOG_FILE.read_text(encoding="utf-8")) if mtime else {}
        catalog.setdefault("datasets", {})
        catalog.setdefault("presets", [])
        catalog.setdefault("kpis", [])
        catalog.setdefault("glossary", [])
        catalog.setdefault("word_synonyms", {})
        catalog.setdefault("domains", [])
        catalog["domains_by_key"] = {d["key"]: d for d in catalog["domains"]}
        catalog["presets_by_id"] = {p["id"]: p for p in catalog["presets"]}
        _cache["catalog"] = catalog
        _cache["mtime"] = mtime
        _cache["index"] = _build_index(catalog)
    return _cache["catalog"]


def _col_label(dataset: dict[str, Any], column: str | None) -> str:
    if not column:
        return ""
    return (dataset.get("columns") or {}).get(column) or column


def _metric(dataset: dict[str, Any], name: str) -> dict[str, Any]:
    for metric in dataset.get("metrics") or []:
        if metric["name"] == name:
            return metric
    return {"name": name, "label": name, "expression": name, "format": None}


def _build_index(catalog: dict[str, Any]) -> dict[str, Any]:
    synonyms = {
        stem(norm(key)): [token for alt in alts for token in tokenize(alt)]
        for key, alts in (catalog.get("word_synonyms") or {}).items()
    }
    presets = []
    for preset in catalog["presets"]:
        dataset = catalog["datasets"].get(preset["dataset"]) or {"columns": {}, "metrics": [], "label": ""}
        domain = catalog["domains_by_key"].get(preset["domain"]) or {"title": "", "synonyms": []}
        fields = [
            (preset.get("label") or "", 3),
            (" ".join(preset.get("keywords") or []), 2),
            (_col_label(dataset, preset.get("groupby")), 2),
            (_col_label(dataset, preset.get("series")), 1),
            (GRAINS.get(preset.get("grain") or "", ""), 1),
            (" ".join(_metric(dataset, name)["label"] for name in preset.get("metrics") or []), 1.5),
            (f"{domain.get('title', '')} {' '.join(domain.get('synonyms') or [])} {dataset.get('label', '')}", 1),
            (f"{preset.get('subheader') or ''} {' '.join(c.get('label', '') for c in preset.get('conditions') or [])}", 1),
        ]
        tokens: dict[str, float] = {}
        for text, weight in fields:
            for token in tokenize(text):
                tokens[token] = max(tokens.get(token, 0), weight)
        presets.append({"preset": preset, "tokens": tokens})
    return {"synonyms": synonyms, "presets": presets}


def search(text: str, limit: int = 12, catalog: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Top presets, same ranking as the bubble."""
    return [hit["preset"] for hit in search_scores(text, catalog)[:limit]]


def _overlap(words: list[str], text: str) -> tuple[int, float]:
    tokens = set(tokenize(text))
    if not words or not tokens:
        return 0, 0.0
    matched = [word for word in words if word in tokens or any(token.startswith(word) for token in tokens if len(word) >= 3)]
    return len(matched), float(len(matched))


def retrieve(question: str, catalog: dict[str, Any] | None = None, preset_limit: int = 8) -> dict[str, Any]:
    """Compact bundle: presets, their datasets, KPI lines and glossary lines."""
    catalog = catalog or load_catalog()
    presets = search(question, limit=12, catalog=catalog)[:preset_limit]
    words = tokenize(question)
    kpis = []
    for kpi in catalog.get("kpis") or []:
        matched, score = _overlap(words, f"{kpi.get('label', '')} {kpi.get('definition', '')}")
        if matched:
            kpis.append((score, matched, kpi))
    kpis.sort(key=lambda item: (-item[1], -item[0], item[2].get("label", "")))
    glossary = []
    for entry in catalog.get("glossary") or []:
        matched, score = _overlap(words, f"{entry.get('term', '')} {entry.get('definition', '')}")
        if matched:
            glossary.append((score, matched, entry))
    glossary.sort(key=lambda item: (-item[1], -item[0], item[2].get("term", "")))

    dataset_keys: list[str] = []
    for preset in presets:
        if preset["dataset"] not in dataset_keys:
            dataset_keys.append(preset["dataset"])
    for _, _, kpi in kpis[:4]:
        key = kpi.get("dataset")
        if key and key not in dataset_keys and key in catalog["datasets"]:
            dataset_keys.append(key)

    ambiguous = False
    if len(presets) >= 2 and presets[0]["dataset"] != presets[1]["dataset"]:
        first = search_scores(question, catalog)
        if len(first) >= 2 and first[1]["score"] >= first[0]["score"] * 0.85:
            ambiguous = True

    return {
        "presets": presets,
        "preset_ids": [p["id"] for p in presets],
        "dataset_keys": dataset_keys,
        "kpis": [item[2] for item in kpis[:4]],
        "glossary": [item[2] for item in glossary[:3]],
        "ambiguous": ambiguous,
    }


def is_period_token(token: str) -> bool:
    """A month name or a year 19xx/20xx. A pay amount such as 3000 is not a year."""
    return token in MONTHS or (len(token) == 4 and token.isdigit() and token[:2] in {"19", "20"})


def content_tokens(text: str) -> list[str]:
    return [word for word in tokenize(text) if not is_period_token(word)]


def named_period(text: str) -> str:
    """Month and year as written, for example ``janvier 2026``."""
    bits = [token for token in _TOKEN_RE.split(norm(text)) if token and is_period_token(token)]
    return " ".join(bits)


def _score_entry(entry: dict[str, Any], words: list[str], synonyms: dict[str, list[str]]) -> tuple[int, float]:
    score = 0.0
    matched = 0
    for word in words:
        alts = synonyms.get(word) or []
        best = 0.0
        for token, weight in entry["tokens"].items():
            if token == word:
                best = max(best, weight * 1.2)
            elif len(word) >= 3 and token.startswith(word):
                best = max(best, weight)
            elif token in alts:
                best = max(best, weight * 0.6)
        if best > 0:
            matched += 1
            score += best
    return matched, score


def _period_rank(preset: dict[str, Any], month_named: bool, year_named: bool) -> int:
    """A named month prefers a monthly preset over one that means today."""
    if not month_named and not year_named:
        return 0
    grain = preset.get("grain")
    label = norm(preset.get("label") or "") + " " + norm(preset.get("subheader") or "")
    if month_named and grain == "P1M":
        return 0
    if year_named and not month_named and grain == "P1Y":
        return 0
    if grain in ("P1M", "P1Y"):
        return 1
    if "aujourd" in label or "ce jour" in label:
        return 3
    return 2


def search_scores(text: str, catalog: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Same hits as ``search`` but keeps the score, for the ambiguity check."""
    catalog = catalog or load_catalog()
    index = _cache["index"] if catalog is _cache["catalog"] else _build_index(catalog)
    words = tokenize(text)
    if not words:
        return []
    period = {word for word in words if is_period_token(word)}
    match_words = [word for word in words if word not in period and word not in FILLER]
    match_words = match_words or [word for word in words if word not in period] or words
    hits = []
    threshold = math.ceil(len(match_words) * 0.6)
    for entry in index["presets"]:
        matched, score = _score_entry(entry, match_words, index["synonyms"])
        if matched and matched >= threshold:
            hits.append({"preset": entry["preset"], "matched": matched, "score": score})
    month_named = any(word in MONTHS for word in period)
    year_named = any(len(word) == 4 and word.isdigit() for word in period)
    if period and hits:
        domains = {hit["preset"]["domain"] for hit in hits}
        seen = {hit["preset"]["id"] for hit in hits}
        for entry in index["presets"]:
            preset = entry["preset"]
            if preset["id"] in seen or preset.get("domain") not in domains:
                continue
            if preset.get("grain") not in ("P1M", "P1Y"):
                continue
            matched, score = _score_entry(entry, match_words, index["synonyms"])
            if matched:
                hits.append({"preset": preset, "matched": matched, "score": score})
                seen.add(preset["id"])
    words_set = set(match_words)
    named = _question_names_breakdown(words_set, hits, catalog)

    def rank(hit: dict[str, Any]) -> tuple:
        group_named, extra = alignment(words_set, hit["preset"], catalog) if named else (0, 0)
        return (
            _period_rank(hit["preset"], month_named, year_named),
            -hit["matched"],
            -group_named,
            extra,
            -hit["score"],
            -(".extra" in hit["preset"]["id"]),
            len(hit["preset"]["label"]),
        )

    hits.sort(key=rank)
    return hits[:12]


def _dim_token_sets(catalog: dict[str, Any], preset: dict[str, Any]) -> list[set[str]]:
    """Tokens of the preset group-by, series, and time grain, in that order."""
    dataset = catalog["datasets"].get(preset["dataset"]) or {}
    columns = dataset.get("columns") or {}
    dims: list[set[str]] = []
    for column in (preset.get("groupby"), preset.get("series")):
        if not column:
            continue
        label = columns.get(column) or column
        tokens = set(tokenize(label)) | set(tokenize(column))
        if tokens:
            dims.append(tokens)
    grain = preset.get("grain")
    if grain and GRAINS.get(grain):
        dims.append(set(tokenize(GRAINS[grain])))
    return dims


def _question_names_breakdown(words: set[str], hits: list[dict[str, Any]], catalog: dict[str, Any]) -> bool:
    for hit in hits:
        for dim in _dim_token_sets(catalog, hit["preset"]):
            if dim & words:
                return True
    return False


def alignment(words: set[str], preset: dict[str, Any], catalog: dict[str, Any]) -> tuple[int, int]:
    """Whether the primary breakdown is named, and how many breakdowns are not."""
    dims = _dim_token_sets(catalog, preset)
    if not dims:
        return 0, 0
    named = [bool(dim & words) for dim in dims]
    return int(named[0]), sum(1 for flag in named if not flag)


def preset_covers(question: str, preset: dict[str, Any], catalog: dict[str, Any]) -> bool:
    """True when the question names this preset's breakdown and no extra split."""
    words = tokenize(question)
    if not words:
        return False
    words_set = set(words)
    dims = _dim_token_sets(catalog, preset)
    if not dims or not (dims[0] & words_set):
        return False
    if any(not (dim & words_set) for dim in dims):
        return False
    dataset = catalog["datasets"].get(preset["dataset"]) or {}
    domain = (catalog.get("domains_by_key") or {}).get(preset["domain"]) or {}
    parts = [
        preset.get("label") or "",
        " ".join(preset.get("keywords") or []),
        domain.get("title") or "",
        " ".join(domain.get("synonyms") or []),
        dataset.get("label") or "",
        " ".join(item.get("label", "") for item in preset.get("conditions") or []),
    ]
    wanted = set(preset.get("metrics") or [])
    parts.extend(metric.get("label") or metric["name"] for metric in dataset.get("metrics") or [] if metric["name"] in wanted)
    columns = dataset.get("columns") or {}
    for column in (preset.get("groupby"), preset.get("series")):
        if column:
            parts.append(columns.get(column) or column)
    grain = preset.get("grain")
    if grain:
        parts.append(GRAINS.get(grain, ""))
    text = set(tokenize(" ".join(parts)))
    return all(
        word in text or any(token.startswith(word) for token in text if len(word) >= 3)
        for word in words
    )


def preset_shares(question: str, preset: dict[str, Any], catalog: dict[str, Any]) -> bool:
    """True when the catalog label, domain or metric contains a real word from the question."""
    words = [word for word in content_tokens(question) if word not in FILLER]
    if not words:
        return False
    dataset = catalog["datasets"].get(preset["dataset"]) or {}
    domain = (catalog.get("domains_by_key") or {}).get(preset.get("domain")) or {}
    wanted = set(preset.get("metrics") or [])
    parts = [
        preset.get("label") or "",
        domain.get("title") or "",
        " ".join(domain.get("synonyms") or []),
        " ".join(metric.get("label") or metric["name"] for metric in dataset.get("metrics") or [] if metric["name"] in wanted),
    ]
    text = set(tokenize(" ".join(parts)))
    synonyms = {
        stem(norm(key)): [token for alt in alts for token in tokenize(alt)]
        for key, alts in (catalog.get("word_synonyms") or {}).items()
    }
    for word in words:
        if word in text or any(token.startswith(word) for token in text if len(word) >= 3):
            return True
        if any(alt in text for alt in synonyms.get(word) or []):
            return True
    return False
