# GRH chatbot: how it was developed

This note describes the assistant added to Apache Superset 4.1 in this repository. It does not replace Superset. It does not generate free Oracle SQL.

## Starting point

There was no chatbot, no Ollama client, and no 30-question benchmark in the repository. The working feature was **Bulle RH**:

- Injected on every page by `docker/pythonpath_dev/grh_portal/templates/tail_js_custom_extra.html`.
- Registered from `docker/pythonpath_dev/superset_config.py` (`grh_portal.install`, `BLUEPRINTS`).
- The browser script `static/bubble.js` searched `catalog.json` by keywords and called `POST /api/v1/chart/data` with the visitor session.

The catalog is produced by `scripts/grh/build_portal_catalog.py`. It lists 17 HR domains, 33 Oracle views exposed as Superset datasets, chart presets, KPI definitions, and a glossary. The view SQL lives in `scripts/grh/sql/`. Metrics such as `COUNT(DISTINCT MAT_PERS)` are already stored on those datasets. Company scope in the datasets is a Jinja `url_param('cod_soc')`, applied only when that URL parameter is present. The bubble also sent `COD_SOC` from the browser.

The bubble missed paraphrases because matching required about 60% of the question tokens to hit a preset label or column label. A small local model writing its own SQL would have missed the same business rules and would have bypassed Superset permissions.

## Design choice

The model only chooses a **query plan**: one catalog dataset, metric names, a group-by, and equality filters. Superset executes that plan. The number in the answer is formatted in Python from the query result. The model is not asked to write the figure.

Keyword retrieval is used. No vector database, no embeddings, and no fine-tuning were added.

## Request flow

1. The page loads either `bubble.js` or `chat.js`, depending on `GRH_ASSISTANT_ENABLED`.
2. The user sends a question to `POST /grh/chat` (session cookie and CSRF token).
3. `retrieve.py` ranks catalog presets with the same tokenizer as the bubble.
4. `ollama_client.py` calls local Ollama (`POST /api/chat`, JSON mode, temperature 0).
5. `planner.py` accepts the JSON only if the dataset, metrics, and columns are in the retrieved slice of the catalog. It forces `COD_SOC` from `GRH_ALLOWED_COMPANIES` (default `01`). It rejects SQL text, multiple statements, and unknown columns. One repair call is allowed. The second failure becomes a clarification, not a query.
6. `execute.py` runs the plan with Superset’s chart-data command as the current user, so datasource permissions stay in force. At most 500 aggregated rows are returned (1 000 for a detail view).
7. The reply is a French sentence, the public plan (no SQL), the rows, and a chart description. `chat.js` draws the chart from those rows. It does not send a second, unvalidated query.

If Ollama is down, the endpoint returns “L'assistant est momentanément indisponible.” Oracle and permission errors shown to the user are “La requête n'a pas abouti.” or “Accès refusé à ces données.” The raw database error stays in the server log. The log line at INFO records the dataset, the metric names, and the row count, not the row values.

The endpoint allows 20 questions per user per minute.

## Files

Created:

| File | Role |
| --- | --- |
| `docker/pythonpath_dev/grh_portal/retrieve.py` | Keyword index and preset search, plus KPI and glossary hits |
| `docker/pythonpath_dev/grh_portal/ollama_client.py` | Local Ollama client |
| `docker/pythonpath_dev/grh_portal/planner.py` | Prompt, JSON checks, company filter, answer text, chart-data body |
| `docker/pythonpath_dev/grh_portal/execute.py` | Runs the plan through Superset chart data |
| `docker/pythonpath_dev/grh_portal/examples.json` | 20 verified question-to-preset pairs. Labels and preset ids only |
| `docker/pythonpath_dev/grh_portal/static/chat.js` | Chat panel, search icon, chart from returned rows |
| `docker/pythonpath_dev/grh_portal/static/chat.css` | Panel styles inside a shadow root |
| `scripts/grh/eval/questions.json` | 30 questions with an expected preset id. `expected_aggregate` is null |
| `scripts/grh/eval/run_eval.py` | Modes A, B, and C |
| `scripts/grh/eval/test_assistant.py` | Checks that do not need Ollama or Oracle |

Modified:

| File | Change |
| --- | --- |
| `docker/pythonpath_dev/grh_portal/__init__.py` | `POST /grh/chat`, login check, rate limit |
| `docker/pythonpath_dev/grh_portal/templates/tail_js_custom_extra.html` | Loads `chat.js` when the flag is on, otherwise `bubble.js` |
| `docker/pythonpath_dev/superset_config.py` | Flag, Ollama URL, model tag, timeout, row limit, allowed companies |
| `bubble.js` / `bubble.css` | Floating button text “RH” replaced by a search icon |

Left unchanged: `catalog.json`, the SQL files, the dashboard builders, Docker volumes, and Superset core.

## Retrieval and prompt

The tokenizer folds accents, drops French stopwords, and applies a light stem. Preset ranking matches `bubble.js`. The prompt is capped at about 2 800 characters. Verified examples and the matching presets are kept first. Long metric SQL is dropped when the cap is reached.

The system text tells the model to return only this JSON shape:

```json
{"preset": null, "dataset": null, "metrics": [], "groupby": null, "series": null, "filters": {}, "time_range": null, "clarify": null, "refuse": null}
```

`groupby` is a column name or `time:P1Y`, `time:P3M`, `time:P1M`, `time:P1D`. If two datasets are close, the model is told to set `clarify` instead of guessing. Business rules included in that text come from the catalog and the SQL already in the repo: headcount uses the catalog metric (often `COUNT(DISTINCT MAT_PERS)`), current staff is `ETAT = Actif` / `EST_ACTIF = 1` unless the question breaks down by status, and the organisation columns are `POLE`, `DIRECTION`, and `SERVICE`.

Fixed conditions that already exist on a preset (for example “12 derniers mois”) are copied from the catalog when that preset id is chosen. The model cannot supply its own SQL.

## Security

Checks in `planner.py` run before any database call:

- The dataset must be one of the presets or KPI datasets retrieved for that question.
- Metrics and group-by columns must belong to that dataset.
- Any model field containing `;`, comments, `UNION`, `SELECT`, or other statement keywords is rejected.
- `COD_SOC` from the model is ignored and replaced by `GRH_ALLOWED_COMPANIES`.
- The question is treated as data. It cannot add a tool or widen the company.

This does not add a Superset row-level security rule. The chart API used by the old bubble can still be called from the browser with whatever company filter the client sends. The new chat path does not have that gap.

`examples.json` and the retrieval index contain labels and expressions, not employee rows, names, or salary amounts. An answer can show an aggregate the same user could already open in the bubble.

## Interface

The button is a magnifying glass, not the letters “RH”. Alt+R still opens the panel. With `GRH_ASSISTANT_ENABLED = True`, the panel is the chat. With the flag off, the original bubble remains, with the same icon.

Static files are served from the mounted `docker/` directory, so a refresh picks up `chat.js` without a frontend rebuild.

## Configuration

In `docker/pythonpath_dev/superset_config.py`:

- `GRH_ASSISTANT_ENABLED` — `True` loads the chat. `False` loads the bubble. This is currently `True`.
- `OLLAMA_BASE_URL` — `http://host.docker.internal:11434` so the Superset container reaches Ollama on the host.
- `OLLAMA_MODEL` — `qwen2.5:3b`.
- `GRH_CHAT_TIMEOUT_SEC` — 45.
- `GRH_QUERY_ROW_LIMIT` — 500.
- `GRH_ALLOWED_COMPANIES` — `["01"]`.

Ollama must be running on the host and the model must be present:

```text
ollama pull qwen2.5:3b
ollama list
```

The Superset container must be restarted after a change to `superset_config.py`. No extra database and no paid API are required. The 3B model needs on the order of 2–4 GB of RAM once it is loaded. The weight file is about 1.9 GB.

To go back to the bubble, set `GRH_ASSISTANT_ENABLED = False` and restart Superset. `bubble.js` and `catalog.json` are still on disk.

## Tests and benchmark

`python scripts/grh/eval/test_assistant.py` checks, without Ollama and without Oracle:

- The six original bubble examples still return the same top preset.
- A plan that names another company is rewritten to `01`.
- SQL-shaped model output is rejected and does not build a query.
- Verified examples appear in the prompt only when that mode is on.
- A catalog condition such as the 12-month congé filter is taken from the preset, not from a `where` field invented by the model.
- The sentence uses the query rows (a test row “Nord / 12” appears as 12).

`python scripts/grh/eval/run_eval.py --mode A` compares the bubble search with the expected preset ids. On 20 October 2026 that run scored:

- Exact preset match: 0.90 (27 of 30).
- Expected preset in the top 3: about 0.97.
- Median latency about 1 ms.

The three misses are short labels (`Effectif payé`, `Effectif actif`, `Mutations de l'année`) where another preset outranks the expected one. `expected_aggregate` is null on every question, so this score is not a claim that the business figure is correct. A query that runs is not marked correct.

Modes B and C call Ollama (B without `examples.json`, C with it). They were not run: `ollama list` was empty when the assistant was built. After `ollama pull qwen2.5:3b` finishes:

```text
python scripts/grh/eval/run_eval.py --mode all --ollama-url http://127.0.0.1:11434 --model qwen2.5:3b
```

Reports are written under `scripts/grh/eval/reports/` and are not committed. `--execute` records whether the plan ran only when the command is inside a running Superset application. That was not done.

## What was deliberately not done

- No rewrite of Superset and no new service.
- No free-form Oracle SQL and no SQL Lab execution.
- No vector index and no model training.
- No employee or salary rows in the prompt or in `examples.json`.
- No change to dashboard SQL, catalog generation, or Docker volumes.
