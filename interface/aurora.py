"""Tema visual «Aurora» para la interfaz Gradio de JobFit.

Contiene:
- `AURORA_CSS`: tokens, scoping y todos los componentes visuales del rediseño.
- `AURORA_JS`: toggle de tema claro/oscuro persistido en `localStorage`.
- Helpers de renderizado HTML (stepper, top bar, gauge, chips…), que toman
  datos planos de Python y devuelven el markup con las clases Aurora.

Diseño según `design_handoff_aurora_redesign/`. Tokens completos en .aurora.
"""

from __future__ import annotations

import html
from typing import Iterable

# ─────────────────────────────────────────────────────────────────────────────
#  CSS Aurora — variables + componentes
# ─────────────────────────────────────────────────────────────────────────────

AURORA_HEAD = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">'
    # Toggle de tema claro/oscuro inyectado en <head>: event delegation sobre
    # document (funciona aunque Gradio renderice el botón después) e independiente
    # del parámetro js= de Blocks. La guarda __auroraTheme evita doble binding.
    #
    # SOLO fija data-theme en <html>; NO toca la clase del body ni observa
    # mutaciones. El conflicto con el body.dark que Gradio aplica por
    # prefers-color-scheme lo resuelve el CSS (las reglas `html[data-theme=...]
    # body` ganan por especificidad sobre `body.dark`). Una versión previa
    # forzaba body.dark con MutationObserver + polling y entraba en bucle
    # infinito contra Gradio, congelando la página al cargar en modo oscuro.
    """
<script>
(function(){
  if (window.__auroraTheme) return;
  window.__auroraTheme = true;

  function setLabel(t){
    var btn = document.getElementById('aurora-toggle');
    if (!btn) return;
    var lbl = btn.querySelector('.aurora-tgl-label');
    if (lbl) lbl.textContent = (t === 'dark') ? 'claro' : 'oscuro';
  }

  function apply(t){
    document.documentElement.setAttribute('data-theme', t);
    setLabel(t);
  }

  var saved = 'light';
  try {
    var s = localStorage.getItem('jobfit-theme');
    if (s === 'dark' || s === 'light') saved = s;
  } catch (e) {}
  apply(saved);

  document.addEventListener('DOMContentLoaded', function(){
    setLabel(document.documentElement.getAttribute('data-theme') || 'light');
  });

  document.addEventListener('click', function(ev){
    var btn = ev.target && ev.target.closest ? ev.target.closest('#aurora-toggle') : null;
    if (!btn) return;
    var next = (document.documentElement.getAttribute('data-theme') === 'dark') ? 'light' : 'dark';
    apply(next);
    try { localStorage.setItem('jobfit-theme', next); } catch (e) {}
  });
})();
</script>
"""
)

AURORA_CSS = """
/* ── Aurora tokens — globales, no scopeados a .aurora ─────────────────── */
/* (Mover los tokens al :root garantiza que toda la página — labels,
   markdown, inputs, accordion — los herede, no solo el shell del wizard). */
html {
    --bg: #ffffff;
    --card: #ffffff;
    --panel: #f5f7fc;
    --ink: #141a26;
    --ink2: #374055;
    --muted: #5b6478;
    --faint: #e8ebf3;
    --line2: #eef1f7;
    --pri: #2f54d6;
    --pri-soft: #ebeefc;
    --pri-ink: #ffffff;
    --acc: #0e9f6e;
    --acc-soft: #e4f5ee;
    --warn: #bd7a10;
    --warn-soft: #f8efda;
    --bad: #cf4747;
    --bad-soft: #fbeae7;
    --track: #e8ebf3;
    --shadow: 0 1px 2px rgba(20,24,35,.05), 0 14px 34px -16px rgba(20,24,35,.2);
    --radius: 16px;
    --page-bg: #e9ebf1;
}
html[data-theme="dark"],
html[data-theme="dark"] body,
body.dark {
    --bg: #0f1422;
    --card: #141b2c;
    --panel: #0d1320;
    --ink: #e9edf8;
    --ink2: #c2c9dd;
    --muted: #94a0bd;
    --faint: #222b41;
    --line2: #1b2336;
    --pri: #6f8cff;
    --pri-soft: #1c2748;
    --pri-ink: #0a0e1a;
    --acc: #33d39b;
    --acc-soft: #103029;
    --warn: #e6a945;
    --warn-soft: #2c2514;
    --bad: #f1746c;
    --bad-soft: #311a1a;
    --track: #222b41;
    --shadow: 0 1px 2px rgba(0,0,0,.5), 0 22px 48px -22px rgba(0,0,0,.7);
    --page-bg: #090b11;
}
/* Forzar light cuando html[data-theme="light"] (cubre el caso en que Gradio
   ha puesto body.dark por prefers-color-scheme pero Aurora pide light) */
html[data-theme="light"],
html[data-theme="light"] body,
body.light {
    --bg: #ffffff;
    --card: #ffffff;
    --panel: #f5f7fc;
    --ink: #141a26;
    --ink2: #374055;
    --muted: #5b6478;
    --faint: #e8ebf3;
    --line2: #eef1f7;
    --pri: #2f54d6;
    --pri-soft: #ebeefc;
    --pri-ink: #ffffff;
    --acc: #0e9f6e;
    --acc-soft: #e4f5ee;
    --warn: #bd7a10;
    --warn-soft: #f8efda;
    --bad: #cf4747;
    --bad-soft: #fbeae7;
    --track: #e8ebf3;
    --shadow: 0 1px 2px rgba(20,24,35,.05), 0 14px 34px -16px rgba(20,24,35,.2);
    --page-bg: #e9ebf1;
}

/* Fondo de la página + tipografía global */
html, body, .gradio-container {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    background: var(--page-bg) !important;
    color: var(--ink) !important;
    transition: background .35s ease, color .35s ease;
}

/* .aurora ya no redefine tokens (heredados de html). Solo asegura color. */
.aurora { color: var(--ink); }

@keyframes auroraPulse { 0%, 100% { opacity: 1 } 50% { opacity: .45 } }

/* ── Barra global sticky con toggle de tema ────────────────────────────── */
.aurora-tbar {
    position: sticky; top: 0; z-index: 60;
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; padding: 13px 30px;
    backdrop-filter: saturate(140%) blur(12px);
    background: rgba(240,242,247,.82) !important;
    color: #161b27 !important;
    border-bottom: 1px solid rgba(20,24,35,.08);
    margin: -16px -16px 24px;
}
html[data-theme="dark"] .aurora-tbar,
body.dark .aurora-tbar {
    background: rgba(11,14,20,.74) !important;
    color: #e9edf8 !important;
    border-bottom: 1px solid rgba(255,255,255,.08);
}
.aurora-tbar *,
.aurora-tbar span,
.aurora-tbar div { color: inherit !important; }
.aurora-tbar-brand {
    display: flex; align-items: center; gap: 11px;
    font-weight: 700 !important; font-size: 14px !important;
    letter-spacing: -.01em;
    color: inherit !important;
}
.aurora-tbar-mark {
    width: 26px; height: 26px; border-radius: 8px;
    background: linear-gradient(140deg, #2f54d6, #0e9f6e) !important;
    display: flex; align-items: center; justify-content: center;
    color: #fff !important; font-size: 11px !important; font-weight: 800 !important;
    flex: none;
}
.aurora-tbar-sub {
    font-weight: 500 !important; font-size: 12px !important;
    color: inherit !important;
    opacity: .65;
}
.aurora-tgl {
    display: inline-flex; align-items: center; gap: 7px;
    border-radius: 999px; padding: 7px 14px;
    font-weight: 600 !important; font-size: 12.5px !important; cursor: pointer;
    border: 1px solid rgba(20,24,35,.12) !important;
    transition: all .2s;
    background: #fff !important; color: #1a2030 !important;
    box-shadow: 0 1px 2px rgba(20,24,35,.06);
    font-family: inherit !important;
}
html[data-theme="dark"] .aurora-tgl,
body.dark .aurora-tgl {
    background: #161c2b !important; color: #e9edf8 !important;
    border-color: rgba(255,255,255,.1) !important;
    box-shadow: none;
}
.aurora-tgl:hover { transform: translateY(-1px); }
.aurora-tgl-dot { width: 9px; height: 9px; border-radius: 50%; background: #2f54d6 !important; }
html[data-theme="dark"] .aurora-tgl-dot,
body.dark .aurora-tgl-dot { background: #33d39b !important; }
.aurora-tgl-label { color: inherit !important; opacity: 1 !important; font-weight: 600 !important; }

/* ── Shell del wizard ──────────────────────────────────────────────────── */
.aurora-shell {
    background: var(--bg);
    border: 1px solid var(--faint);
    border-radius: 22px;
    box-shadow: var(--shadow);
    overflow: hidden;
}

/* ── Top bar de aplicación (marca + estado LM Studio) ──────────────────── */
.aurora-appbar {
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; padding: 18px 26px;
    border-bottom: 1px solid var(--line2);
}
.aurora-appbar-brand { display: flex; align-items: center; gap: 12px; }
.aurora-appbar-mark {
    width: 34px; height: 34px; border-radius: 10px;
    background: linear-gradient(140deg, var(--pri), var(--acc));
    display: flex; align-items: center; justify-content: center;
    color: #fff; font-weight: 800; font-size: 14px;
}
.aurora-appbar-title { font-weight: 800; font-size: 16px; letter-spacing: -.02em; color: var(--ink); }
.aurora-appbar-sub { font-size: 11.5px; color: var(--muted); font-weight: 500; }
.aurora-pill {
    display: inline-flex; align-items: center; gap: 7px;
    font-weight: 600; font-size: 12px;
    padding: 7px 12px; border-radius: 999px;
}
.aurora-pill-dot {
    width: 7px; height: 7px; border-radius: 50%;
    animation: auroraPulse 2s infinite;
}
.aurora-pill.ok    { background: var(--acc-soft);  color: var(--acc); }
.aurora-pill.ok    .aurora-pill-dot { background: var(--acc); }
.aurora-pill.warn  { background: var(--warn-soft); color: var(--warn); }
.aurora-pill.warn  .aurora-pill-dot { background: var(--warn); }
.aurora-pill.bad   { background: var(--bad-soft);  color: var(--bad); }
.aurora-pill.bad   .aurora-pill-dot { background: var(--bad); }

/* ── Wizard stepper ────────────────────────────────────────────────────── */
.aurora-stepper {
    display: flex; align-items: center; gap: 8px;
    padding: 18px 26px;
    background: var(--panel);
    border-bottom: 1px solid var(--line2);
}
.aurora-step {
    display: flex; align-items: center; gap: 10px;
    flex: 0 0 auto;          /* el nodo solo ocupa lo que necesita */
}
.aurora-step-dot {
    width: 26px; height: 26px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700;
    flex: none;
}
.aurora-step-label {
    font-size: 13px;
    white-space: nowrap;     /* sin saltos ni truncado */
}
.aurora-step-line {          /* los conectores son los que absorben el espacio */
    height: 2px;
    flex: 1 1 auto;
    border-radius: 2px;
    background: var(--track);
    min-width: 24px;
}
.aurora-step.done .aurora-step-dot   { background: var(--acc); color: #fff; }
.aurora-step.done .aurora-step-label { color: var(--ink2); font-weight: 600; }
.aurora-step.active .aurora-step-dot {
    background: var(--pri); color: #fff;
    box-shadow: 0 0 0 4px var(--pri-soft);
}
.aurora-step.active .aurora-step-label { color: var(--ink); font-weight: 700; }
.aurora-step.todo .aurora-step-dot   { background: var(--track); color: var(--muted); }
.aurora-step.todo .aurora-step-label { color: var(--muted); font-weight: 600; }
.aurora-step-line.done   { background: var(--acc); }
.aurora-step-line.active { background: var(--pri); }

@media (max-width: 720px) {
    .aurora-step-label { display: none; }
}

/* ── Encabezado de sección Resultados ──────────────────────────────────── */
.aurora-section-head {
    display: flex; align-items: flex-end; justify-content: space-between;
    gap: 16px; margin-bottom: 18px; flex-wrap: wrap;
}
.aurora-eyebrow {
    font-size: 12px; font-weight: 700;
    letter-spacing: .06em; text-transform: uppercase;
    color: var(--muted); margin-bottom: 4px;
}
.aurora-h1 { font-size: 21px; font-weight: 800; letter-spacing: -.02em; color: var(--ink); }
.aurora-prefs { display: flex; gap: 9px; }
.aurora-pref {
    font-size: 12px; font-weight: 600; color: var(--ink2);
    background: var(--panel); border: 1px solid var(--faint);
    padding: 7px 12px; border-radius: 9px;
}

/* ── Grids de tarjetas ─────────────────────────────────────────────────── */
.aurora-grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-bottom: 16px; }
.aurora-grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }

/* ── Tarjeta base ──────────────────────────────────────────────────────── */
.aurora-card {
    background: var(--card);
    border: 1px solid var(--faint);
    border-radius: var(--radius);
    padding: 20px;
    box-shadow: var(--shadow);
}
.aurora-card-h {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 14px;
}
.aurora-card-title { font-size: 14px; font-weight: 700; color: var(--ink); }
.aurora-card-sub   { font-size: 11.5px; color: var(--muted); font-weight: 600; }

/* ── Gauge del score ───────────────────────────────────────────────────── */
.aurora-score { display: flex; gap: 20px; align-items: center; padding: 22px; }
.aurora-gauge {
    position: relative; width: 130px; height: 130px;
    border-radius: 50%; flex: none;
}
.aurora-gauge-inner {
    position: absolute; inset: 11px;
    border-radius: 50%; background: var(--card);
    display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.aurora-gauge-num { font-size: 38px; font-weight: 800; line-height: 1; letter-spacing: -.02em; color: var(--ink); }
.aurora-gauge-tot { font-size: 11px; color: var(--muted); font-weight: 600; }
.aurora-band {
    display: inline-block; font-size: 11.5px; font-weight: 700;
    padding: 4px 10px; border-radius: 999px; margin-bottom: 9px;
}
.aurora-band.ok   { color: var(--acc);  background: var(--acc-soft); }
.aurora-band.warn { color: var(--warn); background: var(--warn-soft); }
.aurora-band.bad  { color: var(--bad);  background: var(--bad-soft); }
.aurora-score-text { font-size: 13.5px; line-height: 1.55; color: var(--ink2); }
.aurora-score-text b { color: var(--ink); }
.aurora-score-text .miss { color: var(--bad); }

/* ── Chips de keywords ─────────────────────────────────────────────────── */
.aurora-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.aurora-chip {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 12.5px; font-weight: 600;
    padding: 6px 11px; border-radius: 8px;
}
.aurora-chip-dot { width: 6px; height: 6px; border-radius: 50%; }
.aurora-chip.ok   { color: var(--acc);  background: var(--acc-soft); }
.aurora-chip.ok   .aurora-chip-dot { background: var(--acc); }
.aurora-chip.warn { color: var(--warn); background: var(--warn-soft); }
.aurora-chip.warn .aurora-chip-dot { background: var(--warn); }
.aurora-chip.bad  { color: var(--bad);  background: var(--bad-soft); }
.aurora-chip.bad  .aurora-chip-dot { background: var(--bad); }

/* ── Plan de cambios ───────────────────────────────────────────────────── */
.aurora-plan { display: flex; flex-direction: column; gap: 11px; }
.aurora-plan-item { display: flex; gap: 10px; font-size: 12.8px; line-height: 1.5; color: var(--ink2); }
.aurora-plan-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex: none; }
.aurora-plan-item.alto    .aurora-plan-dot { background: var(--bad); }
.aurora-plan-item.medio   .aurora-plan-dot { background: var(--warn); }
.aurora-plan-item.opcional .aurora-plan-dot { background: var(--acc); }
.aurora-plan-item b { color: var(--ink); }

/* ── Preview de CV ─────────────────────────────────────────────────────── */
.aurora-cv-doc {
    background: var(--panel); border: 1px solid var(--faint);
    border-radius: 10px; padding: 14px 15px;
    max-height: 320px; overflow-y: auto;
    font-size: 12.5px; line-height: 1.55; color: var(--ink2);
    white-space: pre-wrap; word-break: break-word;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
}
.aurora-cv-doc::-webkit-scrollbar { width: 8px; }
.aurora-cv-doc::-webkit-scrollbar-thumb { background: var(--faint); border-radius: 4px; }

/* ── Checklist ATS ─────────────────────────────────────────────────────── */
.aurora-progress { height: 7px; border-radius: 4px; background: var(--track); overflow: hidden; margin-bottom: 15px; }
.aurora-progress-fill { height: 100%; background: var(--acc); border-radius: 4px; transition: width .4s ease; }
.aurora-check { display: flex; flex-direction: column; gap: 10px; }
.aurora-check-item { display: flex; gap: 9px; align-items: flex-start; font-size: 12.5px; line-height: 1.45; color: var(--ink2); }
.aurora-check-item b { color: var(--ink); }
.aurora-check-glyph { font-weight: 800; flex: none; width: 14px; text-align: center; }
.aurora-check-item.ok    .aurora-check-glyph { color: var(--acc); }
.aurora-check-item.warn  .aurora-check-glyph { color: var(--warn); }
.aurora-check-item.bad   .aurora-check-glyph { color: var(--bad); }

/* ── Variantes (E) ─────────────────────────────────────────────────────── */
.aurora-variants { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
.aurora-variant-h { font-size: 12.5px; font-weight: 700; color: var(--pri); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 8px; }
.aurora-variant-body { font-size: 12.8px; line-height: 1.55; color: var(--ink2); margin-bottom: 12px; }
.aurora-variant-skills { font-size: 12.5px; color: var(--ink2); }
.aurora-variant-skills b { color: var(--ink); }

/* ── Diagnóstico (sección secundaria) ──────────────────────────────────── */
.aurora-diag-kv { display: flex; gap: 10px; flex-wrap: wrap; font-size: 13px; color: var(--ink2); }
.aurora-diag-kv b { color: var(--ink); font-weight: 700; }

/* ── Cuerpo del paso ───────────────────────────────────────────────────── */
.aurora-body { padding: 22px 26px 28px; }
.aurora-body h2 { font-size: 18px; font-weight: 800; letter-spacing: -.01em; margin: 0 0 12px; color: var(--ink); }
.aurora-body p  { color: var(--ink2); font-size: 13.5px; line-height: 1.55; margin: 0 0 14px; }

/* ── Aviso/alerta inline ──────────────────────────────────────────────── */
.aurora-alert {
    border-radius: 10px; padding: 12px 14px;
    font-size: 13px; line-height: 1.5;
    background: var(--bad-soft); color: var(--bad);
    border: 1px solid var(--bad);
    margin-bottom: 12px;
}
.aurora-alert.info { background: var(--pri-soft); color: var(--pri); border-color: var(--pri); }
.aurora-alert.warn { background: var(--warn-soft); color: var(--warn); border-color: var(--warn); }

/* ── Gradio overrides — APLICAN A TODA LA PÁGINA ───────────────────────── */
.gradio-container {
    max-width: 1240px !important;
    margin: 0 auto !important;
    padding: 0 16px 60px !important;
    background: transparent !important;
}
.gradio-container * { font-family: inherit; }
footer { display: none !important; }

/* Markdown — titulares y cuerpo (también fuera del shell, p. ej. accordion) */
.gradio-container h1, .gradio-container h2, .gradio-container h3,
.gradio-container h4, .gradio-container h5,
.gradio-container .prose h1, .gradio-container .prose h2,
.gradio-container .prose h3, .gradio-container .prose h4,
.gradio-container .markdown h1, .gradio-container .markdown h2,
.gradio-container .markdown h3, .gradio-container .markdown h4 {
    color: var(--ink) !important;
    font-weight: 700 !important;
}
.gradio-container p,
.gradio-container li,
.gradio-container .prose,
.gradio-container .prose p,
.gradio-container .prose li,
.gradio-container .markdown,
.gradio-container .markdown p,
.gradio-container .markdown li {
    color: var(--ink2) !important;
}
.gradio-container .prose strong,
.gradio-container .markdown strong { color: var(--ink) !important; }

/* Inline code y bloques de code — buena legibilidad en ambos modos */
.gradio-container .prose code,
.gradio-container .markdown code {
    background: var(--panel) !important;
    color: var(--ink) !important;
    border: 1px solid var(--faint) !important;
    padding: 1px 6px !important;
    border-radius: 6px !important;
    font-size: 12.5px;
}

/* Labels de TODOS los componentes Gradio (no solo dentro del shell) */
.gradio-container label,
.gradio-container .label-wrap,
.gradio-container .label-wrap > span,
.gradio-container .gr-form label,
.gradio-container .gradio-textbox label,
.gradio-container .gradio-dropdown label,
.gradio-container .gradio-file label,
.gradio-container .gradio-slider label {
    color: var(--ink2) !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}

/* Inputs / textareas / dropdowns universales */
.gradio-container input[type="text"],
.gradio-container input[type="url"],
.gradio-container input[type="search"],
.gradio-container input[type="number"],
.gradio-container input[type="email"],
.gradio-container textarea,
.gradio-container .gr-textbox textarea,
.gradio-container .gr-textbox input,
.gradio-container .gradio-dropdown input {
    background: var(--panel) !important;
    border: 1px solid var(--faint) !important;
    border-radius: 10px !important;
    color: var(--ink) !important;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 13.5px !important;
    transition: border-color .15s ease;
}
.gradio-container input::placeholder,
.gradio-container textarea::placeholder {
    color: var(--muted) !important;
    opacity: 1 !important;
}
.gradio-container input:focus,
.gradio-container textarea:focus,
.gradio-container .gr-textbox textarea:focus {
    border-color: var(--pri) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px var(--pri-soft) !important;
}

/* Dropdown menu */
.gradio-container .gradio-dropdown ul,
.gradio-container .gradio-dropdown [role="listbox"] {
    background: var(--card) !important;
    border: 1px solid var(--faint) !important;
    color: var(--ink) !important;
}
.gradio-container .gradio-dropdown li,
.gradio-container .gradio-dropdown [role="option"] {
    color: var(--ink) !important;
}
.gradio-container .gradio-dropdown li:hover,
.gradio-container .gradio-dropdown [role="option"]:hover,
.gradio-container .gradio-dropdown [role="option"][aria-selected="true"] {
    background: var(--pri-soft) !important;
    color: var(--ink) !important;
}

/* Botones */
.gradio-container .gr-button,
.gradio-container button {
    border-radius: 9px !important;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    transition: transform .15s ease, filter .15s ease;
}
.gradio-container .gr-button-primary,
.gradio-container button.primary,
.gradio-container .gr-button[variant="primary"] {
    background: var(--pri) !important;
    color: var(--pri-ink) !important;
    border: none !important;
}
.gradio-container .gr-button-primary:hover,
.gradio-container button.primary:hover {
    transform: translateY(-1px);
    filter: brightness(1.05);
}
.gradio-container .gr-button-secondary,
.gradio-container button.secondary,
.gradio-container .gr-button[variant="secondary"] {
    background: transparent !important;
    color: var(--ink2) !important;
    border: 1px solid var(--faint) !important;
}
.gradio-container .gr-button-secondary:hover,
.gradio-container button.secondary:hover {
    background: var(--panel) !important;
    color: var(--ink) !important;
}

/* File drop zone — Gradio 6.x usa Svelte; estilamos por estructura/atributo */
.gradio-container .gradio-file,
.gradio-container .gr-file,
.gradio-container [data-testid="file"],
.gradio-container [class*="file-upload"],
.gradio-container [class*="upload-container"] {
    background: var(--panel) !important;
    color: var(--ink) !important;
    border: 2px dashed var(--faint) !important;
    border-radius: 12px !important;
    transition: border-color .2s ease;
}
.gradio-container .gradio-file:hover,
.gradio-container [data-testid="file"]:hover { border-color: var(--pri) !important; }
.gradio-container .gradio-file *,
.gradio-container [data-testid="file"] *,
.gradio-container [class*="file-upload"] *,
.gradio-container [class*="upload-container"] * {
    color: var(--ink2) !important;
    background: transparent !important;
}
/* Botón interno "Arrastra tu CV o haz clic" del file uploader */
.gradio-container .gradio-file button,
.gradio-container [data-testid="file"] button,
.gradio-container [class*="upload"] button {
    background: var(--card) !important;
    color: var(--ink) !important;
    border: 1px solid var(--faint) !important;
    border-radius: 10px !important;
    padding: 10px 16px !important;
    font-weight: 600 !important;
}
.gradio-container .gradio-file button:hover,
.gradio-container [data-testid="file"] button:hover,
.gradio-container [class*="upload"] button:hover {
    background: var(--panel) !important;
    border-color: var(--pri) !important;
}
/* SVG/iconos internos */
.gradio-container .gradio-file svg,
.gradio-container [data-testid="file"] svg,
.gradio-container [class*="upload"] svg { color: var(--muted) !important; opacity: .85; }

/* Accordion — envoltura Aurora propia (en la referencia no existe; aquí
   vive fuera del shell como tarjeta independiente) */
.gradio-container .gradio-accordion {
    background: var(--card) !important;
    border: 1px solid var(--faint) !important;
    border-radius: var(--radius) !important;
    color: var(--ink) !important;
    box-shadow: var(--shadow) !important;
    margin-top: 24px !important;
    overflow: hidden;
}
.gradio-container .gradio-accordion > .label-wrap,
.gradio-container .gradio-accordion summary {
    color: var(--ink) !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    padding: 14px 20px !important;
}
.gradio-container .gradio-accordion > .label-wrap:hover,
.gradio-container .gradio-accordion summary:hover {
    background: var(--panel) !important;
}
/* Cuerpo del accordion con su propio padding */
.gradio-container .gradio-accordion > div:not(.label-wrap) {
    padding: 18px 20px 20px !important;
    border-top: 1px solid var(--line2) !important;
}

/* Tabs internas (dentro del accordion) */
.gradio-container .tab-nav button,
.gradio-container [role="tab"] {
    color: var(--ink2) !important;
    background: transparent !important;
    border-bottom: 2px solid transparent !important;
    font-weight: 600 !important;
}
.gradio-container .tab-nav button.selected,
.gradio-container [role="tab"][aria-selected="true"] {
    color: var(--pri) !important;
    border-bottom-color: var(--pri) !important;
}

/* Slider */
.gradio-container .gradio-slider input[type="range"] { accent-color: var(--pri); }

/* Pulir el toggle de tema: el label "oscuro/claro" no debe quedar pálido */
.aurora-tgl, .aurora-tgl * { color: inherit !important; }
.aurora-tgl-label { font-weight: 600 !important; opacity: 1 !important; }
"""

# ─────────────────────────────────────────────────────────────────────────────
#  JS — toggle de tema + persistencia
# ─────────────────────────────────────────────────────────────────────────────

AURORA_JS = """
() => {
    // Restaurar tema guardado
    try {
        const saved = localStorage.getItem('jobfit-theme');
        if (saved === 'dark' || saved === 'light') {
            document.documentElement.setAttribute('data-theme', saved);
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
        }
    } catch (e) {
        document.documentElement.setAttribute('data-theme', 'light');
    }

    // Listener para el botón de toggle (delegación, el botón está en gr.HTML)
    document.addEventListener('click', (ev) => {
        const btn = ev.target.closest('#aurora-toggle');
        if (!btn) return;
        const html = document.documentElement;
        const isDark = html.getAttribute('data-theme') === 'dark';
        const next = isDark ? 'light' : 'dark';
        html.setAttribute('data-theme', next);
        try { localStorage.setItem('jobfit-theme', next); } catch (e) {}
        const label = btn.querySelector('.aurora-tgl-label');
        if (label) label.textContent = (next === 'dark') ? 'claro' : 'oscuro';
    });
}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  Helpers de utilidad
# ─────────────────────────────────────────────────────────────────────────────

def _esc(text: str) -> str:
    """Escape HTML preservando saltos de línea como literales."""
    return html.escape(str(text), quote=True)


def _band_for_score(score: int | float | None) -> tuple[str, str]:
    """Devuelve (clase css, etiqueta) según la banda del score 0-100."""
    if score is None or not isinstance(score, (int, float)):
        return "warn", "Sin score"
    if score >= 85:
        return "ok", "Buen encaje"
    if score >= 70:
        return "warn", "Encaje medio"
    return "bad", "Encaje bajo"


# ─────────────────────────────────────────────────────────────────────────────
#  Componentes estáticos: tbar, app top bar, stepper
# ─────────────────────────────────────────────────────────────────────────────

def render_tbar(subtitle: str = "Adapta tu CV a la oferta con IA local") -> str:
    return f"""
<div class="aurora-tbar">
  <div class="aurora-tbar-brand">
    <span class="aurora-tbar-mark">JF</span>
    JobFit
    <span class="aurora-tbar-sub">· {_esc(subtitle)}</span>
  </div>
  <button class="aurora-tgl" id="aurora-toggle" type="button">
    <span class="aurora-tgl-dot"></span>
    Modo <span class="aurora-tgl-label">oscuro</span>
  </button>
</div>
"""


def render_app_topbar(available: bool, model: str | None) -> str:
    if available and model:
        pill_class = "ok"
        pill_text = f"LM Studio · {_esc(model.split('/')[-1])}"
    elif available:
        pill_class = "ok"
        pill_text = "LM Studio · conectado"
    else:
        pill_class = "warn"
        pill_text = "Modo básico · sin LLM"

    return f"""
<div class="aurora-appbar">
  <div class="aurora-appbar-brand">
    <div class="aurora-appbar-mark">JF</div>
    <div>
      <div class="aurora-appbar-title">JobFit Agent</div>
      <div class="aurora-appbar-sub">Adapta tu CV a la oferta · 100% local</div>
    </div>
  </div>
  <span class="aurora-pill {pill_class}">
    <span class="aurora-pill-dot"></span>{pill_text}
  </span>
</div>
"""


_STEPS = ("Subir CV", "Oferta", "Preferencias", "Resultados")


def render_stepper(current: int) -> str:
    """current es 1..4."""
    nodes = []
    for i, label in enumerate(_STEPS, start=1):
        if i < current:
            state, glyph = "done", "✓"
        elif i == current:
            state, glyph = "active", str(i)
        else:
            state, glyph = "todo", str(i)
        nodes.append(
            f'<div class="aurora-step {state}">'
            f'<div class="aurora-step-dot">{glyph}</div>'
            f'<span class="aurora-step-label">{_esc(label)}</span>'
            f"</div>"
        )

        if i < len(_STEPS):
            if i < current - 1:
                line_cls = "done"
            elif i == current - 1:
                line_cls = "active"
            else:
                line_cls = ""
            nodes.append(f'<div class="aurora-step-line {line_cls}"></div>')

    return f'<div class="aurora-stepper">{"".join(nodes)}</div>'


# ─────────────────────────────────────────────────────────────────────────────
#  Resultados (Paso 4)
# ─────────────────────────────────────────────────────────────────────────────

def render_results_header(
    rol: str,
    idioma: str,
    longitud: str,
    pais: str,
) -> str:
    chips = []
    if idioma or longitud:
        chips.append(f'<span class="aurora-pref">{_esc(idioma or "ES")} · {_esc(longitud or "2 páginas")}</span>')
    if pais:
        chips.append(f'<span class="aurora-pref">{_esc(pais)}</span>')

    eyebrow = f"ANÁLISIS PRO ATS · {_esc((rol or '—').upper())}"
    return f"""
<div class="aurora-section-head">
  <div>
    <div class="aurora-eyebrow">{eyebrow}</div>
    <div class="aurora-h1">Informe de encaje y CV reescrito</div>
  </div>
  <div class="aurora-prefs">{''.join(chips)}</div>
</div>
"""


def render_score_card(diagnosis: dict) -> str:
    score = diagnosis.get("score")
    try:
        score_int = int(score) if score is not None else None
    except (TypeError, ValueError):
        score_int = None

    band_cls, band_label = _band_for_score(score_int)
    band_cls_for_gauge = {"ok": "var(--acc)", "warn": "var(--warn)", "bad": "var(--bad)"}[band_cls]
    deg = (score_int or 0) * 3.6
    num_html = str(score_int) if score_int is not None else "—"

    razon = diagnosis.get("razon_score") or ""
    gaps = diagnosis.get("gaps") or []
    miss_terms = [g.get("gap", "") for g in gaps[:2] if isinstance(g, dict)]
    miss_html = ""
    if miss_terms:
        miss_html = " Faltan: " + " · ".join(
            f'<b class="miss">{_esc(t)}</b>' for t in miss_terms if t
        ) + "."

    text_html = f"{_esc(razon)}{miss_html}"
    if not razon and not miss_terms:
        text_html = "Análisis no disponible."

    return f"""
<div class="aurora-card aurora-score">
  <div class="aurora-gauge" style="background: conic-gradient({band_cls_for_gauge} 0 {deg}deg, var(--track) {deg}deg 360deg);">
    <div class="aurora-gauge-inner">
      <div class="aurora-gauge-num">{num_html}</div>
      <div class="aurora-gauge-tot">/ 100</div>
    </div>
  </div>
  <div>
    <div class="aurora-band {band_cls}">{_esc(band_label)}</div>
    <div class="aurora-score-text">{text_html}</div>
  </div>
</div>
"""


_KW_STATE_MAP = {
    "presente": ("ok", ""),
    "debil":    ("warn", " · débil"),
    "débil":    ("warn", " · débil"),
    "ausente":  ("bad", " · ausente"),
}


def render_keywords_card(b_keywords: dict) -> str:
    items = b_keywords.get("keywords") or []
    if not items:
        return f"""
<div class="aurora-card">
  <div class="aurora-card-h">
    <div class="aurora-card-title">Keywords ATS</div>
  </div>
  <div class="aurora-score-text">No se extrajeron keywords.</div>
</div>
"""

    presentes = sum(1 for k in items if k.get("estado") == "presente")
    debiles   = sum(1 for k in items if k.get("estado") in ("debil", "débil"))
    ausentes  = sum(1 for k in items if k.get("estado") == "ausente")

    parts = []
    for kw in items[:30]:
        name = kw.get("keyword", "")
        estado = kw.get("estado", "presente")
        cls, suffix = _KW_STATE_MAP.get(estado, ("ok", ""))
        parts.append(
            f'<span class="aurora-chip {cls}">'
            f'<span class="aurora-chip-dot"></span>{_esc(name)}{suffix}'
            f"</span>"
        )

    if len(items) > 30:
        parts.append(
            f'<span class="aurora-chip" style="color:var(--muted);background:var(--panel)">+{len(items) - 30} más</span>'
        )

    sub = f"{presentes} presentes · {debiles} débiles · {ausentes} faltan"
    return f"""
<div class="aurora-card">
  <div class="aurora-card-h">
    <div class="aurora-card-title">Keywords ATS</div>
    <div class="aurora-card-sub">{_esc(sub)}</div>
  </div>
  <div class="aurora-chips">{''.join(parts)}</div>
</div>
"""


def render_plan_card(c_changes: dict) -> str:
    cambios = c_changes.get("cambios") or []
    if not cambios:
        return f"""
<div class="aurora-card">
  <div class="aurora-card-h"><div class="aurora-card-title">Plan de cambios priorizado</div></div>
  <div class="aurora-score-text">Sin cambios sugeridos.</div>
</div>
"""

    # Ordenar: alto → medio → opcional
    order = {"alto": 0, "medio": 1, "opcional": 2}
    cambios_sorted = sorted(cambios, key=lambda c: order.get(c.get("prioridad", "opcional"), 9))

    items_html = []
    for c in cambios_sorted[:10]:
        prio = c.get("prioridad", "opcional")
        prio_label = {"alto": "Alto", "medio": "Medio", "opcional": "Opcional"}.get(prio, prio.title())
        seccion = c.get("seccion", "")
        que = c.get("que_cambiar", "")
        body_text = f"{_esc(seccion)}: " if seccion else ""
        body_text += _esc(que)
        items_html.append(
            f'<div class="aurora-plan-item {prio}">'
            f'<span class="aurora-plan-dot"></span>'
            f'<div><b>{_esc(prio_label)} ·</b> {body_text}</div>'
            f"</div>"
        )

    return f"""
<div class="aurora-card">
  <div class="aurora-card-h"><div class="aurora-card-title">Plan de cambios priorizado</div></div>
  <div class="aurora-plan">{''.join(items_html)}</div>
</div>
"""


def render_cv_preview_card(cv_text: str, has_files: bool) -> str:
    badge = ""
    if has_files:
        badge = '<span class="aurora-pill ok" style="font-size:11px;padding:3px 8px;border-radius:6px"><span class="aurora-pill-dot"></span>listo</span>'

    body_html = _esc(cv_text or "(CV no generado)")
    return f"""
<div class="aurora-card" style="display:flex;flex-direction:column">
  <div class="aurora-card-h">
    <div class="aurora-card-title">CV reescrito</div>
    {badge}
  </div>
  <div class="aurora-cv-doc">{body_html}</div>
  <div style="font-size:11.5px;color:var(--muted);margin-top:10px">
    Usa los botones de descarga (debajo) para obtener el DOCX o TXT.
  </div>
</div>
"""


_CHECK_GLYPH_MAP = {
    "ok": ("ok", "✓"),
    "advertencia": ("warn", "!"),
    "warn": ("warn", "!"),
    "fallo": ("bad", "✗"),
    "bad": ("bad", "✗"),
}


def render_checklist_card(f_checklist: dict) -> str:
    items = f_checklist.get("checklist") or []
    if not items:
        return f"""
<div class="aurora-card">
  <div class="aurora-card-h"><div class="aurora-card-title">Checklist ATS</div></div>
  <div class="aurora-score-text">No se generó checklist.</div>
</div>
"""

    total = len(items)
    ok = sum(1 for c in items if c.get("estado") == "ok")
    pct = round(ok / total * 100) if total else 0

    rows = []
    for c in items[:16]:
        cls, glyph = _CHECK_GLYPH_MAP.get(c.get("estado", "ok"), ("ok", "✓"))
        punto = _esc(c.get("punto", ""))
        detalle = c.get("detalle", "")
        detalle_html = f' <span style="color:var(--muted)">— {_esc(detalle)}</span>' if detalle else ""
        rows.append(
            f'<div class="aurora-check-item {cls}">'
            f'<span class="aurora-check-glyph">{glyph}</span>'
            f"<div><b>{punto}</b>{detalle_html}</div>"
            f"</div>"
        )

    return f"""
<div class="aurora-card">
  <div class="aurora-card-h">
    <div class="aurora-card-title">Checklist ATS</div>
    <div class="aurora-card-sub" style="color:var(--acc)">{ok}/{total}</div>
  </div>
  <div class="aurora-progress"><div class="aurora-progress-fill" style="width:{pct}%"></div></div>
  <div class="aurora-check">{''.join(rows)}</div>
</div>
"""


def render_variants_card(e_variants: dict) -> str:
    ats = e_variants.get("ats_first") or {}
    rec = e_variants.get("recruiter_first") or {}

    def _block(title: str, data: dict) -> str:
        resumen = _esc(data.get("resumen", ""))
        skills = _esc(data.get("skills", ""))
        return f"""
<div class="aurora-card">
  <div class="aurora-variant-h">{title}</div>
  <div class="aurora-variant-body">{resumen or 'No disponible.'}</div>
  <div class="aurora-variant-skills"><b>Skills:</b> {skills or '—'}</div>
</div>
"""

    return f"""
<div class="aurora-card-h" style="margin: 20px 0 12px"><div class="aurora-card-title">Variantes Resumen + Skills</div></div>
<div class="aurora-variants">
  {_block('ATS-first · alta densidad de keywords', ats)}
  {_block('Recruiter-first · narrativa diferenciadora', rec)}
</div>
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Validación de avance del wizard
# ─────────────────────────────────────────────────────────────────────────────

def render_alert(message: str, tone: str = "bad") -> str:
    """Aviso inline (bad / warn / info)."""
    return f'<div class="aurora-alert {tone}">{_esc(message)}</div>'
