/* Assistant RH: chat panel. The server validates the plan and returns the rows. */
(function () {
  'use strict';

  if (window.__grhChat) return;
  window.__grhChat = true;
  const script = document.currentScript;
  const params = new URLSearchParams(location.search);
  if (params.has('standalone') || /^\/(login|logout|register|embedded|lang)\b/.test(location.pathname)) return;

  const STATIC = script.dataset.static.replace(/\/?$/, '/');
  const STORE_KEY = 'grh-chat-v1';
  const COLORS = ['#2563eb', '#0ea5e9', '#14b8a6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#64748b'];
  const MONTHS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];

  let CSRF = '';
  let shadow;
  let saved = load();
  let busy = false;
  const charts = new Set();

  function load() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch (e) { return {}; }
  }
  function persist() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(saved)); } catch (e) { /* storage blocked */ }
  }

  const $ = (sel) => shadow.querySelector(sel);

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
  function fmtDate(value, grain) {
    if (value == null || value === '') return '–';
    const d = new Date(typeof value === 'number' ? value : Date.parse(value));
    if (Number.isNaN(d.getTime())) return String(value);
    const y = d.getUTCFullYear();
    const mo = d.getUTCMonth();
    if (grain === 'P1Y') return String(y);
    if (grain === 'P3M') return `T${Math.floor(mo / 3) + 1} ${y}`;
    if (grain === 'P1M') return `${MONTHS[mo]} ${y}`;
    return `${String(d.getUTCDate()).padStart(2, '0')}/${String(mo + 1).padStart(2, '0')}/${y}`;
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.nonce = script.nonce;
      s.onload = resolve;
      s.onerror = () => reject(new Error('Graphique indisponible'));
      document.head.append(s);
    });
  }

  async function ensureCsrf() {
    if (CSRF) return CSRF;
    const res = await fetch(script.dataset.csrf, { credentials: 'same-origin' });
    const body = await res.json();
    CSRF = body.token;
    return CSRF;
  }

  function geometry() {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const g = saved.geom || {};
    const w = Math.min(g.w || 420, vw - 16);
    const hgt = Math.min(g.h || Math.min(640, vh - 110), vh - 16);
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
    handle.addEventListener('pointerdown', (ev) => {
      if (ev.target.closest('button') || saved.max) return;
      const rect = panel.getBoundingClientRect();
      const dx = ev.clientX - rect.left;
      const dy = ev.clientY - rect.top;
      handle.setPointerCapture(ev.pointerId);
      const move = (e) => {
        panel.style.left = `${Math.min(Math.max(0, e.clientX - dx), window.innerWidth - 120)}px`;
        panel.style.top = `${Math.min(Math.max(0, e.clientY - dy), window.innerHeight - 48)}px`;
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

  function addMessage(role, text, extra) {
    const log = $('#log');
    const node = h('div', { class: `msg ${role}` }, text);
    if (extra) node.append(extra);
    log.append(node);
    log.scrollTop = log.scrollHeight;
    return node;
  }

  function renderTable(rows, chart) {
    if (!rows || !rows.length) return null;
    const keys = chart && chart.x ? [chart.x].concat(chart.series ? [chart.series] : [], (chart.metrics || []).map((m) => m.key)) : Object.keys(rows[0]);
    const labels = {};
    if (chart) {
      labels[chart.x] = chart.x_label || chart.x;
      if (chart.series) labels[chart.series] = chart.series_label || chart.series;
      (chart.metrics || []).forEach((m) => { labels[m.key] = m.label; });
    }
    const formats = {};
    (chart && chart.metrics || []).forEach((m) => { formats[m.key] = m.format; });
    const head = h('tr', null, keys.map((key) => h('th', { class: formats[key] ? 'num' : null, text: labels[key] || key })));
    const body = rows.slice(0, 50).map((row) => h('tr', null, keys.map((key) => {
      const value = chart && chart.time_grain && key === chart.x ? fmtDate(row[key], chart.time_grain) : (formats[key] ? fmt(row[key], formats[key]) : (row[key] == null ? '–' : String(row[key])));
      return h('td', { class: formats[key] ? 'num' : null, text: value });
    })));
    return h('div', { class: 'table-wrap' }, h('table', null, h('thead', null, head), h('tbody', null, body)));
  }

  async function drawChart(holder, rows, chart) {
    if (!chart || chart.type === 'table' || chart.type === 'kpi' || !rows.length) return;
    if (!window.echarts) await loadScript(`${STATIC}echarts.min.js`);
    const x = chart.x;
    const cats = [];
    rows.forEach((row) => { if (!cats.includes(row[x])) cats.push(row[x]); });
    const labels = cats.map((c) => (chart.time_grain ? fmtDate(c, chart.time_grain) : (c == null ? '–' : String(c))));
    const metrics = chart.metrics || [];
    let option;
    if (chart.type === 'pie' && metrics.length === 1 && !chart.series) {
      const m = metrics[0];
      option = {
        tooltip: { trigger: 'item' },
        series: [{
          type: 'pie', radius: ['38%', '68%'],
          data: rows.map((row) => ({ name: row[x] == null ? '–' : String(row[x]), value: row[m.key] })),
        }],
      };
    } else {
      const kind = chart.type === 'line' ? 'line' : 'bar';
      let series;
      if (chart.series) {
        const m = metrics[0];
        const groups = [];
        rows.forEach((row) => { if (!groups.includes(row[chart.series])) groups.push(row[chart.series]); });
        series = groups.map((g) => ({
          name: g == null ? 'Non renseigné' : String(g), type: kind,
          data: cats.map((c) => { const row = rows.find((item) => item[x] === c && item[chart.series] === g); return row ? row[m.key] : null; }),
        }));
      } else {
        series = metrics.map((m) => ({
          name: m.label, type: kind, smooth: kind === 'line',
          data: cats.map((c) => { const row = rows.find((item) => item[x] === c); return row ? row[m.key] : null; }),
        }));
      }
      option = {
        tooltip: { trigger: 'axis' },
        legend: { type: 'scroll', top: 0, show: series.length > 1 },
        grid: { left: 8, right: 16, top: series.length > 1 ? 32 : 12, bottom: 8, containLabel: true },
        xAxis: { type: 'category', data: labels, axisLabel: { width: 90, overflow: 'truncate', hideOverlap: true } },
        yAxis: { type: 'value' },
        series,
      };
    }
    option.color = COLORS;
    const instance = window.echarts.init(holder);
    instance.setOption(option);
    charts.add(instance);
  }

  async function ask(text) {
    const input = $('#q');
    const send = $('#send');
    addMessage('user', text);
    input.value = '';
    busy = true;
    send.disabled = true;
    const pending = addMessage('bot', 'Recherche…');
    try {
      await ensureCsrf();
      const res = await fetch(script.dataset.chat, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify({ question: text }),
      });
      let body = {};
      try { body = await res.json(); } catch (e) { body = {}; }
      pending.textContent = body.answer || (res.ok ? 'Aucun résultat.' : 'La requête n’a pas abouti.');
      if (!res.ok) pending.classList.add('error');
      (body.suggestions || []).forEach((item) => {
        const button = h('button', { type: 'button', class: 'suggestion', text: item, onclick: () => { if (!busy) ask(item); } });
        pending.append(button);
      });
      if (body.source && body.source.label) pending.append(h('span', { class: 'source', text: body.source.label }));
      if (body.rows && body.rows.length) {
        const table = renderTable(body.rows, body.chart);
        if (table) pending.append(table);
        if (body.chart && body.chart.type !== 'table') {
          const holder = h('div', { class: 'chart' });
          pending.append(holder);
          try { await drawChart(holder, body.rows, body.chart); } catch (e) { holder.replaceWith(h('p', { text: e.message })); }
        }
      }
    } catch (e) {
      pending.textContent = 'La requête n’a pas abouti.';
      pending.classList.add('error');
    } finally {
      busy = false;
      send.disabled = false;
      $('#log').scrollTop = $('#log').scrollHeight;
    }
  }

  function mount() {
    const host = document.createElement('div');
    host.id = 'grh-chat';
    document.body.append(host);
    shadow = host.attachShadow({ mode: 'open' });
    shadow.append(h('link', { rel: 'stylesheet', href: `${STATIC}chat.css` }));
    const fab = h('button', { type: 'button', class: 'fab', title: 'Assistant RH (Alt+R)', 'aria-label': 'Rechercher' });
    fab.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"></circle><path d="M20 20l-3.5-3.5"></path></svg>';
    const panel = h('section', { class: 'panel', hidden: true, role: 'dialog', 'aria-label': 'Assistant RH' },
      h('header', { class: 'bar' },
        h('span', { class: 'title', text: 'Assistant RH' }),
        h('button', { type: 'button', class: 'icon-btn', id: 'max', title: 'Agrandir / réduire' }, '⤢'),
        h('button', { type: 'button', class: 'icon-btn', id: 'close', title: 'Fermer' }, '✕')),
      h('div', { class: 'log', id: 'log' },
        h('div', { class: 'msg bot', text: 'Posez une question sur l’effectif, les congés, la paie ou les retraites. Les chiffres viennent des tableaux de bord, pas du modèle.' })),
      h('form', { class: 'composer' },
        h('input', { id: 'q', type: 'text', maxlength: '500', autocomplete: 'off', placeholder: 'Ex. effectif actif par direction' }),
        h('button', { type: 'submit', id: 'send', text: 'Envoyer' })));
    shadow.append(fab, panel);

    function open() {
      panel.hidden = false;
      fab.classList.add('open');
      place(panel);
      saved.open = true;
      persist();
      $('#q').focus();
    }
    function close() {
      panel.hidden = true;
      fab.classList.remove('open');
      saved.open = false;
      persist();
    }
    fab.addEventListener('click', () => (panel.hidden ? open() : close()));
    $('#close').addEventListener('click', close);
    $('#max').addEventListener('click', () => { saved.max = !saved.max; place(panel); persist(); charts.forEach((c) => c.resize()); });
    enableDrag(panel, $('.bar'));
    panel.querySelector('form').addEventListener('submit', (e) => {
      e.preventDefault();
      const text = $('#q').value.trim();
      if (!text || busy) return;
      ask(text);
    });
    document.addEventListener('keydown', (e) => {
      if (e.altKey && (e.key === 'r' || e.key === 'R')) { e.preventDefault(); panel.hidden ? open() : close(); }
    });
    window.addEventListener('resize', () => { if (!panel.hidden) place(panel); });
    if (saved.open) open();
  }

  if (document.body) mount();
  else document.addEventListener('DOMContentLoaded', mount);
}());
