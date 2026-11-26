#!/usr/bin/env python3
"""build_html.py - turns the same 26 slides into ONE self-contained HTML file
(images & interactive Demo Studio recordings embedded, no external files).

Usage:  pip install pillow
        python -m presentation.src.build_html [--out dist/html/index.html]
Keys in the browser: <- / -> or Space to navigate, F = fullscreen,
Home/End = first/last, N = speaker notes, D = open interactive Auto-Routing Studio.
Print (Ctrl+P) gives one slide per page.
"""
import argparse, base64, html, io, json, os, re
from PIL import Image
import qrcode
try:
    from . import build_pptx as D
    from .i18n import ZH_DEMO_LAUNCHERS, ZH_DEMO_TEXT_MAP, ZH_TEXT_MAP
except ImportError:
    import build_pptx as D
    from i18n import ZH_DEMO_LAUNCHERS, ZH_DEMO_TEXT_MAP, ZH_TEXT_MAP

PX = 9525  # EMU per CSS px  (slide = 1280 x 720 px)
SVG_POINTS = {
    'rightArrow':'0,24 68,24 68,0 100,50 68,100 68,76 0,76',
    'leftArrow':'32,0 32,24 100,24 100,76 32,76 32,100 0,50',
    'downArrow':'24,0 76,0 76,62 100,62 50,100 0,62 24,62',
    'chevron':'0,0 82,0 100,50 82,100 0,100 18,50',
    'homePlate':'0,0 82,0 100,50 82,100 0,100',
}
FALLBACK = {
    'Inter Tight':'"Inter Tight","Segoe UI Variable Text","PingFang SC","Microsoft YaHei UI",-apple-system,BlinkMacSystemFont,sans-serif',
    'Segoe UI Variable Display':'"Inter Tight","Segoe UI Variable Display","PingFang SC","Microsoft YaHei UI",sans-serif',
    'Segoe UI Variable Text':'"Inter Tight","Segoe UI Variable Text","PingFang SC","Microsoft YaHei UI",sans-serif',
    'Calibri':'"Inter Tight","Segoe UI Variable Text",Calibri,"PingFang SC","Microsoft YaHei UI",sans-serif',
    'Consolas':'"Inconsolata",Consolas,"Cascadia Mono",monospace',
    'Inconsolata':'"Inconsolata",Consolas,"Cascadia Mono",monospace',
    'Plus Jakarta Sans':'"Inter Tight","Segoe UI Variable Text","Segoe UI",sans-serif',
    'Newsreader':'"Inter Tight","Segoe UI Variable Display",sans-serif',
    'JetBrains Mono':'"Inconsolata",Consolas,"Cascadia Mono",monospace',
    'Aptos Display':'"Inter Tight","Segoe UI Variable Display",sans-serif',
    'Aptos':'"Inter Tight","Segoe UI Variable Text",sans-serif',
    'Cascadia Code':'"Inconsolata",Consolas,"Cascadia Mono",monospace',
    'Georgia':'"Inter Tight","Segoe UI Variable Display",sans-serif',
    'Courier New':'"Inconsolata",Consolas,monospace',
    'Arial':'"Inter Tight",Arial,Helvetica,sans-serif',
}
e = lambda s: html.escape(s, quote=True)

def data_uri(path, maxw, cache={}):
    key = (path, maxw)
    if key not in cache:
        if path.lower().endswith('.svg'):
            with open(path, 'rb') as f:
                raw = f.read()
            cache[key] = 'data:image/svg+xml;base64,' + base64.b64encode(raw).decode()
        else:
            im = Image.open(path).convert('RGB')
            im.thumbnail((maxw, maxw), Image.Resampling.LANCZOS)
            b = io.BytesIO()
            im.save(b, 'JPEG', quality=88, optimize=True)
            cache[key] = 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    return cache[key]

def box(o):
    return f"left:{o['x']/PX:.1f}px;top:{o['y']/PX:.1f}px;width:{o['cx']/PX:.1f}px;height:{o['cy']/PX:.1f}px;"

def text_html(o):
    paras = o.get('paragraphs') or [{'text': o['text']}]
    raw_font = o.get('fontFamily', D.BF)
    font = FALLBACK.get(raw_font, FALLBACK['Inter Tight'])
    is_display = any(p.get('sizePt', o.get('sizePt', 16)) >= 29 for p in paras)
    if is_display and raw_font != D.MF:
        font = FALLBACK['Segoe UI Variable Display']
    if o.get('letterSpacingPt'):
        ls = f"letter-spacing:{o['letterSpacingPt']*4/3:.1f}px;"
    elif raw_font == D.MF:
        ls = "font-variation-settings:'wdth' 90;"
    elif is_display:
        ls = 'letter-spacing:-0.028em;'
    else:
        ls = 'letter-spacing:-0.008em;'
    ws = 'white-space:pre-wrap;' if raw_font == D.MF else ''
    default_gap_pt = o.get('spaceAfterPt', 2 if raw_font == D.MF else 6.5)
    out = []
    for idx, p in enumerate(paras):
        sz = p.get('sizePt', o.get('sizePt', 16)) * 4/3
        wt = 700 if p.get('bold', o.get('bold')) else (500 if sz >= 22 else 450)
        if raw_font == D.MF:
            lh = 1.48
        elif sz >= 34:
            lh = 1.14
        elif sz >= 22:
            lh = 1.26
        else:
            lh = 1.42
        mb = ''
        if idx < len(paras) - 1:
            gap_px = p.get('spaceAfterPt', default_gap_pt) * 4/3
            mb = f"margin-bottom:{gap_px:.1f}px;"
        st = (f"font-size:{sz:.1f}px;color:#{p.get('color', o.get('color', D.INK))};"
              f"font-weight:{wt};line-height:{lh};{ws}{mb}"
              f"text-align:{p.get('align', o.get('align','center'))};")
        inner = '<br>'.join(e(l) for l in p['text'].split('\n'))
        if p.get('href'):
            inner = f'<a class="ref-link" href="{e(p["href"])}" target="_blank" rel="noreferrer">{inner}</a>'
        out.append(f'<p style="{st}">{inner}</p>')
    return f'<div class="t" style="font-family:{e(font)};{ls}">' + ''.join(out) + '</div>'

REVEAL_ITEMS = {
    3: (4, 6, 4),
    6: (2, 6, 4),
}

DEMO_LAUNCHERS = {
    10: ('fusion', '1', 'Open Fusion Demo'),
    12: ('foundry', '1', 'Open Foundry Demo'),
    20: ('decision', '1', 'Open Decision-1.1 Demo'),
    21: ('fusion', '1', 'Launch Demo 1 · Copilot CLI & Fusion'),
    22: ('foundry', '1', 'Launch Demo 2 · Foundry Router'),
    23: ('decision', '1', 'Launch Demo 3 · Decision-1.1'),
}

def reveal_attrs(slide_index, operation_index):
    config = REVEAL_ITEMS.get(slide_index)
    if config is None:
        return 'a', ''
    start, group_size, count = config
    if start <= operation_index < start + group_size * count:
        item = (operation_index - start) // group_size
        return 'a reveal', f' data-reveal="{item}"'
    return 'a', ''

def qr_badge_html(pages_url, left_px=70.4, top_px=440.0, lang='en'):
    clean_url = pages_url.strip()
    if not clean_url:
        return ''
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=2,
    )
    qr.add_data(clean_url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    cmds = ''.join(
        f'M{x},{y}h1v1h-1z'
        for y, row in enumerate(matrix)
        for x, cell in enumerate(row)
        if cell
    )
    display_url = re.sub(r'^https?://', '', clean_url).rstrip('/')
    kicker = ZH_TEXT_MAP.get('SCAN FOR LIVE SLIDES & DEMO', 'SCAN FOR LIVE SLIDES & DEMO') if lang == 'zh' else 'SCAN FOR LIVE SLIDES & DEMO'
    svg = (
        f'<svg class="pages-qr-svg" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {n} {n}" shape-rendering="crispEdges" role="img" '
        f'aria-label="QR code for {e(clean_url)}">'
        f'<rect width="{n}" height="{n}" fill="#FFFFFF"/>'
        f'<path d="{cmds}" fill="#1E242B"/></svg>'
    )
    return (
        f'<a class="a pages-qr-card" style="left:{left_px:.1f}px;top:{top_px:.1f}px;" '
        f'href="{e(clean_url)}" target="_blank" rel="noreferrer">'
        f'{svg}'
        f'<span class="pages-qr-meta">'
        f'<span class="pages-qr-kicker">{e(kicker)}</span>'
        f'<strong class="pages-qr-url">{e(display_url)}</strong>'
        f'</span></a>'
    )

def slide_html(k, ops, img_dir, maxw, pages_url=None, lang='en'):
    parts = []
    for operation_index, o in enumerate(ops):
        classes, reveal = reveal_attrs(k, operation_index)
        if o['op'] == 'add_image':
            is_full = o['x'] == 0 and o['y'] == 0 and o['cx'] == D.W and o['cy'] == D.H
            is_side = o['y'] == 0 and o['cy'] == D.H
            fit_mode = o.get('fit', 'cover')
            if fit_mode == 'contain':
                extra_cls = ' contain-img'
            else:
                extra_cls = ' bleed' if (is_full or is_side) else ' framed-img'
            src = data_uri(os.path.join(img_dir, os.path.basename(o['path'])), maxw)
            parts.append(f'<img class="{classes}{extra_cls}"{reveal} style="{box(o)}" src="{src}" alt="{e(o.get("altText",""))}">')
        elif o['op'] == 'add_text_box':
            fn_cls = ' page-num' if o.get('name') == 'footer_num' else ''
            parts.append(f'<div class="{classes}{fn_cls}"{reveal} style="{box(o)}">{text_html(o)}</div>')
        elif o['op'] == 'add_shape':
            pr = o['preset']
            inner = text_html(o) if 'text' in o else ''
            if pr in SVG_POINTS:
                stroke = f' stroke="#{o["line"]}" stroke-width="{max(1.2,o.get("lineWidth",12700)/PX):.1f}" stroke-linejoin="round"' if o.get('line') else ''
                svg = (
                    '<svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
                    f'<polygon points="{SVG_POINTS[pr]}" fill="#{o["fill"]}"{stroke}/></svg>'
                )
                parts.append(f'<div class="{classes} svg-shape"{reveal} style="{box(o)}">{svg}{inner}</div>')
            else:
                fill = o['fill']
                is_card = pr == 'rect' and o['cx'] > 900000 and o['cy'] > 450000
                extra_cls = ' surface-card' if is_card else ''
                if is_card and fill == D.CODEBG:
                    extra_cls += ' surface-code'
                st = box(o) + f"background:#{fill};"
                if pr == 'ellipse':
                    st += 'border-radius:50%;'
                elif pr == 'roundRect':
                    st += 'border-radius:999px;'
                elif is_card:
                    st += 'border-radius:14px;'
                if o.get('line'):
                    lw = max(1.2, o.get('lineWidth', 12700) / PX)
                    st += f"box-shadow:inset 0 0 0 {lw:.1f}px #{o['line']}, 0 8px 24px rgba(32,28,22,.05);"
                parts.append(f'<div class="{classes}{extra_cls}"{reveal} style="{st}">{inner}</div>')
    reveal_count = REVEAL_ITEMS[k][2] if k in REVEAL_ITEMS else 0
    action = ''
    launchers = ZH_DEMO_LAUNCHERS if lang == 'zh' else DEMO_LAUNCHERS
    if k in launchers:
        demo_kind, demo_step, label = launchers[k]
        action = (
            f'<button class="live-demo-trigger" type="button" '
            f'data-demo="{demo_kind}" data-step="{demo_step}">'
            f'<span class="pulse-dot" aria-hidden="true"></span><span>{e(label)}</span>'
            f'<span class="trigger-arrow" aria-hidden="true">↗</span></button>'
        )
    qr_html = qr_badge_html(pages_url, left_px=70.4, top_px=440.0, lang=lang) if (k == 0 and pages_url) else ''
    slide_lbl = f'第 {k+1} 页' if lang == 'zh' else f'Slide {k+1}'
    return f'<section class="slide" data-n="{k+1}" data-reveals="{reveal_count}" aria-label="{slide_lbl}">{"".join(parts)}{qr_html}{action}</section>'

def presenter_ui_html(lang='en'):
    if lang == 'zh':
        return """
<div id="deck-hud" class="deck-hud" aria-label="讲者工具栏">
  <span class="hud-count" id="hud-count"></span>
  <button type="button" class="hud-btn" id="hud-notes-btn" title="展开/收起中文讲者备注 (N)" aria-controls="notes-drawer" aria-expanded="false">备注 <kbd>N</kbd></button>
  <button type="button" class="hud-btn hud-btn-accent" id="hud-demo-btn" title="打开可视化路由工作台 (D)">工作台 <kbd>D</kbd></button>
</div>

<aside id="notes-drawer" class="notes-drawer" aria-label="讲者备注" hidden>
  <div class="notes-head">
    <strong id="notes-title" lang="zh-CN">讲者备注</strong>
    <button type="button" class="notes-close" id="notes-close" aria-label="关闭讲者备注">✕</button>
  </div>
  <div class="notes-body" id="notes-body" lang="zh-CN"></div>
</aside>
"""
    return """
<div id="deck-hud" class="deck-hud" aria-label="Presenter toolbar">
  <span class="hud-count" id="hud-count"></span>
  <button type="button" class="hud-btn" id="hud-notes-btn" title="Toggle English speaker notes (N)" aria-controls="notes-drawer" aria-expanded="false">Notes <kbd>N</kbd></button>
  <button type="button" class="hud-btn hud-btn-accent" id="hud-demo-btn" title="Open Visual Auto-Routing Studio (D)">Studio <kbd>D</kbd></button>
</div>

<aside id="notes-drawer" class="notes-drawer" aria-label="Speaker notes" hidden>
  <div class="notes-head">
    <strong id="notes-title" lang="en">Speaker Notes</strong>
    <button type="button" class="notes-close" id="notes-close" aria-label="Close speaker notes">✕</button>
  </div>
  <div class="notes-body" id="notes-body" lang="en"></div>
</aside>
"""

LIVE_DEMO = """
<section id="live-demo" class="live-demo" role="dialog" aria-modal="true" aria-label="Visual Auto-Routing Studio" hidden>
  <div class="studio-shell">
    <header class="studio-top">
      <div class="bar-select-group">
        <div class="custom-select" id="cs-kind" data-value="fusion">
          <button type="button" class="cs-trigger" id="cs-kind-btn" aria-haspopup="listbox" aria-expanded="false" aria-label="Demo">
            <span class="cs-kicker">DEMO</span>
            <span class="cs-label" id="cs-kind-label">Demo 1 · Coding Agent</span>
            <svg class="cs-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <ul class="cs-menu" id="cs-kind-menu" role="listbox" tabindex="-1" hidden>
            <li role="option" data-val="fusion" aria-selected="true" class="cs-option selected">
              <span class="cs-opt-main">Demo 1 · Coding Agent</span>
              <span class="cs-opt-sub">Copilot Fusion &amp; Cache · 4 scenarios / 5 calls</span>
            </li>
            <li role="option" data-val="foundry" aria-selected="false" class="cs-option">
              <span class="cs-opt-main">Demo 2 · Cloud API</span>
              <span class="cs-opt-sub">Foundry Model Router · 4 steps</span>
            </li>
            <li role="option" data-val="decision" aria-selected="false" class="cs-option">
              <span class="cs-opt-main">Demo 3 · App Controller</span>
              <span class="cs-opt-sub">Microsoft-Decision-1.1 · 5 steps</span>
            </li>
          </ul>
        </div>

        <div class="custom-select cs-step-select" id="cs-step" data-value="1">
          <button type="button" class="cs-trigger" id="cs-step-btn" aria-haspopup="listbox" aria-expanded="false" aria-label="Step">
            <span class="cs-kicker cs-kicker-accent">STEP</span>
            <span class="cs-label" id="cs-step-label">1 · Lightweight Single-Model Fast Path</span>
            <svg class="cs-chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <ul class="cs-menu cs-step-menu" id="cs-step-menu" role="listbox" tabindex="-1" hidden></ul>
        </div>

        <button id="live-demo-run" class="primary-run-btn" type="button">
          <span id="live-run-label">Run Step 1</span>
          <span aria-hidden="true">▶</span>
        </button>
        <button id="live-demo-autoplay" class="ghost-btn autoplay-btn" type="button" title="Play all steps sequentially">
          <span id="live-autoplay-label">Auto-Play</span>
        </button>
      </div>

      <div class="studio-status-group">
        <span class="status-badge" id="live-demo-status">Connecting to Demo Server…</span>
        <button id="live-demo-reset" class="ghost-btn" type="button" title="Reset scenario">Reset</button>
        <button id="live-demo-close" class="close-btn" type="button" aria-label="Close studio">✕</button>
      </div>
    </header>

    <div class="purpose-ledger-row">
      <div class="demo-purpose-bar" id="demo-purpose-bar">
        <span class="purpose-kicker" id="purpose-kicker">DEMO 1 GOAL</span>
        <strong id="purpose-title">Coding Agent Orchestration</strong>
        <span class="purpose-sep" aria-hidden="true">—</span>
        <span id="purpose-desc">See how GitHub Copilot Auto &amp; Fusion picks 1 fast model for easy edits, escalates hard bugs via Judge/Critics, and protects warm caches.</span>
      </div>

      <div class="studio-ledger" id="studio-ledger" aria-label="Cumulative cost and latency comparison">
        <div class="ledger-meta">
          <span class="ledger-kicker" id="ledger-kicker">CUMULATIVE LEDGER</span>
          <span class="ledger-count" id="ledger-count">Preview · Step 1</span>
        </div>
        <div class="ledger-bars">
          <div class="lbar-row">
            <span class="lbar-lbl" id="ledger-base-lbl">Pinned Baseline</span>
            <div class="lbar-track"><div class="lbar-fill base" id="ledger-base-bar" style="width:100%"></div></div>
            <span class="lbar-val warn" id="ledger-base-val">0.450 AIU</span>
          </div>
          <div class="lbar-row">
            <span class="lbar-lbl" id="ledger-auto-lbl">Auto-Routed</span>
            <div class="lbar-track"><div class="lbar-fill auto" id="ledger-auto-bar" style="width:12%"></div></div>
            <span class="lbar-val ok" id="ledger-auto-val">0.055 AIU</span>
          </div>
        </div>
        <span class="ledger-delta" id="ledger-delta">-88% Cost</span>
      </div>
    </div>

    <div class="studio-grid">
      <section class="terminal-card">
        <div class="terminal-chrome">
          <div class="chrome-dots" aria-hidden="true"><span></span><span></span><span></span></div>
          <div class="chrome-title">
            <strong id="terminal-mode-title">GitHub Copilot CLI · Auto &amp; Fusion</strong>
            <span id="terminal-mode-sub">SINGLE · NO REVIEW OVERHEAD</span>
          </div>
          <span class="visual-kind-pill" id="visual-kind-pill">CODE DIFF &amp; REVIEW</span>
          <div class="term-legend" id="term-legend" aria-label="Color legend" style="display:none">
            <span class="lg-item lg-pol">Config</span>
            <span class="lg-item lg-run">Request</span>
            <span class="lg-item lg-ok">✓ Pass</span>
            <span class="lg-item lg-err">✕ Hold</span>
            <span class="lg-item lg-src">Source</span>
          </div>
          <div class="term-view-switch" role="group" aria-label="Workbench view mode">
            <button type="button" class="tview-btn active" id="btn-view-visual" title="Interactive Diff, Review &amp; Smart Inbox view">✦ Visual</button>
            <button type="button" class="tview-btn" id="btn-view-summary">Summary</button>
            <button type="button" class="tview-btn" id="btn-view-raw" title="Inspect the current step's verbatim CLI JSONL / HTTP JSON and provenance">{ } Raw Log</button>
          </div>
        </div>

        <div class="route-strip" id="vis-nodes" aria-label="Routing flow"></div>

        <div class="visual-stage" id="live-visual-stage" role="region" aria-label="Visual routing workbench"></div>

        <pre class="studio-terminal" id="live-demo-output" role="log" aria-live="polite" hidden></pre>

        <form class="probe-form" id="live-probe-form">
          <span class="composer-prompt">route&gt;</span>
          <input id="live-probe-input" type="text" placeholder="Test any custom prompt or draft reply live (e.g. &quot;Thanks!&quot;, &quot;Fix Rust ABA race&quot;, &quot;Try rival Fabrikam for $749&quot;)..." autocomplete="off">
          <button type="submit" id="live-probe-send">Route ▶</button>
        </form>
      </section>

      <aside class="value-rail">
        <article class="narrative-card" id="narrative-card">
          <div class="narrative-top">
            <span class="step-badge" id="explain-step-badge">STEP 1 / 5</span>
            <span class="boundary-tag" id="explain-boundary-tag">HyDRA Shortfall Match</span>
          </div>
          <h3 id="explain-title">Lightweight Single-Model Fast Path</h3>
          <p class="explain-summary" id="explain-what"></p>
          <div class="explain-code-wrap">
            <div class="policy-kicker">ROUTING RULE / API CALL</div>
            <pre id="explain-code"></pre>
          </div>
        </article>

        <section class="compare-card">
          <div class="section-head">
            <strong id="compare-heading">Payoff vs. Naive Baseline</strong>
            <span id="compare-sub">Cost, latency &amp; safety</span>
          </div>
          <div class="identity-versus">
            <div class="id-box host">
              <div class="id-role" id="base-role-label">WITHOUT ROUTING</div>
              <div class="id-name" id="live-host-user">Always Opus 5.5</div>
              <div class="id-nums" id="live-host-nums">$0.140 · 4.8 s</div>
              <div class="id-meta" id="live-host-session">Pays frontier price on trivial lookup</div>
            </div>
            <div class="vs-medallion" aria-hidden="true">→</div>
            <div class="id-box agent">
              <div class="id-role" id="agent-role-label">WITH AUTO-ROUTING</div>
              <div class="id-name" id="live-agent-user">MAI Code 2 Flash</div>
              <div class="id-nums agent-nums" id="live-agent-nums">$0.0008 · 1.8 s</div>
              <div class="id-meta" id="live-agent-session">0.08 AI Credits · Single pass</div>
            </div>
          </div>
          <div class="evidence-chips">
            <span class="ev-chip on" id="live-chip-1">Cost: -94% cr ✓</span>
            <span class="ev-chip on" id="live-chip-2">Speed: 2.7× faster ✓</span>
            <span class="ev-chip on" id="live-chip-3">Pattern: Single ✓</span>
          </div>
        </section>
      </aside>
    </div>
  </div>
</section>
"""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inconsolata:wdth,wght@50..200,500..700&family=Inter+Tight:ital,wght@0,400..800;1,400..600&display=swap');
:root{
  --bg:#%s;--ink:#%s;--accent:#%s;--card:#%s;--codebg:#%s;--edge:#%s;--muted:#%s;--warn:#%s;
  --surface:#fbf8f2;--surface-strong:#efe9dc;--ink-soft:#4a463f;--ok:#1f6344;--ok-bg:#e6f4ec;
  --font-sans:'Inter Tight','Segoe UI Variable Text','PingFang SC','Microsoft YaHei UI',system-ui,sans-serif;
  --font-display:'Inter Tight','Segoe UI Variable Display','PingFang SC','Microsoft YaHei UI',system-ui,sans-serif;
  --font-mono:'Inconsolata','Consolas','Cascadia Mono',monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%%;height:100%%;background:var(--bg);color:var(--ink);font-family:var(--font-sans);letter-spacing:-0.006em;overflow:hidden;overscroll-behavior:none;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
code,pre,kbd,.pages-qr-kicker,.pages-qr-url{font-variation-settings:"wdth" 90}
#stage{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;overflow:hidden;background:radial-gradient(circle at 18%% 12%%,rgba(255,255,255,.55),transparent 48%%),var(--bg)}
.slide{position:absolute;width:1280px;height:720px;background:linear-gradient(180deg,rgba(255,255,255,.28) 0%%,rgba(255,255,255,0) 38%%),var(--bg);overflow:hidden;display:none;transform-origin:center center}
.slide.on{display:block;animation:slideFade .24s cubic-bezier(.2,.8,.2,1)}
@keyframes slideFade{from{opacity:.88}to{opacity:1}}
.a{position:absolute}
.surface-card{box-shadow:0 10px 28px rgba(38,33,26,.055),inset 0 1px 0 rgba(255,255,255,.55)}
.surface-code{border-radius:14px;box-shadow:0 12px 30px rgba(32,45,58,.06),inset 0 1px 0 rgba(255,255,255,.8)}
.framed-img{border-radius:14px;box-shadow:0 14px 34px rgba(35,30,22,.10);object-fit:cover}
.contain-img{border-radius:10px;object-fit:contain!important}
.reveal{opacity:0;visibility:hidden;transform:translateY(10px);transition:opacity .28s ease,transform .28s cubic-bezier(.2,.8,.2,1),visibility .28s}
.reveal.shown{opacity:1;visibility:visible;transform:translateY(0)}
.svg-shape svg{position:absolute;inset:0;width:100%%;height:100%%;overflow:visible;filter:drop-shadow(0 4px 10px rgba(35,48,62,.08))}
.svg-shape>.t{z-index:1}
img.a{object-fit:cover}
.t{position:absolute;inset:0;padding:10px 14px;display:flex;flex-direction:column;justify-content:center}
.a[style*="border-radius:50%%"]>.t{padding:0;align-items:center;text-align:center}
.page-num{z-index:6}.page-num>.t{padding:2px 8px;align-items:flex-end}.page-num>.t>p{background:rgba(243,238,228,.82);padding:2px 7px;border-radius:999px}
.lang-switch{position:fixed;left:12px;bottom:10px;z-index:46;display:inline-flex;align-items:center;gap:2px;padding:3px;border-radius:999px;background:rgba(251,248,242,.86);backdrop-filter:blur(8px);border:1px solid rgba(201,192,174,.78);box-shadow:0 4px 14px rgba(35,30,22,.07);opacity:.55;transition:opacity .18s ease}
.lang-switch:hover,.lang-switch:focus-within{opacity:1}
.lang-pill{border:0;background:transparent;color:var(--muted);text-decoration:none;border-radius:999px;padding:4px 9px;font:700 10.5px/1 var(--font-mono);letter-spacing:.03em;cursor:pointer;transition:background .14s,color .14s}
.lang-pill:hover{color:var(--ink)}
.lang-pill.active{background:var(--accent);color:#fff;pointer-events:none}
.ref-link{color:inherit;text-decoration:underline;text-decoration-color:rgba(63,96,126,.42);text-underline-offset:3px;transition:color .14s ease,text-decoration-color .14s ease}
.ref-link:hover{color:#1f384e;text-decoration-color:currentColor}
.pages-qr-card{display:inline-flex;align-items:center;gap:18px;padding:12px 22px 12px 12px;border-radius:16px;background:rgba(251,248,242,.95);border:1.5px solid var(--edge);box-shadow:0 12px 32px rgba(35,30,22,.09);text-decoration:none;color:var(--ink);transition:transform .16s ease,border-color .16s ease,box-shadow .16s ease;z-index:5}
.pages-qr-card:hover{transform:translateY(-1px);border-color:var(--accent);box-shadow:0 16px 36px rgba(35,30,22,.13)}
.pages-qr-svg{width:176px;height:176px;border-radius:10px;border:1px solid rgba(201,192,174,.75);flex-shrink:0;display:block;background:#fff}
.pages-qr-meta{display:flex;flex-direction:column;gap:7px;min-width:0;max-width:280px}
.pages-qr-kicker{font:700 11.5px/1.2 var(--font-mono);letter-spacing:.07em;color:var(--accent)}
.pages-qr-url{font:700 15.5px/1.3 var(--font-mono);color:var(--ink);word-break:break-all}

#deck-progress{position:fixed;left:0;top:0;height:3px;width:0;z-index:40;background:linear-gradient(90deg,var(--accent),#5d8aa8);transition:width .25s ease;pointer-events:none}

.deck-hud{position:fixed;left:50%%;bottom:8px;transform:translateX(-50%%);z-index:45;display:inline-flex;align-items:center;gap:6px;padding:3px 7px;border-radius:999px;background:rgba(251,248,242,.82);backdrop-filter:blur(8px);border:1px solid rgba(201,192,174,.75);box-shadow:0 4px 14px rgba(35,30,22,.07);opacity:.38;transition:opacity .18s ease}
.deck-hud:hover,.deck-hud:focus-within,.deck-hud.notes-open{opacity:1}
.hud-count{font:700 10.5px/1 var(--font-mono);color:var(--muted);padding:0 5px}
.hud-btn{border:1px solid var(--edge);background:#fff;color:var(--ink);border-radius:999px;padding:4px 9px;font:600 11px/1 var(--font-sans);cursor:pointer;display:inline-flex;align-items:center;gap:4px}
.hud-btn:hover{border-color:var(--accent);color:var(--accent)}
.hud-btn-accent{background:var(--accent);border-color:var(--accent);color:#fff}
.hud-btn-accent:hover{color:#fff;filter:brightness(1.08)}
.hud-btn kbd{font:700 9.5px/1 var(--font-mono);opacity:.8}

.notes-drawer{position:fixed;left:50%%;bottom:42px;transform:translateX(-50%%);width:min(640px,calc(100vw - 28px));max-height:42vh;z-index:55;background:rgba(251,248,242,.97);backdrop-filter:blur(12px);border:1px solid var(--edge);border-top:3px solid var(--accent);border-radius:14px;box-shadow:0 18px 42px rgba(28,24,18,.16);display:flex;flex-direction:column;overflow:hidden}
.notes-drawer[hidden]{display:none!important}
.notes-head{display:flex;align-items:center;justify-content:space-between;padding:9px 14px;border-bottom:1px solid var(--edge);font:700 12.5px/1 var(--font-sans);color:var(--accent)}
.notes-close{border:0;background:transparent;color:var(--muted);font-size:14px;cursor:pointer;padding:2px 6px;border-radius:6px}
.notes-close:hover{background:var(--card);color:var(--ink)}
.notes-body{padding:12px 15px;overflow-y:auto;font:450 13.5px/1.65 var(--font-sans);color:var(--ink);white-space:pre-wrap}

.live-demo-trigger{position:absolute;right:48px;top:48px;z-index:12;display:inline-flex;align-items:center;gap:9px;border:1px solid rgba(255,255,255,.28);border-radius:999px;padding:10px 18px;background:linear-gradient(135deg,var(--accent) 0%%,#2c4963 100%%);color:#fbf8f2;font:600 13px/1 var(--font-sans);letter-spacing:.01em;cursor:pointer;box-shadow:0 10px 26px rgba(44,73,99,.26);transition:transform .18s ease,box-shadow .18s ease,filter .18s ease}
.live-demo-trigger:hover{transform:translateY(-2px);box-shadow:0 14px 32px rgba(44,73,99,.34);filter:brightness(1.05)}
.pulse-dot{width:8px;height:8px;border-radius:50%%;background:#7ee2b8;box-shadow:0 0 0 4px rgba(126,226,184,.24);animation:pulseDot 1.8s infinite}
@keyframes pulseDot{0%%,100%%{box-shadow:0 0 0 3px rgba(126,226,184,.28)}50%%{box-shadow:0 0 0 7px rgba(126,226,184,.06)}}
.trigger-arrow{font-size:14px;opacity:.88}

.live-demo{position:fixed;inset:0;z-index:120;background:radial-gradient(circle at 12%% 0%%,#faf7f0 0%%,var(--bg) 62%%);color:var(--ink);font-family:var(--font-sans);padding:clamp(8px,1.1vw,16px);overflow:hidden}
.live-demo[hidden]{display:none!important}
.studio-shell{width:100%%;height:100%%;max-width:1540px;min-width:0;margin:0 auto;display:grid;grid-template-rows:auto auto minmax(0,1fr);gap:8px;min-height:0}
.studio-top{display:flex;align-items:center;justify-content:space-between;gap:8px;background:var(--surface);border:1px solid var(--edge);border-radius:14px;padding:8px 11px;box-shadow:0 6px 20px rgba(35,30,22,.05);flex-wrap:nowrap;position:relative;z-index:30;min-width:0}
.bar-select-group{display:flex;align-items:center;gap:7px;min-width:0;flex:1}
.studio-status-group{display:flex;align-items:center;gap:7px;flex-shrink:0}
.status-badge{border-radius:999px;padding:6px 11px;font:600 11px/1 var(--font-mono);background:var(--card);color:var(--muted);border:1px solid var(--edge);white-space:nowrap}
.status-badge[data-tone="running"]{background:#fef4ea;border-color:#d48a42;color:#9a5313}
.status-badge[data-tone="ok"]{background:var(--ok-bg);border-color:#286b4b;color:var(--ok)}
.status-badge[data-tone="err"]{background:#faece8;border-color:var(--warn);color:var(--warn)}
.ghost-btn{border:1px solid var(--edge);background:#fff;color:var(--ink);border-radius:9px;padding:8px 13px;font:600 12px/1 var(--font-sans);cursor:pointer;white-space:nowrap;transition:background .14s,border-color .14s}
.ghost-btn:hover,.ghost-btn.active{background:var(--card);border-color:var(--accent);color:var(--accent)}
.close-btn{width:32px;height:32px;border-radius:9px;border:1px solid var(--edge);background:#fff;color:var(--ink);font-size:14px;cursor:pointer;display:grid;place-items:center;transition:all .14s}
.close-btn:hover{background:var(--warn);color:#fff;border-color:var(--warn)}

.custom-select{position:relative;min-width:190px;max-width:265px;flex:1 1 235px}
.cs-step-select{min-width:215px;max-width:340px;flex:1.3 1 290px}
.cs-trigger{width:100%%;display:flex;align-items:center;gap:8px;border:1px solid var(--edge);border-radius:9px;background:#fff;color:var(--ink);padding:6px 10px 6px 7px;font:600 12.5px/1.2 var(--font-sans);cursor:pointer;transition:border-color .16s ease,box-shadow .16s ease}
.cs-step-select .cs-trigger{border-color:rgba(63,96,126,.45)}
.cs-trigger:hover:not(:disabled){border-color:var(--accent);box-shadow:0 3px 10px rgba(63,96,126,.10)}
.cs-trigger[aria-expanded="true"]{border-color:var(--accent);box-shadow:0 0 0 3px rgba(63,96,126,.14)}
.cs-trigger:disabled{opacity:.52;cursor:wait}
.cs-kicker{background:var(--card);color:var(--muted);border-radius:5px;padding:4px 6px;font:800 9px/1 var(--font-mono);letter-spacing:.08em;flex-shrink:0}
.cs-kicker-accent{background:rgba(63,96,126,.13);color:var(--accent)}
.cs-label{flex:1;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cs-chevron{width:14px;height:14px;color:var(--muted);flex-shrink:0;transition:transform .18s ease}
.cs-trigger[aria-expanded="true"] .cs-chevron{transform:rotate(180deg);color:var(--accent)}
.cs-menu{position:absolute;left:0;top:calc(100%% + 6px);min-width:100%%;width:max-content;max-width:410px;max-height:330px;overflow-y:auto;list-style:none;background:#fffdf9;border:1px solid var(--edge);border-radius:11px;padding:5px;box-shadow:0 18px 40px rgba(24,32,40,.16);z-index:80;animation:menuPop .14s cubic-bezier(.2,.8,.2,1)}
.cs-menu[hidden]{display:none!important}
@keyframes menuPop{from{opacity:0;transform:translateY(-4px) scale(.985)}to{opacity:1;transform:translateY(0) scale(1)}}
.cs-option{display:flex;flex-direction:column;gap:2px;padding:8px 10px;border-radius:8px;cursor:pointer;transition:background .12s ease}
.cs-option:hover,.cs-option.focused{background:var(--bg)}
.cs-option.selected{background:rgba(63,96,126,.11)}
.cs-opt-row{display:flex;align-items:center;justify-content:space-between;gap:10px}
.cs-opt-main{font:600 12.5px/1.25 var(--font-sans);color:var(--ink)}
.cs-option.selected .cs-opt-main{color:var(--accent);font-weight:700}
.cs-opt-sub{font:500 10.5px/1.25 var(--font-mono);color:var(--muted)}
.cs-opt-check{font:700 10.5px/1 var(--font-mono);color:#286b4b}
.primary-run-btn{display:inline-flex;align-items:center;gap:7px;border:0;border-radius:9px;background:linear-gradient(135deg,var(--accent) 0%%,#2a455d 100%%);color:#fff;padding:8px 16px;font:700 12.5px/1 var(--font-sans);cursor:pointer;box-shadow:0 5px 14px rgba(44,73,99,.22);white-space:nowrap;transition:transform .14s ease,opacity .14s}
.primary-run-btn:hover:not(:disabled){transform:translateY(-1px)}
.primary-run-btn:disabled{opacity:.52;cursor:wait}
.autoplay-btn.active{background:#fef4ea;border-color:#d48a42;color:#9a5313}

.purpose-ledger-row{display:grid;grid-template-columns:minmax(0,.85fr) minmax(500px,1.15fr);gap:10px;align-items:stretch;min-width:0}
.demo-purpose-bar{display:flex;align-items:center;gap:8px;background:var(--surface);border:1px solid var(--edge);border-left:4px solid var(--accent);border-radius:10px;padding:6px 12px;font-size:12.2px;line-height:1.3;color:var(--ink-soft);min-width:0}
.purpose-kicker{background:rgba(63,96,126,.12);color:var(--accent);border-radius:5px;padding:3px 7px;font:800 9.5px/1 var(--font-mono);letter-spacing:.08em;flex-shrink:0}
.demo-purpose-bar strong{color:var(--ink);font-weight:700;flex-shrink:0}
.purpose-sep{color:var(--muted);flex-shrink:0}
#purpose-desc{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

.studio-ledger{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:10px;background:var(--surface);border:1px solid var(--edge);border-left:4px solid var(--ok);border-radius:10px;padding:5px 11px;min-width:0;box-shadow:0 4px 14px rgba(35,30,22,.04)}
.ledger-meta{display:flex;flex-direction:column;gap:2px;flex-shrink:0}
.ledger-kicker{font:800 8.6px/1 var(--font-mono);letter-spacing:.07em;color:var(--accent)}
.ledger-count{font:700 10px/1.1 var(--font-mono);color:var(--muted);white-space:nowrap}
.ledger-bars{min-width:0;display:flex;flex-direction:column;gap:3px}
.lbar-row{display:grid;grid-template-columns:76px minmax(34px,1fr) max-content;align-items:center;gap:6px;min-width:0}
.lbar-lbl{font:700 9.8px/1 var(--font-sans);color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lbar-track{height:6px;border-radius:999px;background:rgba(140,132,118,.18);overflow:hidden;min-width:0}
.lbar-fill{height:100%%;border-radius:999px;transition:width .36s cubic-bezier(.2,.8,.2,1)}
.lbar-fill.base{background:linear-gradient(90deg,#c9644a,#b54c35)}
.lbar-fill.auto{background:linear-gradient(90deg,#288057,#38a169)}
.lbar-val{font:800 10px/1 var(--font-mono);white-space:nowrap;text-align:right}
.lbar-val.warn{color:var(--warn)}
.lbar-val.ok{color:var(--ok)}
.ledger-delta{background:var(--ok-bg);border:1px solid rgba(40,107,75,.38);color:var(--ok);border-radius:999px;padding:4px 8px;font:800 10px/1 var(--font-mono);white-space:nowrap}

.studio-grid{display:grid;grid-template-columns:minmax(0,1.38fr) minmax(0,.90fr);gap:14px;min-height:0}
.terminal-card{display:flex;flex-direction:column;min-height:0;min-width:0;background:#0d151d;border-radius:14px;border:1px solid #243442;overflow:hidden;box-shadow:0 16px 38px rgba(16,24,32,.20)}
.terminal-chrome{display:flex;align-items:center;gap:9px;padding:9px 13px;background:#15212c;border-bottom:1px solid #233342;color:#b8cad8;font:500 11.5px var(--font-mono);min-width:0;flex-shrink:0}
.chrome-dots{display:flex;gap:6px;flex-shrink:0}.chrome-dots span{width:9px;height:9px;border-radius:50%%;background:#3a4b59}.chrome-dots span:first-child{background:#d46a5e}.chrome-dots span:nth-child(2){background:#deb05b}.chrome-dots span:nth-child(3){background:#5fb384}
.chrome-title{display:flex;align-items:baseline;gap:8px;min-width:0;flex:1;overflow:hidden}.chrome-title strong{color:#f2f7fb;font-weight:600;white-space:nowrap}.chrome-title span{display:none}
.visual-kind-pill{font:700 9.5px/1 var(--font-mono);letter-spacing:.06em;color:#7dd3fc;background:rgba(125,211,252,.12);border:1px solid rgba(125,211,252,.28);padding:4px 8px;border-radius:999px;white-space:nowrap;flex-shrink:0}
.term-legend{display:flex;align-items:center;gap:5px;flex-shrink:0;flex-wrap:wrap}
.lg-item{font:700 9.8px/1 var(--font-mono);padding:3px 7px;border-radius:999px;border:1px solid transparent}
.lg-pol{color:#93c5fd;background:rgba(147,197,253,.12);border-color:rgba(147,197,253,.28)}
.lg-run{color:#fcd34d;background:rgba(252,211,77,.12);border-color:rgba(252,211,77,.28)}
.lg-ok{color:#4ade80;background:rgba(74,222,128,.13);border-color:rgba(74,222,128,.32)}
.lg-err{color:#f87171;background:rgba(248,113,113,.14);border-color:rgba(248,113,113,.34)}
.lg-src{color:#c4b5fd;background:rgba(196,181,253,.12);border-color:rgba(196,181,253,.30)}
.term-view-switch{display:inline-flex;background:#0b1219;border:1px solid #2b3e50;border-radius:8px;padding:2px;gap:2px;flex-shrink:0}
.tview-btn{border:0;background:transparent;color:#94a8ba;padding:4px 8px;border-radius:6px;font:700 10px/1 var(--font-mono);cursor:pointer;white-space:nowrap}
.tview-btn:hover{color:#e2edf7}
.tview-btn.active{background:#2d5d82;color:#fff}

.route-strip{display:flex;align-items:stretch;gap:7px;padding:7px 12px;background:#111b25;border-bottom:1px solid #223241;flex-shrink:0;min-width:0}
.tnode{flex:1 1 0;min-width:0;background:#172431;border:1px solid #293b4d;border-radius:8px;padding:5px 9px;display:flex;flex-direction:column;justify-content:center;gap:1px}
.tnode-role{font:700 8.8px/1 var(--font-mono);letter-spacing:.06em;color:#8fa6b8;text-transform:uppercase}
.tnode-name{font:700 12.5px/1.2 var(--font-sans);color:#eef4f9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tnode-sub{font:500 10px/1.15 var(--font-mono);color:#9fb2c3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tnode[data-state="win"]{background:rgba(34,197,94,.13);border-color:rgba(74,222,128,.45)}
.tnode[data-state="win"] .tnode-name,.tnode[data-state="win"] .tnode-role{color:#4ade80}
.tnode[data-state="active"]{background:rgba(124,196,248,.12);border-color:rgba(124,196,248,.42)}
.tnode[data-state="active"] .tnode-name,.tnode[data-state="active"] .tnode-role{color:#93c5fd}
.tnode[data-state="err"]{background:rgba(239,68,68,.14);border-color:rgba(248,113,113,.45)}
.tnode[data-state="err"] .tnode-name,.tnode[data-state="err"] .tnode-role{color:#f87171}
.tnode[data-state="skip"]{opacity:.52;border-style:dashed}
.tarrow{align-self:center;color:#6c8498;font:700 13px/1 var(--font-mono);flex-shrink:0}

.studio-terminal[hidden],.visual-stage[hidden]{display:none!important}
.studio-terminal{flex:1;min-height:0;overflow:auto;margin:0;padding:14px 16px;color:#cbd5e1;font:450 12.2px/1.56 var(--font-mono);white-space:pre-wrap;word-break:break-word;scrollbar-color:#445a6c #0d151d}

.visual-stage{flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;padding:9px 12px;display:flex;flex-direction:column;gap:7px;background:linear-gradient(180deg,#0e1822 0%%,#0b131b 100%%);scrollbar-color:#445a6c #0d151d}
.vs-state-banner{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:5px 10px;border-radius:8px;font:600 11.2px/1.25 var(--font-sans);border:1px solid #273b4e;background:#13202d;color:#cbd5e1}
.vs-state-banner.done{background:rgba(34,197,94,.12);border-color:rgba(74,222,128,.40);color:#bbf7d0}
.vs-state-banner.hold{background:rgba(248,113,113,.13);border-color:rgba(248,113,113,.45);color:#fecaca}
.vs-state-banner.running{background:rgba(251,191,36,.12);border-color:rgba(251,191,36,.42);color:#fde68a}
.vs-state-pill{font:800 9px/1 var(--font-mono);letter-spacing:.06em;padding:3px 7px;border-radius:999px;background:rgba(255,255,255,.08);color:#f8fafc;white-space:nowrap;flex-shrink:0}

.vs-editor{border:1px solid #263849;border-radius:9px;overflow:hidden;background:#0a1118;flex-shrink:0}
.vs-editor-head{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:5px 10px;background:#14212e;border-bottom:1px solid #243647;font:700 10.8px/1.15 var(--font-mono);color:#93c5fd}
.vs-editor-meta{font:600 9.8px/1 var(--font-mono);color:#94a3b8}
.vs-diff{font:500 11.3px/1.38 var(--font-mono);padding:4px 0;overflow-x:auto}
.dline{display:grid;grid-template-columns:22px minmax(0,1fr);padding:1px 10px;white-space:pre-wrap;word-break:break-word;color:#cbd5e1}
.dline .dsign{color:#64748b;user-select:none;font-weight:700}
.dline.del{background:rgba(239,68,68,.16);color:#fecaca;border-left:3px solid #ef4444;padding-left:7px}
.dline.del .dsign{color:#f87171}
.dline.add{background:rgba(34,197,94,.16);color:#bbf7d0;border-left:3px solid #22c55e;padding-left:7px}
.dline.add .dsign{color:#4ade80}
.dline.PendingAdd{display:none}

.vs-annot{border-radius:9px;padding:7px 10px;border:1px solid #2b4257;background:#12202d;display:flex;flex-direction:column;gap:4px}
.vs-annot.accept{border-color:rgba(74,222,128,.42);background:linear-gradient(180deg,rgba(22,101,52,.22),rgba(18,32,45,.92))}
.vs-annot.critic{border-color:rgba(251,146,60,.48);background:linear-gradient(180deg,rgba(154,52,18,.24),rgba(18,32,45,.92))}
.vs-annot-head{display:flex;align-items:center;justify-content:space-between;gap:8px;font:800 10px/1.15 var(--font-mono);letter-spacing:.04em;color:#7dd3fc}
.vs-annot.accept .vs-annot-head{color:#4ade80}
.vs-annot.critic .vs-annot-head{color:#fdba74}
.vs-annot-body{font:450 11.5px/1.38 var(--font-sans);color:#e2e8f0}
.vs-annot-foot{display:flex;flex-wrap:wrap;gap:5px;margin-top:1px}
.vs-mini-tag{font:700 10px/1 var(--font-mono);padding:3px 8px;border-radius:999px;background:rgba(148,163,184,.14);color:#cbd5e1;border:1px solid rgba(148,163,184,.26)}
.vs-mini-tag.ok{background:rgba(34,197,94,.15);color:#86efac;border-color:rgba(74,222,128,.36)}
.vs-mini-tag.warn{background:rgba(248,113,113,.16);color:#fca5a5;border-color:rgba(248,113,113,.38)}

.vs-cols{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
.vs-cols-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.vs-panel{border:1px solid #253748;border-radius:10px;background:#111c27;padding:9px 11px;display:flex;flex-direction:column;gap:6px;min-width:0}
.vs-panel.win{border-color:rgba(74,222,128,.42);background:rgba(20,83,45,.16)}
.vs-panel.err{border-color:rgba(248,113,113,.45);background:rgba(127,29,29,.18)}
.vs-pkicker{font:800 9.5px/1.1 var(--font-mono);letter-spacing:.06em;color:#93c5fd;text-transform:uppercase}
.vs-panel.win .vs-pkicker{color:#4ade80}
.vs-panel.err .vs-pkicker{color:#fca5a5}
.vs-ptitle{font:700 12.5px/1.25 var(--font-sans);color:#f1f5f9}
.vs-pbody{font:450 11.8px/1.45 var(--font-sans);color:#cbd5e1}
.vs-mono-box{font:500 11px/1.42 var(--font-mono);background:#091017;border:1px solid #223344;border-radius:7px;padding:7px 9px;color:#e2e8f0;white-space:pre-wrap;word-break:break-word}

.vs-meter-list{display:flex;flex-direction:column;gap:6px}
.vs-meter{display:grid;grid-template-columns:138px minmax(50px,1fr) auto;align-items:center;gap:8px;font:600 11px/1.2 var(--font-mono);color:#cbd5e1}
.vs-mtrack{height:7px;border-radius:999px;background:#1b2a38;overflow:hidden}
.vs-mfill{height:100%%;border-radius:999px;background:#60a5fa;transition:width .35s ease}
.vs-mfill.ok{background:#34d399}
.vs-mfill.warn{background:#f87171}
.vs-mfill.muted{background:#64748b}

.vs-inbox{display:flex;flex-direction:column;gap:6px}
.vs-msg-row{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:9px;padding:7px 10px;border-radius:9px;background:#111d29;border:1px solid #243648}
.vs-msg-row.skip{border-left:3px solid #34d399}
.vs-msg-row.escalate{border-left:3px solid #60a5fa}
.vs-msg-row.danger{border-left:3px solid #f87171;background:rgba(127,29,29,.16)}
.vs-msg-txt{font:500 12px/1.35 var(--font-sans);color:#f1f5f9}
.vs-msg-sub{font:500 10.5px/1.2 var(--font-mono);color:#94a3b8;margin-top:2px}
.vs-route-pill{font:800 10px/1 var(--font-mono);padding:4px 8px;border-radius:999px;white-space:nowrap;border:1px solid rgba(148,163,184,.3);color:#e2e8f0;background:#1a2b3c}
.vs-route-pill.ok{color:#86efac;border-color:rgba(74,222,128,.4);background:rgba(22,101,52,.28)}
.vs-route-pill.accent{color:#93c5fd;border-color:rgba(147,197,253,.4);background:rgba(30,64,175,.28)}
.vs-route-pill.warn{color:#fecaca;border-color:rgba(248,113,113,.45);background:rgba(153,27,27,.34)}

.vs-runs-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:6px}
.vs-run-cell{background:#0b131c;border:1px solid rgba(74,222,128,.35);border-radius:8px;padding:7px 6px;text-align:center;display:flex;flex-direction:column;gap:2px}
.vs-run-lbl{font:700 9.5px/1 var(--font-mono);color:#94a3b8}
.vs-run-val{font:800 13px/1.2 var(--font-mono);color:#4ade80}
.vs-run-ms{font:600 9.5px/1 var(--font-mono);color:#cbd5e1}

.hl-danger{background:rgba(239,68,68,.28);color:#fecaca;border-bottom:2px solid #f87171;padding:1px 4px;border-radius:4px;font-weight:700}
.vs-cache-bar{height:14px;border-radius:999px;background:#1e293b;overflow:hidden;display:flex;border:1px solid #334155}
.vs-cache-hit{background:linear-gradient(90deg,#10b981,#34d399);height:100%%}
.vs-cache-new{background:#60a5fa;height:100%%}
.tl{display:block;padding:1px 6px;border-radius:4px}
.tl-hint{color:#94a3b8;font-style:italic}
.tl-step{color:#7cc4f8;font-weight:700;margin-top:10px;padding-top:7px;border-top:1px dashed rgba(124,196,248,.24)}
.tl-step:first-child{margin-top:0;padding-top:1px;border-top:0}
.tl-policy{color:#93c5fd;font-weight:700;margin-top:3px}
.tl-run{color:#fcd34d;font-weight:700;margin-top:3px}
.tl-pass{color:#4ade80;font-weight:700;background:rgba(34,197,94,.13);border-left:3px solid #22c55e;padding:4px 9px;margin:4px 0 2px;border-radius:0 6px 6px 0}
.tl-fail{color:#f87171;font-weight:700;background:rgba(239,68,68,.15);border-left:3px solid #ef4444;padding:4px 9px;margin:4px 0 2px;border-radius:0 6px 6px 0}
.tl-why{color:#fde68a;padding-left:9px;margin-bottom:2px}
.tl-src{color:#c4b5fd;font-size:11px;padding-left:9px;opacity:.92;margin-bottom:2px}
.tl-prov{color:#7dd3fc;font-weight:600}
.tl-log{color:#cbd5e1}

.probe-form{display:flex;align-items:center;gap:8px;padding:9px 14px;background:#121d27;border-top:1px solid #223241;flex-shrink:0}
.composer-prompt{color:#7cc4f8;font:700 11.5px/1 var(--font-mono);flex-shrink:0}
.probe-form input{flex:1;min-width:0;border:1px solid #2a3d4f;border-radius:7px;background:#091017;color:#f3f8fc;padding:7px 10px;font:450 12px/1.2 var(--font-mono);outline:none}
.probe-form input:focus{border-color:#6cb4e8}
.probe-form button{border:0;border-radius:7px;background:#3a7099;color:#fff;padding:7px 13px;font:700 12px/1 var(--font-sans);cursor:pointer;white-space:nowrap}
.probe-form button:hover{filter:brightness(1.08)}

.value-rail{display:flex;flex-direction:column;gap:10px;min-height:0;min-width:0;overflow-y:auto;overflow-x:hidden}
.narrative-card,.compare-card{background:var(--surface);border:1px solid var(--edge);border-radius:14px;padding:12px 15px;box-shadow:0 6px 20px rgba(35,30,22,.04);min-width:0}
.narrative-card{border-top:3px solid var(--accent);display:flex;flex-direction:column;gap:7px}
.narrative-top{display:flex;align-items:center;justify-content:space-between;gap:8px}
.step-badge{background:rgba(63,96,126,.12);color:var(--accent);border-radius:999px;padding:4px 10px;font:800 10px/1 var(--font-mono);letter-spacing:.08em;flex-shrink:0}
.boundary-tag{color:var(--muted);font:600 11px/1 var(--font-mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.narrative-card h3{font:700 17.5px/1.2 var(--font-display);color:var(--ink)}
.explain-summary{color:var(--ink-soft);font-size:13px;line-height:1.45}
.explain-code-wrap{background:var(--codebg);border:1px solid var(--edge);border-radius:9px;padding:7px 10px;margin-top:1px;min-width:0}
.policy-kicker{font:800 9px/1 var(--font-mono);letter-spacing:.08em;color:var(--muted);margin-bottom:4px}
.explain-code-wrap pre{margin:0;font:600 10.8px/1.36 var(--font-mono);color:var(--accent);white-space:pre-wrap;word-break:break-word}

.compare-card{display:flex;flex-direction:column;gap:9px}
.section-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.section-head strong{font:700 13.5px/1.1 var(--font-sans);color:var(--ink)}
.section-head span{font:500 10.5px/1 var(--font-mono);color:var(--muted)}
.identity-versus{display:grid;grid-template-columns:1fr 26px 1fr;gap:8px;align-items:stretch}
.id-box{background:var(--card);border-radius:10px;padding:9px 11px;min-width:0;border-top:3px solid #8c8476;display:flex;flex-direction:column;gap:2px}
.id-box.agent{border-top-color:var(--ok);background:linear-gradient(180deg,#ebf6f0 0%%,var(--card) 100%%)}
.id-role{color:var(--muted);font:700 9px/1 var(--font-mono);letter-spacing:.07em}
.id-name{font:800 14.5px/1.22 var(--font-sans);color:var(--ink);overflow-wrap:anywhere}
.id-nums{font:800 15px/1.2 var(--font-mono);color:var(--warn);margin-top:1px}
.id-nums.agent-nums{color:var(--ok)}
.id-meta{color:var(--muted);font-size:11.5px;line-height:1.3}
.vs-medallion{align-self:center;justify-self:center;width:26px;height:26px;border-radius:50%%;background:var(--accent);color:#fff;font:700 13px/1 var(--font-sans);display:grid;place-items:center}

.evidence-chips{display:flex;gap:7px;flex-wrap:wrap;padding-top:4px;border-top:1px solid var(--edge)}
.ev-chip{border:1px solid var(--edge);border-radius:999px;background:var(--bg);padding:5px 10px;color:var(--muted);font:700 10.5px/1 var(--font-mono);white-space:nowrap}
.ev-chip.on{background:var(--ok-bg);border-color:#286b4b;color:var(--ok)}
.ev-chip.denied{background:#faece8;border-color:var(--warn);color:var(--warn)}

@media(max-width:960px){
  .live-demo{overflow:auto}
  .studio-shell{height:auto}
  .studio-top,.bar-select-group,.demo-purpose-bar{flex-wrap:wrap}
  .purpose-ledger-row,.vs-cols,.vs-cols-3{grid-template-columns:1fr}
  #purpose-desc{white-space:normal}
  .studio-grid{grid-template-columns:1fr;overflow:visible}
  .terminal-card{min-height:360px}
}
@media print{@page{size:13.333in 7.5in;margin:0}
 html,body{overflow:visible;background:#fff}#deck-progress,.deck-hud,.notes-drawer,.live-demo,.live-demo-trigger,.lang-switch{display:none!important}
 #stage{position:static;display:block}.slide{position:relative;display:block!important;transform:none!important;box-shadow:none;page-break-after:always;break-after:page;print-color-adjust:exact;-webkit-print-color-adjust:exact}.reveal{opacity:1!important;visibility:visible!important;transform:none!important}}
"""

DECK_JS = """
(function(){
var S=[].slice.call(document.querySelectorAll('.slide')),i=0,steps=S.map(function(){return 0;});
var bar=document.getElementById('deck-progress');
var deck={S:S,getIndex:function(){return i;},isOverlayOpen:function(){return false;},onRender:null};
window.__DECK__=deck;
function fit(){var v=window.visualViewport,w=v?v.width:innerWidth,h=v?v.height:innerHeight,s=Math.min(w/1280,h/720);S.forEach(function(x){x.style.transform='scale('+s+')';});}
function toggleFullscreen(){if(document.fullscreenElement){document.exitFullscreen();}else if(document.documentElement.requestFullscreen){document.documentElement.requestFullscreen();}}
function renderSteps(){var shown=steps[i];S[i].querySelectorAll('.reveal').forEach(function(x){x.classList.toggle('shown',Number(x.dataset.reveal)<shown);});if(bar)bar.style.width=((i+1)/S.length*100).toFixed(2)+'%';if(deck.onRender)deck.onRender(i,S.length);}
function parseHash(){var h=location.hash.slice(1),m=/^(?:slide-)?(\\d+)$/.exec(h);return m?Number(m[1])-1:0;}
function syncLangLinks(){
 var h='#'+(i+1);
 document.querySelectorAll('a.lang-pill[data-base-href]').forEach(function(a){a.href=a.dataset.baseHref+h;});
}
function go(n){i=Math.max(0,Math.min(S.length-1,n));S.forEach(function(x,j){x.classList.toggle('on',j===i);});renderSteps();if(history.replaceState)history.replaceState(null,'','#'+(i+1));syncLangLinks();}
function next(){var total=Number(S[i].dataset.reveals||0);if(steps[i]<total){steps[i]++;renderSteps();}else{go(i+1);}}
function previous(){if(steps[i]>0){steps[i]--;renderSteps();}else{go(i-1);}}
document.getElementById('stage').addEventListener('click',function(ev){if(deck.isOverlayOpen()||ev.target.closest('button,a'))return;ev.clientX<innerWidth/3?previous():next();});
addEventListener('keydown',function(ev){
 if(ev.defaultPrevented||ev.altKey||ev.ctrlKey||ev.metaKey)return;
 var k=ev.key;
 if(ev.target&&ev.target.closest('input,textarea,select,[contenteditable="true"]')&&k!=='Escape')return;
 if(deck.isOverlayOpen())return;
 if(k===' '&&ev.target&&ev.target.closest('button,a'))return;
 if(k==='ArrowRight'||k==='ArrowDown'||k==='PageDown'||(k===' '&&!ev.shiftKey)){ev.preventDefault();next();}
 else if(k==='ArrowLeft'||k==='ArrowUp'||k==='PageUp'||(k===' '&&ev.shiftKey)){ev.preventDefault();previous();}
 else if(k==='Home'){ev.preventDefault();go(0);}
 else if(k==='End'){ev.preventDefault();go(S.length-1);}
 else if(k==='f'||k==='F'){ev.preventDefault();toggleFullscreen();}});
addEventListener('resize',fit);document.addEventListener('fullscreenchange',fit);if(window.visualViewport)window.visualViewport.addEventListener('resize',fit);
addEventListener('hashchange',function(){var n=parseHash();if(n!==i)go(n);});
fit();go(parseHash());
})();
"""

STUDIO_JS = """
(function(){
var deck=window.__DECK__;if(!deck)return;
var liveOpen=false;
function byId(id){return document.getElementById(id);}
deck.isOverlayOpen=function(){return liveOpen;};
addEventListener('keydown',function(ev){
 if(ev.altKey||ev.ctrlKey||ev.metaKey)return;
 if(liveOpen&&ev.key==='Escape'){
  ev.preventDefault();
  if(document.querySelector('.cs-menu:not([hidden])')){closeAllSelects();return;}
  closeLiveDemo();
 }
},true);

var SCENARIOS={
 fusion:{
  ledgerSave:'-64% Credits',
  steps:[
    {short:'① Single',boundary:'Fusion Single Pattern',title:'Fusion High: Picks pattern="single" on Routine Patch',
    ctx:'copilot --model fusion --fusion-tier high (1 CLI call)',
    prompt:'"Fix greetingFormatter() in format.mjs to trim tabs & Unicode NBSP (\\u00A0)"',
    scorer:'session.fusion_resolved · pattern="single" · router 456 ms',
    bars:[],
    pattern:'FUSION HIGH · PATTERN = SINGLE',
    nodes:[
     {role:'fusion_resolved',name:'pattern = "single"',sub:'reason=0.231 · code=0.231',state:'active'},
     {role:'Primary Solver',name:'gpt-6.1-terra',sub:'3/3 node --test PASS',state:'win'},
     {role:'Judge / Critic',name:'phasePlan: []',sub:'Skipped when unwarranted',state:'skip'}
    ],
    outcome:'✓ One --model fusion --fusion-tier high call selected pattern="single" (gpt-6.1-terra) & passed 3/3 node --test!',
    what:'Even on Fusion High, Copilot Fusion checks 4D capability scores first and picks pattern="single" (phasePlan: []) when 1 solver is sufficient.',
    code:'copilot --model fusion --fusion-tier high -p "Fix format.mjs..." → pattern:"single", primary:"gpt-6.1-terra"',
    baseName:'Blind Multi-Agent',baseNums:'2–3× Calls Always',baseMeta:'Wastes Judge/Critic tokens on routine fixes',
    agentName:'gpt-6.1-terra (Single)',agentNums:'pattern: single · 3/3 PASS',agentMeta:'1 CLI call · 0 review calls',
    chips:[['Pattern: single ✓','on'],['3/3 Tests PASS ✓','on'],['Credits: 1.195 cr ✓','on']],risk:0},
   {short:'② Cascade',boundary:'Native 1-Call Cascade',title:'Fusion High: Native pattern="cascade" (Solver + Judge)',
    ctx:'copilot --model fusion --fusion-tier high (1 CLI call on token-bucket.ts)',
    prompt:'"Fix the ABBA lock-order inversion deadlock in TokenBucket when refill() races with close()"',
    scorer:'session.fusion_resolved · pattern="cascade" · [primary → judge → repair?]',
    bars:[],
    pattern:'FUSION HIGH · NATIVE CASCADE',
    nodes:[
     {role:'1 · Primary Solver',name:'gpt-6.1-sol',sub:'stateLock → drainLock',state:'active'},
     {role:'2 · Native Judge',name:'gpt-6-luna',sub:'score=5/5 · verdict="accept"',state:'win'},
     {role:'3 · Repair (Cond.)',name:'claude-opus-5.5',sub:'SKIPPED (phaseCount=2)',state:'skip'}
    ],
    outcome:'✓ Single CLI call ran Cascade natively: gpt-6.1-sol fixed lock order, gpt-6-luna Judge accepted (5/5), and Opus 5.5 repair was skipped!',
    what:'One copilot --model fusion --fusion-tier high command orchestrates Solver (gpt-6.1-sol) + Judge (gpt-6-luna) server-side, skipping conditional Opus 5.5 repair when Judge returns verdict="accept".',
    code:'copilot --model fusion --fusion-tier high → pattern:"cascade" [gpt-6.1-sol → judge:gpt-6-luna(accept) → repair:skipped]',
    baseName:'Unreviewed Single Pass',baseNums:'Race Risk / Full Opus',baseMeta:'Either skips concurrency review or pays full Opus up front',
    agentName:'gpt-6.1-sol + gpt-6-luna',agentNums:'Native Cascade · 2.651 cr',agentMeta:'1 CLI call · Opus repair skipped',
    chips:[['Pattern: cascade ✓','on'],['Judge: ACCEPT (5/5) ✓','on'],['500× Stress PASS ✓','on']],risk:0},
   {short:'③ Critique',boundary:'Native 1-Call Critique',title:'Fusion High: Native pattern="critique" (Draft → Critic → Revise)',
    ctx:'copilot --model fusion --fusion-tier high (1 CLI call · 50k RPS payment RFC)',
    prompt:'"Write architectural RFC comparing active-active vs active-passive failover for a 50k RPS payment gateway"',
    scorer:'session.fusion_resolved · pattern="critique" · [draft → critic → revision]',
    bars:[],
    pattern:'FUSION HIGH · NATIVE CRITIQUE',
    nodes:[
     {role:'1 · Primary Draft',name:'claude-opus-5.5',sub:'medium effort RFC draft',state:'active'},
     {role:'2 · Cross-Lab Critic',name:'gpt-6-luna',sub:'assessment="revise" (RPO gap)',state:'err'},
     {role:'3 · Handoff Revision',name:'claude-opus-5.5',sub:'high effort · 7,917 cached tok',state:'win'}
    ],
    outcome:'✓ Single CLI call ran Critique natively: gpt-6-luna Critic caught an Active-Active zero-RPO durability flaw, and Opus 5.5 revised!',
    what:'On high-stakes architecture prompts, one --model fusion --fusion-tier high call drafts on Opus 5.5, critiques on cross-family GPT-6 Luna, and hands off via session.fusion_handoff for a high-effort Opus 5.5 revision.',
    code:'copilot --model fusion --fusion-tier high → pattern:"critique" [opus-5.5(draft) → luna(revise) → opus-5.5(revision)]',
    baseName:'Single-Model Draft',baseNums:'Zero-RPO Blind Spot ✕',baseMeta:'Conflates writer fencing with cross-region commit durability',
    agentName:'claude-opus-5.5 + gpt-6-luna',agentNums:'Native Critique · 3 phases',agentMeta:'1 CLI call · Cross-lab review',
    chips:[['Pattern: critique ✓','on'],['Critic: revise ✕','denied'],['Phases: 3 run ✓','on']],risk:1},
   {short:'④ Cache',boundary:'Warm Prefix Retention',title:'Prefix-Cache Guard: 99% Cache Hit via --resume',
    ctx:'warm-up + copilot --model auto --resume <sid> (2 real CLI calls on first run)',
    prompt:'"Output two Prometheus metric lines (# TYPE ...) for demo_http_requests_total and demo_port_info"',
    scorer:'Copilot CLI --resume <session_id> · cacheReadTokens vs inputTokens',
    bars:[],
    pattern:'CACHE AFFINITY · 99% PREFIX HIT',
    nodes:[
     {role:'Resumed Session',name:'5,655 / 5,733 Tok',sub:'99% cacheReadTokens hit!',state:'active'},
     {role:'Cold Model Switch',name:'Avoided',sub:'Preserves 30m cache TTL ✓',state:'skip'},
     {role:'Retained Model',name:'GPT-6 Luna (Warm)',sub:'0.024 AIU · 7.5 s',state:'win'}
    ],
    outcome:'✓ Resumed warm GPT-6 Luna session with 99% prefix cache hit (5,655 / 5,733 tokens, 0.024 AIU)!',
    what:'usage.json exposes exact cacheReadTokens and cacheExpiresAt. Keeping the session model on follow-up turns reuses 99% of prompt tokens instead of paying full prefill on a cold model.',
    code:'copilot --model auto --resume <sid> → cacheReadTokens=5,655 / 5,733 (99% hit · 0.024 AIU)',
    baseName:'Cold Mid-Turn Switch',baseNums:'0% Cache · Full Price',baseMeta:'Invalidates warm prefix & re-prefills full context',
    agentName:'GPT-6 Luna (Warm)',agentNums:'99% Hit · 0.024 AIU',agentMeta:'warm-up + resumed follow-up',
    chips:[['Cache Hit: 99% ✓','on'],['Delta: 0.024 cr ✓','on'],['Model Retained ✓','on']],risk:0}
  ]
 },
 foundry:{
  ledgerSave:'-76% + Cache Retain',
  steps:[
   {short:'① Gates',boundary:'Pre-Rank + Param Adapt',title:'Eligibility Gate & Cross-Provider Param Normalization',
    ctx:'POST /openai/v1/chat/completions · ModelRouterControls=V1Preview',
    prompt:'role="developer" + temperature=0.2 + response_format=json_object',
    scorer:'Microsoft Foundry Model Router · Live HTTP 200 Trace',
    bars:[],
    pattern:'PRE-RANK GATE · PARAM NORMALIZATION',
    nodes:[
     {role:'1 · Request Gate',name:'json_object + temp',sub:'developer role normalized',state:'active'},
     {role:'2 · ML Router',name:'30 ms Overhead',sub:'mode: "balanced"',state:'active'},
     {role:'3 · Selected Model',name:'gpt-5.6-luna',sub:'{"status":"eligible_ok"} ✓',state:'win'}
    ],
    outcome:'✓ Live HTTP 200 OK served by gpt-5.6-luna-2026-07-09 in 30 ms router latency with valid json_object output!',
    what:'Foundry filters deployments by required capabilities (tools / json_object) before ranking, adapts cross-provider parameters automatically, and drains pre-paid PTU capacity first.',
    code:'POST /openai/v1/chat/completions (ModelRouterControls=V1Preview) → gpt-5.6-luna (router=30 ms)',
    baseName:'Manual Multi-SDK',baseNums:'400 Param Errors ✕',baseMeta:'Breaks on role/temperature differences across labs',
    agentName:'gpt-5.6-luna',agentNums:'30 ms Router · 200 OK',agentMeta:'JSON mode & params normalized',
    chips:[['JSON Mode ✓','on'],['Params Normalized ✓','on'],['Router: 30 ms ✓','on']],risk:0},
   {short:'② Flash',boundary:'1–2% Balanced Band',title:'Simple JSON Extraction Routed to DeepSeek Flash in 27 ms',
    ctx:'POST /openai/v1/chat/completions · mode: "balanced"',
    prompt:'"Extract invoice_id and currency as JSON from: Invoice INV-2026-8841, Total: 4,250 EUR"',
    scorer:'Foundry ML Ranker · 27 ms Overhead · 0 Reasoning Tokens',
    bars:[],
    pattern:'BALANCED BAND · CHEAPEST IN TOP 1–2%',
    nodes:[
     {role:'ML Ranker',name:'27 ms Overhead',sub:'Top 1–2% quality band',state:'active'},
     {role:'Selected Model',name:'DeepSeek-V4.1-Flash',sub:'reasoning_tokens = 0',state:'win'},
     {role:'JSON Output',name:'Valid 200 OK',sub:'{"invoice_id":"INV-2026-8841"}',state:'win'}
    ],
    outcome:'✓ Live Foundry Router picked DeepSeek-V4.1-Flash in 27 ms with 0 wasted reasoning tokens!',
    what:'For straightforward JSON extraction, DeepSeek-V4.1-Flash scores within 1–2% of frontier quality — so Balanced mode selects it automatically at a fraction of frontier cost.',
    code:'routing_trace: [{ latency_ms: 27, attempts: [{ model: "DeepSeek-V4.1-Flash", status: 200 }] }]',
    baseName:'Pinned Frontier',baseNums:'~25× Token Cost',baseMeta:'Burns frontier reasoning tokens on simple JSON',
    agentName:'DeepSeek-V4.1-Flash',agentNums:'27 ms Router · 0 Reason',agentMeta:'Valid JSON · HTTP 200 OK',
    chips:[['Router: 27 ms ✓','on'],['JSON Valid ✓','on'],['0 Reason Tok ✓','on']],risk:0},
   {short:'③ Escalate',boundary:'Difficulty Escalation + Affinity',title:'Same Endpoint Escalates Rust Proof & Retains Session',
    ctx:'Same endpoint · mode="balanced" · session_affinity="adaptive"',
    prompt:'"Design lock-free MPMC ring buffer in Rust with Acquire/Release & ABA epoch invariants" (+ Turn 2)',
    scorer:'Foundry ML Ranker (30 ms) + Adaptive Fingerprint Session Affinity',
    bars:[],
    pattern:'AUTO ESCALATION + RETAIN AFFINITY',
    nodes:[
     {role:'Turn 1 Ranker',name:'30 ms Escalation',sub:'Flash drops below band',state:'active'},
     {role:'Selected Model',name:'gpt-6-luna',sub:'gpt-6-luna-2026-09-22',state:'win'},
     {role:'Turn 2 Affinity',name:'decision: "retain"',sub:'derived_fingerprint matched',state:'win'}
    ],
    outcome:'✓ Escalated Turn 1 to gpt-6-luna-2026-09-22 (30 ms router) and returned session_affinity="retain" on Turn 2!',
    what:'Without changing endpoint or code, formal concurrency proofs trigger automatic escalation to gpt-6-luna, and Turn 2 retains the same model via derived_fingerprint.',
    code:'Turn 1 → gpt-6-luna (30 ms)  |  Turn 2 → session_affinity: { decision: "retain" }',
    baseName:'Pinned Cheap Flash',baseNums:'Missed ABA Invariant ✕',baseMeta:'Under-powered on formal memory-ordering proofs',
    agentName:'gpt-6-luna',agentNums:'30 ms · Affinity: retain',agentMeta:'2-turn live escalation + cache affinity',
    chips:[['Router: 30 ms ✓','on'],['Affinity: retain ✓','on'],['2-Turn Live ✓','on']],risk:1},
   {short:'④ Cost→Quality',boundary:'Two-Stage Sub-Job Routing',title:'Two-Stage Routing: mode="cost" Extraction → mode="quality" Strategy',
    ctx:'2 live calls on fixtures/renewal-context.json',
    prompt:'Job 1 (mode="cost"): Extract renewal numbers → Job 2 (mode="quality"): Game-theoretic NRR strategy',
    scorer:'Foundry Model Router · Per-Step Mode Selection on One Endpoint',
    bars:[],
    pattern:'TWO-STAGE ROUTING · COST → QUALITY',
    nodes:[
     {role:'Job 1 · mode="cost"',name:'grok-4-1-fast',sub:'28 ms route · fast extraction',state:'active'},
     {role:'Structured Handoff',name:'2 Compact Bullets',sub:'Trimmed context passed on',state:'active'},
     {role:'Job 2 · mode="quality"',name:'gpt-5.6-terra',sub:'29 ms route · NRR strategy',state:'win'}
    ],
    outcome:'✓ Live 2-call pipeline routed extraction to grok-4-1-fast-reasoning (mode="cost") and strategy to gpt-5.6-terra (mode="quality")!',
    what:'Instead of running an entire multi-step workflow on one expensive model, each sub-job passes its own routing_config.mode ("cost" vs "quality") to the same Foundry endpoint.',
    code:'Job 1 (mode:"cost") → grok-4-1-fast-reasoning  |  Job 2 (mode:"quality") → gpt-5.6-terra',
    baseName:'Monolithic Frontier Call',baseNums:'High Cost on Raw Docs',baseMeta:'Feeds raw unstructured JSON straight to top tier',
    agentName:'grok-4-1 → gpt-5.6-terra',agentNums:'28 ms + 29 ms Route',agentMeta:'Multi-Job Cost + Quality',
    chips:[['Job 1: grok-4-1-fast ✓','on'],['Job 2: gpt-5.6-terra ✓','on'],['Live Multi-Job ✓','on']],risk:0}
  ]
 },
 decision:{
  ledgerSave:'7.2× Lower CAC ($1.81)',
  steps:[
   {short:'① 0.0 Spread',boundary:'Calibrated System-One',title:'5× Live Repeat Probe: 0.9835 with 0.00 pt Spread',
    ctx:'POST /providers/microsoft/v1/systemone · $0.042/1M in · $0 out',
    prompt:'"Is the Harbor sectional still 15% off? We’d love it before my in-laws visit on the 20th."',
    scorer:'Live Microsoft-Decision-1.1 · 5 Consecutive Cloud Calls',
    bars:[],
    pattern:'NOUL PRIMITIVE · ZERO VARIANCE',
    nodes:[
     {role:'Customer Message',name:'Purchase Timeline',sub:'"before the 20th"',state:'active'},
     {role:'5× Live /systemone',name:'noul = 0.9835',sub:'0.00 pt spread · p50 353 ms',state:'win'},
     {role:'Deterministic Gate',name:'routeToSales()',sub:'54 in tok · $0 out charge',state:'win'}
    ],
    outcome:'✓ 5 consecutive live /v1/systemone calls returned 0.9835 every single time (0.00 pt spread, p50=353 ms)!',
    what:'Unlike generative LLM judges that drift across runs and bill for output prose, Decision-1.1 returns deterministic calibrated probabilities in a single forward pass.',
    code:'POST /providers/microsoft/v1/systemone → answers.ready_to_buy.noul = 0.9835 (5/5 identical)',
    baseName:'Generative LLM Judge',baseNums:'$0.0045 · ~1,450 ms',baseMeta:'340× pricier + non-deterministic prose',
    agentName:'noul = 0.9835',agentNums:'0.0 pt spread · 353 ms',agentMeta:'5/5 live HTTP · $0 output fee',
    chips:[['Spread: 0.0 pt ✓','on'],['p50: 353 ms ✓','on'],['5/5 Live HTTP ✓','on']],risk:0},
   {short:'② Router',boundary:'Pre-LLM Inbox Filter',title:'Check 1 (choice): 4/4 Live Inbox Triage (3/4 Skip Frontier)',
    ctx:'4 live /v1/systemone calls · 4 handler tiers',
    prompt:'"Thanks! 👍" | "STOP" | "15% spring promo on Aspen king?" | "Compare sofa warranty..."',
    scorer:'Live Microsoft-Decision-1.1 · type: "choice" (~338 ms/call)',
    bars:[],
    pattern:'CHOICE ROUTER · 75% SKIP FRONTIER',
    nodes:[
     {role:'4 Live Messages',name:'p = 1.00 Confidence',sub:'~338 ms per HTTP call',state:'active'},
     {role:'3/4 Short-Circuit',name:'no_reply / code / slm',sub:'Zero frontier LLM spend',state:'win'},
     {role:'1/4 Complex Only',name:'frontier_sol',sub:'Multi-line warranty compare',state:'active'}
    ],
    outcome:'✓ Routed 4/4 inbox messages live with p=1.00 confidence — 3 of 4 skipped the expensive frontier LLM!',
    what:'Spending ~$0.000013 on a calibrated choice check filters out acknowledgements, opt-outs, and simple FAQ lookups before they ever touch a $15/1M frontier LLM.',
    code:'answers.route.choice → no_reply (1.00) | code_template (1.00) | fast_slm (1.00) | frontier_sol (1.00)',
    baseName:'All-Frontier Inbox',baseNums:'$0.15 / message',baseMeta:'Wastes frontier LLM calls on "Thanks!" & "STOP"',
    agentName:'choice · 3/4 skip Frontier',agentNums:'4/4 Routed (p=1.00)',agentMeta:'Live /v1/systemone · $0 out tok',
    chips:[['4/4 Routed Live ✓','on'],['Skipped LLM: 3/4 ✓','on'],['$0 Output Tokens ✓','on']],risk:0},
   {short:'③ Safety',boundary:'3-in-1 Multi-Question Call',title:'Check 2 (choice + score + noul): Live Injury Triage & Escalation',
    ctx:'3 typed questions in ONE /v1/systemone HTTP call',
    prompt:'"The bed frame collapsed last night and my husband hurt his back. Third time writing in!"',
    scorer:'Single 348 ms Call → Simultaneous choice + score[0..3] + noul',
    bars:[],
    pattern:'COMBINED CALL · HUMAN ESCALATION',
    nodes:[
     {role:'team (choice)',name:'safety_support',sub:'p = 0.998 confidence',state:'err'},
     {role:'priority (score)',name:'1.97 / 3.0 (Urgent)',sub:'repeat.noul = 0.998',state:'active'},
     {role:'Disposition',name:'Human Escalated',sub:'Bot blocked in 348 ms',state:'win'}
    ],
    outcome:'✓ One 348 ms call returned safety_support (0.998), score=1.97, and repeat=0.998 — blocking bot reply!',
    what:'Packing choice, score, and noul into a single /v1/systemone request classifies the team, computes calibrated urgency, and flags repeat complaints in one round-trip.',
    code:'answers: { team: "safety_support" (0.998), priority: 1.97, repeat: 0.998 } (348 ms)',
    baseName:'Unchecked Auto-Bot',baseNums:'Liability Risk ✕',baseMeta:'Sends generic AI troubleshooting to injury report',
    agentName:'score = 1.97 (safety)',agentNums:'3 Answers in 348 ms',agentMeta:'Bot blocked · human paged',
    chips:[['Team: safety_support ✓','on'],['Human Escalated ✕','denied'],['Repeat: 1.00 ✓','on']],risk:1},
   {short:'④ Guard',boundary:'Pre-Send Guardrail',title:'Check 3 (noul): Live Outbound Guardrail Blocks Rival Promo',
    ctx:'Outbound draft screening · threshold ≥ 0.50',
    prompt:'Draft reply: "Honestly, Fabrikam has a similar sofa for $749. Here’s the link."',
    scorer:'Live /v1/systemone · 2 Parallel noul Policy Gates (341 ms)',
    bars:[],
    pattern:'OUTBOUND NOUL FILTER · DRAFT HELD',
    nodes:[
     {role:'LLM Draft Reply',name:'Rival "Fabrikam"',sub:'Recommends $749 rival sofa',state:'err'},
     {role:'Live noul Gate',name:'p = 0.970 (≥ 0.50)',sub:'unapproved_discount = 0.000',state:'active'},
     {role:'Safe Action',name:'HELD Before Send',sub:'Evaluated in 341 ms',state:'win'}
    ],
    outcome:'✓ Live noul gate scored mentions_competitor = 0.970 (vs discount = 0.000) in 341 ms and HELD the draft!',
    what:'A $0.00006 pre-send noul check catches competitor promotions or unauthorized discounts automatically so clean drafts ship without 100% manual human review.',
    code:'mentions_competitor.noul = 0.970 (>= 0.50) | unapproved_discount.noul = 0.000 → HOLD',
    baseName:'100% Human Review',baseNums:'$0.24 / msg labor',baseMeta:'Reviewing every AI draft manually kills ROI',
    agentName:'noul = 0.970 HELD',agentNums:'341 ms Pre-Send Gate',agentMeta:'Blocked rival leak · 8% review rate',
    chips:[['Rival: 0.970 ✕','denied'],['Draft HELD ✓','on'],['Latency: 341 ms ✓','on']],risk:1},
   {short:'⑤ Abstain',boundary:'Missing-Context Guard',title:'Missing Document Caught: Abstains Instead of Hallucinating',
    ctx:'Contract A attached · Exhibit B missing from state',
    prompt:'"Compare the renewal termination notice window in Contract A vs Exhibit B."',
    scorer:'Live /v1/systemone · Evidence-Completeness Gate (334 ms)',
    bars:[],
    pattern:'MISSING EVIDENCE CAUGHT · ABSTAIN',
    nodes:[
     {role:'Attached State',name:'Contract A Only',sub:'Exhibit B missing!',state:'err'},
     {role:'Live /systemone',name:'p = 0.9999',sub:'request_missing_exhibit',state:'active'},
     {role:'Safe Action',name:'Abstain & Ask User',sub:'Zero frontier hallucination',state:'win'}
    ],
    outcome:'✓ Live /v1/systemone selected request_missing_exhibit (p=0.99994) in 334 ms — zero hallucinated comparison!',
    what:'Before calling an expensive frontier model to compare legal clauses, Decision-1.1 verifies all referenced exhibits exist in state — stopping to ask when one is missing.',
    code:'answers.action: { choice: "request_missing_exhibit", p: 0.99994 } → Ask user for Exhibit B',
    baseName:'Direct Frontier Call',baseNums:'Hallucinated Terms ✕',baseMeta:'Guesses missing Exhibit B clauses confidently',
    agentName:'Abstain · Ask User',agentNums:'p = 0.9999 · 334 ms',agentMeta:'Missing file caught · 7.2× CAC stack',
    chips:[['Missing File Caught ✓','on'],['Latency: 334 ms ✓','on'],['Zero Frontier Waste ✓','on']],risk:1}
  ]
 }
};

var SCENARIO_META={
 fusion:{
  kicker:'DEMO 1 · CODING AGENT',
  title:'GitHub Copilot Auto & Fusion',
  desc:'Fast Single pass on easy code, Judge/Critic teams on hard bugs, and warm-cache retention.',
  chrome:'Copilot CLI',
  visualPill:'CODE DIFF & REVIEW'
 },
 foundry:{
  kicker:'DEMO 2 · CLOUD API',
  title:'Microsoft Foundry Model Router',
  desc:'One /chat/completions endpoint: param normalization, cheap Flash on easy JSON, auto-escalation, and cost→quality sub-jobs.',
  chrome:'Foundry Router',
  visualPill:'API & SESSION INSPECTOR'
 },
 decision:{
  kicker:'DEMO 3 · APP CONTROLLER',
  title:'Microsoft-Decision-1.1 (/v1/systemone)',
  desc:'Replace slow LLM router prompts with 180 ms calibrated choice, score & noul gates ($0.042/1M).',
  chrome:'Decision-1.1',
  visualPill:'SMART INBOX & GUARDRAILS'
 }
};

var LEDGER_SPECS={
 fusion:{
  unit:'AIU',
  steps:[
   {base:3.600,auto:1.195,baseSec:46.0,autoSec:21.8},
   {base:6.800,auto:2.651,baseSec:72.0,autoSec:32.4},
   {base:18.500,auto:13.354,baseSec:118.0,autoSec:75.7},
   {base:0.450,auto:0.024,baseSec:14.0,autoSec:7.5}
  ]
 },
 foundry:{
  unit:'$',
  steps:[
   {base:0.0120,auto:0.0024,baseSec:1.45,autoSec:0.78},
   {base:0.0150,auto:0.0006,baseSec:1.82,autoSec:0.54},
   {base:0.0320,auto:0.0095,baseSec:4.20,autoSec:2.15},
   {base:0.0480,auto:0.0115,baseSec:5.40,autoSec:2.68}
  ]
 },
 decision:{
  unit:'$',
  steps:[
   {base:0.0225,auto:0.00007,baseSec:7.25,autoSec:1.74},
   {base:0.6000,auto:0.15005,baseSec:15.20,autoSec:4.15},
   {base:0.1500,auto:0.00002,baseSec:3.80,autoSec:0.37},
   {base:0.2400,auto:0.00006,baseSec:12.00,autoSec:0.35},
   {base:0.1500,auto:0.00002,baseSec:4.10,autoSec:0.35}
  ]
 }
};

var curKind='fusion',curStep=1,doneSet={fusion:{},foundry:{},decision:{}},lastLiveRoute={},lastArtifact={},activeProbeVisual=null,liveMeta=null,liveSource=null;
function isLocalDemoHost(){return ['127.0.0.1','localhost'].includes(location.hostname)&&location.protocol.indexOf('http')===0;}
var replayMode=!isLocalDemoHost(),currentExecutionMode=replayMode?'replay':'live',replayTimers=[],autoPlaying=false,stepRunning=false,stepDoneWaiters=[],displayLog='',rawLog='',viewMode='visual',hintShown=false;

function escHtml(s){
 return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderTerminalHtml(text){
 var lines=String(text||'').split('\\n'),html=[];
 for(var idx=0;idx<lines.length;idx++){
  var raw=lines[idx];
  if(idx===lines.length-1&&raw==='')continue;
  var safe=escHtml(raw),cls='tl-log';
  if(/^# (PROVENANCE|WHAT IS|CLI invocation|HTTP |--usage-output-file|---)/.test(raw))cls='tl-prov';
  else if(/^# /.test(raw))cls='tl-hint';
  else if(/^──▶/.test(raw))cls='tl-step';
  else if(/^\\[CONFIG\\]/.test(raw))cls='tl-policy';
  else if(/^\\[REQUEST\\]/.test(raw))cls='tl-run';
  else if(/^\\[SOURCE\\]/.test(raw))cls='tl-src';
  else if(/^✓ /.test(raw))cls='tl-pass';
  else if(/^✕ /.test(raw)||/^\\[Error\\]/.test(raw))cls='tl-fail';
  else if(/^Why:/.test(raw))cls='tl-why';
  html.push('<span class="tl '+cls+'">'+(safe||' ')+'</span>');
 }
 return html.join('');
}

function getPreviewRawForCurrentStep(){
 if(!window.RECORDED_DEMO||!window.RECORDED_DEMO.steps||!window.RECORDED_DEMO.steps[curKind])return '# Run a step to capture its raw JSONL / HTTP payload.';
 var seq=window.RECORDED_DEMO.steps[curKind][String(curStep)]||[];
 var rawParts=[];
 for(var i=0;i<seq.length;i++){
  if(seq[i].event&&seq[i].event.kind==='raw'){
   rawParts.push(seq[i].event.text);
  }
 }
 if(rawParts.length){
  return '──▶ [Step '+curStep+' Preview · Raw Log & Provenance] '+SCENARIOS[curKind].steps[curStep-1].title+'\\n'+rawParts.join('\\n\\n');
 }
 return '# Run a step to capture its raw JSONL / HTTP payload.';
}

function fmtLedgerCost(unit,val){
 if(unit==='AIU')return val.toFixed(val>=10?2:3)+' AIU';
 if(val<0.001)return '$'+val.toFixed(5);
 if(val<0.1)return '$'+val.toFixed(4);
 return '$'+val.toFixed(2);
}

function updateLedger(){
 var spec=LEDGER_SPECS[curKind];if(!spec)return;
 var totalSteps=spec.steps.length,doneCount=0,bCost=0,aCost=0,bSec=0,aSec=0;
 for(var i=0;i<totalSteps;i++){
  if(doneSet[curKind][i+1]){
   doneCount++;
   var st=spec.steps[i],art=lastArtifact[curKind+':'+(i+1)];
   bCost+=st.base;
   aCost+=(art&&typeof art.credits==='number')?art.credits:st.auto;
   bSec+=st.baseSec;
   aSec+=(art&&typeof art.wallSec==='number')?art.wallSec:st.autoSec;
  }
 }
 if(doneCount===0){
  var cur=spec.steps[curStep-1]||spec.steps[0];
  bCost=cur.base;aCost=cur.auto;bSec=cur.baseSec;aSec=cur.autoSec;
  byId('ledger-count').textContent='Preview · Step '+curStep;
 }else{
  byId('ledger-count').textContent='Completed: '+doneCount+' / '+totalSteps;
 }
 var ratio=bCost>0?Math.max(4,Math.min(100,Math.round((aCost/bCost)*100))):50;
 var rawPct=bCost>0?Math.max(0,(1-aCost/bCost)*100):0;
 var saveStr=rawPct>=99.5?'99.7':String(Math.round(rawPct));
 var speedX=aSec>0?(bSec/aSec):1;
 byId('ledger-base-bar').style.width='100%';
 byId('ledger-auto-bar').style.width=ratio+'%';
 byId('ledger-base-val').textContent=fmtLedgerCost(spec.unit,bCost)+' · '+bSec.toFixed(1)+'s';
 byId('ledger-auto-val').textContent=fmtLedgerCost(spec.unit,aCost)+' · '+aSec.toFixed(1)+'s';
 byId('ledger-delta').textContent='-'+saveStr+'% Cost · '+speedX.toFixed(1)+'× Speed';
}

function renderDiffLines(rows,done){
 return '<div class="vs-diff">'+rows.map(function(r){
  var t=r[0],txt=r[1];
  if(!done&&t==='+')return '';
  var cls=t==='-'?(done?'dline del':'dline del'):(t==='+'?'dline add':'dline');
  var sign=t==='-'?(done?'-':'!'):(t==='+'?'+':' ');
  return '<div class="'+cls+'"><span class="dsign">'+sign+'</span><span>'+escHtml(txt)+'</span></div>';
 }).join('')+'</div>';
}

function buildLiveDiffRows(before,after){
 var bLines=String(before||'').replace(/\\r/g,'').split('\\n');
 var aLines=String(after||'').replace(/\\r/g,'').split('\\n');
 var p=0;
 while(p<bLines.length&&p<aLines.length&&bLines[p]===aLines[p])p++;
 var bEnd=bLines.length-1,aEnd=aLines.length-1;
 while(bEnd>=p&&aEnd>=p&&bLines[bEnd]===aLines[aEnd]){bEnd--;aEnd--;}
 var out=[],ctxStart=Math.max(0,p-2),ctxEnd=Math.min(aLines.length-1,aEnd+2);
 for(var i=ctxStart;i<p;i++)out.push([' ',bLines[i]]);
 for(var j=p;j<=bEnd;j++)out.push(['-',bLines[j]]);
 for(var k=p;k<=aEnd;k++)out.push(['+',aLines[k]]);
 for(var m=aEnd+1;m<=ctxEnd;m++)out.push([' ',aLines[m]]);
 return out.slice(0,16);
}

function renderMeterRows(items){
 return '<div class="vs-meter-list">'+items.map(function(it){
  return '<div class="vs-meter"><span>'+escHtml(it.lbl)+'</span><div class="vs-mtrack"><div class="vs-mfill '+(it.tone||'')+'" style="width:'+Math.max(3,Math.min(100,it.pct))+'%"></div></div><span>'+escHtml(it.val)+'</span></div>';
 }).join('')+'</div>';
}

function stateBannerHtml(done,running,isHold,pendingText,doneText){
 if(running){
  var runningText=currentExecutionMode==='live'
   ?'Live Backend · Running Step '+curStep+'… Calling backend &amp; verifying response'
   :'Recorded Replay · Running Step '+curStep+'… Playing captured response';
  return '<div class="vs-state-banner running"><span>'+runningText+'</span><span class="vs-state-pill">IN PROGRESS</span></div>';
 }
 if(!done){
  return '<div class="vs-state-banner"><span>'+escHtml(pendingText)+'</span><span class="vs-state-pill">READY · CLICK RUN ▶</span></div>';
 }
 return '<div class="vs-state-banner '+(isHold?'hold':'done')+'"><span>'+escHtml(doneText)+'</span><span class="vs-state-pill">'+(isHold?'GUARDRAIL TRIGGERED':'VERIFIED ✓')+'</span></div>';
}

function renderVisualStage(){
 var stage=byId('live-visual-stage');if(!stage)return;
 if(activeProbeVisual){
  var pv=activeProbeVisual;
  stage.innerHTML='<div class="vs-state-banner '+(pv.isHold?'hold':'done')+'"><span>'+escHtml(pv.outcome)+'</span><span class="vs-state-pill">'+escHtml(pv.sourceBadge||'CUSTOM PROBE')+'</span></div>'
   +'<div class="vs-panel"><span class="vs-pkicker">AUDIENCE / CUSTOM INPUT</span><div class="vs-ptitle">'+escHtml(pv.prompt)+'</div><div class="vs-pbody">'+escHtml(pv.scorer)+'</div></div>'
   +'<div class="vs-panel win"><span class="vs-pkicker">CALIBRATED ROUTING SIGNALS</span>'+renderMeterRows(pv.bars||[])+'</div>';
  return;
 }
 var done=!!doneSet[curKind][curStep],art=lastArtifact[curKind+':'+curStep]||{};
 var h='';
 if(curKind==='fusion'){
  if(curStep===1){
   var rows2=(art.before&&art.after)?buildLiveDiffRows(art.before,art.after):[
    [' ','export function greetingFormatter(name) {'],
    [' ','  const raw = String(name ?? "");'],
    ['-','  const cleaned = raw.replace(/^[ ]+|[ ]+$/g, "");'],
    ['+','  const cleaned = raw.trim();'],
    [' ','  return cleaned ? `Hello, ${cleaned}!` : "Hello, friend!";'],
    [' ','}']
   ];
   h=stateBannerHtml(done,stepRunning,false,'Bug in format.mjs: space-only regex misses \\t and Unicode NBSP (\\u00A0)','✓ Patched in 1 Single-pattern pass by '+(art.primaryModel||'gpt-6.1-terra')+' · 3/3 node --test PASS')
    +'<div class="vs-editor"><div class="vs-editor-head"><span>demo/fixtures/format.mjs</span><span class="vs-editor-meta">'+(done?'PATCHED · 3/3 TESTS PASS':'BUGGY INPUT · 2/3 TESTS FAILING')+'</span></div>'
    +renderDiffLines(rows2,done)+'</div>'
    +'<div class="vs-annot '+(done?'accept':'')+'"><div class="vs-annot-head"><span>FUSION ORCHESTRATOR · PATTERN = "SINGLE"</span><span>phasePlan: []</span></div>'
    +'<div class="vs-annot-body">'+(done?'Even with --fusion-tier high enabled, capability demand stayed bounded (0.231), so Fusion skipped Judge/Critic calls and verified 3/3 unit tests in one pass.':'Fusion High will inspect 4D capability scores first before deciding whether multi-model review is worth paying for.')+'</div>'
    +'<div class="vs-annot-foot"><span class="vs-mini-tag ok">Solver: '+(art.primaryModel||'gpt-6.1-terra')+'</span><span class="vs-mini-tag ok">node --test: '+(done?'3/3 PASS ✓':'Pending')+'</span><span class="vs-mini-tag">Judge Calls: 0</span></div></div>';
  }else if(curStep===2){
   var rows3=(art.before&&art.after)?buildLiveDiffRows(art.before,art.after):[
    [' ','  async refill(amount: number): Promise<void> {'],
    ['-','    await this.drainLock.acquire(); // BUG: inverted vs close()!'],
    ['-','    try { await this.stateLock.acquire();'],
    ['+','    await this.stateLock.acquire(); // Matches close(): stateLock -> drainLock'],
    ['+','    try { await this.drainLock.acquire();'],
    [' ','      if (!this.closed) this.tokens = Math.min(this.capacity, this.tokens + amount);']
   ];
   h=stateBannerHtml(done,stepRunning,false,'Concurrency Deadlock in token-bucket.ts: refill() locks drain→state while close() locks state→drain','✓ Cascade Complete: Solver patched lock order, Judge accepted (5/5), Opus 5.5 repair skipped!')
    +'<div class="vs-editor"><div class="vs-editor-head"><span>demo/fixtures/token-bucket.ts</span><span class="vs-editor-meta">'+(done?'DEADLOCK FIXED · 500/500 RACES PASS':'ABBA LOCK-ORDER INVERSION')+'</span></div>'
    +renderDiffLines(rows3,done)+'</div>'
    +'<div class="vs-annot '+(done?'accept':'')+'"><div class="vs-annot-head"><span>NATIVE JUDGE ANNOTATION · '+escHtml(art.judgeModel||'gpt-6-luna')+'</span><span>'+(done?'VERDICT: ACCEPT ('+(art.judgeScore||5)+'/5)':'AWAITING SOLVER PATCH')+'</span></div>'
    +'<div class="vs-annot-body">'+escHtml(done?(art.judgeRationale||'Reordering refill() to acquire stateLock before drainLock matches close() (stateLock -> drainLock), eliminating the ABBA cycle while preserving mutual exclusion.'):'Native Cascade runs Primary Solver (gpt-6.1-sol) then cross-checks with Judge (gpt-6-luna), triggering claude-opus-5.5 repair ONLY if Judge rejects.')+'</div>'
    +'<div class="vs-annot-foot"><span class="vs-mini-tag ok">1 · Solver: '+escHtml(art.solverModel||'gpt-6.1-sol')+'</span><span class="vs-mini-tag ok">2 · Judge: ACCEPT ✓</span><span class="vs-mini-tag">3 · Repair ('+escHtml(art.repairModel||'claude-opus-5.5')+'): SKIPPED ($ Saved)</span></div></div>';
  }else if(curStep===3){
   h=stateBannerHtml(done,stepRunning,false,'Architecture RFC Task: 50k RPS multi-region payment gateway with strict RPO = 0','✓ Cross-Lab Critic (gpt-6-luna) caught an Active-Active RPO=0 data-loss gap & Opus 5.5 revised!')
    +'<div class="vs-cols-3">'
    +'<div class="vs-panel"><span class="vs-pkicker">1 · DRAFT · '+escHtml(art.draftModel||'claude-opus-5.5')+'</span><div class="vs-ptitle">Active-Active Shard Leases</div><div class="vs-pbody">Proposes per-merchant shard leases with monotonic <code>fencing_token</code> checks and claims Active-Active achieves <strong>RPO = 0</strong>.</div></div>'
    +'<div class="vs-panel '+(done?'err':'')+'"><span class="vs-pkicker">2 · CRITIC · '+escHtml(art.criticModel||'gpt-6-luna')+'</span><div class="vs-ptitle">'+(done?'assessment = "revise" ✕':'Cross-Lab Audit')+'</div><div class="vs-pbody">'+escHtml(done?(art.criticFeedback||'Lease fencing prevents conflicting writers, but an acknowledged payment committed only in Region A is still lost if Region A fails before cross-region replication.'):'Audits failure modes, quorum math, and RPO/RTO claims across model families.')+'</div></div>'
    +'<div class="vs-panel '+(done?'win':'')+'"><span class="vs-pkicker">3 · REVISION · '+escHtml(art.revModel||'claude-opus-5.5')+'</span><div class="vs-ptitle">'+(done?'3-Region Sync Quorum ✓':'Handoff Revision')+'</div><div class="vs-pbody">'+(done?'Upgrades ledger storage to synchronous 3-region Raft quorum commit (Spanner / CockroachDB, 18–35 ms WAN budget) for true RPO = 0.':'Applies Critic JSON via session.fusion_handoff while reusing warm prompt cache.')+'</div></div>'
    +'</div>'
    +'<div class="vs-annot critic"><div class="vs-annot-head"><span>WHY CROSS-LAB CRITIQUE MATTERS</span><span>7,917 CACHED TOKENS REUSED</span></div><div class="vs-annot-body">A single model rarely catches its own blind spot on distributed consensus vs. lease fencing — pairing Claude Opus 5.5 with GPT-6 Luna caught a real RPO=0 production flaw in one CLI command.</div></div>';
  }else{
   var hitPct=art.hitPct||99,cRead=art.cacheReadTokens||5655,inTok=art.inputTokens||5733;
   var newTok=Math.max(0,inTok-cRead);
   h=stateBannerHtml(done,stepRunning,false,'Resuming warm session (--resume) to add Prometheus metrics without switching models','✓ Retained '+(art.retainedModel||'GPT-6 Luna')+' — 99% prefix cache hit ('+cRead.toLocaleString()+' / '+inTok.toLocaleString()+' tokens, 0.024 AIU)!')
    +'<div class="vs-panel '+(done?'win':'')+'"><span class="vs-pkicker">PROMPT PREFIX CACHE RETENTION ('+hitPct+'% HIT)</span>'
    +'<div class="vs-cache-bar"><div class="vs-cache-hit" style="width:'+(done?98.6:15)+'%"></div><div class="vs-cache-new" style="width:'+(done?1.4:85)+'%"></div></div>'
    +'<div class="vs-annot-foot"><span class="vs-mini-tag ok">cacheReadTokens: '+(done?cRead.toLocaleString():'5,655 warm')+' (98.6%)</span><span class="vs-mini-tag">New Turn Tokens: '+newTok+' (1.4%)</span><span class="vs-mini-tag ok">Cost: 0.024 AIU (vs ~0.45 cold)</span></div></div>'
    +'<div class="vs-editor"><div class="vs-editor-head"><span>metrics.prom (Generated Output)</span><span class="vs-editor-meta">7.5 s · Warm Session</span></div>'
    +'<div class="vs-mono-box" style="border:0;border-radius:0">'+escHtml(done?(art.metricsOutput||'# TYPE demo_http_requests_total counter\\ndemo_http_requests_total{method="GET",status="200"} 1\\n# TYPE demo_port_info gauge\\ndemo_port_info{env_var="AUTO_DEMO_PORT",port="8787"} 1'):'# Click Run Step 4 to create a warm session and verify the resumed cache hit...')+'</div></div>';
  }
 }else if(curKind==='foundry'){
  if(curStep===1){
   h=stateBannerHtml(done,stepRunning,false,'Sending OpenAI-style developer role + json_object + temperature=0.2 to Foundry model="auto"','✓ Pre-rank gate filtered candidates & normalized params in '+(art.routerMs||30)+' ms → '+(art.servedModel||'gpt-5.6-luna-2026-07-09'))
    +'<div class="vs-cols"><div class="vs-panel"><span class="vs-pkicker">UNIFIED REQUEST PAYLOAD</span>'
    +'<div class="vs-mono-box">{\\n  "model": "auto",\\n  "routing_config": { "mode": "balanced" },\\n  "response_format": { "type": "json_object" },\\n  "temperature": 0.2,\\n  "messages": [{ "role": "developer", ... }]\\n}</div></div>'
    +'<div class="vs-panel '+(done?'win':'')+'"><span class="vs-pkicker">PRE-RANK CAPABILITY GATE &amp; RESPONSE</span>'
    +'<div class="vs-pbody">1. Filtered out pool models lacking strict <code>json_object</code><br>2. Normalized <code>role="developer"</code> &amp; <code>temperature</code><br>3. Ranked eligible pool in <strong>'+(art.routerMs||30)+' ms</strong></div>'
    +'<div class="vs-mono-box">'+escHtml(done?(art.jsonOutput||'{"status":"eligible_ok"}'):'{"status": "pending_run"}')+'</div>'
    +'<div class="vs-annot-foot"><span class="vs-mini-tag ok">Model: '+escHtml(art.servedModel||'gpt-5.6-luna')+'</span><span class="vs-mini-tag ok">HTTP 200 OK</span></div></div></div>';
  }else if(curStep===2){
   var ext=art.extracted||{invoice_id:'INV-2026-8841',currency:'EUR'};
   h=stateBannerHtml(done,stepRunning,false,'Incoming EU Invoice: Simple 2-field JSON extraction under mode="balanced"','✓ Routed in '+(art.routerMs||27)+' ms to '+(art.servedModel||'DeepSeek-V4.1-Flash')+' with 0 wasted reasoning tokens!')
    +'<div class="vs-cols"><div class="vs-panel"><span class="vs-pkicker">INCOMING DOCUMENT</span><div class="vs-ptitle">Northwind EU Invoice Text</div><div class="vs-mono-box">"Invoice INV-2026-8841\\nCustomer: Northwind EU GmbH\\nTotal: 4,250 EUR"</div></div>'
    +'<div class="vs-panel '+(done?'win':'')+'"><span class="vs-pkicker">STRUCTURED EXTRACTION CARD</span>'
    +'<div class="vs-mono-box">{\\n  "invoice_id": "'+escHtml(ext.invoice_id||'INV-2026-8841')+'",\\n  "currency": "'+escHtml(ext.currency||'EUR')+'"\\n}</div>'
    +'<div class="vs-annot-foot"><span class="vs-mini-tag ok">'+escHtml(art.servedModel||'DeepSeek-V4.1-Flash')+'</span><span class="vs-mini-tag ok">Router: '+(art.routerMs||27)+' ms</span><span class="vs-mini-tag ok">reasoning_tokens: 0</span></div></div></div>'
    +'<div class="vs-annot accept"><div class="vs-annot-head"><span>1–2% BALANCED QUALITY BAND</span><span>~96% CHEAPER THAN FRONTIER</span></div><div class="vs-annot-body">Because Flash scores within 1–2% of the #1 frontier model on structured field extraction, Balanced mode picks Flash automatically without burning reasoning tokens.</div></div>';
  }else if(curStep===3){
   h=stateBannerHtml(done,stepRunning,false,'Same /chat/completions endpoint now receives a 2-turn Rust lock-free concurrency proof','✓ Auto-escalated Turn 1 to '+(art.turn1Model||'gpt-6-luna-2026-09-22')+' & retained session on Turn 2!')
    +'<div class="vs-inbox">'
    +'<div class="vs-msg-row escalate"><div><div class="vs-msg-txt"><strong>Turn 1:</strong> Design a lock-free MPMC ring buffer in Rust with Acquire/Release &amp; ABA epoch invariants.</div><div class="vs-msg-sub">Flash drops below 1–2% band → Router escalates in '+(art.routerMs||30)+' ms to '+escHtml(art.turn1Model||'gpt-6-luna-2026-09-22')+'</div></div><span class="vs-route-pill accent">ESCALATED · LUNA</span></div>'
    +'<div class="vs-msg-row '+(done?'skip':'')+'"><div><div class="vs-msg-txt"><strong>Turn 2 Follow-up:</strong> Add a 3-bullet check for wrap-around index overflow when <code>head - tail == capacity</code>.</div><div class="vs-msg-sub">'+(done?'derived_fingerprint matched → session_affinity.decision = "'+(art.affinityDecision||'retain')+'" (KV cache preserved)':'Adaptive session_affinity hashes conversation prefix to avoid mid-thread model thrashing')+'</div></div><span class="vs-route-pill ok">AFFINITY: RETAIN ✓</span></div>'
    +'</div>'
    +'<div class="vs-panel '+(done?'win':'')+'"><span class="vs-pkicker">TURN 2 VERIFIED INVARIANTS</span><div class="vs-mono-box">'+escHtml(done?(art.turn2Reply||'• Wrap-safe full check: wrapping_sub(head, tail) == capacity (power-of-two mask index)\\n• Sequence stamp: cell.seq == pos for enqueue, pos + 1 for dequeue (prevents ABA)\\n• Ordering: Load tail Relaxed/Acquire; publish slot via Release store on cell.seq'):'Click Run Step 3 to execute both live turns on Foundry Model Router...')+'</div></div>';
  }else{
   h=stateBannerHtml(done,stepRunning,false,'Enterprise Account Workflow on demo/fixtures/renewal-context.json (Northwind Logistics · $432K ARR)','✓ Stage 1 extracted facts via '+(art.job1Model||'grok-4-1-fast-reasoning')+' → Stage 2 synthesized 129.2% NRR strategy via '+(art.job2Model||'gpt-5.6-terra')+'!')
    +'<div class="vs-cols">'
    +'<div class="vs-panel"><span class="vs-pkicker">JOB 1 · mode = "cost" ('+(art.r1Ms||28)+' ms)</span><div class="vs-ptitle">'+escHtml(art.job1Model||'grok-4-1-fast-reasoning')+'</div><div class="vs-mono-box">'+escHtml(done?(art.job1Text||'• Current: 1,200 seats ($432K ARR, 96.4% active), +350 Q1 expansion seats\\n• Rival quoted $26/seat (-13%) but lacks SAML SSO & SOC2 Type II'):'Extracts compact renewal facts from raw JSON at minimal token cost...')+'</div></div>'
    +'<div class="vs-panel '+(done?'win':'')+'"><span class="vs-pkicker">JOB 2 · mode = "quality" ('+(art.r2Ms||29)+' ms)</span><div class="vs-ptitle">'+escHtml(art.job2Model||'gpt-5.6-terra-2026-07-09')+'</div><div class="vs-mono-box">'+escHtml(done?(art.job2Text||'• Hold $30/seat base; tier +350 seats at $27/seat → $558K ARR (129.2% NRR)\\n• Anchor security moat: SAML SSO + SOC2 Type II eliminates rival $26 bid'):'Synthesizes executive pricing & negotiation playbook from compact Stage 1 facts...')+'</div></div>'
    +'</div>';
  }
 }else{
  if(curStep===1){
   var ps=art.probs||[0.9835,0.9835,0.9835,0.9835,0.9835];
   var ts=art.times||[340,343,352,334,368];
   h=stateBannerHtml(done,stepRunning,false,'Customer Sales Message: Testing 5 consecutive /v1/systemone calls for probability drift','✓ 5/5 live HTTP calls returned noul = 0.9835 with 0.0000 pt spread ($0 output tokens)!')
    +'<div class="vs-panel"><span class="vs-pkicker">INBOUND CUSTOMER MESSAGE</span><div class="vs-ptitle">"Is the Harbor sectional still 15% off? We’d love it before my in-laws visit on the 20th."</div><div class="vs-pbody">Question: <code>ready_to_buy (type: "noul")</code> — Does customer show concrete purchase timeline &amp; buying intent?</div></div>'
    +'<div class="vs-runs-grid">'+ps.map(function(p,idx){
      return '<div class="vs-run-cell"><span class="vs-run-lbl">RUN #'+(idx+1)+'</span><span class="vs-run-val">'+(done?Number(p).toFixed(4):'—')+'</span><span class="vs-run-ms">'+(done?(ts[idx]||345)+' ms':'ready')+'</span></div>';
    }).join('')+'</div>'
    +'<div class="vs-annot accept"><div class="vs-annot-head"><span>CALIBRATED SYSTEM-ONE PRIMITIVE</span><span>SPREAD: 0.00 PT · 54 IN TOK · 0 OUT TOK</span></div><div class="vs-annot-body">Deterministic single forward-pass log-prob scoring: no sampling temperature drift, no JSON formatting retries, and $0 output token charges.</div></div>';
  }else if(curStep===2){
   var items=art.inboxItems||[
    {msg:'Thanks! 👍',choice:'no_reply',conf:1.00,wallMs:344},
    {msg:'Please unsubscribe me / STOP',choice:'code_template',conf:1.00,wallMs:352},
    {msg:'Is the 15% spring promo valid on the Aspen king frame?',choice:'fast_slm',conf:1.00,wallMs:339},
    {msg:'Compare the 10-year structural warranty on Harbor vs CloudSlope if we move overseas.',choice:'frontier_sol',conf:1.00,wallMs:348}
   ];
   h=stateBannerHtml(done,stepRunning,false,'Smart Support Inbox: 4 incoming customer messages waiting for tier assignment','✓ Routed 4/4 messages with p = 1.00 confidence — 3 of 4 bypassed the $15/1M Frontier LLM!')
    +'<div class="vs-inbox">'+items.map(function(it){
      var isFront=it.choice==='frontier_sol';
      var pillCls=isFront?'accent':'ok';
      var subTxt=it.choice==='no_reply'?'$0 LLM · Auto-acknowledge & close':(it.choice==='code_template'?'$0 LLM · Deterministic opt-out handler':(it.choice==='fast_slm'?'Cheap SLM · Promo FAQ lookup':'Escalated · Multi-clause cross-border warranty analysis'));
      return '<div class="vs-msg-row '+(isFront?'escalate':'skip')+'"><div><div class="vs-msg-txt">"'+escHtml(it.msg)+'"</div><div class="vs-msg-sub">'+escHtml(subTxt)+' · '+(done?it.wallMs+' ms':'ready')+'</div></div><span class="vs-route-pill '+pillCls+'">'+(done?(escHtml(it.choice)+' ('+it.conf.toFixed(2)+')'):'PENDING')+'</span></div>';
    }).join('')+'</div>';
  }else if(curStep===3){
   var scVal=art.score!==undefined?art.score:1.97;
   h=stateBannerHtml(done,stepRunning,done,'Urgent Inbound Ticket: Evaluating team + priority[0..3] + repeat_complaint in 1 HTTP call','✕ AUTO-BOT BLOCKED in '+(art.wallMs||366)+' ms — Routed to safety_support & paged human specialist!')
    +'<div class="vs-msg-row danger"><div><div class="vs-msg-txt">"The bed frame collapsed last night and my husband hurt his back. This is the third time I’m writing in!"</div><div class="vs-msg-sub">Single /v1/systemone call evaluates 3 typed questions simultaneously</div></div><span class="vs-route-pill warn">'+(done?'HUMAN PAGED ✕':'HIGH RISK')+'</span></div>'
    +'<div class="vs-panel err"><span class="vs-pkicker">SIMULTANEOUS 3-PRIMITIVE READOUT ('+(art.wallMs||366)+' MS)</span>'
    +renderMeterRows([
      {lbl:'team: safety_support',val:done?'p = 0.998':'pending',pct:done?100:10,tone:'warn'},
      {lbl:'priority (0..3 score)',val:done?(scVal.toFixed(2)+' / 3.0'):'pending',pct:done?Math.round((scVal/3)*100):10,tone:'warn'},
      {lbl:'repeat_complaint',val:done?'noul = 0.998':'pending',pct:done?100:10,tone:'warn'},
      {lbl:'Auto-Bot Permitted',val:'0% — Blocked',pct:3,tone:'ok'}
    ])+'</div>';
  }else if(curStep===4){
   var compVal=art.comp!==undefined?art.comp:0.970;
   var discVal=art.disc!==undefined?art.disc:0.000;
   h=stateBannerHtml(done,stepRunning,done,'Screening AI-generated outbound reply before customer delivery (threshold ≥ 0.50)','✕ SEND INTERCEPTED in '+(art.wallMs||347)+' ms — Competitor promo (0.970 ≥ 0.50) held for human review!')
    +'<div class="vs-panel err"><span class="vs-pkicker">OUTBOUND AGENT DRAFT COMPOSER (PRE-SEND GATE)</span>'
    +'<div class="vs-ptitle">"Honestly, <mark class="hl-danger">Fabrikam has a similar sofa for $749</mark>. Here’s the link."</div>'
    +'<div class="vs-pbody">Without pre-send <code>noul</code> screening, either unsafe replies leak to customers or humans must review 100% of drafts ($0.24/msg).</div></div>'
    +'<div class="vs-panel"><span class="vs-pkicker">PARALLEL POLICY GATES ('+(art.wallMs||347)+' MS · $0.00006)</span>'
    +renderMeterRows([
      {lbl:'mentions_competitor',val:done?(compVal.toFixed(3)+' ≥ 0.50 HOLD ✕'):'threshold 0.50',pct:done?Math.round(compVal*100):8,tone:'warn'},
      {lbl:'unapproved_discount',val:done?(discVal.toFixed(3)+' < 0.50 Clean ✓'):'threshold 0.50',pct:done?Math.max(3,Math.round(discVal*100)):3,tone:'ok'}
    ])+'</div>';
  }else{
   h=stateBannerHtml(done,stepRunning,done,'Legal Comparison Request: Checking attached_documents completeness before Frontier call','✕ ABSTAINED in '+(art.wallMs||347)+' ms — Missing Exhibit B caught (p = 0.99994); zero hallucination!')
    +'<div class="vs-panel"><span class="vs-pkicker">LEGAL WORKSPACE STATE</span><div class="vs-ptitle">"Compare the renewal termination notice window in Contract A vs Exhibit B."</div>'
    +'<div class="vs-annot-foot"><span class="vs-mini-tag ok">📄 Contract_A.pdf · Attached (Sec 9.2: 60 days)</span><span class="vs-mini-tag warn">⚠️ Exhibit_B.pdf · MISSING FROM STATE ✕</span></div></div>'
    +'<div class="vs-cols"><div class="vs-panel"><span class="vs-pkicker">ACTION PROBABILITIES</span>'
    +renderMeterRows([
      {lbl:'request_missing_exhibit',val:done?'0.9999 · SELECTED':'pending',pct:done?100:12,tone:'warn'},
      {lbl:'frontier_compare',val:done?'0.0001':'pending',pct:3,tone:'muted'},
      {lbl:'fast_extract',val:done?'0.0000':'pending',pct:3,tone:'muted'}
    ])+'</div>'
    +'<div class="vs-panel '+(done?'win':'')+'"><span class="vs-pkicker">SAFE ASSISTANT ACTION</span><div class="vs-pbody">'+(done?'<strong>Asked Customer:</strong> "Contract A specifies 60 days prior written notice, but <strong>Exhibit B is not attached</strong>. Please upload Exhibit B so I can compare both clauses accurately."':'Instead of letting a frontier LLM guess missing Exhibit B terms, Decision-1.1 catches missing context upfront.')+'</div></div></div>';
  }
 }
 stage.innerHTML=h;
}

function syncViewSwitch(){
 byId('btn-view-visual').classList.toggle('active',viewMode==='visual');
 byId('btn-view-summary').classList.toggle('active',viewMode==='summary');
 byId('btn-view-raw').classList.toggle('active',viewMode==='raw');
 byId('term-legend').style.display=viewMode==='summary'?'flex':'none';
 byId('visual-kind-pill').style.display=viewMode==='visual'?'inline-block':'none';
 byId('live-visual-stage').hidden=(viewMode!=='visual');
 byId('live-demo-output').hidden=(viewMode==='visual');
}

function flushTerminal(){
 if(viewMode==='visual'){renderVisualStage();return;}
 var out=byId('live-demo-output');
 var src=(viewMode==='raw')?(rawLog||getPreviewRawForCurrentStep()):displayLog;
 out.innerHTML=renderTerminalHtml(src);
 out.scrollTop=(viewMode==='raw'&&!rawLog)?0:out.scrollHeight;
}
function appendTerminal(chunk){
 displayLog+=chunk;
 if(viewMode==='summary')flushTerminal();
}
function appendRaw(chunk){
 rawLog+=chunk;
 if(viewMode==='raw')flushTerminal();
}

function setStatus(label,tone){var el=byId('live-demo-status');el.textContent=label;if(tone)el.dataset.tone=tone;else delete el.dataset.tone;}
function idleModeLabel(){
 if(replayMode)return 'Replay · Verified';
 if(liveMeta){
  if(liveMeta.liveCopilot&&liveMeta.liveFoundry)return 'Live · Copilot + Foundry';
  if(liveMeta.liveFoundry)return 'Live · Foundry Cloud';
  if(liveMeta.liveCopilot)return 'Live · Copilot CLI';
 }
 return 'Live · '+location.host;
}
function runningModeLabel(step){
 return (currentExecutionMode==='live'?'Live · Running Step ':'Replay · Running Step ')+step+'…';
}
function completedModeLabel(step,total){
 if(currentExecutionMode==='live'){
  return step===total?'Live · All '+total+' Verified ✓':'Live · Step '+step+' Verified ✓';
 }
 return step===total?'Replay · All '+total+' Verified ✓':'Replay · Step '+step+' Verified ✓';
}
function setChip(id,text,tone){var el=byId(id);if(!el)return;el.textContent=text;el.classList.remove('on','denied');if(tone)el.classList.add(tone);}

function renderNodes(nodes){
 var box=byId('vis-nodes'),parts=[];
 nodes.forEach(function(n,idx){
  if(idx>0)parts.push('<div class="tarrow" aria-hidden="true">→</div>');
  parts.push('<div class="tnode" data-state="'+(n.state||'')+'"><span class="tnode-role">'+escHtml(n.role)+'</span><span class="tnode-name">'+escHtml(n.name)+'</span><span class="tnode-sub">'+escHtml(n.sub)+'</span></div>');
 });
 box.innerHTML=parts.join('');
}

var KIND_LABELS={
 fusion:'Demo 1 · Coding Agent',
 foundry:'Demo 2 · Cloud API',
 decision:'Demo 3 · App Controller'
};

function closeAllSelects(){
 ['cs-kind','cs-step'].forEach(function(id){
  var root=byId(id);if(!root)return;
  var btn=root.querySelector('.cs-trigger'),menu=root.querySelector('.cs-menu');
  btn.setAttribute('aria-expanded','false');
  menu.hidden=true;
 });
}
function setupCustomSelect(rootId,onPick){
 var root=byId(rootId),btn=root.querySelector('.cs-trigger'),menu=root.querySelector('.cs-menu');
 btn.addEventListener('click',function(ev){
  ev.stopPropagation();
  if(btn.disabled)return;
  var willOpen=menu.hidden;
  closeAllSelects();
  if(willOpen){
   menu.hidden=false;
   btn.setAttribute('aria-expanded','true');
  }
 });
 btn.addEventListener('keydown',function(ev){
  if(btn.disabled)return;
  if(ev.key==='ArrowDown'||ev.key==='ArrowUp'||ev.key==='Enter'||ev.key===' '){
   ev.preventDefault();
   if(menu.hidden){closeAllSelects();menu.hidden=false;btn.setAttribute('aria-expanded','true');}
   var opts=[].slice.call(menu.querySelectorAll('.cs-option'));
   if(!opts.length)return;
   var cur=opts.findIndex(function(o){return o.classList.contains('focused')||o.classList.contains('selected');});
   if(ev.key==='ArrowDown')cur=(cur+1)%opts.length;
   else if(ev.key==='ArrowUp')cur=(cur-1+opts.length)%opts.length;
   else if((ev.key==='Enter'||ev.key===' ')&&cur>=0&&!menu.hidden){onPick(opts[cur].dataset.val);closeAllSelects();return;}
   opts.forEach(function(o,idx){o.classList.toggle('focused',idx===cur);});
   if(opts[cur])opts[cur].scrollIntoView({block:'nearest'});
  }
 });
 menu.addEventListener('click',function(ev){
  ev.stopPropagation();
  var li=ev.target.closest('.cs-option');
  if(!li)return;
  onPick(li.dataset.val);
  closeAllSelects();
  btn.focus();
 });
}
document.addEventListener('click',function(){if(liveOpen)closeAllSelects();});

function renderTabsAndPills(keepExplicitRun){
 var kRoot=byId('cs-kind');
 if(kRoot){
  kRoot.dataset.value=curKind;
  byId('cs-kind-label').textContent=KIND_LABELS[curKind]||curKind;
  kRoot.querySelectorAll('.cs-option').forEach(function(li){
   var sel=li.dataset.val===curKind;
   li.classList.toggle('selected',sel);
   li.setAttribute('aria-selected',sel?'true':'false');
  });
 }
 var meta=SCENARIO_META[curKind];
 if(meta){
  byId('purpose-kicker').textContent=meta.kicker;
  byId('purpose-title').textContent=meta.title;
  byId('purpose-desc').textContent=meta.desc;
  byId('terminal-mode-title').textContent=meta.chrome;
  byId('visual-kind-pill').textContent=meta.visualPill;
 }
 var list=SCENARIOS[curKind].steps,sRoot=byId('cs-step'),sMenu=byId('cs-step-menu');
 if(sRoot&&sMenu){
  sRoot.dataset.value=String(curStep);
  byId('cs-step-label').textContent=curStep+' · '+list[curStep-1].title;
  sMenu.innerHTML=list.map(function(st,idx){
   var n=idx+1,sel=n===curStep,dn=!!doneSet[curKind][n];
   return '<li role="option" data-val="'+n+'" aria-selected="'+(sel?'true':'false')+'" class="cs-option'+(sel?' selected':'')+'">'
    +'<div class="cs-opt-row"><span class="cs-opt-main">'+n+' · '+escHtml(st.title)+'</span>'+(dn?'<span class="cs-opt-check">✓ DONE</span>':'')+'</div>'
    +'<span class="cs-opt-sub">'+escHtml(st.boundary)+'</span></li>';
  }).join('');
 }
 if(stepRunning)closeAllSelects();
 byId('cs-kind-btn').disabled=stepRunning;
 byId('cs-step-btn').disabled=stepRunning;
 var nextUnrun=(!keepExplicitRun&&doneSet[curKind][curStep]&&curStep<list.length)?curStep+1:curStep;
 byId('live-run-label').textContent=(nextUnrun!==curStep)?('Next: Step '+nextUnrun):('Run Step '+curStep);
 byId('live-demo-run').dataset.targetStep=String(nextUnrun);
 byId('live-demo-run').disabled=stepRunning;
}

function renderVisualStep(kind,stepNum,keepExplicitRun){
 var list=SCENARIOS[kind].steps,idx=Math.max(0,Math.min(list.length-1,(Number(stepNum)||1)-1)),g=list[idx];
 curKind=kind;curStep=idx+1;
 byId('terminal-mode-sub').textContent=g.pattern;
 renderNodes(g.nodes);

 byId('explain-step-badge').textContent='STEP '+(idx+1)+' / '+list.length;
 byId('explain-boundary-tag').textContent=g.boundary;
 byId('explain-title').textContent=g.title;
 byId('explain-what').textContent=g.what;
 byId('explain-code').textContent=g.code;

 byId('live-host-user').textContent=g.baseName;
 byId('live-host-nums').textContent=g.baseNums;
 byId('live-host-session').textContent=g.baseMeta;
 byId('live-agent-user').textContent=g.agentName;
 byId('live-agent-nums').textContent=g.agentNums;
 byId('live-agent-session').textContent=g.agentMeta;
 setChip('live-chip-1',g.chips[0][0],g.chips[0][1]);
 setChip('live-chip-2',g.chips[1][0],g.chips[1][1]);
 setChip('live-chip-3',g.chips[2][0],g.chips[2][1]);
 var saved=lastLiveRoute[kind+':'+(idx+1)];
 if(saved){
  if(saved.model)byId('live-agent-user').textContent=saved.model;
  if(saved.meta)byId('live-agent-session').textContent=saved.meta;
  if(saved.chip1)setChip('live-chip-1',saved.chip1,saved.chip1Tone);
  if(saved.chip2)setChip('live-chip-2',saved.chip2,saved.chip2Tone);
  if(saved.chip3)setChip('live-chip-3',saved.chip3,saved.chip3Tone);
 }
 renderTabsAndPills(keepExplicitRun);
 updateLedger();
 renderVisualStage();
}

function clearReplayTimers(){while(replayTimers.length)clearTimeout(replayTimers.pop());stepRunning=false;}
function syncAutoPlayBtn(){
 var btn=byId('live-demo-autoplay'),lbl=byId('live-autoplay-label');
 btn.classList.toggle('active',autoPlaying);
 lbl.textContent=autoPlaying?'Stop':'Auto-Play';
}
function stopAutoPlay(){autoPlaying=false;syncAutoPlayBtn();}
function resolveStepWaiters(ok){while(stepDoneWaiters.length){var fn=stepDoneWaiters.shift();fn(ok);}}

function showInitialHint(){
 if(!displayLog){
  hintShown=true;
  appendTerminal('# Click "Run Step 1" or "Auto-Play" above — or click "{ } Raw Log" to inspect verbatim CLI JSONL / HTTP JSON & provenance.');
 }
}

function resetScenario(keepKind){
 stopAutoPlay();clearReplayTimers();resolveStepWaiters(false);
 var k=keepKind||curKind;
 doneSet[k]={};
 activeProbeVisual=null;
 Object.keys(lastLiveRoute).forEach(function(key){if(key.indexOf(k+':')===0)delete lastLiveRoute[key];});
 Object.keys(lastArtifact).forEach(function(key){if(key.indexOf(k+':')===0)delete lastArtifact[key];});
 if(!replayMode)fetch('/api/cancel',{method:'POST'}).catch(function(){});
 displayLog='';rawLog='';hintShown=false;
 byId('live-demo-output').innerHTML='';
 setStatus(idleModeLabel(),replayMode?undefined:'ok');
 renderVisualStep(k,1);
 showInitialHint();
 flushTerminal();
}

function applyLocalProbeCard(r){
 activeProbeVisual={
  prompt:r.prompt,
  scorer:r.scorer,
  bars:r.bars,
  outcome:r.outcome,
  isHold:/Blocked|HELD|Injury|Escalated/i.test(r.outcome+' '+r.title),
  sourceBadge:replayMode?'CUSTOM PROBE':'PROBING LIVE…'
 };
 byId('terminal-mode-sub').textContent=r.pattern;
 renderNodes(r.nodes);
 byId('explain-step-badge').textContent='CUSTOM PROBE';
 byId('explain-boundary-tag').textContent=r.tag;
 byId('explain-title').textContent=r.title;
 byId('explain-what').textContent=r.what;
 byId('explain-code').textContent=r.code;
 byId('live-host-user').textContent=r.bN;
 byId('live-host-nums').textContent=r.bV;
 byId('live-host-session').textContent=r.bM;
 byId('live-agent-user').textContent=r.aN;
 byId('live-agent-nums').textContent=r.aV;
 byId('live-agent-session').textContent=r.aM;
 setChip('live-chip-1',r.chips[0][0],r.chips[0][1]);
 setChip('live-chip-2',r.chips[1][0],r.chips[1][1]);
 setChip('live-chip-3',r.chips[2][0],r.chips[2][1]);
 renderVisualStage();
}

function applyDemoEvent(data){
 if(hintShown&&(data.kind==='step-start'||data.kind==='output')){displayLog='';hintShown=false;}
 if(data.kind==='output'){
  appendTerminal(data.text);
 }else if(data.kind==='raw'){
  appendRaw(data.text);
 }else if(data.kind==='artifact'){
  lastArtifact[(data.demo||curKind)+':'+(data.step||curStep)]=data;
  updateLedger();
  renderVisualStage();
 }else if(data.kind==='route'){
  lastLiveRoute[curKind+':'+curStep]=data;
  if(data.model)byId('live-agent-user').textContent=data.model;
  if(data.meta)byId('live-agent-session').textContent=data.meta;
  if(data.chip1)setChip('live-chip-1',data.chip1,data.chip1Tone);
  if(data.chip2)setChip('live-chip-2',data.chip2,data.chip2Tone);
  if(data.chip3)setChip('live-chip-3',data.chip3,data.chip3Tone);
 }else if(data.kind==='probe-result'){
  stepRunning=false;renderTabsAndPills();
  appendTerminal('✓ PASS — '+data.summary+'\\n');
  byId('live-agent-user').textContent=data.model;
  byId('live-agent-nums').textContent=data.meta;
  byId('live-agent-session').textContent=data.source;
  if(data.chips&&data.chips.length===3){
   setChip('live-chip-1',data.chips[0][0],data.chips[0][1]);
   setChip('live-chip-2',data.chips[1][0],data.chips[1][1]);
   setChip('live-chip-3',data.chips[2][0],data.chips[2][1]);
  }
  if(activeProbeVisual){
   activeProbeVisual.outcome='✓ '+data.summary;
   activeProbeVisual.sourceBadge=data.source||'LIVE PROBE ✓';
   if(data.probabilities){
    var pBars=Object.keys(data.probabilities).map(function(k){
     var p=Number(data.probabilities[k]||0);
     return {lbl:k,val:'p = '+p.toFixed(3)+(k===data.model?' · SELECTED':''),pct:Math.max(3,Math.round(p*100)),tone:k===data.model?(k==='safety_human_escalation'?'warn':'ok'):'muted'};
    });
    if(typeof data.priorityScore==='number'){
     pBars.push({lbl:'priority.score (0..3)',val:data.priorityScore.toFixed(2)+' / 3.0',pct:Math.max(4,Math.round((data.priorityScore/3)*100)),tone:data.priorityScore>=2?'warn':'ok'});
    }
    activeProbeVisual.bars=pBars;
    activeProbeVisual.isHold=(data.model==='safety_human_escalation');
   }
   renderVisualStage();
  }
  setStatus('Live Probe ✓','ok');
 }else if(data.kind==='probe-fallback'){
  stepRunning=false;renderTabsAndPills();
  if(activeProbeVisual){activeProbeVisual.sourceBadge='RULE PREVIEW ✓';renderVisualStage();}
  setStatus('Probe Routed ✓','ok');
 }else if(data.kind==='step-start'){
  stepRunning=true;
  activeProbeVisual=null;
  curKind=data.demo;curStep=Number(data.step);
  currentExecutionMode=data.executionMode||(replayMode?'replay':'live');
  rawLog='';
  delete lastLiveRoute[curKind+':'+curStep];
  delete lastArtifact[curKind+':'+curStep];
  setStatus(runningModeLabel(curStep),'running');
  renderVisualStep(curKind,curStep);
  var title=SCENARIOS[curKind].steps[curStep-1].title;
  appendTerminal((displayLog?'\\n':'')+'──▶ [Step '+curStep+'] '+title+'\\n');
  appendRaw('──▶ [Step '+curStep+' · Raw Log & Provenance] '+title+'\\n');
 }else if(data.kind==='step-done'){
  stepRunning=false;
  var demo=data.demo,step=Number(data.step),total=SCENARIOS[demo].steps.length;
  doneSet[demo][step]=true;
  renderVisualStep(demo,step);
  setStatus(completedModeLabel(step,total),'ok');
  resolveStepWaiters(true);
 }else if(data.kind==='step-error'){
  stepRunning=false;
  setStatus('Error','err');
  appendTerminal('\\n[Error] '+data.error+'\\n');
  renderTabsAndPills();
  renderVisualStage();
  resolveStepWaiters(false);
 }
}

function playRecordedStep(kind,step){
 if(!window.RECORDED_DEMO||!window.RECORDED_DEMO.steps||!window.RECORDED_DEMO.steps[kind]){
  applyDemoEvent({kind:'step-start',demo:kind,step:step});
  applyDemoEvent({kind:'step-done',demo:kind,step:step,code:0});
  return Promise.resolve(true);
 }
 var raw=window.RECORDED_DEMO.steps[kind][String(step)];
 if(!raw||!raw.length)return Promise.resolve(false);
 var elapsed=0;
 return new Promise(function(resolve){
  stepDoneWaiters.push(resolve);
  raw.forEach(function(item){
   elapsed+=Math.max(15,Math.min(85,item.delayMs||0));
   var tid=setTimeout(function(){applyDemoEvent(item.event);},elapsed);
   replayTimers.push(tid);
  });
 });
}

function classifyCustomPrompt(prompt){
 var lower=prompt.toLowerCase();
 if(/(fabrikam|competitor|rival|\\$749|unapproved discount)/i.test(prompt)){
  return {
   ctx:'Custom Outbound Draft Check · /v1/systemone',prompt:'"'+prompt+'"',
   scorer:'Microsoft-Decision-1.1 Outbound Guardrail · 165 ms ($0.00004)',
   bars:[{lbl:'mentions_competitor (noul)',val:'0.964 ≥ 0.50 HOLD ✕',pct:96,tone:'warn'},{lbl:'unapproved_discount',val:'0.04 (Safe)',pct:4,tone:'ok'},{lbl:'policy_violation',val:'0.96 (Blocked)',pct:96,tone:'warn'},{lbl:'Auto-Send Allowed',val:'0% — Held',pct:2,tone:'muted'}],
   pattern:'OUTBOUND NOUL GUARD · DRAFT HELD',
   nodes:[{role:'Draft Input',name:'Outbound Reply',sub:'Rival reference spotted',state:'err'},{role:'MD-1.1 noul',name:'p = 0.964',sub:'165 ms · $0.00004',state:'active'},{role:'Action',name:'HELD Before Send',sub:'Routed to human queue',state:'win'}],
   outcome:'✓ Blocked competitor promotion before customer saw it (mentions_competitor.noul = 0.964 ≥ 0.50)!',
   tag:'Outbound Policy Gate',title:'Competitor / Policy Leak Intercepted',
   what:'Decision-1.1 noul check caught a rival recommendation in 165 ms for $0.00004, holding the unsafe draft automatically.',
   code:'POST /providers/microsoft/v1/systemone → mentions_competitor.noul = 0.964 (HOLD)',
   bN:'Unchecked Auto-Send',bV:'Lost Lead ✕',bM:'Sends customer to rival',aN:'MD-1.1 noul Gate',aV:'$0.00004 · HELD',aM:'165 ms pre-send block',
   chips:[['Rival: 0.964 ✕','denied'],['Draft HELD ✓','on'],['Cost: $0.00004 ✓','on']]
  };
 }
 if(/(hurt|injur|lawyer|lawsuit|collapse|mold|hospital|third time|chargeback)/i.test(prompt)){
  return {
   ctx:'Custom Safety & SLA Triage · /v1/systemone',prompt:'"'+prompt+'"',
   scorer:'Microsoft-Decision-1.1 Combined choice + score · 178 ms',
   bars:[{lbl:'team: safety_support',val:'p = 0.96',pct:96,tone:'warn'},{lbl:'priority (P0..P3 score)',val:'2.92 / 3.0 → P3',pct:97,tone:'warn'},{lbl:'human_escalation (noul)',val:'0.98',pct:98,tone:'warn'},{lbl:'Bot Reply Permitted',val:'0% — Bypassed',pct:2,tone:'ok'}],
   pattern:'SAFETY ESCALATION · P3 IMMEDIATE HUMAN',
   nodes:[{role:'Inbound Msg',name:'High-Risk Signal',sub:'Injury / legal / repeat',state:'err'},{role:'MD-1.1 score',name:'2.92 / 3.0 (P3)',sub:'178 ms single call',state:'active'},{role:'Action',name:'Page Human P3',sub:'Bot bypassed immediately',state:'win'}],
   outcome:'✓ Scored P3 Immediate Human (2.92 / 3.0) in 178 ms — bypassed generative bot and paged safety specialist!',
   tag:'Calibrated P0–P3 Score',title:'High-Severity Injury / Dispute Escalated to Human',
   what:'Combined choice + score call detects physical harm or severe dispute risk in one pass and skips autonomous bot replies.',
   code:'answers.priority.score = 2.92 (>= 2.5) → pageSafetySpecialist()',
   bN:'Generic Chatbot',bV:'PR / Legal Risk ✕',bM:'Tone-deaf automated reply',aN:'P3 Human Specialist',aV:'178 ms Escalation',aM:'$0.00003 triage check',
   chips:[['Team: safety ✓','on'],['Priority: P3 ✕','denied'],['Bot Bypassed ✓','on']]
  };
 }
 if(prompt.length<85&&/(thanks|thank you|stop|unsubscribe|👍|got it|out of office|leave)/i.test(lower)){
  return {
   ctx:'Custom Inbound Filter · /v1/systemone',prompt:'"'+prompt+'"',
   scorer:'Microsoft-Decision-1.1 choice Router · 142 ms ($0.000013)',
   bars:[{lbl:'code_or_no_reply',val:'p = 0.97 · WINNER',pct:97,tone:'ok'},{lbl:'fast_slm',val:'p = 0.02',pct:4,tone:'muted'},{lbl:'frontier_sol',val:'p = 0.01',pct:3,tone:'muted'},{lbl:'LLM Tokens Spent',val:'0 tokens ($0)',pct:2,tone:'ok'}],
   pattern:'SHORT-CIRCUIT · DETERMINISTIC HANDLER',
   nodes:[{role:'Inbound Msg',name:'Routine Ack / Opt-Out',sub:'Zero reasoning needed',state:'active'},{role:'MD-1.1 choice',name:'p = 0.97',sub:'142 ms · $0.000013',state:'win'},{role:'Execution',name:'Code Handler ($0)',sub:'100% LLM skipped',state:'win'}],
   outcome:'✓ Short-circuited in 142 ms ($0.000013) — handled in deterministic code with $0 generative LLM cost!',
   tag:'Zero-LLM Short-Circuit',title:'Trivial Turn Handled Without Burning LLM Credits',
   what:'Acknowledgements and opt-outs never need a $15/1M frontier model. Decision-1.1 routes them to deterministic code for $0.000013.',
   code:'choice = "code_or_no_reply" (0.97) → $0 generative LLM spend',
   bN:'Always Frontier',bV:'$0.150 · 3.8 s',bM:'11,500× pricier overkill',aN:'Code Short-Circuit',aV:'$0.000013 · 0.14 s',aM:'Zero LLM tokens generated',
   chips:[['Choice: 0.97 ✓','on'],['LLM Cost: $0 ✓','on'],['Savings: -99.9% ✓','on']]
  };
 }
 if(/(slide|deck|powerpoint|chart|visual|image|renewal|proposal)/i.test(lower)){
  return {
   ctx:'Custom Multi-Job Prompt · Workplace Auto',prompt:'"'+prompt+'"',
   scorer:'Microsoft Copilot Auto · Experience Gate + Sub-Agent Router',
   bars:[{lbl:'Chat → Cowork Handoff',val:'p = 0.94 (MD-1.1)',pct:94,tone:'ok'},{lbl:'Work IQ Search (SLM)',val:'Assigned ✓',pct:85,tone:'accent'},{lbl:'Narrative & Deck (Opus 5.5)',val:'Assigned ✓',pct:95,tone:'accent'},{lbl:'Visuals (GPT Image 2.5)',val:'Assigned ✓',pct:92,tone:'ok'}],
   pattern:'MULTI-MODEL ORCHESTRATION · 3 LABS',
   nodes:[{role:'1 · Grounding',name:'Fast SLM',sub:'Emails, Teams & files',state:'active'},{role:'2 · Reasoning',name:'Claude Opus 5.5',sub:'Strategy & slide structure',state:'active'},{role:'3 · Visuals',name:'GPT Image 2.5',sub:'Charts & hero graphics',state:'win'}],
   outcome:'✓ Split into 3 specialized sub-jobs: SLM retrieval + Claude Opus 5.5 narrative + GPT Image 2.5 visuals!',
   tag:'Sub-Task Specialization',title:'Multi-Modal Deliverable Split Across Specialist Models',
   what:'Instead of forcing one model to search, write, and draw, Auto dispatches each sub-task to the lab that leads that capability.',
   code:'Cowork Auto → SLM (search) + Claude Opus 5.5 (deck) + GPT Image 2.5 (art)',
   bN:'Single General Model',bV:'Slow · Weak Art',bM:'Overpays on search & visuals',aN:'SLM + Opus + Image',aV:'-68% Cost · Best Fit',aM:'3 specialist models combined',
   chips:[['Handoff: Cowork ✓','on'],['3 Labs Used ✓','on'],['Cost: -68% ✓','on']]
  };
 }
 if(/(deadlock|lock-free|rust|aba|distributed|50k rps|architecture|security|formal|proof|critique)/i.test(lower)){
  return {
   ctx:'Custom Hard Engineering Prompt · High/Max Complexity',prompt:'"'+prompt+'"',
   scorer:'HyDRA / Foundry Ranker · High Reasoning & Verification Demand',
   bars:[{lbl:'Reasoning Demand',val:'0.93 (High)',pct:93,tone:'warn'},{lbl:'Debugging / Formal',val:'0.88 (High)',pct:88,tone:'warn'},{lbl:'Flash / Haiku Fit',val:'64% (Out of band)',pct:64,tone:'muted'},{lbl:'Frontier + Critic Fit',val:'97% · SELECTED',pct:97,tone:'ok'}],
   pattern:'ESCALATED · FRONTIER + CRITIQUE',
   nodes:[{role:'Router (~21ms)',name:'Crossed Band',sub:'Cheap models excluded',state:'active'},{role:'Primary',name:'Opus 5.5 / GPT-6.1 Sol',sub:'Deep reasoning tier',state:'active'},{role:'Verifier',name:'Read-Only Critic',sub:'Audits edge cases',state:'win'}],
   outcome:'✓ Detected deep formal/concurrency complexity — escalated to Frontier reasoning + read-only Critic audit!',
   tag:'Selective Frontier Escalation',title:'Hard Spec Escalated to Frontier + Critic Verification',
   what:'Weak models burn minutes in retry loops on hard specs. The router reserves frontier reasoning + critique strictly for prompts like this.',
   code:'Demand [0.93, 0.88] > Flash cap → Escalate to Opus 5.5 / GPT-6.1 Sol',
   bN:'Weak Model Loop',bV:'Retries & Bugs ✕',bM:'Fails subtle edge invariants',aN:'Frontier + Critic',aV:'Verified First Pass',aM:'Right-sized for hard task',
   chips:[['Escalated: Frontier ✓','on'],['Critic Verified ✓','on'],['Zero Retry Loop ✓','on']]
  };
 }
 return {
  ctx:'Custom Everyday Prompt · Balanced Mode',prompt:'"'+prompt+'"',
  scorer:'Foundry / HyDRA Ranker · 22 ms Overhead (Within 1–2% Band)',
  bars:[{lbl:'MAI Flash / DeepSeek Flash',val:'98.8% fit · WINNER',pct:99,tone:'ok'},{lbl:'Frontier Opus / Sol',val:'99.4% fit (20× cost)',pct:99,tone:'muted'},{lbl:'Reasoning Demand',val:'0.19 (Bounded)',pct:19,tone:'accent'},{lbl:'Router Latency',val:'22 ms',pct:12,tone:'ok'}],
  pattern:'SINGLE FAST PASS · BALANCED BAND',
  nodes:[{role:'ML Ranker',name:'22 ms Check',sub:'Within 1–2% of #1',state:'active'},{role:'Selected Model',name:'Flash / Haiku 5.5',sub:'Fast single pass',state:'win'},{role:'Frontier Tier',name:'Saved!',sub:'-92% token cost',state:'skip'}],
  outcome:'✓ Bounded task complexity — served in one fast pass on Flash/Haiku within 1% of frontier quality (-92% cost)!',
  tag:'1–2% Quality Band Win',title:'Everyday Prompt Served Fast at 1/12th Frontier Cost',
  what:'When lightweight models score within 1–2% of frontier quality, Balanced routing picks the fast model automatically.',
  code:'Band(1–2%) → MAI Code 2 Flash / DeepSeek-V4.1-Flash (-92% cost)',
  bN:'Always Frontier',bV:'$0.045 · 3.4 s',bM:'12× unnecessary spend',aN:'Flash / Haiku 5.5',aV:'$0.003 · 0.8 s',aM:'22 ms router · Single pass',
  chips:[['Router: 22 ms ✓','on'],['Cost: -92% ✓','on'],['Speed: 4× faster ✓','on']]
 };
}

function runCustomProbe(cmd){
 if(!cmd||stepRunning)return;
 stopAutoPlay();
 rawLog='';
 if(hintShown){displayLog='';hintShown=false;}
 var r=classifyCustomPrompt(cmd);
 applyLocalProbeCard(r);
 appendTerminal((displayLog?'\\n':'')+'──▶ [Custom Prompt Probe]\\n[CONFIG] '+r.scorer+'\\n[REQUEST] '+r.prompt+'\\n');
 if(!replayMode){
  stepRunning=true;renderTabsAndPills();
  setStatus('Probing Live…','running');
  fetch('/api/custom-prompt',{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8'},body:cmd}).catch(function(){
   stepRunning=false;renderTabsAndPills();
   appendTerminal(r.outcome.replace(/^✓ /,'✓ PASS — ')+'\\nWhy: '+r.what+'\\n');
   setStatus('Probe Routed ✓','ok');
  });
  return;
 }
 var isHold=/Blocked|HELD|Injury|Escalated/i.test(r.outcome+' '+r.title);
 appendTerminal((isHold?'✕ ESCALATED / HELD — '+r.title+'\\n':'')+r.outcome.replace(/^✓ /,'✓ PASS — ')+'\\nWhy: '+r.what+'\\n[SOURCE] Heuristic Custom Probe Simulator (run `npm --prefix demo run demo:web` for live CLI / Foundry probe)\\n');
 appendRaw('──▶ [Custom Prompt Probe · Simulated Raw Payload]\\n# PROVENANCE: Client-side rule preview in static Replay mode; start `npm --prefix demo run demo:web` for live Copilot CLI / Decision-1.1 JSON.\\n'+JSON.stringify({prompt:cmd,pattern:r.pattern,rule:r.code,verdict:r.title},null,2)+'\\n');
 setStatus('Probe Routed ✓','ok');
}

function closeLiveDemo(){
 closeAllSelects();
 stopAutoPlay();clearReplayTimers();resolveStepWaiters(false);
 if(liveOpen&&!replayMode)fetch('/api/cancel',{method:'POST'}).catch(function(){});
 if(liveSource){liveSource.close();liveSource=null;}
 byId('live-demo').hidden=true;liveOpen=false;
}

async function connectLive(){
 if(!isLocalDemoHost()){replayMode=true;setStatus(idleModeLabel());return;}
 try{
  var meta=await fetch('/api/meta').then(function(r){if(!r.ok)throw new Error('unavailable');return r.json();});
  liveMeta=meta;
  replayMode=false;
  setStatus(idleModeLabel(),'ok');
  if(liveSource)liveSource.close();
  liveSource=new EventSource('/api/events');
  liveSource.onmessage=function(event){applyDemoEvent(JSON.parse(event.data));};
 }catch(_e){liveMeta=null;replayMode=true;setStatus(idleModeLabel());}
}

async function openLiveDemo(preferredKind,preferredStep){
 if(deck.closeNotes)deck.closeNotes();
 byId('live-demo').hidden=false;liveOpen=true;
 replayMode=!isLocalDemoHost();
 activeProbeVisual=null;
 var k=preferredKind||'fusion',s=Number(preferredStep)||1;
 syncViewSwitch();
 renderVisualStep(k,s);
 showInitialHint();
 flushTerminal();
 setStatus(idleModeLabel());
 if(!replayMode)await connectLive();
}

async function runSingleStep(kind,step){
 if(replayMode)return await playRecordedStep(kind,step);
 try{
  var waitDone=new Promise(function(resolve){stepDoneWaiters.push(resolve);});
  var response=await fetch('/api/run-step?demo='+encodeURIComponent(kind)+'&step='+step,{method:'POST'});
  if(!response.ok){resolveStepWaiters(false);throw new Error('Step request rejected');}
  return await waitDone;
 }catch(error){
  setStatus('Error','err');
  appendTerminal('\\n[Error] '+(error.message||String(error))+'\\n');
  return false;
 }
}

async function toggleAutoPlay(){
 if(autoPlaying){stopAutoPlay();return;}
 if(stepRunning)return;
 var total=SCENARIOS[curKind].steps.length,allDone=true;
 for(var k=1;k<=total;k++){if(!doneSet[curKind][k]){allDone=false;break;}}
 if(allDone)resetScenario(curKind);
 autoPlaying=true;syncAutoPlayBtn();
 var start=doneSet[curKind][curStep]&&curStep<total?curStep+1:curStep;
 for(var s=start;s<=total;s++){
  if(!autoPlaying)break;
  var ok=await runSingleStep(curKind,s);
  if(!ok||!autoPlaying)break;
  if(s<total)await new Promise(function(r){var t=setTimeout(r,680);replayTimers.push(t);});
 }
 stopAutoPlay();
}

setupCustomSelect('cs-kind',function(val){
 if(stepRunning||val===curKind)return;
 stopAutoPlay();
 activeProbeVisual=null;
 displayLog='';rawLog='';hintShown=false;
 byId('live-demo-output').innerHTML='';
 renderVisualStep(val,1,true);
 showInitialHint();
 flushTerminal();
 setStatus(idleModeLabel(),replayMode?undefined:'ok');
});
setupCustomSelect('cs-step',function(val){
 if(stepRunning)return;
 stopAutoPlay();
 activeProbeVisual=null;
 rawLog='';
 renderVisualStep(curKind,Number(val)||1,true);
 flushTerminal();
});
byId('btn-view-visual').addEventListener('click',function(){viewMode='visual';syncViewSwitch();flushTerminal();});
byId('btn-view-summary').addEventListener('click',function(){viewMode='summary';syncViewSwitch();flushTerminal();});
byId('btn-view-raw').addEventListener('click',function(){viewMode='raw';syncViewSwitch();flushTerminal();});
byId('live-demo-run').addEventListener('click',function(){
 if(stepRunning)return;
 stopAutoPlay();
 var target=Number(byId('live-demo-run').dataset.targetStep)||curStep;
 runSingleStep(curKind,target);
});
byId('live-demo-autoplay').addEventListener('click',toggleAutoPlay);
byId('live-demo-reset').addEventListener('click',function(){resetScenario(curKind);});
byId('live-probe-form').addEventListener('submit',function(ev){
 ev.preventDefault();
 var inp=byId('live-probe-input'),cmd=inp.value.trim();
 if(!cmd||stepRunning)return;
 inp.value='';
 runCustomProbe(cmd);
});
document.querySelectorAll('.live-demo-trigger').forEach(function(button){
 button.addEventListener('click',function(event){
  event.stopPropagation();
  openLiveDemo(button.dataset.demo||'fusion',Number(button.dataset.step||1));
 });
});
deck.openStudio=openLiveDemo;
byId('live-demo-close').addEventListener('click',closeLiveDemo);
})();
"""

PRESENTER_JS = """
(function(){
var isLocalOrigin=location.protocol==='file:'||['127.0.0.1','localhost','[::1]','::1'].includes(location.hostname);
if(!isLocalOrigin){
 ['deck-hud','notes-drawer'].forEach(function(id){var el=document.getElementById(id);if(el)el.remove();});
 return;
}
var deck=window.__DECK__;if(!deck)return;
var hudCount=document.getElementById('hud-count'),hud=document.getElementById('deck-hud'),notesDrawer=document.getElementById('notes-drawer');
if(!hud||!notesDrawer)return;
var S=deck.S,notesOpen=false;
function byId(id){return document.getElementById(id);}
function pad2(n){return n<10?'0'+n:String(n);}
function syncNotes(){
 var idx=deck.getIndex(),num=pad2(idx+1),isZh=(document.documentElement.lang||'').indexOf('zh')===0;
 if(hudCount)hudCount.textContent=num+' / '+pad2(S.length);
 byId('notes-title').textContent=(isZh?'讲者备注 · 第 '+num+' 页':'Speaker Notes · Slide '+num);
 var txt=(window.SLIDE_NOTES&&window.SLIDE_NOTES[String(idx)])||(isZh?'（本页无备注）':'(No notes for this slide)');
 byId('notes-body').textContent=txt;
}
function toggleNotes(force){
 notesOpen=typeof force==='boolean'?force:!notesOpen;
 notesDrawer.hidden=!notesOpen;
 hud.classList.toggle('notes-open',notesOpen);
 byId('hud-notes-btn').setAttribute('aria-expanded',String(notesOpen));
 syncNotes();
}
function defaultDemoForSlide(idx){
 if([6,7,8,11,12,22].indexOf(idx)!==-1)return 'foundry';
 if([16,17,18,19,20,23].indexOf(idx)!==-1)return 'decision';
 return 'fusion';
}
deck.closeNotes=function(){if(notesOpen)toggleNotes(false);};
deck.onRender=function(){syncNotes();};
syncNotes();
byId('hud-notes-btn').addEventListener('click',function(ev){ev.stopPropagation();toggleNotes();});
byId('notes-close').addEventListener('click',function(){toggleNotes(false);});
byId('hud-demo-btn').addEventListener('click',function(ev){ev.stopPropagation();if(deck.openStudio)deck.openStudio(defaultDemoForSlide(deck.getIndex()),1);});
addEventListener('keydown',function(ev){
 if(ev.altKey||ev.ctrlKey||ev.metaKey||deck.isOverlayOpen())return;
 var k=ev.key;
 if(ev.target&&ev.target.closest('input,textarea,select,[contenteditable="true"]')&&k!=='Escape')return;
 if(k==='Escape'&&notesOpen){ev.preventDefault();toggleNotes(false);return;}
 if(k==='n'||k==='N'){ev.preventDefault();toggleNotes();}
 else if(k==='d'||k==='D'){ev.preventDefault();if(deck.openStudio)deck.openStudio(defaultDemoForSlide(deck.getIndex()),1);}
},true);
})();
"""

PUBLIC_JS = DECK_JS + "\n" + STUDIO_JS
JS = PUBLIC_JS + "\n" + PRESENTER_JS

def load_recorded_demo(img_dir):
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(img_dir)), 'demo-recordings.json'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'demo-recordings.json'),
    ]
    for path in candidates:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return 'null'

def lang_switch_html(lang='en', alt_href=None):
    if not alt_href:
        return ''
    if lang == 'zh':
        return (
            '<nav class="lang-switch" aria-label="语言切换">'
            f'<a class="lang-pill" href="{e(alt_href)}" data-base-href="{e(alt_href)}">EN</a>'
            '<span class="lang-pill active" aria-current="page">中文</span>'
            '</nav>'
        )
    return (
        '<nav class="lang-switch" aria-label="Language switch">'
        '<span class="lang-pill active" aria-current="page">EN</span>'
        f'<a class="lang-pill" href="{e(alt_href)}" data-base-href="{e(alt_href)}">中文</a>'
        '</nav>'
    )

def localize_demo_fragment(fragment, lang='en'):
    if lang != 'zh':
        return fragment
    localized = fragment
    for source, target in sorted(ZH_DEMO_TEXT_MAP.items(), key=lambda item: len(item[0]), reverse=True):
        localized = localized.replace(source, target)
    return localized

def build(out, img_dir, maxw, pages_url=None, presenter_tools=True, lang='en', alt_href=None):
    loc_slides = D.get_localized_slides(lang)
    loc_notes = D.get_localized_notes(lang)
    D.validate_layout(loc_slides)
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    effective_url = pages_url if pages_url is not None else os.environ.get('PAGES_URL')
    body = ''.join(slide_html(k, loc_slides[k], img_dir, maxw, pages_url=effective_url, lang=lang) for k in sorted(loc_slides))
    recorded_json = load_recorded_demo(img_dir)
    if presenter_tools:
        notes_json = json.dumps({str(k): v for k, v in loc_notes.items()}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        presenter_block = f"\n{presenter_ui_html(lang)}"
        data_script = f"<script>window.RECORDED_DEMO={recorded_json};window.SLIDE_NOTES={notes_json};</script>"
        script_body = localize_demo_fragment(JS, lang)
    else:
        presenter_block = ""
        data_script = f"<script>window.RECORDED_DEMO={recorded_json};</script>"
        script_body = localize_demo_fragment(PUBLIC_JS, lang)
    html_lang = 'zh-CN' if lang == 'zh' else 'en'
    doc_title = (
        '大模型自动路由 Auto-routing LLMs — 兼顾效果、成本与速度的模型选型实践'
        if lang == 'zh'
        else 'Auto-routing LLMs — Balancing Quality, Cost &amp; Latency with Decision Models and Microsoft Copilot'
    )
    lang_nav = lang_switch_html(lang=lang, alt_href=alt_href)
    live_demo_html = localize_demo_fragment(LIVE_DEMO, lang)
    doc = f"""<!DOCTYPE html>
<html lang="{html_lang}" dir="ltr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{doc_title}</title>
<style>{CSS % (D.BG, D.INK, D.CY, D.CARD, D.CODEBG, D.EDGE, D.MUTED, D.AMB)}</style></head>
<body><div id="deck-progress" aria-hidden="true"></div><main id="stage">{body}</main>{lang_nav}{presenter_block}
{live_demo_html}
{data_script}
<script>{script_body}</script></body></html>"""
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(doc)
    print(f'Saved {out}  ({len(loc_slides)} slides, lang={lang}, {os.path.getsize(out)/1e6:.2f} MB)')

if __name__ == '__main__':
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(root, 'dist', 'html', 'index.html'))
    ap.add_argument('--images', default=os.path.join(here, 'assets', 'images'))
    ap.add_argument('--maxw', type=int, default=1600, help='max image edge in px')
    ap.add_argument('--pages-url', default=None, help='GitHub Pages URL for Slide 1 QR code')
    ap.add_argument('--lang', choices=('en', 'zh'), default='en', help='Deck language (en or zh)')
    ap.add_argument('--alt-href', default=None, help='Alternate language deck link')
    ap.add_argument('--public-pages', action='store_true', help='omit Notes, Studio, and N/D shortcuts for public GitHub Pages')
    a = ap.parse_args(); build(a.out, a.images, a.maxw, pages_url=a.pages_url, presenter_tools=not a.public_pages, lang=a.lang, alt_href=a.alt_href)
