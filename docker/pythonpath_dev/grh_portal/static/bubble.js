/* Bulle RH: floating, draggable and resizable HR quick access on every Superset page.
   Plain JS in a shadow root (no build step). Every figure comes from
   POST /api/v1/chart/data on the GRH datasets of catalog.json, with the visitor's session. */
(function () {
  'use strict';

  if (window.__grhBubble) return;
  window.__grhBubble = true;
  const script = document.currentScript;
  const params = new URLSearchParams(location.search);
  if (params.has('standalone') || /^\/(login|logout|register|embedded|lang)\b/.test(location.pathname)) return;

  const STATIC = script.dataset.static.replace(/\/?$/, '/');
  const STORE_KEY = 'grh-bubble-v1';
  const AUTO = '__auto__';
  const QUERY_ROW_LIMIT = 10000;
  const AUTO_ROW_LIMIT = 15;
  const DETAIL_ROW_LIMIT = 1000;
  const EXPORT_ROW_LIMIT = 100000;
  const OPTIONS_ROW_LIMIT = 2000;
  const GRAINS = { P1Y: 'Année', P3M: 'Trimestre', P1M: 'Mois', P1D: 'Jour' };
  const MONTHS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
  const COLORS = ['#2563eb', '#0ea5e9', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#64748b', '#22c55e', '#f97316'];
  const EXAMPLES = [
    'Effectif actif par direction', 'Pyramide des âges', 'Masse salariale et coût employeur par direction (12 mois)',
    'Jours de congé par direction et par type (12 mois)', 'Retraites prévues dans 5 ans par direction',
    "Taux d'absentéisme maladie par direction (12 mois)",
  ];
  const STOP = new Set(['le', 'la', 'les', 'de', 'des', 'du', 'par', 'en', 'et', 'au', 'aux', 'un', 'une', 'pour',
    'sur', 'dans', 'quel', 'quels', 'quelle', 'quelles', 'est', 'sont', 'nos', 'notre', 'mes', 'ma', 'mon', 'qui',
    'que', 'quoi', 'avec', 'ce', 'ces', 'cette', 'il', 'ils', 'on', 'nous', 'je', 'veux', 'voir', 'afficher', 'donne',
    'moi', 'svp', 'chaque', 'tous', 'toutes', 'tout']);

  let CAT = null;
  let CSRF = '';
  let INDEX = [];
  let SYNONYMS = new Map();
  let S = null;                 // current selection
  let saved = load();
  const charts = new Set();
  const optionsCache = new Map();
  let shadow;
  let ready = null;
  let runTimer = null;

  // ------------------------------------------------------------------ helpers

  function load() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch (e) { return {}; }
  }
  function persist() {
    const sel = S && {
      dsKey: S.dsKey, metrics: S.metrics, groupby: S.groupby, series: S.series, filters: S.filters,
      from: S.from, to: S.to, label: S.label, presetId: S.presetId, view: S.view, tab: S.tab,
      timeColumn: S.timeColumn, conditions: S.conditions, detailColumns: S.detailColumns,
    };
    saved = { ...saved, selection: sel || saved.selection };
    try { localStorage.setItem(STORE_KEY, JSON.stringify(saved)); } catch (e) { /* storage full or blocked */ }
  }

  const $ = (sel) => shadow.querySelector(sel);
  const $$ = (sel) => Array.from(shadow.querySelectorAll(sel));

  function h(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') node.className = v;
      else if (k === 'text') node.textContent = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? '' : v);
    }
    for (const c of children.flat()) {
      if (c != null && c !== false) node.append(c.nodeType ? c : String(c));
    }
    return node;
  }

  const norm = (s) => String(s ?? '').replace(/[œŒ]/g, 'oe').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const stem = (t) => (t.length > 4 ? t.replace(/(es|s|x)$/, '') : t);
  const tokenize = (s) => norm(s).split(/[^a-z0-9%]+/).filter((t) => t.length > 1 && !STOP.has(t)).map(stem);
  const nf = (digits) => new Intl.NumberFormat('fr-FR', { minimumFractionDigits: digits, maximumFractionDigits: digits });

  function fmt(value, format) {
    if (value == null || value === '') return '–';
    if (typeof value !== 'number') return String(value);
    let m = /^,?\.(\d+)%$/.exec(format || '');
    if (m) return `${nf(+m[1]).format(value * 100)} %`;
    m = /^,?\.(\d+)f$/.exec(format || '');
    if (m) return nf(+m[1]).format(value);
    return nf(Number.isInteger(value) ? 0 : 1).format(value);
  }

  function fmtDate(v, grain) {
    if (v == null || v === '') return '–';
    const d = new Date(typeof v === 'number' ? v : Date.parse(v));
    if (Number.isNaN(d.getTime())) return String(v);
    const y = d.getUTCFullYear();
    const mo = d.getUTCMonth();
    if (grain === 'P1Y') return String(y);
    if (grain === 'P3M') return `T${Math.floor(mo / 3) + 1} ${y}`;
    if (grain === 'P1M') return `${MONTHS[mo]} ${y}`;
    return `${String(d.getUTCDate()).padStart(2, '0')}/${String(mo + 1).padStart(2, '0')}/${y}`;
  }

  const isoDate = (d) => d.toISOString().slice(0, 10);
  function addDays(iso, n) {
    const d = new Date(`${iso}T00:00:00Z`);
    d.setUTCDate(d.getUTCDate() + n);
    return isoDate(d);
  }
  const slug = (s) => norm(s).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60);
  const colLabel = (ds, col) => (ds.columns && ds.columns[col]) || col;
  const metricDef = (ds, name) => ds.metrics.find((m) => m.name === name) || { name, label: name, expression: name };
  const isPercent = (m) => /%$/.test(m.format || '');

  // ------------------------------------------------------------------ boot: catalog, csrf, charts library

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.nonce = script.nonce;
      s.onload = resolve;
      s.onerror = () => reject(new Error(`Chargement impossible : ${src}`));
      document.head.append(s);
    });
  }

  function ensureReady() {
    if (!ready) {
      ready = Promise.all([
        fetch(script.dataset.catalog, { credentials: 'same-origin' }).then((r) => r.json()),
        fetch(script.dataset.csrf, { credentials: 'same-origin' }).then((r) => r.json()),
        window.echarts ? null : loadScript(`${STATIC}echarts.min.js`),
      ]).then(([catalog, csrf]) => {
        CAT = catalog;
        CSRF = csrf.token;
        CAT.domainsByKey = Object.fromEntries(CAT.domains.map((d) => [d.key, d]));
        CAT.presetsById = Object.fromEntries(CAT.presets.map((p) => [p.id, p]));
        buildIndex();
      });
      ready.catch(() => { ready = null; });
    }
    return ready;
  }

  // ------------------------------------------------------------------ Superset API

  async function apiError(res) {
    let msg = '';
    try {
      const body = await res.json();
      msg = body.message || (body.errors && body.errors[0] && body.errors[0].message) || '';
      if (typeof msg === 'object') msg = JSON.stringify(msg);
    } catch (e) { /* not JSON */ }
    if (res.status === 401 || res.status === 403) {
      return new Error(`Accès refusé à ces données : connectez-vous avec un compte autorisé. ${msg}`.trim());
    }
    return new Error(msg || `Erreur ${res.status}`);
  }

  async function chartData(query, format = 'json') {
    const res = await fetch('/api/v1/chart/data', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({
        datasource: { id: S.ds.id, type: 'table' }, force: false, queries: [query],
        result_format: format, result_type: 'full',
      }),
    });
    if (!res.ok) throw await apiError(res);
    return res;
  }

  async function rows(query) {
    const body = await (await chartData(query)).json();
    return (body.result && body.result[0] && body.result[0].data) || [];
  }

  // ------------------------------------------------------------------ query building

  function emptyQuery() {
    return {
      filters: [], extras: { where: '', having: '' }, applied_time_extras: {}, annotation_layers: [],
      series_limit: 0, order_desc: true, url_params: {}, custom_params: {}, custom_form_data: {},
      orderby: [], post_processing: [],
    };
  }

  function companyFilter(q) {
    if (S.ds.has_company && S.company) q.filters.push({ col: 'COD_SOC', op: '==', val: S.company });
  }

  function baseQuery() {
    const q = emptyQuery();
    const where = [];
    companyFilter(q);
    for (const [col, vals] of Object.entries(S.filters)) {
      if (vals && vals.length) q.filters.push({ col, op: 'IN', val: vals });
    }
    if (S.ds.main_dttm_col && (S.from || S.to)) {
      q.filters.push({
        col: S.ds.main_dttm_col, op: 'TEMPORAL_RANGE',
        val: `${S.from || '1900-01-01'} : ${S.to ? addDays(S.to, 1) : 'now'}`,
      });
    }
    for (const c of S.conditions) {
      if (!c.on) continue;
      if (c.sql) where.push(`(${c.sql})`);
      else q.filters.push({ col: c.col, op: c.op, val: c.val });
    }
    q.extras.where = where.join(' AND ');
    return q;
  }

  const grainOf = (groupby) => (groupby && groupby.startsWith('time:') ? groupby.slice(5) : null);
  const adhocColumn = (col) => ({ expressionType: 'SQL', sqlExpression: col, label: colLabel(S.ds, col) });

  // Oracle returns NUMBER as Decimal, which CSV writes with a dot and every digit:
  // round to the display precision, and use BINARY_DOUBLE so the CSV decimal comma applies.
  function exportExpression(m) {
    const fixed = /\.(\d+)f$/.exec(m.format || '');
    const digits = isPercent(m) ? 4 : fixed ? +fixed[1] : 2;
    const rounded = `ROUND(${m.expression}, ${digits})`;
    return isPercent(m) || (fixed && digits > 0) ? `CAST(${rounded} AS BINARY_DOUBLE)` : rounded;
  }

  function metricRef(name, labelled) {
    if (!labelled) return name;
    const m = metricDef(S.ds, name);
    return { expressionType: 'SQL', sqlExpression: exportExpression(m), label: m.label };
  }

  function axisKey(groupby, labelled) {
    const grain = grainOf(groupby);
    if (grain) return labelled ? GRAINS[grain] : S.timeColumn;
    return labelled ? colLabel(S.ds, groupby) : groupby;
  }

  function groupedQuery(labelled, view = S) {
    const q = baseQuery();
    const grain = grainOf(view.groupby);
    q.columns = [];
    if (view.groupby) {
      q.columns.push(grain
        ? { columnType: 'BASE_AXIS', expressionType: 'SQL', sqlExpression: S.timeColumn, label: axisKey(view.groupby, labelled), timeGrain: grain }
        : (labelled ? adhocColumn(view.groupby) : view.groupby));
    }
    if (view.series) q.columns.push(labelled ? adhocColumn(view.series) : view.series);
    q.metrics = view.metrics.map((m) => metricRef(m, labelled));
    if (grain) {
      q.extras.time_grain_sqla = grain;
      q.post_processing = [{ operation: 'sort', options: { by: axisKey(view.groupby, labelled), ascending: true } }];
    } else if (q.columns.length) {
      q.orderby = [[q.metrics[0], false]];
    }
    q.row_limit = labelled ? EXPORT_ROW_LIMIT : (view.limit || QUERY_ROW_LIMIT);
    return q;
  }

  function totalsQuery(labelled) {
    const q = baseQuery();
    q.columns = [];
    q.metrics = S.metrics.map((m) => metricRef(m, labelled));
    q.row_limit = 1;
    return q;
  }

  function allColumnKeys(ds = S.ds) {
    return Object.keys((ds && ds.columns) || {});
  }

  function sanitizeDetailColumns(ds, columns) {
    const known = allColumnKeys(ds);
    if (!Array.isArray(columns)) return known.slice();
    const kept = [];
    for (const column of columns) {
      if (typeof column === 'string' && known.includes(column) && !kept.includes(column)) kept.push(column);
    }
    return kept.length ? kept : known.slice();
  }

  function usefulColumns(ds = S.ds) {
    return sanitizeDetailColumns(ds, ds.detail_columns);
  }

  const detailColumns = () => (S.detailColumns && S.detailColumns.length ? S.detailColumns : allColumnKeys());

  function detailQuery(labelled) {
    const q = baseQuery();
    q.columns = detailColumns().map((c) => (labelled ? adhocColumn(c) : c));
    q.row_limit = labelled ? EXPORT_ROW_LIMIT : DETAIL_ROW_LIMIT;
    return q;
  }

  async function columnValues(col) {
    const q = emptyQuery();
    if (col !== 'COD_SOC') companyFilter(q);
    const pole = (col === 'DIRECTION' || col === 'SERVICE') && S.filters.POLE && S.filters.POLE.length;
    if (pole) q.filters.push({ col: 'POLE', op: 'IN', val: S.filters.POLE });
    const key = `${S.ds.id}|${col}|${col === 'COD_SOC' ? '' : S.company}|${pole ? S.filters.POLE.join(',') : ''}`;
    if (!optionsCache.has(key)) {
      q.columns = [col];
      q.metrics = [];
      q.orderby = [[col, true]];
      q.row_limit = OPTIONS_ROW_LIMIT;
      optionsCache.set(key, rows(q).then((data) => data.map((r) => r[col]).filter((v) => v != null))
        .catch((e) => { optionsCache.delete(key); throw e; }));
    }
    return optionsCache.get(key);
  }

  // ------------------------------------------------------------------ search

  function buildIndex() {
    SYNONYMS = new Map(Object.entries(CAT.word_synonyms || {}).map(([k, alts]) => [stem(norm(k)), alts.flatMap(tokenize)]));
    INDEX = CAT.presets.map((p) => {
      const ds = CAT.datasets[p.dataset];
      const d = CAT.domainsByKey[p.domain] || { title: '', synonyms: [] };
      const fields = [
        [p.label, 3],
        [(p.keywords || []).join(' '), 2],
        [p.groupby ? colLabel(ds, p.groupby) : '', 2],
        [p.series ? colLabel(ds, p.series) : '', 1],
        [p.grain ? GRAINS[p.grain] : '', 1],
        [p.metrics.map((m) => metricDef(ds, m).label).join(' '), 1.5],
        [`${d.title} ${(d.synonyms || []).join(' ')} ${ds.label}`, 1],
        [`${p.subheader || ''} ${p.conditions.map((c) => c.label).join(' ')}`, 1],
      ];
      const tokens = new Map();
      for (const [text, weight] of fields) {
        for (const t of tokenize(text)) tokens.set(t, Math.max(tokens.get(t) || 0, weight));
      }
      return { preset: p, tokens };
    });
  }

  function search(text) {
    const words = tokenize(text);
    if (!words.length) return [];
    const hits = [];
    for (const entry of INDEX) {
      let score = 0;
      let matched = 0;
      for (const w of words) {
        const alts = SYNONYMS.get(w) || [];
        let best = 0;
        for (const [tok, weight] of entry.tokens) {
          if (tok === w) best = Math.max(best, weight * 1.2);
          else if (w.length >= 3 && tok.startsWith(w)) best = Math.max(best, weight);
          else if (alts.includes(tok)) best = Math.max(best, weight * 0.6);
        }
        if (best > 0) { matched += 1; score += best; }
      }
      if (matched && matched >= Math.ceil(words.length * 0.6)) hits.push({ preset: entry.preset, matched, score });
    }
    const extra = (p) => (p.id.includes('.extra') ? 1 : 0);
    hits.sort((a, b) => b.matched - a.matched || b.score - a.score
      || extra(b.preset) - extra(a.preset) || a.preset.label.length - b.preset.label.length);
    return hits.slice(0, 12).map((x) => x.preset);
  }

  function renderSuggestions() {
    if (!CAT) return;
    const input = $('#q');
    const box = $('#suggest');
    const text = input.value.trim();
    const list = text ? search(text) : EXAMPLES.map((l) => CAT.presets.find((p) => p.label === l)).filter(Boolean);
    if (!list.length) {
      box.replaceChildren(h('p', { class: 'empty', text: 'Aucune question ne correspond. Essayez : effectif, congés, salaire, retraite…' }));
    } else {
      box.replaceChildren(h('div', { class: 'head', text: text ? 'Questions' : 'Exemples' }), ...list.map((p, i) => {
        const ds = CAT.datasets[p.dataset];
        const domain = (CAT.domainsByKey[p.domain] || {}).title || '';
        return h('button', {
          type: 'button', class: i === 0 && text ? 'hl' : null,
          onmousedown: (e) => { e.preventDefault(); applyPreset(p); },
        }, p.label, h('small', { text: [domain, ds.label, ...p.conditions.map((c) => c.label)].join(' · ') }));
      }));
    }
    box.hidden = false;
  }

  // ------------------------------------------------------------------ selection

  function newSelection(dsKey, overrides = {}) {
    const ds = CAT.datasets[dsKey];
    return {
      dsKey, ds, company: saved.company ?? CAT.default_company ?? '', from: '', to: '',
      filters: {}, conditions: [], metrics: [ds.metrics[0].name], groupby: AUTO, series: '',
      timeColumn: ds.main_dttm_col, label: '', presetId: null, view: 'bar', tab: 'chart',
      detailColumns: allColumnKeys(ds), rows: [], detailLoaded: false, token: 0,
      ...overrides,
    };
  }

  function applyPreset(p) {
    $('#suggest').hidden = true;
    $('#q').value = '';
    const ds = CAT.datasets[p.dataset];
    S = newSelection(p.dataset, {
      label: p.label, presetId: p.id, view: p.view,
      metrics: p.metrics.slice(),
      groupby: p.grain ? `time:${p.grain}` : (p.groupby || AUTO),
      series: p.series || '',
      filters: JSON.parse(JSON.stringify(p.filters || {})),
      conditions: (p.conditions || []).map((c) => ({ ...c, on: true })),
      timeColumn: p.time_column || ds.main_dttm_col,
      tab: p.view === 'table' ? 'table' : p.view === 'detail' ? 'detail' : 'chart',
      detailColumns: allColumnKeys(ds),
    });
    renderExplorer();
  }

  function chooseDataset(dsKey, metric) {
    S = newSelection(dsKey, metric ? { metrics: [metric] } : {});
    renderExplorer();
  }

  function restoreSelection() {
    const sel = saved.selection;
    if (sel && CAT.datasets[sel.dsKey]) {
      const ds = CAT.datasets[sel.dsKey];
      const metrics = (sel.metrics || []).filter((m) => ds.metrics.some((x) => x.name === m));
      S = newSelection(sel.dsKey, {
        ...sel, metrics: metrics.length ? metrics : [ds.metrics[0].name],
        detailColumns: sanitizeDetailColumns(ds, sel.detailColumns),
      });
    } else {
      const first = CAT.presets.find((p) => p.label === EXAMPLES[0]);
      if (first) { applyPreset(first); return; }
      S = newSelection(Object.keys(CAT.datasets)[0]);
    }
    renderExplorer();
  }

  // ------------------------------------------------------------------ explorer controls

  function multiSelect(col, options) {
    const btn = h('button', { type: 'button', class: 'ms-btn' });
    const list = h('div', { class: 'ms-list' });
    const finder = h('input', { type: 'search', placeholder: 'Rechercher…' });
    const panel = h('div', { class: 'ms-panel', hidden: true }, finder, list,
      h('div', { class: 'ms-tools' },
        h('button', { type: 'button', class: 'link', onclick: () => set([]) }, 'Tout effacer'),
        h('button', { type: 'button', class: 'link', onclick: () => { panel.hidden = true; } }, 'Fermer')));
    let values = options || null;
    const selected = () => S.filters[col] || [];

    function set(vals) {
      S.filters[col] = vals;
      refresh();
      draw();
      updateFilterCount();
      scheduleRun();
    }
    function refresh() {
      const sel = selected();
      btn.textContent = !sel.length ? 'Tous' : sel.length <= 2 ? sel.join(', ') : `${sel.length} sélectionnés`;
      btn.title = sel.join(', ');
    }
    function draw() {
      if (!values) return;
      const q = norm(finder.value);
      const sel = selected().map(String);
      list.replaceChildren(...values.filter((v) => !q || norm(v).includes(q)).slice(0, 500).map((v) => {
        const box = h('input', { type: 'checkbox', checked: sel.includes(String(v)) });
        box.addEventListener('change', () => {
          const cur = selected().filter((x) => String(x) !== String(v));
          set(box.checked ? cur.concat([v]) : cur);
        });
        return h('label', null, box, v === '' ? '(vide)' : String(v));
      }));
    }
    btn.addEventListener('click', async () => {
      panel.hidden = !panel.hidden;
      if (panel.hidden) return;
      finder.focus();
      list.replaceChildren(h('p', { class: 'note', text: 'Chargement…' }));
      try {
        values = await columnValues(col);
        draw();
      } catch (e) {
        list.replaceChildren(h('p', { class: 'note', text: e.message }));
      }
    });
    finder.addEventListener('input', draw);
    refresh();
    return h('div', { class: 'ms' }, btn, panel);
  }

  function field(label, control) {
    return h('label', { class: 'field' }, h('span', { text: label }), control);
  }

  function updateFilterCount() {
    const n = Object.values(S.filters).filter((v) => v && v.length).length + (S.from || S.to ? 1 : 0);
    const badge = $('#fcount');
    if (badge) { badge.textContent = n; badge.hidden = !n; }
  }

  function renderExplorer() {
    const ds = S.ds;
    const domainSel = $('#domain');
    domainSel.replaceChildren(...CAT.domains.map((d) => h('option', { value: d.key, selected: d.key === ds.domain }, d.title)));
    const sourceSel = $('#source');
    sourceSel.replaceChildren(...Object.entries(CAT.datasets).filter(([, d]) => d.domain === ds.domain)
      .map(([key, d]) => h('option', { value: key, selected: key === S.dsKey }, d.label)));

    $('#metrics').replaceChildren(...ds.metrics.map((m) => h('button', {
      type: 'button', class: `chip${S.metrics.includes(m.name) ? ' on' : ''}`, title: m.expression,
      onclick: () => {
        const on = S.metrics.includes(m.name);
        if (on && S.metrics.length === 1) return;
        S.metrics = on ? S.metrics.filter((x) => x !== m.name) : S.metrics.concat([m.name]);
        renderExplorer();
      },
    }, m.label)));

    const groupby = $('#groupby');
    const times = S.timeColumn
      ? Object.entries(GRAINS).filter(([g]) => g !== 'P1D' || grainOf(S.groupby) === 'P1D')
        .map(([g, l]) => h('option', { value: `time:${g}` }, `${l} (${colLabel(ds, S.timeColumn).toLowerCase()})`))
      : [];
    groupby.replaceChildren(
      h('option', { value: AUTO }, 'Automatique (plusieurs graphiques)'),
      h('option', { value: '' }, 'Total uniquement'),
      ...ds.dimensions.map((d) => h('option', { value: d }, colLabel(ds, d))), ...times);
    groupby.value = S.groupby;
    const series = $('#series');
    series.replaceChildren(h('option', { value: '' }, '— Aucun —'),
      ...ds.dimensions.filter((d) => d !== S.groupby).map((d) => h('option', { value: d }, colLabel(ds, d))));
    if (S.series === S.groupby) S.series = '';
    series.value = S.series;
    series.disabled = S.groupby === AUTO || !S.groupby;

    const grid = $('#fgrid');
    grid.replaceChildren();
    if (ds.has_company) {
      const company = h('select', null, h('option', { value: S.company }, S.company || 'Toutes'));
      company.addEventListener('change', () => {
        S.company = company.value;
        saved.company = company.value;
        scheduleRun();
      });
      grid.append(field('Société', company));
      columnValues('COD_SOC').then((values) => {
        if (S.company && !values.map(String).includes(String(S.company))) {
          S.company = values.length === 1 ? values[0] : '';
          scheduleRun();
        }
        company.replaceChildren(h('option', { value: '' }, 'Toutes'),
          ...values.map((v) => h('option', { value: v, selected: String(v) === String(S.company) }, v)));
      }).catch(() => { /* reported by the results call */ });
    }
    if (ds.main_dttm_col) {
      const from = h('input', { type: 'date', value: S.from });
      const to = h('input', { type: 'date', value: S.to });
      const quick = h('select', null,
        h('option', { value: '' }, 'Raccourci…'), h('option', { value: 'all' }, 'Toute la période'),
        h('option', { value: 'year' }, 'Année en cours'), h('option', { value: 'last_year' }, 'Année précédente'),
        h('option', { value: '12m' }, '12 derniers mois'));
      const apply = () => { from.value = S.from; to.value = S.to; updateFilterCount(); scheduleRun(); };
      from.addEventListener('change', () => { S.from = from.value; apply(); });
      to.addEventListener('change', () => { S.to = to.value; apply(); });
      quick.addEventListener('change', () => {
        const today = new Date();
        const y = today.getFullYear();
        const ranges = {
          all: ['', ''], year: [`${y}-01-01`, ''], last_year: [`${y - 1}-01-01`, `${y - 1}-12-31`],
          '12m': [isoDate(new Date(Date.UTC(y - 1, today.getMonth(), today.getDate()))), ''],
        };
        [S.from, S.to] = ranges[quick.value] || [S.from, S.to];
        quick.value = '';
        apply();
      });
      grid.append(field('Du', from), field('Au', to), field('Période', quick));
    }
    for (const col of ds.filters) grid.append(field(colLabel(ds, col), multiSelect(col)));
    updateFilterCount();

    $('#conds').replaceChildren(...S.conditions.map((c) => h('button', {
      type: 'button', class: `chip cond${c.on ? '' : ' off'}`, title: 'Condition fixe : cliquer pour la retirer ou la remettre',
      onclick: () => { c.on = !c.on; renderExplorer(); },
    }, `${c.on ? '✓' : '✕'} ${c.label}`)));
    $('#conds').hidden = !S.conditions.length;
    scheduleRun(0);
  }

  // ------------------------------------------------------------------ results

  function status(text, isError) {
    const box = $('#status');
    box.hidden = !text;
    box.textContent = text || '';
    box.classList.toggle('error', !!isError);
  }

  function scheduleRun(delay = 350) {
    clearTimeout(runTimer);
    runTimer = setTimeout(run, delay);
  }

  function disposeCharts() {
    charts.forEach((c) => c.dispose());
    charts.clear();
  }

  function autoPlan() {
    const ds = S.ds;
    const plan = [];
    if (S.timeColumn) {
      const monthly = /^DT_/.test(S.timeColumn) || S.timeColumn === 'JOUR';
      plan.push({ groupby: `time:${monthly ? 'P1M' : 'P1Y'}`, series: '', metrics: [S.metrics[0]] });
    }
    for (const d of ds.dimensions.filter((x) => x !== 'ANNEE').slice(0, 4 - plan.length)) {
      plan.push({ groupby: d, series: '', metrics: [S.metrics[0]], limit: AUTO_ROW_LIMIT });
    }
    return plan;
  }

  function headerTitle() {
    const ds = S.ds;
    const what = S.metrics.map((m) => metricDef(ds, m).label).join(', ');
    if (S.label) return S.label;
    if (S.groupby === AUTO || !S.groupby) return what;
    const by = grainOf(S.groupby) ? GRAINS[grainOf(S.groupby)].toLowerCase() : colLabel(ds, S.groupby).toLowerCase();
    return `${what} par ${by}`;
  }

  async function run() {
    if (!S) return;
    persist();
    const token = ++S.token;
    const ds = S.ds;
    const domain = CAT.domainsByKey[ds.domain] || {};
    $('#rtitle').replaceChildren(headerTitle(), h('span', { class: 'sub', text: `${domain.title} · ${ds.label}` }));
    $('#dash').href = `/superset/dashboard/${domain.slug}/${S.company ? `?cod_soc=${encodeURIComponent(S.company)}` : ''}`;
    S.detailLoaded = false;
    detailCache = null;
    status('Chargement…');
    try {
      const auto = S.groupby === AUTO;
      const grouped = !auto && (S.groupby || S.series);
      const plan = auto ? autoPlan() : [];
      const [totals, data, autoRows] = await Promise.all([
        rows(totalsQuery(false)),
        grouped ? rows(groupedQuery(false)) : Promise.resolve([]),
        Promise.all(plan.map((v) => rows(groupedQuery(false, v)))),
      ]);
      if (token !== S.token) return;
      S.rows = data;
      S.totals = totals[0] || {};
      S.auto = plan.map((v, i) => ({ ...v, rows: autoRows[i] }));
      renderKpis();
      showTab(S.tab);
      status(data.length >= QUERY_ROW_LIMIT ? `Résultat limité aux ${QUERY_ROW_LIMIT} premières lignes.` : '');
    } catch (e) {
      if (token === S.token) status(e.message, true);
    }
  }

  function renderKpis() {
    $('#kpis').replaceChildren(...S.metrics.map((name) => {
      const m = metricDef(S.ds, name);
      return h('div', { class: 'kpi', title: m.expression },
        h('div', { class: 'v', text: fmt(S.totals[name], m.format) }), h('div', { class: 'l', text: m.label }));
    }));
  }

  function showTab(tab) {
    S.tab = tab;
    $$('.rtabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
    $$('[data-panel]').forEach((p) => { p.hidden = p.dataset.panel !== tab; });
    syncChartActions();
    if (tab === 'chart') renderCharts();
    if (tab === 'table') renderGrouped();
    if (tab === 'detail' && !S.detailLoaded) loadDetail();
    persist();
  }

  function axisLabel(groupby, value) {
    const grain = grainOf(groupby);
    if (grain) return fmtDate(value, grain);
    return value == null || value === '' ? 'Non renseigné' : String(value);
  }

  function renderCharts() {
    disposeCharts();
    const box = $('#charts');
    if (!window.echarts) { box.replaceChildren(h('p', { class: 'empty', text: 'Bibliothèque graphique indisponible.' })); return; }
    if (S.groupby === AUTO) {
      box.className = 'charts';
      box.replaceChildren(...S.auto.map((v) => {
        const m = metricDef(S.ds, v.metrics[0]);
        const by = grainOf(v.groupby) ? GRAINS[grainOf(v.groupby)].toLowerCase() : colLabel(S.ds, v.groupby).toLowerCase();
        const holder = h('div', { class: 'c' });
        const card = h('div', { class: 'mini' },
          h('button', {
            type: 'button', class: 't', title: 'Analyser en détail',
            onclick: () => { S.groupby = v.groupby; S.label = ''; renderExplorer(); },
          }, `${m.label} par ${by} ↗`), holder);
        return card;
      }));
      $$('.mini .c').forEach((holder, i) => {
        const v = S.auto[i];
        const m = metricDef(S.ds, v.metrics[0]);
        const by = grainOf(v.groupby) ? GRAINS[grainOf(v.groupby)].toLowerCase() : colLabel(S.ds, v.groupby).toLowerCase();
        drawChart(holder, v, v.rows, 'auto', `${m.label} par ${by}`);
      });
      return;
    }
    box.className = '';
    if (!S.groupby) {
      box.replaceChildren(h('p', { class: 'empty', text: 'Choisissez « Analyser par » pour afficher un graphique.' }));
      return;
    }
    const holder = h('div', { class: 'big' });
    box.replaceChildren(holder);
    drawChart(holder, S, S.rows, S.view, headerTitle());
  }

  function drawChart(holder, view, data, kindHint, title) {
    if (!data.length) { holder.replaceChildren(h('p', { class: 'empty', text: 'Aucune donnée.' })); return; }
    const grain = grainOf(view.groupby);
    const key = axisKey(view.groupby, false);
    const cats = [];
    for (const r of data) if (!cats.includes(r[key])) cats.push(r[key]);
    const catLabels = cats.map((c) => axisLabel(view.groupby, c));
    const metrics = view.metrics.map((n) => metricDef(S.ds, n));
    const formats = [...new Set(metrics.map((m) => m.format))].slice(0, 2);
    const kind = kindHint === 'line' || (grain && (grain !== 'P1Y' || cats.length > 12) && !view.series) ? 'line' : 'bar';
    const pie = !grain && !view.series && metrics.length === 1 && !isPercent(metrics[0])
      && (kindHint === 'pie' || (kindHint === 'auto' && cats.length <= 6));
    const valueFmt = (m) => (v) => fmt(v, m.format);
    let option;

    if (pie) {
      const m = metrics[0];
      option = {
        tooltip: { trigger: 'item', valueFormatter: valueFmt(m) },
        legend: { type: 'scroll', top: 0 },
        series: [{
          type: 'pie', radius: ['38%', '68%'], top: 24, itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
          label: { formatter: (p) => `${nf(1).format(p.percent)} %` },
          data: data.map((r) => ({ name: axisLabel(view.groupby, r[key]), value: r[m.name] })),
        }],
      };
    } else {
      let series;
      if (view.series) {
        const m = metrics[0];
        const groups = [];
        for (const r of data) if (!groups.includes(r[view.series])) groups.push(r[view.series]);
        series = groups.map((g) => ({
          name: g == null ? 'Non renseigné' : String(g), type: kind, stack: kind === 'bar' ? 'total' : undefined,
          tooltip: { valueFormatter: valueFmt(m) },
          data: cats.map((c) => { const r = data.find((x) => x[key] === c && x[view.series] === g); return r ? r[m.name] : null; }),
        }));
      } else {
        series = metrics.map((m) => ({
          name: m.label, type: kind, yAxisIndex: Math.max(0, formats.indexOf(m.format)), smooth: kind === 'line',
          showSymbol: cats.length <= 40,
          tooltip: { valueFormatter: valueFmt(m) },
          label: { show: metrics.length === 1 && cats.length <= 12, position: 'top', formatter: (p) => fmt(p.value, m.format) },
          data: cats.map((c) => { const r = data.find((x) => x[key] === c); return r ? r[m.name] : null; }),
        }));
      }
      const horizontal = !grain && kind === 'bar' && cats.length > 6;
      const valueAxes = (view.series ? [metrics[0].format] : formats).map((f) => ({
        type: 'value', axisLabel: { formatter: (v) => fmt(v, f) }, splitLine: { lineStyle: { color: '#edf1f7' } },
      }));
      const catAxis = {
        type: 'category', data: horizontal ? catLabels.slice().reverse() : catLabels,
        axisLabel: { width: horizontal ? 150 : 90, overflow: 'truncate', hideOverlap: true },
      };
      if (horizontal) {
        series.forEach((s) => {
          s.data = s.data.slice().reverse();
          if (s.label) s.label.position = 'right';
          delete s.yAxisIndex;
        });
        holder.style.height = `${Math.max(kindHint === 'auto' ? 230 : 380, cats.length * 22 + 60)}px`;
      }
      option = {
        tooltip: { trigger: 'axis' },
        legend: { type: 'scroll', top: 0, show: series.length > 1 },
        grid: { left: 8, right: 24, top: series.length > 1 ? 34 : 14, bottom: cats.length > 40 && !horizontal ? 40 : 8, containLabel: true },
        xAxis: horizontal ? valueAxes[0] : catAxis,
        yAxis: horizontal ? catAxis : valueAxes,
        dataZoom: cats.length > 40 && !horizontal ? [{ type: 'slider', height: 14, bottom: 6 }] : [],
        series,
      };
    }
    option.color = COLORS;
    const chart = window.echarts.init(holder);
    chart.setOption(option);
    chart.__grh = {
      option,
      title,
      view: { groupby: view.groupby, series: view.series || '', metrics: view.metrics.slice(), limit: view.limit },
    };
    charts.add(chart);
  }

  function liveCharts() {
    return [...charts].filter((c) => c.__grh && !c.isDisposed());
  }

  function syncChartActions() {
    const onChart = S && S.tab === 'chart';
    $$('[data-image], #create-chart').forEach((b) => { b.hidden = !onChart; });
  }

  function downloadUrl(url, name) {
    const a = h('a', { href: url, download: name });
    shadow.append(a);
    a.click();
    a.remove();
  }

  function pngUrl(chart) {
    return chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' });
  }

  function svgUrl(option, width, height) {
    const host = h('div', { style: `position:fixed;left:-10000px;top:0;width:${width}px;height:${height}px` });
    shadow.append(host);
    const chart = window.echarts.init(host, null, { renderer: 'svg', width, height });
    chart.setOption({ ...option, dataZoom: [] });
    const url = chart.getDataURL({ type: 'svg' });
    chart.dispose();
    host.remove();
    return url;
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
  }

  async function exportImages(format) {
    const list = liveCharts();
    if (!list.length) { status('Aucun graphique à exporter.', true); return; }
    const buttons = $$('[data-image], [data-export], #create-chart');
    buttons.forEach((b) => { b.disabled = true; });
    try {
      for (let i = 0; i < list.length; i += 1) {
        const snap = list[i].__grh;
        const name = `${slug(snap.title) || 'graphique'}_${isoDate(new Date())}`;
        if (format === 'png') downloadUrl(pngUrl(list[i]), `${name}.png`);
        else downloadUrl(svgUrl(snap.option, list[i].getWidth() || 800, list[i].getHeight() || 400), `${name}.svg`);
        if (i < list.length - 1) await new Promise((resolve) => setTimeout(resolve, 300));
      }
      status('');
    } catch (e) {
      status(`Export impossible : ${e.message}`, true);
    } finally {
      buttons.forEach((b) => { b.disabled = false; });
    }
  }

  function printCharts() {
    const list = liveCharts();
    if (!list.length) { status('Aucun graphique à imprimer.', true); return; }
    const win = window.open('', '_blank');
    if (!win) { status('Autorisez les fenêtres pour imprimer ou enregistrer le PDF.', true); return; }
    const figures = list.map((c) => `<figure><figcaption>${escapeHtml(c.__grh.title)}</figcaption><img alt="" src="${pngUrl(c)}"></figure>`).join('');
    win.document.open();
    win.document.write(`<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>${escapeHtml(headerTitle())}</title>
      <style>body{font-family:sans-serif;margin:24px;color:#0f172a}figcaption{font-weight:600;margin:12px 0 6px}img{max-width:100%}figure{break-inside:avoid;margin:0 0 24px}</style>
      </head><body>${figures}<script>window.onload=function(){window.print()}<\\/script></body></html>`);
    win.document.close();
  }

  function cellText(col, value) {
    if (col.type === 'num') return fmt(value, col.format);
    if (col.type === 'date') return fmtDate(value, col.grain);
    return value == null || value === '' ? '–' : String(value);
  }

  function renderTable(box, columns, data, onRemove, onMove) {
    if (!data.length) { box.replaceChildren(h('p', { class: 'empty', text: 'Aucune donnée pour ces critères.' })); return; }
    if (onMove && detailSort.key && !columns.some((c) => c.key === detailSort.key)) detailSort = { key: null, asc: true };
    let sortKey = onMove ? detailSort.key : null;
    let asc = onMove ? detailSort.asc : true;
    const body = h('tbody');
    const head = h('tr', null, columns.map((c) => {
      const th = h('th', { class: c.type === 'num' ? 'num' : null, title: onMove ? 'Glisser pour déplacer, cliquer pour trier' : 'Trier' }, c.label);
      th.addEventListener('click', () => {
        if (detailDragged) return;
        asc = sortKey === c.key ? !asc : c.type !== 'num';
        sortKey = c.key;
        if (onMove) detailSort = { key: sortKey, asc };
        draw();
      });
      if (onRemove) {
        th.append(h('button', {
          type: 'button', class: 'col-x', title: columns.length > 1 ? 'Retirer cette colonne' : 'Au moins une colonne reste affichée',
          disabled: columns.length <= 1,
          onclick: (e) => { e.stopPropagation(); onRemove(c.key); },
        }, '✕'));
      }
      if (onMove) {
        th.classList.add('col-drag');
        bindColumnDrag(th, c.key);
      }
      return th;
    }));
    function draw() {
      const sorted = sortKey == null ? data : data.slice().sort((a, b) => {
        const x = a[sortKey];
        const y = b[sortKey];
        if (x == null) return 1;
        if (y == null) return -1;
        const r = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y), 'fr');
        return asc ? r : -r;
      });
      body.replaceChildren(...sorted.map((r) => h('tr', null, columns.map((c) => h('td', {
        class: c.type === 'num' ? 'num' : null,
      }, cellText(c, r[c.key]))))));
    }
    draw();
    box.replaceChildren(h('div', { class: 'table-wrap' }, h('table', null, h('thead', null, head), body)));
  }

  function renderGrouped() {
    const box = $('#table');
    if (S.groupby === AUTO || (!S.groupby && !S.series)) {
      renderTable(box, [{ key: 'l', label: 'Indicateur' }, { key: 'v', label: 'Valeur' }],
        S.metrics.map((n) => ({ l: metricDef(S.ds, n).label, v: fmt(S.totals[n], metricDef(S.ds, n).format) })));
      return;
    }
    const cols = [];
    if (S.groupby) {
      const grain = grainOf(S.groupby);
      cols.push({ key: axisKey(S.groupby, false), label: grain ? GRAINS[grain] : colLabel(S.ds, S.groupby), type: grain ? 'date' : 'text', grain });
    }
    if (S.series) cols.push({ key: S.series, label: colLabel(S.ds, S.series) });
    for (const n of S.metrics) {
      const m = metricDef(S.ds, n);
      cols.push({ key: n, label: m.label, type: 'num', format: m.format });
    }
    renderTable(box, cols, S.rows);
  }

  let detailToken = 0;
  let detailCache = null;
  let detailSort = { key: null, asc: true };
  let detailDragged = false;

  function detailCovers(columns) {
    return Boolean(detailCache && columns.every((c) => detailCache.keys.includes(c)));
  }

  function detailColumnModels() {
    const cols = detailColumns().map((c) => ({
      key: c, label: colLabel(S.ds, c), type: S.ds.temporal.includes(c) ? 'date' : 'text',
    }));
    (detailCache ? detailCache.rows : []).forEach((r) => cols.forEach((c) => {
      if (typeof r[c.key] === 'number' && c.type !== 'date') c.type = 'num';
    }));
    return cols;
  }

  function paintDetail() {
    const box = $('#detail');
    renderColumnBar();
    if (!detailCache || !box) return;
    renderTable(box, detailColumnModels(), detailCache.rows, removeDetailColumn, moveDetailColumn);
  }

  function setDetailColumns(columns) {
    const next = sanitizeDetailColumns(S.ds, columns);
    const prev = S.detailColumns || [];
    if (next.length === prev.length && next.every((c, i) => c === prev[i])) return;
    S.detailColumns = next;
    persist();
    if (S.tab !== 'detail') renderColumnBar();
    else if (detailCovers(next)) paintDetail();
    else {
      S.detailLoaded = false;
      loadDetail();
    }
  }

  function moveDetailColumn(fromKey, toKey, after) {
    if (!fromKey || !toKey || fromKey === toKey) return;
    const order = detailColumns().slice();
    const from = order.indexOf(fromKey);
    if (from < 0) return;
    order.splice(from, 1);
    let to = order.indexOf(toKey);
    if (to < 0) return;
    order.splice(after ? to + 1 : to, 0, fromKey);
    setDetailColumns(order);
  }

  function dropAfter(el, event) {
    const rect = el.getBoundingClientRect();
    return event.clientX > rect.left + rect.width / 2;
  }

  function bindColumnDrag(el, key) {
    el.dataset.col = key;
    el.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      if (e.target.closest && e.target.closest('.col-x')) return;
      e.preventDefault();
      const originX = e.clientX;
      const originY = e.clientY;
      const pointerId = e.pointerId;
      let dragging = false;
      try { el.setPointerCapture(pointerId); } catch (err) { /* pointer already released */ }
      const place = (event) => {
        const hit = shadow.elementFromPoint(event.clientX, event.clientY);
        const target = hit && hit.closest ? hit.closest('[data-col]') : null;
        $$('.drop-before, .drop-after').forEach((n) => n.classList.remove('drop-before', 'drop-after'));
        if (!target || target === el || !target.dataset.col) return null;
        const after = dropAfter(target, event);
        target.classList.add(after ? 'drop-after' : 'drop-before');
        return { key: target.dataset.col, after };
      };
      const move = (event) => {
        if (event.pointerId !== pointerId) return;
        if (!dragging) {
          if (Math.hypot(event.clientX - originX, event.clientY - originY) < 4) return;
          dragging = true;
          detailDragged = true;
          el.classList.add('dragging');
        }
        place(event);
      };
      const finish = (event) => {
        if (event.pointerId !== pointerId) return;
        window.removeEventListener('pointermove', move, true);
        window.removeEventListener('pointerup', finish, true);
        window.removeEventListener('pointercancel', finish, true);
        const placed = dragging ? place(event) : null;
        el.classList.remove('dragging');
        $$('.drop-before, .drop-after').forEach((n) => n.classList.remove('drop-before', 'drop-after'));
        if (placed) moveDetailColumn(key, placed.key, placed.after);
        else if (!dragging) el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        setTimeout(() => { detailDragged = false; }, 0);
      };
      window.addEventListener('pointermove', move, true);
      window.addEventListener('pointerup', finish, true);
      window.addEventListener('pointercancel', finish, true);
    });
  }

  function removeDetailColumn(col) {
    const current = detailColumns();
    if (current.length <= 1 || !current.includes(col)) return;
    setDetailColumns(current.filter((c) => c !== col));
  }

  function addDetailColumn(col) {
    const current = detailColumns();
    if (!allColumnKeys().includes(col) || current.includes(col)) return;
    setDetailColumns(current.concat([col]));
  }

  function renderColumnBar() {
    const bar = $('#colbar');
    if (!bar || !S) return;
    const shown = detailColumns();
    const hidden = allColumnKeys().filter((c) => !shown.includes(c));
    const chips = shown.map((c) => {
      const chip = h('span', { class: 'col-chip', title: 'Glisser pour déplacer' },
        colLabel(S.ds, c),
        h('button', {
          type: 'button', class: 'col-x',
          title: shown.length > 1 ? 'Retirer cette colonne' : 'Au moins une colonne reste affichée',
          disabled: shown.length <= 1,
          onclick: () => removeDetailColumn(c),
        }, '✕'));
      bindColumnDrag(chip, c);
      return chip;
    });
    const list = h('div', { class: 'ms-list' });
    const finder = hidden.length > 8
      ? h('input', { type: 'search', placeholder: 'Rechercher une colonne…' })
      : null;
    const panel = h('div', { class: 'ms-panel', hidden: true }, finder, list);
    const addBtn = h('button', { type: 'button', class: 'btn', disabled: !hidden.length }, 'Ajouter');

    function draw(query) {
      const q = norm(query || '');
      const items = hidden.filter((c) => !q || norm(colLabel(S.ds, c)).includes(q) || norm(c).includes(q));
      list.replaceChildren(...(items.length
        ? items.map((c) => h('button', { type: 'button', class: 'col-add', onclick: () => addDetailColumn(c) }, colLabel(S.ds, c)))
        : [h('p', { class: 'note', text: 'Aucune colonne' })]));
    }
    addBtn.addEventListener('click', () => {
      panel.hidden = !panel.hidden;
      if (panel.hidden) return;
      draw(finder ? finder.value : '');
      if (finder) finder.focus();
    });
    if (finder) finder.addEventListener('input', () => draw(finder.value));

    bar.replaceChildren(
      h('span', { class: 'colbar-label', text: 'Colonnes' }),
      h('div', { class: 'chips' }, ...chips),
      h('div', { class: 'colbar-tools' },
        h('div', { class: 'ms' }, addBtn, panel),
        h('button', { type: 'button', class: 'link', onclick: () => setDetailColumns(allColumnKeys()) }, 'Toutes'),
        h('button', { type: 'button', class: 'link', onclick: () => setDetailColumns(usefulColumns()) }, 'Liste utile')));
  }

  async function loadDetail() {
    const token = ++detailToken;
    const requested = detailColumns().slice();
    detailCache = null;
    const box = $('#detail');
    const note = $('#dnote');
    renderColumnBar();
    box.replaceChildren(h('p', { class: 'empty', text: 'Chargement de la liste…' }));
    try {
      const data = await rows(detailQuery(false));
      if (token !== detailToken) return;
      detailCache = { keys: requested, rows: data };
      S.detailLoaded = true;
      note.textContent = data.length >= DETAIL_ROW_LIMIT
        ? `${DETAIL_ROW_LIMIT} premières lignes affichées ; l'export contient toutes les lignes.` : `${data.length} ligne(s).`;
      paintDetail();
    } catch (e) {
      if (token === detailToken) box.replaceChildren(h('p', { class: 'empty', text: e.message }));
    }
  }

  function chartKind(option) {
    const series = option.series && option.series[0];
    if (!series || series.type === 'pie') return { viz: 'pie', horizontal: false, stacked: false };
    const xAxis = Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis;
    return {
      viz: series.type === 'line' ? 'echarts_timeseries_line' : 'echarts_timeseries_bar',
      horizontal: !!(xAxis && xAxis.type === 'value'),
      stacked: option.series.some((s) => s.stack),
    };
  }

  function simpleFilter(subject, operator, comparator) {
    return { clause: 'WHERE', expressionType: 'SIMPLE', subject, operator, comparator };
  }

  function adhocFilters() {
    const filters = [];
    if (S.ds.has_company && S.company) filters.push(simpleFilter('COD_SOC', '==', S.company));
    for (const [col, vals] of Object.entries(S.filters)) {
      if (vals && vals.length) filters.push(simpleFilter(col, 'IN', vals));
    }
    if (S.ds.main_dttm_col && (S.from || S.to)) {
      filters.push(simpleFilter(
        S.ds.main_dttm_col, 'TEMPORAL_RANGE',
        `${S.from || '1900-01-01'} : ${S.to ? addDays(S.to, 1) : 'now'}`,
      ));
    }
    for (const c of S.conditions) {
      if (!c.on) continue;
      if (c.sql) filters.push({ clause: 'WHERE', expressionType: 'SQL', sqlExpression: c.sql });
      else filters.push(simpleFilter(c.col, c.op, c.val));
    }
    return filters;
  }

  function sqlMetric(name) {
    const m = metricDef(S.ds, name);
    return { expressionType: 'SQL', sqlExpression: m.expression, label: m.label, hasCustomLabel: true };
  }

  function chartFormData(snap) {
    const view = snap.view;
    const kind = chartKind(snap.option);
    const metrics = view.metrics.map(sqlMetric);
    const grain = grainOf(view.groupby);
    const axis = grain ? S.timeColumn : view.groupby;
    const base = {
      datasource: `${S.ds.id}__table`,
      viz_type: kind.viz,
      adhoc_filters: adhocFilters(),
      row_limit: view.limit || QUERY_ROW_LIMIT,
      color_scheme: 'supersetColors',
    };
    if (kind.viz === 'pie') {
      return { ...base, groupby: [axis], metric: metrics[0], show_legend: true, number_format: metricDef(S.ds, view.metrics[0]).format || 'SMART_NUMBER' };
    }
    return {
      ...base,
      x_axis: axis,
      time_grain_sqla: grain || undefined,
      metrics,
      groupby: view.series ? [view.series] : [],
      orientation: kind.horizontal ? 'horizontal' : 'vertical',
      stack: kind.stacked ? 'Stack' : null,
      show_legend: true,
      y_axis_format: metricDef(S.ds, view.metrics[0]).format || 'SMART_NUMBER',
    };
  }

  async function postChart(snap) {
    const form = chartFormData(snap);
    const res = await fetch('/api/v1/chart/', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({
        slice_name: String(snap.title).slice(0, 250),
        viz_type: form.viz_type,
        datasource_id: S.ds.id,
        datasource_type: 'table',
        params: JSON.stringify(form),
      }),
    });
    if (res.status === 403) throw new Error('Ce compte ne peut pas créer de graphique dans Superset.');
    if (!res.ok) throw await apiError(res);
    return (await res.json()).id;
  }

  async function createSupersetCharts() {
    const list = liveCharts();
    if (!list.length) {
      status(S.groupby ? 'Aucun graphique à créer.' : 'Choisissez « Analyser par » pour créer un graphique.', true);
      return;
    }
    const button = $('#create-chart');
    const buttons = $$('[data-image], [data-export], #create-chart');
    const popup = list.length === 1 ? window.open('', '_blank') : null;
    buttons.forEach((b) => { b.disabled = true; });
    status(list.length > 1 ? 'Création des graphiques…' : 'Création du graphique…');
    try {
      const created = [];
      for (const chart of list) {
        created.push({ id: await postChart(chart.__grh), title: chart.__grh.title });
      }
      const link = (c) => h('a', { href: `/explore/?slice_id=${c.id}`, target: '_blank', rel: 'noopener' }, c.title);
      if (created.length === 1) {
        const url = `/explore/?slice_id=${created[0].id}`;
        if (popup && !popup.closed) popup.location.href = url;
        const box = $('#status');
        box.hidden = false;
        box.classList.remove('error');
        box.replaceChildren('Graphique créé dans Superset : ', link(created[0]));
      } else {
        if (popup && !popup.closed) popup.close();
        const box = $('#status');
        box.hidden = false;
        box.classList.remove('error');
        const nodes = [`${created.length} graphiques créés : `];
        created.forEach((c, i) => {
          if (i) nodes.push(', ');
          nodes.push(link(c));
        });
        box.replaceChildren(...nodes);
      }
    } catch (e) {
      if (popup && !popup.closed) popup.close();
      status(e.message, true);
    } finally {
      buttons.forEach((b) => { b.disabled = false; });
      if (button) button.disabled = false;
    }
  }

  async function exportData(format) {
    const detail = S.tab === 'detail';
    const grouped = S.groupby !== AUTO && (S.groupby || S.series);
    const query = detail ? detailQuery(true) : grouped ? groupedQuery(true) : totalsQuery(true);
    const buttons = $$('[data-export]');
    buttons.forEach((b) => { b.disabled = true; });
    status('Préparation du fichier…');
    try {
      const res = await chartData(query, format);
      // Excel only reads a UTF-8 CSV with accents correctly when it starts with a BOM.
      const blob = format === 'csv'
        ? new Blob([`\ufeff${(await res.text()).replace(/^\ufeff/, '')}`], { type: 'text/csv;charset=utf-8' })
        : await res.blob();
      const url = URL.createObjectURL(blob);
      const a = h('a', { href: url, download: `${slug(headerTitle())}${detail ? '_detail' : ''}_${isoDate(new Date())}.${format}` });
      shadow.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      status('');
    } catch (e) {
      status(`Export impossible : ${e.message}`, true);
    } finally {
      buttons.forEach((b) => { b.disabled = false; });
    }
  }

  // ------------------------------------------------------------------ KPI dictionary

  function formatName(f) {
    if (!f) return '';
    if (/%$/.test(f)) return 'Pourcentage';
    return /^,?\.0f$/.test(f) || f === 'SMART_NUMBER' ? 'Nombre' : 'Nombre décimal';
  }

  function renderKpiView() {
    const input = $('#kq');
    const domainSel = $('#kdomain');
    const mainOnly = $('#kmain');
    if (!domainSel.options.length) {
      domainSel.append(h('option', { value: '' }, 'Tous les domaines'), ...CAT.domains.map((d) => h('option', { value: d.key }, d.title)));
      $('#glossary').replaceChildren(...CAT.glossary.flatMap((g) => [h('dt', { text: g.term }), h('dd', { text: g.definition })]));
    }
    const words = tokenize(input.value);
    const list = CAT.kpis.filter((k) => (!domainSel.value || k.domain === domainSel.value)
      && (!mainOnly.checked || k.source === 'guide')
      && words.every((w) => tokenize([k.label, k.definition, k.dashboard, k.expression].join(' ')).some((t) => t.startsWith(w))));
    $('#kcount').textContent = `${list.length} indicateur(s)`;
    $('#klist').replaceChildren(...list.map((k) => {
      const domain = CAT.domainsByKey[k.domain];
      const ds = k.dataset && CAT.datasets[k.dataset];
      return h('article', { class: 'kpi-item' },
        h('h4', null, h('span', { text: k.label }), k.source === 'guide' ? h('span', { class: 'star', text: '★ Indicateur clé' }) : null),
        h('p', null, h('strong', null, 'Définition : '), k.definition),
        k.expression ? h('p', null, h('strong', null, 'Formule :'), h('code', { text: k.expression })) : null,
        h('p', { class: 'meta' }, domain
          ? h('a', { href: `/superset/dashboard/${domain.slug}/`, target: '_blank', rel: 'noopener' }, domain.title) : k.dashboard,
        k.format ? ` · ${formatName(k.format)}` : '', ds ? ` · ${ds.label}` : ''),
        k.dataset && k.metric ? h('button', {
          type: 'button', class: 'btn',
          onclick: () => { setView('explorer'); chooseDataset(k.dataset, k.metric); },
        }, 'Explorer cet indicateur') : null);
    }));
  }

  // ------------------------------------------------------------------ bubble shell

  function setView(view) {
    saved.view = view;
    $$('.tabs button').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
    $('#explorer').hidden = view !== 'explorer';
    $('#kpiview').hidden = view !== 'kpi';
    if (view === 'kpi') renderKpiView();
    else if (S && S.tab === 'chart') renderCharts();
    persist();
  }

  function geometry() {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const g = saved.geom || {};
    const w = Math.min(g.w || 560, vw - 16);
    const hgt = Math.min(g.h || Math.min(700, vh - 110), vh - 16);
    const x = Math.min(Math.max(0, g.x ?? vw - w - 24), Math.max(0, vw - 120));
    const y = Math.min(Math.max(0, g.y ?? vh - hgt - 92), Math.max(0, vh - 48));
    return { x, y, w, h: hgt };
  }

  function place(panel) {
    if (saved.max) {
      Object.assign(panel.style, { left: '12px', top: '12px', width: `${window.innerWidth - 24}px`, height: `${window.innerHeight - 24}px` });
      return;
    }
    const g = geometry();
    Object.assign(panel.style, { left: `${g.x}px`, top: `${g.y}px`, width: `${g.w}px`, height: `${g.h}px` });
  }

  function saveGeometry(panel) {
    if (saved.max) return;
    const r = panel.getBoundingClientRect();
    saved.geom = { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) };
    persist();
  }

  function enableDrag(panel, handle) {
    handle.addEventListener('pointerdown', (e) => {
      if (e.target.closest('button') || saved.max) return;
      const r = panel.getBoundingClientRect();
      const dx = e.clientX - r.left;
      const dy = e.clientY - r.top;
      handle.setPointerCapture(e.pointerId);
      const move = (ev) => {
        panel.style.left = `${Math.min(Math.max(0, ev.clientX - dx), window.innerWidth - 120)}px`;
        panel.style.top = `${Math.min(Math.max(0, ev.clientY - dy), window.innerHeight - 48)}px`;
      };
      const up = () => {
        handle.removeEventListener('pointermove', move);
        handle.removeEventListener('pointerup', up);
        saveGeometry(panel);
      };
      handle.addEventListener('pointermove', move);
      handle.addEventListener('pointerup', up);
    });
  }

  function mount() {
    const host = document.createElement('div');
    host.id = 'grh-bubble';
    document.body.append(host);
    shadow = host.attachShadow({ mode: 'open' });
    shadow.append(h('link', { rel: 'stylesheet', href: `${STATIC}bubble.css` }));

    const fab = h('button', { type: 'button', class: 'fab', title: 'Constructeur de graphique (Alt+R)', 'aria-label': 'Constructeur de graphique' });
    fab.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path></svg>';
    const panel = h('section', { class: 'panel', hidden: true, role: 'dialog', 'aria-label': 'Constructeur de graphique' },
      h('header', { class: 'bar' },
        h('span', { class: 'title' }, 'Constructeur de graphique'),
        h('nav', { class: 'tabs' },
          h('button', { type: 'button', 'data-view': 'explorer', class: 'active' }, 'Données'),
          h('button', { type: 'button', 'data-view': 'kpi' }, 'KPI')),
        h('button', { type: 'button', class: 'icon-btn', id: 'max', title: 'Agrandir / réduire' }, '⤢'),
        h('button', { type: 'button', class: 'icon-btn', id: 'close', title: 'Fermer' }, '✕')),
      h('div', { class: 'body' },
        h('div', { class: 'view explorer', id: 'explorer' },
          h('div', { class: 'controls' },
            h('div', { class: 'search' },
              h('input', { id: 'q', type: 'search', autocomplete: 'off', placeholder: 'Rechercher : effectif actif par direction…' }),
              h('div', { id: 'suggest', class: 'suggest', hidden: true })),
            h('div', { class: 'row2' },
              field('Domaine', h('select', { id: 'domain' })),
              field('Données', h('select', { id: 'source' }))),
            h('div', { class: 'field' }, h('span', { text: 'Indicateurs' }), h('div', { class: 'chips', id: 'metrics' })),
            h('div', { class: 'row2' },
              field('Analyser par', h('select', { id: 'groupby' })),
              field('Puis par', h('select', { id: 'series' }))),
            h('details', { class: 'filters' },
              h('summary', null, 'Filtres', h('span', { class: 'badge', id: 'fcount', hidden: true })),
              h('div', { class: 'grid', id: 'fgrid' })),
            h('div', { class: 'chips', id: 'conds', hidden: true })),
          h('div', { class: 'results' },
            h('div', { class: 'res-head' },
              h('h3', { id: 'rtitle' }),
              h('div', { class: 'exports' },
                h('button', { type: 'button', class: 'btn', 'data-image': 'png', hidden: true }, 'PNG'),
                h('button', { type: 'button', class: 'btn', 'data-image': 'svg', hidden: true }, 'SVG'),
                h('button', { type: 'button', class: 'btn', 'data-image': 'pdf', hidden: true }, 'PDF'),
                h('button', { type: 'button', class: 'btn', id: 'create-chart', hidden: true }, 'Créer dans Superset'),
                h('button', { type: 'button', class: 'btn', 'data-export': 'csv' }, 'CSV'),
                h('button', { type: 'button', class: 'btn', 'data-export': 'xlsx' }, 'Excel'))),
            h('div', { id: 'status', class: 'status', hidden: true }),
            h('div', { id: 'kpis', class: 'kpis' }),
            h('div', { class: 'rtabs' },
              h('button', { type: 'button', 'data-tab': 'chart', class: 'active' }, 'Graphiques'),
              h('button', { type: 'button', 'data-tab': 'table' }, 'Tableau'),
              h('button', { type: 'button', 'data-tab': 'detail' }, 'Détail'),
              h('a', { id: 'dash', href: '#', target: '_blank', rel: 'noopener', style: 'margin-left:auto;align-self:center;font-size:12px' },
                'Tableau de bord ↗')),
            h('div', { 'data-panel': 'chart' }, h('div', { id: 'charts' })),
            h('div', { 'data-panel': 'table', hidden: true }, h('div', { id: 'table' })),
            h('div', { 'data-panel': 'detail', hidden: true },
              h('div', { class: 'colbar', id: 'colbar' }),
              h('p', { class: 'note', id: 'dnote' }),
              h('div', { id: 'detail' })))),
        h('div', { class: 'view kpi-view', id: 'kpiview', hidden: true },
          h('div', { class: 'kpi-tools' },
            h('input', { id: 'kq', type: 'search', placeholder: 'Rechercher un indicateur : turnover, absentéisme…' }),
            h('label', null, h('input', { type: 'checkbox', id: 'kmain' }), 'Indicateurs clés')),
          h('div', { class: 'kpi-tools' }, h('select', { id: 'kdomain' }), h('span', { class: 'note', id: 'kcount' })),
          h('div', { class: 'kpi-list', id: 'klist' }),
          h('details', { class: 'glossary' }, h('summary', null, 'Glossaire'), h('dl', { id: 'glossary' })))));
    shadow.append(fab, panel);

    async function open() {
      panel.hidden = false;
      fab.classList.add('open');
      place(panel);
      saved.open = true;
      persist();
      if (!CAT) {
        $('#rtitle').textContent = 'Chargement…';
        try {
          await ensureReady();
        } catch (e) {
          status(`Données indisponibles : ${e.message}`, true);
          return;
        }
        const typed = $('#q').value;
        restoreSelection();
        $('#q').value = typed;
        if (typed.trim() && shadow.activeElement === $('#q')) renderSuggestions();
      }
      setView(saved.view === 'kpi' ? 'kpi' : 'explorer');
    }
    function close() {
      panel.hidden = true;
      fab.classList.remove('open');
      saved.open = false;
      persist();
    }
    const toggle = () => (panel.hidden ? open() : close());

    fab.addEventListener('click', toggle);
    $('#close').addEventListener('click', close);
    $('#max').addEventListener('click', () => { saved.max = !saved.max; place(panel); persist(); });
    $$('.tabs button').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));
    enableDrag(panel, $('.bar'));

    let resizeTimer = null;
    new ResizeObserver(() => {
      charts.forEach((c) => c.resize());
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => !panel.hidden && saveGeometry(panel), 300);
    }).observe(panel);
    window.addEventListener('resize', () => !panel.hidden && place(panel));
    document.addEventListener('keydown', (e) => {
      if (e.altKey && (e.key === 'r' || e.key === 'R')) { e.preventDefault(); toggle(); }
      if (e.key === 'Escape' && !panel.hidden && saved.max) { saved.max = false; place(panel); }
    });

    const q = $('#q');
    q.addEventListener('focus', renderSuggestions);
    q.addEventListener('input', renderSuggestions);
    q.addEventListener('blur', () => setTimeout(() => { $('#suggest').hidden = true; }, 150));
    q.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const first = CAT && q.value.trim() && search(q.value)[0];
        if (first) applyPreset(first);
      }
      if (e.key === 'Escape') { q.value = ''; $('#suggest').hidden = true; }
    });
    $('#domain').addEventListener('change', (e) => {
      const key = Object.keys(CAT.datasets).find((k) => CAT.datasets[k].domain === e.target.value);
      chooseDataset(key);
    });
    $('#source').addEventListener('change', (e) => chooseDataset(e.target.value));
    $('#groupby').addEventListener('change', (e) => { S.groupby = e.target.value; S.label = ''; S.view = 'bar'; renderExplorer(); });
    $('#series').addEventListener('change', (e) => { S.series = e.target.value; S.label = ''; scheduleRun(0); });
    $$('.rtabs button').forEach((b) => b.addEventListener('click', () => showTab(b.dataset.tab)));
    $$('[data-export]').forEach((b) => b.addEventListener('click', () => exportData(b.dataset.export)));
    $$('[data-image]').forEach((b) => b.addEventListener('click', () => (b.dataset.image === 'pdf' ? printCharts() : exportImages(b.dataset.image))));
    $('#create-chart').addEventListener('click', createSupersetCharts);
    ['#kq', '#kdomain', '#kmain'].forEach((sel) => $(sel).addEventListener(sel === '#kq' ? 'input' : 'change', renderKpiView));
    shadow.addEventListener('click', (e) => {
      $$('.ms-panel').forEach((p) => { if (!p.parentElement.contains(e.target)) p.hidden = true; });
    });

    if (saved.open) open();
  }

  if (document.body) mount();
  else document.addEventListener('DOMContentLoaded', mount);
}());
