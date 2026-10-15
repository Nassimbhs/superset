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
      timeColumn: S.timeColumn, conditions: S.conditions,
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

  const detailColumns = () => (S.detailColumns && S.detailColumns.length ? S.detailColumns : S.ds.detail_columns);

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
      detailColumns: null, rows: [], detailLoaded: false, token: 0,
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
      detailColumns: p.detail_columns || null,
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
      const preset = sel.presetId && CAT.presetsById[sel.presetId];
      S = newSelection(sel.dsKey, {
        ...sel, metrics: metrics.length ? metrics : [ds.metrics[0].name],
        detailColumns: preset ? preset.detail_columns || null : null,
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
      $$('.mini .c').forEach((holder, i) => drawChart(holder, S.auto[i], S.auto[i].rows, 'auto'));
      return;
    }
    box.className = '';
    if (!S.groupby) {
      box.replaceChildren(h('p', { class: 'empty', text: 'Choisissez « Analyser par » pour afficher un graphique.' }));
      return;
    }
    const holder = h('div', { class: 'big' });
    box.replaceChildren(holder);
    drawChart(holder, S, S.rows, S.view);
  }

  function drawChart(holder, view, data, kindHint) {
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
    charts.add(chart);
  }

  function cellText(col, value) {
    if (col.type === 'num') return fmt(value, col.format);
    if (col.type === 'date') return fmtDate(value, col.grain);
    return value == null || value === '' ? '–' : String(value);
  }

  function renderTable(box, columns, data) {
    if (!data.length) { box.replaceChildren(h('p', { class: 'empty', text: 'Aucune donnée pour ces critères.' })); return; }
    let sortKey = null;
    let asc = true;
    const body = h('tbody');
    const head = h('tr', null, columns.map((c) => {
      const th = h('th', { class: c.type === 'num' ? 'num' : null, title: 'Trier' }, c.label);
      th.addEventListener('click', () => { asc = sortKey === c.key ? !asc : c.type !== 'num'; sortKey = c.key; draw(); });
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

  async function loadDetail() {
    const cols = detailColumns().map((c) => ({ key: c, label: colLabel(S.ds, c), type: S.ds.temporal.includes(c) ? 'date' : 'text' }));
    const box = $('#detail');
    const note = $('#dnote');
    box.replaceChildren(h('p', { class: 'empty', text: 'Chargement de la liste…' }));
    try {
      const data = await rows(detailQuery(false));
      data.forEach((r) => cols.forEach((c) => { if (typeof r[c.key] === 'number' && c.type !== 'date') c.type = 'num'; }));
      renderTable(box, cols, data);
      note.textContent = data.length >= DETAIL_ROW_LIMIT
        ? `${DETAIL_ROW_LIMIT} premières lignes affichées ; l'export contient toutes les lignes.` : `${data.length} ligne(s).`;
      S.detailLoaded = true;
    } catch (e) {
      box.replaceChildren(h('p', { class: 'empty', text: e.message }));
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

    const fab = h('button', { type: 'button', class: 'fab', title: 'Accès rapide aux données RH (Alt+R)' }, 'RH');
    const panel = h('section', { class: 'panel', hidden: true, role: 'dialog', 'aria-label': 'Accès rapide RH' },
      h('header', { class: 'bar' },
        h('span', { class: 'title' }, 'Accès rapide RH'),
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
              h('button', { type: 'button', class: 'btn', 'data-export': 'csv' }, 'CSV'),
              h('button', { type: 'button', class: 'btn', 'data-export': 'xlsx' }, 'Excel')),
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
            h('div', { 'data-panel': 'detail', hidden: true }, h('p', { class: 'note', id: 'dnote' }), h('div', { id: 'detail' })))),
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
    ['#kq', '#kdomain', '#kmain'].forEach((sel) => $(sel).addEventListener(sel === '#kq' ? 'input' : 'change', renderKpiView));
    shadow.addEventListener('click', (e) => {
      $$('.ms-panel').forEach((p) => { if (!p.parentElement.contains(e.target)) p.hidden = true; });
    });

    if (saved.open) open();
  }

  if (document.body) mount();
  else document.addEventListener('DOMContentLoaded', mount);
}());
