#!/usr/bin/env python3
"""build_html.py - turns the same 26 slides into ONE self-contained HTML file
(images & interactive Demo Studio recordings embedded, no external files).

Usage:  pip install pillow
        python -m presentation.src.build_html [--out dist/html/index.html]
Keys in the browser: <- / -> or Space to navigate, F = fullscreen,
Home/End = first/last, N = speaker notes, D = open interactive Auto-Routing Studio.
Print (Ctrl+P) gives one slide per page.
"""
import argparse, base64, html, io, json, os
from PIL import Image
try:
    from . import build_pptx as D
except ImportError:
    import build_pptx as D

PX = 9525  # EMU per CSS px  (slide = 1280 x 720 px)
SVG_POINTS = {
    'rightArrow':'0,24 68,24 68,0 100,50 68,100 68,76 0,76',
    'leftArrow':'32,0 32,24 100,24 100,76 32,76 32,100 0,50',
    'downArrow':'24,0 76,0 76,62 100,62 50,100 0,62 24,62',
    'chevron':'0,0 82,0 100,50 82,100 0,100 18,50',
    'homePlate':'0,0 82,0 100,50 82,100 0,100',
}
FALLBACK = {
    'Plus Jakarta Sans':'"Plus Jakarta Sans","Inter","Segoe UI Variable Display","Segoe UI",-apple-system,BlinkMacSystemFont,sans-serif',
    'Newsreader':'"Newsreader","Fraunces",Georgia,"Times New Roman",serif',
    'JetBrains Mono':'"JetBrains Mono","Cascadia Code","Fira Code",Consolas,monospace',
    'Aptos Display':'"Plus Jakarta Sans","Aptos Display","Segoe UI Variable Display","Segoe UI",sans-serif',
    'Aptos':'"Plus Jakarta Sans",Aptos,"Segoe UI Variable Text","Segoe UI",sans-serif',
    'Cascadia Code':'"JetBrains Mono","Cascadia Code","Cascadia Mono",Consolas,monospace',
    'Georgia':'"Newsreader",Georgia,"Times New Roman",serif',
    'Calibri':'"Plus Jakarta Sans",Calibri,"Segoe UI",sans-serif',
    'Courier New':'"JetBrains Mono","Courier New",Consolas,monospace',
    'Arial':'"Plus Jakarta Sans",Arial,Helvetica,sans-serif',
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
    font = FALLBACK.get(raw_font, FALLBACK['Plus Jakarta Sans'])
    is_display = any(p.get('sizePt', o.get('sizePt', 16)) >= 29 for p in paras)
    if is_display and raw_font != D.MF:
        font = '"Newsreader","Plus Jakarta Sans",Georgia,serif'
    ls = f"letter-spacing:{o['letterSpacingPt']*4/3:.1f}px;" if o.get('letterSpacingPt') else ('letter-spacing:-0.02em;' if is_display else '')
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
    3: (4, 5, 4),
    6: (2, 5, 4),
}

DEMO_LAUNCHERS = {
    10: ('fusion', '1', 'Replay Fusion Demo'),
    12: ('foundry', '1', 'Replay Foundry Demo'),
    20: ('decision', '1', 'Replay Decision-1.1 Demo'),
    21: ('fusion', '1', 'Launch Demo 1 · Copilot Fusion'),
    22: ('foundry', '1', 'Launch Demo 2 · Foundry & Copilot'),
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

def slide_html(k, ops, img_dir, maxw):
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
            parts.append(f'<div class="{classes}"{reveal} style="{box(o)}">{text_html(o)}</div>')
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
                if fill == D.CODEBG:
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
    if k in DEMO_LAUNCHERS:
        demo_kind, demo_step, label = DEMO_LAUNCHERS[k]
        action = (
            f'<button class="live-demo-trigger" type="button" '
            f'data-demo="{demo_kind}" data-step="{demo_step}">'
            f'<span class="pulse-dot" aria-hidden="true"></span><span>{e(label)}</span>'
            f'<span class="trigger-arrow" aria-hidden="true">↗</span></button>'
        )
    return f'<section class="slide" data-n="{k+1}" data-reveals="{reveal_count}" aria-label="Slide {k+1}">{"".join(parts)}{action}</section>'

PRESENTER_UI = """
<div id="deck-hud" class="deck-hud" aria-label="Presenter toolbar">
  <span class="hud-count" id="hud-count"></span>
  <button type="button" class="hud-btn" id="hud-notes-btn" title="Toggle Chinese speaker notes (N)" aria-controls="notes-drawer" aria-expanded="false">Notes <kbd>N</kbd></button>
  <button type="button" class="hud-btn hud-btn-accent" id="hud-demo-btn" title="Open Visual Auto-Routing Studio (D)">Studio <kbd>D</kbd></button>
</div>

<aside id="notes-drawer" class="notes-drawer" aria-label="Speaker notes" hidden>
  <div class="notes-head">
    <strong id="notes-title" lang="zh-CN">讲者备注</strong>
    <button type="button" class="notes-close" id="notes-close" aria-label="Close speaker notes">✕</button>
  </div>
  <div class="notes-body" id="notes-body" lang="zh-CN"></div>
</aside>
"""

LIVE_DEMO = """
<section id="live-demo" class="live-demo" role="dialog" aria-modal="true" aria-label="Visual Auto-Routing Studio" hidden>
  <div class="studio-shell">
    <header class="studio-top">
      <div class="scenario-tabs" role="tablist" aria-label="Routing scenario">
        <button type="button" role="tab" class="sc-tab active" data-kind="fusion" aria-selected="true">1 · Coding Agent <span class="tab-sub">Fusion</span></button>
        <button type="button" role="tab" class="sc-tab" data-kind="foundry" aria-selected="false">2 · Cloud API <span class="tab-sub">Foundry</span></button>
        <button type="button" role="tab" class="sc-tab" data-kind="decision" aria-selected="false">3 · App Controller <span class="tab-sub">Decision-1.1</span></button>
      </div>

      <div class="step-pills" id="step-pills" role="group" aria-label="Scenario steps"></div>

      <div class="studio-actions">
        <button id="live-demo-run" class="primary-run-btn" type="button">
          <span id="live-run-label">Run Step 1</span>
          <span aria-hidden="true">▶</span>
        </button>
        <button id="live-demo-autoplay" class="ghost-btn autoplay-btn" type="button" title="Play all 5 steps sequentially">
          <span id="live-autoplay-label">Auto-Play</span>
        </button>
        <span class="status-badge" id="live-demo-status">Replay · Verified</span>
        <button id="live-demo-reset" class="ghost-btn" type="button" title="Reset scenario">Reset</button>
        <button id="live-demo-close" class="close-btn" type="button" aria-label="Close studio">✕</button>
      </div>
    </header>

    <div class="demo-purpose-bar" id="demo-purpose-bar">
      <span class="purpose-kicker" id="purpose-kicker">DEMO 1 GOAL</span>
      <strong id="purpose-title">Coding Agent Orchestration</strong>
      <span class="purpose-sep" aria-hidden="true">—</span>
      <span id="purpose-desc">See how GitHub Copilot Auto &amp; Fusion picks 1 fast model for easy edits, escalates hard bugs via Judge/Critics, and protects warm caches.</span>
    </div>

    <div class="studio-grid">
      <section class="terminal-card">
        <div class="terminal-chrome">
          <div class="chrome-dots" aria-hidden="true"><span></span><span></span><span></span></div>
          <div class="chrome-title">
            <strong id="terminal-mode-title">GitHub Copilot CLI · Auto &amp; Fusion</strong>
            <span id="terminal-mode-sub">SINGLE · NO REVIEW OVERHEAD</span>
          </div>
          <div class="term-legend" aria-label="Color legend">
            <span class="lg-item lg-pol">Config</span>
            <span class="lg-item lg-run">Request</span>
            <span class="lg-item lg-ok">✓ Pass</span>
            <span class="lg-item lg-err">✕ Escalate / Hold</span>
            <span class="lg-item lg-log">Log</span>
          </div>
        </div>

        <div class="route-strip" id="vis-nodes" aria-label="Routing flow"></div>

        <pre class="studio-terminal" id="live-demo-output" role="log" aria-live="polite"></pre>

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
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@450;600;700&family=Newsreader:ital,opsz,wght@0,6..72,600;0,6..72,700;1,6..72,500&family=Plus+Jakarta+Sans:wght@450;500;600;700;800&display=swap');
:root{
  --bg:#%s;--ink:#%s;--accent:#%s;--card:#%s;--codebg:#%s;--edge:#%s;--muted:#%s;--warn:#%s;
  --surface:#fbf8f2;--surface-strong:#efe9dc;--ink-soft:#4a463f;--ok:#1f6344;--ok-bg:#e6f4ec;
  --font-sans:'Plus Jakarta Sans','Inter','Segoe UI Variable Text','Segoe UI',system-ui,sans-serif;
  --font-display:'Newsreader','Plus Jakarta Sans',Georgia,serif;
  --font-mono:'JetBrains Mono','Cascadia Code',Consolas,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:100%%;height:100%%;background:var(--bg);color:var(--ink);font-family:var(--font-sans);overflow:hidden;overscroll-behavior:none;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
#stage{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;overflow:hidden;background:radial-gradient(circle at 18%% 12%%,rgba(255,255,255,.55),transparent 48%%),var(--bg)}
.slide{position:absolute;width:1280px;height:720px;background:linear-gradient(180deg,rgba(255,255,255,.28) 0%%,rgba(255,255,255,0) 38%%),var(--bg);overflow:hidden;display:none;transform-origin:center center}
.slide.on{display:block;animation:slideFade .24s cubic-bezier(.2,.8,.2,1)}
@keyframes slideFade{from{opacity:.88}to{opacity:1}}
.a{position:absolute}
.surface-card{box-shadow:0 10px 28px rgba(38,33,26,.055),inset 0 1px 0 rgba(255,255,255,.55)}
.surface-code{border-radius:14px!important;box-shadow:0 12px 30px rgba(32,45,58,.07),inset 0 1px 0 rgba(255,255,255,.8)!important}
.framed-img{border-radius:14px;box-shadow:0 14px 34px rgba(35,30,22,.10);object-fit:cover}
.contain-img{border-radius:10px;object-fit:contain!important}
.reveal{opacity:0;visibility:hidden;transform:translateY(10px);transition:opacity .28s ease,transform .28s cubic-bezier(.2,.8,.2,1),visibility .28s}
.reveal.shown{opacity:1;visibility:visible;transform:translateY(0)}
.svg-shape svg{position:absolute;inset:0;width:100%%;height:100%%;overflow:visible;filter:drop-shadow(0 4px 10px rgba(35,48,62,.08))}
.svg-shape>.t{z-index:1}
img.a{object-fit:cover}
.t{position:absolute;inset:0;padding:10px 14px;display:flex;flex-direction:column;justify-content:center}
.ref-link{color:inherit;text-decoration:underline;text-decoration-color:rgba(63,96,126,.42);text-underline-offset:3px;transition:color .14s ease,text-decoration-color .14s ease}
.ref-link:hover{color:#1f384e;text-decoration-color:currentColor}

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

.live-demo{position:fixed;inset:0;z-index:120;background:radial-gradient(circle at 12%% 0%%,#faf7f0 0%%,var(--bg) 62%%);color:var(--ink);font-family:var(--font-sans);padding:clamp(10px,1.5vw,20px);overflow:hidden}
.live-demo[hidden]{display:none!important}
.studio-shell{width:100%%;height:100%%;max-width:1540px;min-width:0;margin:0 auto;display:grid;grid-template-rows:auto auto minmax(0,1fr);gap:10px;min-height:0}
.studio-top{display:flex;align-items:center;justify-content:space-between;gap:8px;background:var(--surface);border:1px solid var(--edge);border-radius:13px;padding:7px 11px;box-shadow:0 4px 16px rgba(35,30,22,.05);flex-wrap:wrap;min-width:0}
.scenario-tabs{display:inline-flex;background:var(--card);padding:3px;border-radius:9px;gap:3px;flex-shrink:0}
.sc-tab{border:0;background:transparent;color:var(--muted);padding:6px 11px;border-radius:7px;font:700 12px/1 var(--font-sans);cursor:pointer;transition:all .14s ease;white-space:nowrap;display:inline-flex;align-items:baseline;gap:5px}
.sc-tab .tab-sub{font:600 10px/1 var(--font-mono);opacity:.75}
.sc-tab:hover{color:var(--ink)}
.sc-tab.active{background:#fff;color:var(--accent);box-shadow:0 2px 6px rgba(35,30,22,.08)}

.step-pills{display:inline-flex;align-items:center;gap:5px;flex-wrap:wrap;min-width:0}
.step-pill{border:1px solid var(--edge);background:#fff;color:var(--muted);border-radius:8px;padding:6px 9px;font:700 10.8px/1 var(--font-mono);cursor:pointer;display:inline-flex;align-items:center;gap:4px;transition:all .14s ease;white-space:nowrap}
.step-pill:hover:not(:disabled){border-color:var(--accent);color:var(--ink)}
.step-pill.active{background:rgba(63,96,126,.12);border-color:var(--accent);color:var(--accent)}
.step-pill.done{border-color:#8ec4a8;color:var(--ok)}
.step-pill.active.done{background:var(--ok-bg);border-color:var(--ok);color:var(--ok)}
.step-pill:disabled{opacity:.5;cursor:wait}

.studio-actions{display:flex;align-items:center;gap:6px;flex-shrink:0}
.primary-run-btn{display:inline-flex;align-items:center;gap:6px;border:0;border-radius:9px;background:linear-gradient(135deg,var(--accent) 0%%,#2a455d 100%%);color:#fff;padding:8px 14px;font:700 12px/1 var(--font-sans);cursor:pointer;box-shadow:0 4px 12px rgba(44,73,99,.22);white-space:nowrap}
.primary-run-btn:hover:not(:disabled){filter:brightness(1.06)}
.primary-run-btn:disabled{opacity:.52;cursor:wait}
.ghost-btn{border:1px solid var(--edge);background:#fff;color:var(--ink);border-radius:9px;padding:7px 11px;font:600 11.5px/1 var(--font-sans);cursor:pointer;white-space:nowrap}
.ghost-btn:hover,.ghost-btn.active{background:var(--card);border-color:var(--accent);color:var(--accent)}
.autoplay-btn.active{background:#fef4ea;border-color:#d48a42;color:#9a5313}
.status-badge{border-radius:999px;padding:5px 10px;font:600 10.5px/1 var(--font-mono);background:var(--card);color:var(--muted);border:1px solid var(--edge);white-space:nowrap}
.status-badge[data-tone="running"]{background:#fef4ea;border-color:#d48a42;color:#9a5313}
.status-badge[data-tone="ok"]{background:var(--ok-bg);border-color:#286b4b;color:var(--ok)}
.status-badge[data-tone="err"]{background:#faece8;border-color:var(--warn);color:var(--warn)}
.close-btn{width:30px;height:30px;border-radius:9px;border:1px solid var(--edge);background:#fff;color:var(--ink);font-size:13px;cursor:pointer;display:grid;place-items:center}
.close-btn:hover{background:var(--warn);color:#fff;border-color:var(--warn)}

.demo-purpose-bar{display:flex;align-items:center;gap:9px;background:var(--surface);border:1px solid var(--edge);border-left:4px solid var(--accent);border-radius:10px;padding:8px 14px;font-size:13px;line-height:1.35;color:var(--ink-soft);min-width:0}
.purpose-kicker{background:rgba(63,96,126,.12);color:var(--accent);border-radius:5px;padding:3px 7px;font:800 9.5px/1 var(--font-mono);letter-spacing:.08em;flex-shrink:0}
.demo-purpose-bar strong{color:var(--ink);font-weight:700;flex-shrink:0}
.purpose-sep{color:var(--muted);flex-shrink:0}
#purpose-desc{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

.studio-grid{display:grid;grid-template-columns:minmax(0,1.36fr) minmax(0,.92fr);gap:14px;min-height:0}
.terminal-card{display:flex;flex-direction:column;min-height:0;min-width:0;background:#0d151d;border-radius:14px;border:1px solid #243442;overflow:hidden;box-shadow:0 16px 38px rgba(16,24,32,.20)}
.terminal-chrome{display:flex;align-items:center;gap:10px;padding:10px 14px;background:#15212c;border-bottom:1px solid #233342;color:#b8cad8;font:500 11.5px var(--font-mono);min-width:0;flex-shrink:0}
.chrome-dots{display:flex;gap:6px;flex-shrink:0}.chrome-dots span{width:9px;height:9px;border-radius:50%%;background:#3a4b59}.chrome-dots span:first-child{background:#d46a5e}.chrome-dots span:nth-child(2){background:#deb05b}.chrome-dots span:nth-child(3){background:#5fb384}
.chrome-title{display:flex;align-items:baseline;gap:10px;min-width:0;flex:1;overflow:hidden}.chrome-title strong{color:#f2f7fb;font-weight:600;white-space:nowrap}.chrome-title span{color:#8fa4b5;font-size:10.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.term-legend{display:flex;align-items:center;gap:5px;flex-shrink:0;flex-wrap:wrap}
.lg-item{font:700 9.8px/1 var(--font-mono);padding:3px 7px;border-radius:999px;border:1px solid transparent}
.lg-pol{color:#93c5fd;background:rgba(147,197,253,.12);border-color:rgba(147,197,253,.28)}
.lg-run{color:#fcd34d;background:rgba(252,211,77,.12);border-color:rgba(252,211,77,.28)}
.lg-ok{color:#4ade80;background:rgba(74,222,128,.13);border-color:rgba(74,222,128,.32)}
.lg-err{color:#f87171;background:rgba(248,113,113,.14);border-color:rgba(248,113,113,.34)}
.lg-log{color:#cbd5e1;background:rgba(203,213,225,.10);border-color:rgba(203,213,225,.22)}

.route-strip{display:flex;align-items:stretch;gap:7px;padding:10px 14px;background:#111b25;border-bottom:1px solid #223241;flex-shrink:0;min-width:0}
.tnode{flex:1 1 0;min-width:0;background:#172431;border:1px solid #293b4d;border-radius:9px;padding:7px 10px;display:flex;flex-direction:column;justify-content:center;gap:2px}
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

.studio-terminal{flex:1;min-height:0;overflow:auto;margin:0;padding:14px 16px;color:#cbd5e1;font:450 12.2px/1.56 var(--font-mono);white-space:pre-wrap;word-break:break-word;scrollbar-color:#445a6c #0d151d}
.tl{display:block;padding:1px 6px;border-radius:4px}
.tl-hint{color:#94a3b8;font-style:italic}
.tl-step{color:#7cc4f8;font-weight:700;margin-top:10px;padding-top:7px;border-top:1px dashed rgba(124,196,248,.24)}
.tl-step:first-child{margin-top:0;padding-top:1px;border-top:0}
.tl-policy{color:#93c5fd;font-weight:700;margin-top:3px}
.tl-run{color:#fcd34d;font-weight:700;margin-top:3px}
.tl-pass{color:#4ade80;font-weight:700;background:rgba(34,197,94,.13);border-left:3px solid #22c55e;padding:4px 9px;margin:4px 0 2px;border-radius:0 6px 6px 0}
.tl-fail{color:#f87171;font-weight:700;background:rgba(239,68,68,.15);border-left:3px solid #ef4444;padding:4px 9px;margin:4px 0 2px;border-radius:0 6px 6px 0}
.tl-why{color:#fde68a;padding-left:9px;margin-bottom:2px}
.tl-log{color:#cbd5e1}

.probe-form{display:flex;align-items:center;gap:8px;padding:9px 14px;background:#121d27;border-top:1px solid #223241;flex-shrink:0}
.composer-prompt{color:#7cc4f8;font:700 11.5px/1 var(--font-mono);flex-shrink:0}
.probe-form input{flex:1;min-width:0;border:1px solid #2a3d4f;border-radius:7px;background:#091017;color:#f3f8fc;padding:7px 10px;font:450 12px/1.2 var(--font-mono);outline:none}
.probe-form input:focus{border-color:#6cb4e8}
.probe-form button{border:0;border-radius:7px;background:#3a7099;color:#fff;padding:7px 13px;font:700 12px/1 var(--font-sans);cursor:pointer;white-space:nowrap}
.probe-form button:hover{filter:brightness(1.08)}

.value-rail{display:flex;flex-direction:column;gap:14px;min-height:0;min-width:0;overflow-y:auto;overflow-x:hidden}
.narrative-card,.compare-card{background:var(--surface);border:1px solid var(--edge);border-radius:14px;padding:16px 18px;box-shadow:0 6px 20px rgba(35,30,22,.04);min-width:0}
.narrative-card{border-top:3px solid var(--accent);display:flex;flex-direction:column;gap:10px}
.narrative-top{display:flex;align-items:center;justify-content:space-between;gap:8px}
.step-badge{background:rgba(63,96,126,.12);color:var(--accent);border-radius:999px;padding:4px 10px;font:800 10px/1 var(--font-mono);letter-spacing:.08em;flex-shrink:0}
.boundary-tag{color:var(--muted);font:600 11px/1 var(--font-mono);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.narrative-card h3{font:700 19px/1.22 var(--font-display);color:var(--ink)}
.explain-summary{color:var(--ink-soft);font-size:13.5px;line-height:1.52}
.explain-code-wrap{background:var(--codebg);border:1px solid var(--edge);border-radius:9px;padding:9px 12px;margin-top:2px;min-width:0}
.policy-kicker{font:800 9.5px/1 var(--font-mono);letter-spacing:.08em;color:var(--muted);margin-bottom:6px}
.explain-code-wrap pre{margin:0;font:600 11.2px/1.42 var(--font-mono);color:var(--accent);white-space:pre-wrap;word-break:break-word}

.compare-card{display:flex;flex-direction:column;gap:13px}
.section-head{display:flex;align-items:baseline;justify-content:space-between;gap:8px}
.section-head strong{font:700 14px/1.1 var(--font-sans);color:var(--ink)}
.section-head span{font:500 11px/1 var(--font-mono);color:var(--muted)}
.identity-versus{display:grid;grid-template-columns:1fr 28px 1fr;gap:9px;align-items:stretch}
.id-box{background:var(--card);border-radius:11px;padding:12px 13px;min-width:0;border-top:3px solid #8c8476;display:flex;flex-direction:column;gap:3px}
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

@media(max-width:1240px){
  .status-badge,.sc-tab .tab-sub{display:none}
  .sc-tab{padding:5px 9px;font-size:11.5px}
  .step-pill{padding:5px 7px;font-size:10px}
}
@media(max-width:960px){
  .live-demo{overflow:auto}
  .studio-shell{height:auto}
  .studio-top,.demo-purpose-bar{flex-wrap:wrap}
  #purpose-desc{white-space:normal}
  .studio-grid{grid-template-columns:1fr;overflow:visible}
  .terminal-card{min-height:360px}
}
}
@media print{@page{size:13.333in 7.5in;margin:0}
 html,body{overflow:visible;background:#fff}#deck-progress,.deck-hud,.notes-drawer,.live-demo,.live-demo-trigger{display:none!important}
 #stage{position:static;display:block}.slide{position:relative;display:block!important;transform:none!important;box-shadow:none;page-break-after:always;break-after:page;print-color-adjust:exact;-webkit-print-color-adjust:exact}.reveal{opacity:1!important;visibility:visible!important;transform:none!important}}
"""

JS = """
(function(){
var S=[].slice.call(document.querySelectorAll('.slide')),i=0,steps=S.map(function(){return 0;}),liveOpen=false,notesOpen=false;
var bar=document.getElementById('deck-progress'),hudCount=document.getElementById('hud-count'),hud=document.getElementById('deck-hud'),notesDrawer=document.getElementById('notes-drawer');
function byId(id){return document.getElementById(id);}
function fit(){var v=window.visualViewport,w=v?v.width:innerWidth,h=v?v.height:innerHeight,s=Math.min(w/1280,h/720);S.forEach(function(x){x.style.transform='scale('+s+')';});}
function toggleFullscreen(){if(document.fullscreenElement){document.exitFullscreen();}else if(document.documentElement.requestFullscreen){document.documentElement.requestFullscreen();}}
function pad2(n){return n<10?'0'+n:String(n);}
function syncNotes(){
 if(!notesDrawer)return;
 var num=pad2(i+1);
 if(hudCount)hudCount.textContent=num+' / '+pad2(S.length);
 byId('notes-title').textContent='讲者备注 · Slide '+num;
 var txt=(window.SLIDE_NOTES&&window.SLIDE_NOTES[String(i)])||'（本页无备注）';
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
function renderSteps(){var shown=steps[i];S[i].querySelectorAll('.reveal').forEach(function(x){x.classList.toggle('shown',Number(x.dataset.reveal)<shown);});if(bar)bar.style.width=((i+1)/S.length*100).toFixed(2)+'%';syncNotes();}
function parseHash(){var h=location.hash.slice(1),m=/^(?:slide-)?(\\d+)$/.exec(h);return m?Number(m[1])-1:0;}
function go(n){i=Math.max(0,Math.min(S.length-1,n));S.forEach(function(x,j){x.classList.toggle('on',j===i);});renderSteps();if(history.replaceState)history.replaceState(null,'','#'+(i+1));}
function next(){var total=Number(S[i].dataset.reveals||0);if(steps[i]<total){steps[i]++;renderSteps();}else{go(i+1);}}
function previous(){if(steps[i]>0){steps[i]--;renderSteps();}else{go(i-1);}}
byId('stage').addEventListener('click',function(ev){if(liveOpen||ev.target.closest('button,a'))return;ev.clientX<innerWidth/3?previous():next();});
byId('hud-notes-btn').addEventListener('click',function(ev){ev.stopPropagation();toggleNotes();});
byId('notes-close').addEventListener('click',function(){toggleNotes(false);});
byId('hud-demo-btn').addEventListener('click',function(ev){ev.stopPropagation();openLiveDemo(defaultDemoForSlide(i),1);});

addEventListener('keydown',function(ev){
 if(ev.altKey||ev.ctrlKey||ev.metaKey)return;
 var k=ev.key;
 if(ev.target&&ev.target.closest('input,textarea,select,[contenteditable="true"]')&&k!=='Escape')return;
 if(liveOpen){
  if(k==='Escape'){ev.preventDefault();closeLiveDemo();}
  return;
 }
 if(k==='Escape'&&notesOpen){ev.preventDefault();toggleNotes(false);return;}
 if(k===' '&&ev.target&&ev.target.closest('button,a'))return;
 if(k==='ArrowRight'||k==='ArrowDown'||k==='PageDown'||(k===' '&&!ev.shiftKey)){ev.preventDefault();next();}
 else if(k==='ArrowLeft'||k==='ArrowUp'||k==='PageUp'||(k===' '&&ev.shiftKey)){ev.preventDefault();previous();}
 else if(k==='Home'){ev.preventDefault();go(0);}
 else if(k==='End'){ev.preventDefault();go(S.length-1);}
 else if(k==='n'||k==='N'){ev.preventDefault();toggleNotes();}
 else if(k==='d'||k==='D'){ev.preventDefault();openLiveDemo(defaultDemoForSlide(i),1);}
 else if(k==='f'||k==='F'){ev.preventDefault();toggleFullscreen();}});
addEventListener('resize',fit);document.addEventListener('fullscreenchange',fit);if(window.visualViewport)window.visualViewport.addEventListener('resize',fit);
addEventListener('hashchange',function(){var n=parseHash();if(n!==i)go(n);});
fit();go(parseHash());

var SCENARIOS={
 fusion:{
  ledgerSave:'-64% Credits',
  steps:[
   {short:'① Single',boundary:'HyDRA Shortfall Match',title:'Lightweight Single-Model Fast Path',
    ctx:'27,740 ctx tokens · Turn 1 · --model auto',
    prompt:'"Extract the default port and env var from config.ts"',
    scorer:'HyDRA 4-Head ModernBERT · 86 ms CPU (threshold τ = 0.05)',
    bars:[
     {lbl:'Tool Use Demand',val:'0.28',pct:28,tone:'accent'},
     {lbl:'CodeGen Demand',val:'0.14',pct:14,tone:'muted'},
     {lbl:'Reasoning Demand',val:'0.11',pct:11,tone:'muted'},
     {lbl:'Debugging Demand',val:'0.06',pct:6,tone:'muted'}
    ],
    pattern:'SINGLE · NO REVIEW OVERHEAD',
    nodes:[
     {role:'Scorer',name:'HyDRA (86 ms)',sub:'All heads ≤ Flash cap',state:'active'},
     {role:'Primary',name:'MAI Code 2 Flash',sub:'0.08 cr · 1.8 s',state:'win'},
     {role:'Judge / Critic',name:'Bypassed',sub:'$0 review tax',state:'skip'}
    ],
    outcome:'✓ Returned DEFAULT_PORT=8787 (AUTO_DEMO_PORT) in 1.8 s for $0.0008 (0.08 AI Credits)',
    what:'HyDRA ModernBERT scores 4 capability demands in 86 ms on CPU. Because every head fits MAI Code 2 Flash, Fusion executes Single with zero extra judge latency.',
    code:'copilot -p "Extract default port..." --model auto → mai-code-2-flash (0.08 cr)',
    baseName:'Always Opus 5.5',baseNums:'$0.140 · 4.8 s',baseMeta:'1.40 cr frontier call on trivial lookup',
    agentName:'MAI Code 2 Flash',agentNums:'$0.0008 · 1.8 s',agentMeta:'0.08 cr · Single pass',
    chips:[['Cost: -94% cr ✓','on'],['Speed: 2.7× faster ✓','on'],['Pattern: Single ✓','on']],risk:0},
   {short:'② Cascade',boundary:'Short-Circuit Savings',title:'Cascade: Cheap Draft Verified & Accepted by Judge',
    ctx:'Multi-file edit + vitest · --reasoning-effort high',
    prompt:'"Trim whitespace in greetingFormatter(), add regression test, and run vitest"',
    scorer:'Copilot Fusion Orchestrator · High Effort → Cascade Pattern',
    bars:[
     {lbl:'CodeGen + Test',val:'0.58',pct:58,tone:'accent'},
     {lbl:'Primary Pass Rate',val:'14/14 PASS',pct:100,tone:'ok'},
     {lbl:'Judge Spec Verdict',val:'ACCEPT ✓',pct:96,tone:'ok'},
     {lbl:'Frontier Repair Cost',val:'$0 Saved',pct:8,tone:'muted'}
    ],
    pattern:'CASCADE · SHORT-CIRCUIT ACCEPT',
    nodes:[
     {role:'1 · Primary Draft',name:'Claude Haiku 5.5',sub:'14/14 vitest PASS',state:'active'},
     {role:'2 · Secondary Judge',name:'GPT-5.6 Luna',sub:'Tabs/NBSP verified → ACCEPT',state:'win'},
     {role:'3 · Frontier Repair',name:'Skipped!',sub:'Saved -52% credits',state:'skip'}
    ],
    outcome:'✓ Judge confirmed diff & Unicode whitespace edge cases — accepted Haiku draft without frontier repair!',
    what:'Cascade lets an efficient Primary attempt the edit + tests first, then runs a fast Judge check. Clean patches short-circuit immediately, saving 52% AI Credits.',
    code:'Haiku 5.5 (draft) → GPT-5.6 Luna (Judge: ACCEPT) → Repair skipped',
    baseName:'Single Frontier Max',baseNums:'2.90 cr · 19 s',baseMeta:'Pays heavy frontier tokens up front',
    agentName:'Haiku + Luna Judge',agentNums:'1.40 cr · 11.8 s',agentMeta:'Short-circuited after Judge PASS',
    chips:[['Credits: -52% ✓','on'],['Time: -38% ✓','on'],['14/14 Tests PASS ✓','on']],risk:0},
   {short:'③ Escalate',boundary:'Quality Safety Net',title:'Cascade: Judge Catches Lock Inversion & Escalates',
    ctx:'Concurrency race bug · --reasoning-effort high',
    prompt:'"Fix intermittent deadlock when TokenBucket.refill() races with close()"',
    scorer:'Secondary Judge Inspection · Concurrency Invariant Audit',
    bars:[
     {lbl:'Debugging Demand',val:'0.89',pct:89,tone:'warn'},
     {lbl:'Unit Test Naive Pass',val:'100% (Missed race)',pct:100,tone:'muted'},
     {lbl:'Lock-Order Hazard',val:'INVERTED ✕',pct:94,tone:'warn'},
     {lbl:'Repair Stress Test',val:'500/500 PASS',pct:100,tone:'ok'}
    ],
    pattern:'CASCADE · JUDGE ESCALATION → REPAIR',
    nodes:[
     {role:'1 · Primary Draft',name:'GPT-5.6 Luna',sub:'Naive mutex (race left)',state:'err'},
     {role:'2 · Judge Gate',name:'Claude Sonnet 5.5',sub:'ESCALATE: lock order!',state:'active'},
     {role:'3 · Fresh Repair',name:'GPT-6.1 Sol',sub:'Monotonic lock · 500× PASS',state:'win'}
    ],
    outcome:'✓ Judge caught inverted close()→drain() vs refill()→notify() lock order; GPT-6.1 Sol fixed it cleanly!',
    what:'Unit tests passed on the cheap draft, but Sonnet Judge caught a subtle lock-order inversion and escalated to GPT-6.1 Sol for a clean fresh-start repair.',
    code:'Luna (draft) → Sonnet 5.5 (ESCALATE) → GPT-6.1 Sol (500× stress PASS)',
    baseName:'Cheap Model Alone',baseNums:'Prod Deadlock ✕',baseMeta:'Unit tests missed close()/refill() race',
    agentName:'Cascade Escalation',agentNums:'500× Stress PASS',agentMeta:'Only hard bugs pay for GPT-6.1 Sol',
    chips:[['Race Bug Caught ✓','on'],['Escalated: Sol ✓','on'],['Zero Prod Outage ✓','on']],risk:1},
   {short:'④ Critique',boundary:'Multi-Model Synthesis',title:'Critique: Parallel Read-Only Critics Audit 50k-RPS Design',
    ctx:'Distributed architecture · --reasoning-effort max',
    prompt:'"Design multi-region Redis sliding-window limiter for 50k RPS (<2ms p99) & audit failure modes"',
    scorer:'Copilot Fusion Max · Multi-Lab Read-Only Critique Topology',
    bars:[
     {lbl:'Architecture Depth',val:'0.95',pct:95,tone:'accent'},
     {lbl:'Critic A (GPT-6 Sol)',val:'Clock-skew caught',pct:92,tone:'warn'},
     {lbl:'Critic B (Gemini Argon)',val:'Hot-key burst caught',pct:88,tone:'warn'},
     {lbl:'AA Coding Index',val:'60 pts (-50% cost)',pct:97,tone:'ok'}
    ],
    pattern:'CRITIQUE · PARALLEL READ-ONLY REVIEW',
    nodes:[
     {role:'1 · Primary Draft',name:'Claude Opus 5.5',sub:'Lua ZREMRANGEBYSCORE',state:'active'},
     {role:'2 · Parallel Critics',name:'Sol + Gemini Argon',sub:'Read-only: 2 flaws flagged',state:'active'},
     {role:'3 · Final Revision',name:'Claude Opus 5.5',sub:'Redis TIME + local lease',state:'win'}
    ],
    outcome:'✓ Two read-only Critics caught Redis failover clock-skew & hot-key saturation; Opus revised cleanly!',
    what:'Critics run in parallel with strictly read-only permissions (preventing conflicting edits), surfacing blind spots single-model max reasoning missed at ~50% lower cost.',
    code:'Opus Draft + [Sol ∥ Argon Critics] → Opus Monotonic Lease Revision',
    baseName:'Single Opus Max',baseNums:'2× API Cost',baseMeta:'Single-lab blind spots on Redis skew',
    agentName:'Fusion Max Critique',agentNums:'-48% Cost · -40% Time',agentMeta:'3 labs · 2 distributed flaws fixed',
    chips:[['2 Flaws Caught ✓','on'],['Cost: -48% vs Max ✓','on'],['Read-Only Safe ✓','on']],risk:1},
   {short:'⑤ Cache',boundary:'10× Cache Economics',title:'Prefix-Cache Guard Prevents Mid-Session Thrash',
    ctx:'Turn 2 follow-up · 64,200 tokens warm in Opus prefix cache',
    prompt:'"Now export Prometheus metrics for lease_hits_total and fallback_open_total."',
    scorer:'Cache-Boundary Guard · Prefix TTL 1800s Active',
    bars:[
     {lbl:'Warm Prefix Reuse',val:'64,200 tok (90% off)',pct:95,tone:'ok'},
     {lbl:'Keep Cached Opus',val:'$0.038 · 2.1 s',pct:16,tone:'ok'},
     {lbl:'Uncached Model Switch',val:'$0.195 · 6.4 s ✕',pct:88,tone:'warn'},
     {lbl:'New Task Demand',val:'0.22 (Simple)',pct:22,tone:'muted'}
    ],
    pattern:'CACHE AFFINITY · KEEP WARM MODEL',
    nodes:[
     {role:'Prefix Cache',name:'64.2k Tokens Warm',sub:'90% cache_read discount',state:'active'},
     {role:'Switch Rejected',name:'Cold Model',sub:'Would re-prefill 64.2k ✕',state:'skip'},
     {role:'Retained Model',name:'Claude Opus 5.5',sub:'2.1 s · 10× cheaper read',state:'win'}
    ],
    outcome:'✓ Kept warm Claude Opus 5.5 on Turn 2 — 90% cache_read discount beat switching to an uncached cheaper model!',
    what:'Switching model families mid-thread invalidates the 64.2k prompt cache and forces full-price re-prefilling. Copilot only re-routes at natural cache boundaries.',
    code:'cacheReadTokens=64,200 (90% discount) → Retain warm claude-opus-5.5',
    baseName:'Naive Mid-Turn Switch',baseNums:'$0.195 · 6.4 s',baseMeta:'Breaks prefix cache & re-prefills 64.2k',
    agentName:'Warm Cache Retain',agentNums:'$0.038 · 2.1 s',agentMeta:'90% cache-read discount preserved',
    chips:[['Cache Hit: 90% ✓','on'],['5× Cheaper Turn ✓','on'],['Latency: 2.1 s ✓','on']],risk:0}
  ]
 },
 foundry:{
  ledgerSave:'-76% + 0 Outages',
  steps:[
   {short:'① Gates',boundary:'Pre-Rank + Param Adapt',title:'Pre-Rank Eligibility Gate & Cross-Lab Param Adaptation',
    ctx:'45-model pool (7 labs) · tools + json_schema + temperature=0.2',
    prompt:'[Pipeline Check] Filter approved subset, adapt incompatible params & order PTU capacity',
    scorer:'Foundry Model Router · Stage 1 Eligibility + Stage 4 Param Adapter',
    bars:[
     {lbl:'Pool → Approved Subset',val:'45 → 8 Eligible',pct:78,tone:'accent'},
     {lbl:'Capability Gate',val:'tools + json_schema ✓',pct:100,tone:'ok'},
     {lbl:'Param Auto-Adapt',val:'drop temp / map role ✓',pct:100,tone:'ok'},
     {lbl:'OpenAI PTU Usage Fee',val:'$0 Extra Model Fee',pct:100,tone:'ok'}
    ],
    pattern:'6-STAGE PIPELINE · PTU FIRST',
    nodes:[
     {role:'1 · Pre-Rank Gate',name:'Region ∩ Subset',sub:'tools + schema checked',state:'active'},
     {role:'2 · Param Adapter',name:'Auto-Normalize',sub:'developer→system · drop temp',state:'active'},
     {role:'3 · Capacity Order',name:'Own PTU → PAYG',sub:'$0 model fee on PTU!',state:'win'}
    ],
    outcome:'✓ Subset locked to approved models; unsupported optional params auto-adapted; pre-paid PTUs prioritized first!',
    what:'Before ranking, Foundry excludes models missing tools/schema support. After selection, it adapts unsupported params (like temperature on reasoning models) and drains your PTUs first.',
    code:'Eligible(subset, tools, schema) → Rank(~20ms) → Own PTU ($0) → PAYG → Managed',
    baseName:'Manual Multi-SDK',baseNums:'400 Errors / Idle PTU',baseMeta:'Crashes on param mismatch across labs',
    agentName:'Foundry Router',agentNums:'$0.14 / 1M in ($0 out)',agentMeta:'Zero-code param adapt + PTU drain',
    chips:[['Gate: tools+schema ✓','on'],['Params: Adapted ✓','on'],['PTU: $0 Model Fee ✓','on']],risk:0},
   {short:'② Flash',boundary:'1–2% Balanced Band',title:'Simple JSON Extraction Routed to Flash in 23 ms',
    ctx:'POST /openai/v1/chat/completions · mode: "balanced"',
    prompt:'"Extract invoice ID & currency as JSON: Invoice INV-2026-8841, Total 4,250 EUR"',
    scorer:'Non-LLM ML Ranker · 23 ms Router Overhead (1–2% Balanced Band)',
    bars:[
     {lbl:'DeepSeek-V4.1-Flash',val:'99.1% fit · WINNER',pct:99,tone:'ok'},
     {lbl:'gpt-5.6-sol (Frontier)',val:'99.6% fit (25× cost)',pct:100,tone:'muted'},
     {lbl:'claude-sonnet-5-5',val:'99.4% fit (20× cost)',pct:99,tone:'muted'},
     {lbl:'Reasoning Tokens Spent',val:'0 tokens',pct:4,tone:'ok'}
    ],
    pattern:'BALANCED BAND · CHEAPEST IN TOP 1–2%',
    nodes:[
     {role:'ML Ranker',name:'23 ms Overhead',sub:'4 candidates in 1–2% band',state:'active'},
     {role:'Selected Model',name:'DeepSeek-V4.1-Flash',sub:'0 reasoning tokens',state:'win'},
     {role:'JSON Output',name:'Valid 200 OK',sub:'{"invoice_id":"INV-2026-8841"}',state:'win'}
    ],
    outcome:'✓ Live trace: routed in 23 ms to DeepSeek-V4.1-Flash — valid JSON with 0 wasted reasoning tokens!',
    what:'Because structured extraction is easy for fast models, DeepSeek-V4.1-Flash lands within 1% of frontier quality — so Balanced mode picks it at ~25× lower token cost.',
    code:'routing_trace: [{ latency_ms: 23, attempts: [{ model: "DeepSeek-V4.1-Flash", status: 200 }] }]',
    baseName:'Pinned Frontier',baseNums:'$0.012 · 1.9 s',baseMeta:'Burns frontier reasoning on trivial JSON',
    agentName:'DeepSeek-V4.1-Flash',agentNums:'$0.0004 · 0.42 s',agentMeta:'23 ms router · 0 reasoning tokens',
    chips:[['Router: 23 ms ✓','on'],['Cost: ~25× lower ✓','on'],['JSON: Valid 200 ✓','on']],risk:0},
   {short:'③ Escalate',boundary:'Difficulty Escalation + Cache',title:'Same Endpoint Escalates Hard Rust Proof & Retains Cache',
    ctx:'Same endpoint & "balanced" mode · Formal concurrency proof',
    prompt:'"Design a lock-free ring buffer in Rust with formal ABA hazard-pointer & Acquire/Release proofs"',
    scorer:'Non-LLM ML Ranker · 20 ms Overhead + Adaptive Fingerprint Affinity',
    bars:[
     {lbl:'gpt-5.6-luna (Reasoning)',val:'96.4% fit · WINNER',pct:96,tone:'ok'},
     {lbl:'DeepSeek-V4.1-Flash',val:'68.0% (Outside 1–2%)',pct:68,tone:'warn'},
     {lbl:'Turn 2 Adaptive Cache',val:'decision: "retain" ✓',pct:100,tone:'ok'},
     {lbl:'User-Visible TTFT',val:'130 ms',pct:86,tone:'accent'}
    ],
    pattern:'AUTO ESCALATION + ADAPTIVE AFFINITY',
    nodes:[
     {role:'ML Ranker',name:'20 ms Overhead',sub:'Flash drops out of band',state:'active'},
     {role:'Escalated Model',name:'gpt-5.6-luna',sub:'TTFT 130ms · 120 reason tok',state:'win'},
     {role:'Turn 2 Follow-up',name:'decision: "retain"',sub:'Fingerprint keeps warm cache',state:'win'}
    ],
    outcome:'✓ Escalated automatically to gpt-5.6-luna in 20 ms; follow-up turn retained luna via derived_fingerprint!',
    what:'When prompt difficulty spikes, small models fall outside the 1–2% band and the router escalates to reasoning. On follow-up turns, adaptive affinity retains the warm cache.',
    code:'routing_trace: [{ latency_ms: 20, model: "gpt-5.6-luna" }] · affinity: "retain"',
    baseName:'Pinned Cheap Flash',baseNums:'Broken ABA Proof ✕',baseMeta:'Fails formal memory-ordering invariants',
    agentName:'gpt-5.6-luna (Auto)',agentNums:'20 ms route · 130 ms TTFT',agentMeta:'Escalated + retained warm cache',
    chips:[['Router: 20 ms ✓','on'],['Escalated: Luna ✓','on'],['Affinity: retain ✓','on']],risk:1},
   {short:'④ 4-Job',boundary:'Multi-Lab Specialization',title:'Microsoft Copilot: One Renewal Prompt → Four Models',
    ctx:'M365 Copilot Home → Cowork Auto (>90% of Copilot traffic)',
    prompt:'"Customer renewal Thursday: should we expand, hold, or discount? Build a 6-slide proposal deck."',
    scorer:'Multi-Stage Workplace Orchestration · 3 Labs Combined',
    bars:[
     {lbl:'Experience Gate (MD-1.1)',val:'Chat → Cowork (4.4× cheaper)',pct:94,tone:'ok'},
     {lbl:'Work IQ Grounding',val:'SLM (Emails + PDFs)',pct:88,tone:'accent'},
     {lbl:'Strategy & Slide Deck',val:'Claude Opus 5.5 (Cached)',pct:96,tone:'accent'},
     {lbl:'Proposal Hero Visuals',val:'GPT Image 2.5',pct:95,tone:'ok'}
    ],
    pattern:'SUB-TASK SPECIALIZATION · 3 LABS',
    nodes:[
     {role:'1 · Handoff',name:'Decision-1.1',sub:'Chat → Cowork (2.2× faster)',state:'active'},
     {role:'2 · Retrieval',name:'Fast SLM',sub:'Work IQ emails & contracts',state:'active'},
     {role:'3 · Deck + Art',name:'Opus 5.5 + Image 2.5',sub:'Best writer + best artist',state:'win'}
    ],
    outcome:'✓ Delivered grounded 6-slide renewal deck + custom visuals by pairing SLM, Claude Opus 5.5 & GPT Image 2.5!',
    what:'Charles Lamanna’s core lesson in action: the first model choice is not the only model choice — retrieval, reasoning, and visuals each route to their best-in-class specialist.',
    code:'Decision-1.1 (Cowork) → SLM (Work IQ) + Claude Opus 5.5 (Deck) + GPT Image 2.5',
    baseName:'Single Monolithic LLM',baseNums:'Slow · Weak Visuals',baseMeta:'Overpays on search & lacks native art',
    agentName:'4-Job Auto Pipeline',agentNums:'84% Lower Cost',agentMeta:'3 labs · right-sized per sub-job',
    chips:[['Handoff: 4.4× cheaper ✓','on'],['3 Labs Combined ✓','on'],['Deck + Art Ready ✓','on']],risk:0},
   {short:'⑤ Failover',boundary:'Two-Tier Resilience',title:'Transparent HTTP 429 → 200 Failover Inside Subset',
    ctx:'Traffic burst on primary gpt-6-sol deployment · Subset locked',
    prompt:'[Burst Test] Primary deployment returns HTTP 429 Too Many Requests under peak load',
    scorer:'Two-Tier Failover · Capacity Waterfall → Next-Ranked Subset Model (19 ms)',
    bars:[
     {lbl:'Attempt 1 · gpt-6-sol',val:'HTTP 429 Rate Limit ✕',pct:100,tone:'warn'},
     {lbl:'Attempt 2 · gpt-5.6-sol',val:'HTTP 200 OK (19 ms) ✓',pct:98,tone:'ok'},
     {lbl:'Subset Compliance',val:'100% Inside Allow-List',pct:100,tone:'ok'},
     {lbl:'Caller Exceptions',val:'0 App Errors',pct:4,tone:'ok'}
    ],
    pattern:'AUTOMATIC FAILOVER · ZERO APP ERROR',
    nodes:[
     {role:'Attempt 1',name:'gpt-6-sol',sub:'HTTP 429 Rate Limited ✕',state:'err'},
     {role:'Router Retry',name:'19 ms Switch',sub:'Stays inside subset',state:'active'},
     {role:'Attempt 2',name:'gpt-5.6-sol',sub:'HTTP 200 OK Served ✓',state:'win'}
    ],
    outcome:'✓ Absorbed HTTP 429 spike transparently in 19 ms — served 200 OK from next-ranked model inside subset!',
    what:'When all capacity tiers for #1 return 429/5xx, Foundry automatically retries the next-ranked model inside your approved compliance subset — overriding affinity so requests never fail.',
    code:'attempts: [{ model: "gpt-6-sol", status: 429 }, { model: "gpt-5.6-sol", status: 200 }]',
    baseName:'Direct Deployment',baseNums:'HTTP 429 Crash ✕',baseMeta:'User sees failure or slow client backoff',
    agentName:'Subset Failover',agentNums:'HTTP 200 · +19 ms',agentMeta:'Zero app error · compliance preserved',
    chips:[['Attempt 1: 429 ✕','denied'],['Attempt 2: 200 OK ✓','on'],['Subset Safe ✓','on']],risk:1}
  ]
 },
 decision:{
  ledgerSave:'7.2× Lower CAC ($1.81)',
  steps:[
   {short:'① 180ms',boundary:'Calibrated System-One',title:'Zero-Spread Calibrated Probability in 180 ms',
    ctx:'POST /providers/microsoft/v1/systemone · $0.042/1M in · $0 out',
    prompt:'"Is the Harbor sectional still 15% off? We’d love it before my in-laws visit on the 20th."',
    scorer:'Microsoft-Decision-1.1 (Gemma 4 26B-A4B MoE) · 5× Repeat Probe',
    bars:[
     {lbl:'Run #1 – #5 ready_to_buy',val:'0.9800 (0.0 pt spread)',pct:98,tone:'ok'},
     {lbl:'Median Latency (p50)',val:'180 ms (35× faster)',pct:18,tone:'accent'},
     {lbl:'Shuffle Flip Rate',val:'1.3% (Order-invariant)',pct:6,tone:'ok'},
     {lbl:'Call Cost ($0 output!)',val:'$0.000013 / check',pct:3,tone:'ok'}
    ],
    pattern:'NOUL PRIMITIVE · SINGLE FORWARD PASS',
    nodes:[
     {role:'Unstructured Msg',name:'Buyer Timeline Cue',sub:'"before the 20th"',state:'active'},
     {role:'SystemOne noul',name:'p = 0.9800',sub:'180 ms · $0.000013',state:'win'},
     {role:'Deterministic Code',name:'routeToSales()',sub:'Threshold p ≥ 0.80',state:'win'}
    ],
    outcome:'✓ 5 consecutive runs returned 0.9800 with 0.0 pt spread in 180 ms for $0.000013 ($0 output token charge)!',
    what:'Unlike generative LLMs that charge 400–2,000 ms of prose tokens to say "yes", Decision-1.1 outputs calibrated probabilities in one pass at $0.042/1M input and FREE output.',
    code:'questions: { ready_to_buy: { type: "noul", instructions: "Ready within 2 weeks?" } } → 0.98',
    baseName:'Generative LLM Judge',baseNums:'$0.0045 · 1,450 ms',baseMeta:'340× pricier + prompt order bias',
    agentName:'Decision-1.1 noul',agentNums:'$0.000013 · 180 ms',agentMeta:'0.0 pt spread · $0 output tokens',
    chips:[['Spread: 0.0 pts ✓','on'],['Latency: 180 ms ✓','on'],['Cost: $0.000013 ✓','on']],risk:0},
   {short:'② Router',boundary:'100% Inbox Accuracy',title:'Check 1 (choice): 57% of Traffic Skips Frontier LLM',
    ctx:'32-message Contoso customer inbox · 4 routing destinations',
    prompt:'Batch triage: "Thanks! 👍" | "STOP / unsubscribe" | "15% valid on king?" | "Compare pet warranty"',
    scorer:'Decision-1.1 type: "choice" · 32-Reply Benchmark (100% vs. 88% Regex)',
    bars:[
     {lbl:'"Thanks! 👍" → no_reply',val:'p = 0.97 ($0 LLM)',pct:97,tone:'ok'},
     {lbl:'"STOP" → code_template',val:'p = 0.98 ($0 LLM)',pct:98,tone:'ok'},
     {lbl:'"15% promo?" → fast_slm',val:'p = 0.93 (Cheap SLM)',pct:93,tone:'accent'},
     {lbl:'"Compare..." → frontier_sol',val:'p = 0.96 (43% of msgs)',pct:96,tone:'accent'}
    ],
    pattern:'CHOICE ROUTER · 57% SKIP FRONTIER SOL',
    nodes:[
     {role:'32 Inbox Replies',name:'100% Accuracy',sub:'Regex scored only 88%',state:'active'},
     {role:'57% Short-Circuit',name:'No-Reply / Code / SLM',sub:'Zero frontier Sol cost',state:'win'},
     {role:'43% Complex Only',name:'Frontier Sol',sub:'Reserved for real nuance',state:'active'}
    ],
    outcome:'✓ 100% routing accuracy across all 32 replies (total batch router cost: $0.0004) — 57% skipped Frontier Sol!',
    what:'Keyword regex fails on polite phrasing ("We went with a local store, thanks!" → 88%), whereas Decision-1.1 hits 100% accuracy and cuts frontier LLM calls by more than half.',
    code:'criteria: { no_reply, code_template, fast_slm, frontier_sol } → 100% accuracy',
    baseName:'Regex / All-Sol',baseNums:'88% Acc / $0.15 msg',baseMeta:'Wastes Sol on "Thanks!" or misfires regex',
    agentName:'MD-1.1 choice Gate',agentNums:'100% Acc · 57% Skip',agentMeta:'$0.0004 total for all 32 messages',
    chips:[['MD-1.1: 100% Acc ✓','on'],['Regex: 88% Acc ✕','denied'],['57% Skip Sol ✓','on']],risk:0},
   {short:'③ P0–P3',boundary:'Multi-Question Call',title:'Check 2 (choice + score + noul): Instant P3 Injury Escalation',
    ctx:'3 typed questions in ONE /systemone request · Safety triage',
    prompt:'"The bed frame collapsed last night and my husband hurt his back. Third time writing in!"',
    scorer:'Single API Call → Simultaneous choice + score[0..3] + noul Answers',
    bars:[
     {lbl:'team (choice: safety)',val:'p = 0.95',pct:95,tone:'warn'},
     {lbl:'priority (score: 0..3)',val:'2.94 / 3.0 → P3 URGENT',pct:98,tone:'warn'},
     {lbl:'repeat_contact (noul)',val:'p = 0.99 (3rd ping)',pct:99,tone:'warn'},
     {lbl:'Bot Reply Allowed?',val:'0% — Bypass to Human',pct:2,tone:'ok'}
    ],
    pattern:'COMBINED CALL · P3 IMMEDIATE HUMAN',
    nodes:[
     {role:'One /systemone Call',name:'3 Typed Answers',sub:'choice + score + noul',state:'active'},
     {role:'Autonomous Bot',name:'Bypassed!',sub:'Prevents tone-deaf AI reply',state:'skip'},
     {role:'P3 Safety Specialist',name:'Paged Immediately',sub:'score 2.94 ≥ 2.5 gate',state:'win'}
    ],
    outcome:'✓ Single 180 ms call returned safety_support (0.95) + P3 score (2.94/3.0) + repeat (0.99) — paged human!',
    what:'You can pack choice, score, and noul questions into one /systemone call over the same state — getting calibrated routing, SLA queue ordering, and flags in one round-trip.',
    code:'if (answers.priority.score >= 2.5) return pageHumanSpecialist(answers.team.choice);',
    baseName:'Blind Auto-Bot',baseNums:'Liability Risk ✕',baseMeta:'Sends generic AI troubleshooting to injury',
    agentName:'Combined MD-1.1',agentNums:'P3 Human in 180 ms',agentMeta:'3 decisions in 1 request ($0.00004)',
    chips:[['Team: safety (0.95) ✓','on'],['Score: 2.94 (P3) ✕','denied'],['Human Paged ✓','on']],risk:1},
   {short:'④ Guard',boundary:'Pre-Send Guardrail',title:'Check 3 (noul): Blocks Draft Recommending Competitor',
    ctx:'Outbound QC before send · Customer asked: "Anything cheaper? Be honest."',
    prompt:'Sol Draft: "Honestly, Fabrikam has a similar sofa for $749. Here’s the link."',
    scorer:'Outbound Policy Gate · Independent noul Checks (Hold if ≥ 0.50)',
    bars:[
     {lbl:'mentions_competitor (noul)',val:'0.964 ≥ 0.50 HOLD ✕',pct:96,tone:'warn'},
     {lbl:'unapproved_discount (noul)',val:'0.031 (Safe)',pct:3,tone:'ok'},
     {lbl:'medical_or_legal (noul)',val:'0.008 (Safe)',pct:2,tone:'ok'},
     {lbl:'Human Review Needed',val:'Only 8% of drafts!',pct:8,tone:'ok'}
    ],
    pattern:'OUTBOUND NOUL FILTER · DRAFT HELD',
    nodes:[
     {role:'Generative Draft',name:'Frontier Sol',sub:'Leaked rival "Fabrikam"',state:'err'},
     {role:'MD-1.1 noul Gate',name:'noul = 0.964',sub:'Exceeds 0.50 threshold',state:'active'},
     {role:'Safe Disposition',name:'HELD for Review',sub:'92% clean drafts auto-send',state:'win'}
    ],
    outcome:'✓ Caught competitor promotion (noul = 0.964) before send — while letting 92% of safe replies ship automatically!',
    what:'Helpful LLMs can be tricked into recommending rivals or inventing discounts. A $0.00006 noul check screens every outbound draft so humans review 8% instead of 100%.',
    code:'if (res.mentions_competitor.noul >= 0.50) holdDraft(); // Cut review 100% → 8%',
    baseName:'100% Human Review',baseNums:'$0.24 / msg labor',baseMeta:'Reviewing every AI draft kills ROI',
    agentName:'MD-1.1 noul Filter',agentNums:'$0.00006 · 8% Review',agentMeta:'Blocked Fabrikam leak · 92% auto-sent',
    chips:[['Rival Leak: 0.964 ✕','denied'],['Draft HELD ✓','on'],['Review: 100%→8% ✓','on']],risk:1},
   {short:'⑤ 7.2× ROI',boundary:'Abstain + Unit Economics',title:'Calibrated Abstention & 7.2× Customer Acquisition Win',
    ctx:'Missing Exhibit B confidence check + $10,000/mo Contoso pipeline',
    prompt:'"Compare termination notice in Contract A vs Exhibit B" (Exhibit B missing from context)',
    scorer:'Confidence Gate (max p < 0.75 → Abstain) + Full 3-Check Economics',
    bars:[
     {lbl:'request_missing_exhibit',val:'p = 0.48 (Top choice)',pct:48,tone:'warn'},
     {lbl:'Max Confidence vs 0.75 Gate',val:'0.48 < 0.75 → ABSTAIN',pct:48,tone:'warn'},
     {lbl:'Cost / Lead ($0.31 → $0.05)',val:'-84% Cost / Lead',pct:84,tone:'ok'},
     {lbl:'Monthly Customers ($10k)',val:'764 → 5,511 (7.2×)',pct:100,tone:'ok'}
    ],
    pattern:'CALIBRATED ABSTAIN + 7.2× CAC WATERFALL',
    nodes:[
     {role:'Missing Context',name:'max(p) = 0.48',sub:'Below 0.75 gate → Abstain',state:'active'},
     {role:'3 MD-1.1 Checks',name:'$0.000189 / msg',sub:'Router + Score + Filter',state:'win'},
     {role:'Business Impact',name:'CAC $13 → $1.81',sub:'5,511 vs 764 customers/mo',state:'win'}
    ],
    outcome:'✓ Abstained safely on missing Exhibit B; across $10k/mo budget, 3 checks ($0.00019) cut CAC from $13 to $1.81!',
    what:'Calibrated probabilities let code abstain when evidence is missing. Combining all three $0.00019 Decision-1.1 gates drops cost/lead from $0.31 to $0.05 (7.2× more customers).',
    code:'Baseline CAC $13.00 (764 cust) → +3 MD-1.1 gates = CAC $1.81 (5,511 cust, 7.2×)',
    baseName:'All-Sol + 100% Human',baseNums:'CAC $13.00 · 764/mo',baseMeta:'$0.31 per lead caps $10k/mo growth',
    agentName:'+ 3 MD-1.1 Gates',agentNums:'CAC $1.81 · 5,511/mo',agentMeta:'$0.05/lead · $0.000189 total check cost',
    chips:[['Missing Info: Abstain ✓','on'],['Leads: 7.2× More ✓','on'],['CAC: $13 → $1.81 ✓','on']],risk:1}
  ]
 }
};

var SCENARIO_META={
 fusion:{
  kicker:'DEMO 1 · CODING AGENT',
  title:'GitHub Copilot Auto & Fusion',
  desc:'Fast Single pass on easy code, Judge/Critic teams on hard bugs, and warm-cache retention.',
  chrome:'GitHub Copilot CLI · Auto & Fusion'
 },
 foundry:{
  kicker:'DEMO 2 · CLOUD API',
  title:'Microsoft Foundry Model Router',
  desc:'One /chat/completions endpoint: cheap Flash on easy JSON, auto-escalation, and 429 failover.',
  chrome:'Microsoft Foundry · Model Router API'
 },
 decision:{
  kicker:'DEMO 3 · APP CONTROLLER',
  title:'Microsoft-Decision-1.1 (/v1/systemone)',
  desc:'Replace slow LLM router prompts with 180 ms calibrated choice, score & noul gates ($0.042/1M).',
  chrome:'Microsoft-Decision-1.1 · /v1/systemone'
 }
};

var curKind='fusion',curStep=1,doneSet={fusion:{},foundry:{},decision:{}},lastLiveRoute={},liveMeta=null,liveSource=null;
function isLocalDemoHost(){return ['127.0.0.1','localhost'].includes(location.hostname)&&location.protocol.indexOf('http')===0;}
var replayMode=!isLocalDemoHost(),replayTimers=[],autoPlaying=false,stepRunning=false,stepDoneWaiters=[],displayLog='',hintShown=false;

function escHtml(s){
 return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderTerminalHtml(text){
 var lines=String(text||'').split('\\n'),html=[];
 for(var idx=0;idx<lines.length;idx++){
  var raw=lines[idx];
  if(idx===lines.length-1&&raw==='')continue;
  var safe=escHtml(raw),cls='tl-log';
  if(/^# /.test(raw))cls='tl-hint';
  else if(/^──▶/.test(raw))cls='tl-step';
  else if(/^\\[CONFIG\\]/.test(raw))cls='tl-policy';
  else if(/^\\[REQUEST\\]/.test(raw))cls='tl-run';
  else if(/^✓ /.test(raw))cls='tl-pass';
  else if(/^✕ /.test(raw)||/^\\[Error\\]/.test(raw))cls='tl-fail';
  else if(/^Why:/.test(raw))cls='tl-why';
  html.push('<span class="tl '+cls+'">'+(safe||' ')+'</span>');
 }
 return html.join('');
}

function flushTerminal(){
 var out=byId('live-demo-output');
 out.innerHTML=renderTerminalHtml(displayLog);
 out.scrollTop=out.scrollHeight;
}
function appendTerminal(chunk){
 displayLog+=chunk;
 flushTerminal();
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
function setChip(id,text,tone){var el=byId(id);if(!el)return;el.textContent=text;el.classList.remove('on','denied');if(tone)el.classList.add(tone);}

function renderNodes(nodes){
 var box=byId('vis-nodes'),parts=[];
 nodes.forEach(function(n,idx){
  if(idx>0)parts.push('<div class="tarrow" aria-hidden="true">→</div>');
  parts.push('<div class="tnode" data-state="'+(n.state||'')+'"><span class="tnode-role">'+escHtml(n.role)+'</span><span class="tnode-name">'+escHtml(n.name)+'</span><span class="tnode-sub">'+escHtml(n.sub)+'</span></div>');
 });
 box.innerHTML=parts.join('');
}

function renderTabsAndPills(){
 document.querySelectorAll('.sc-tab').forEach(function(btn){
  var on=btn.dataset.kind===curKind;
  btn.classList.toggle('active',on);
  btn.setAttribute('aria-selected',on?'true':'false');
  btn.disabled=stepRunning;
 });
 var meta=SCENARIO_META[curKind];
 if(meta){
  byId('purpose-kicker').textContent=meta.kicker;
  byId('purpose-title').textContent=meta.title;
  byId('purpose-desc').textContent=meta.desc;
  byId('terminal-mode-title').textContent=meta.chrome;
 }
 var list=SCENARIOS[curKind].steps,pills=byId('step-pills');
 pills.innerHTML=list.map(function(st,idx){
  var n=idx+1,act=n===curStep,dn=!!doneSet[curKind][n];
  return '<button type="button" class="step-pill'+(act?' active':'')+(dn?' done':'')+'" data-step="'+n+'"'+(stepRunning?' disabled':'')+' title="'+escHtml(st.title)+'">'+(dn?'✓ ':'')+escHtml(st.short)+'</button>';
 }).join('');
 var nextUnrun=curStep;
 if(doneSet[curKind][curStep]&&curStep<list.length)nextUnrun=curStep+1;
 byId('live-run-label').textContent=(doneSet[curKind][curStep]&&curStep<list.length)?('Next: Step '+nextUnrun):('Run Step '+curStep);
 byId('live-demo-run').dataset.targetStep=String(nextUnrun);
 byId('live-demo-run').disabled=stepRunning;
}

function renderVisualStep(kind,stepNum){
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
 renderTabsAndPills();
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
  appendTerminal('# Click "Run Step 1" or "Auto-Play" above — Config is blue, Request is amber, Pass is green, Escalate/Hold is red.');
 }
}

function resetScenario(keepKind){
 stopAutoPlay();clearReplayTimers();resolveStepWaiters(false);
 var k=keepKind||curKind;
 doneSet[k]={};
 Object.keys(lastLiveRoute).forEach(function(key){if(key.indexOf(k+':')===0)delete lastLiveRoute[key];});
 if(!replayMode)fetch('/api/cancel',{method:'POST'}).catch(function(){});
 displayLog='';hintShown=false;
 byId('live-demo-output').innerHTML='';
 setStatus(idleModeLabel(),replayMode?undefined:'ok');
 renderVisualStep(k,1);
 showInitialHint();
}

function applyLocalProbeCard(r){
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
}

function applyDemoEvent(data){
 if(hintShown&&(data.kind==='step-start'||data.kind==='output')){displayLog='';hintShown=false;}
 if(data.kind==='output'){
  appendTerminal(data.text);
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
  setStatus('Live Probe ✓','ok');
 }else if(data.kind==='probe-fallback'){
  stepRunning=false;renderTabsAndPills();
  setStatus('Probe Routed ✓','ok');
 }else if(data.kind==='step-start'){
  stepRunning=true;
  curKind=data.demo;curStep=Number(data.step);
  delete lastLiveRoute[curKind+':'+curStep];
  setStatus((replayMode?'Running Step ':'Running Live Step ')+curStep+'…','running');
  renderVisualStep(curKind,curStep);
  appendTerminal((displayLog?'\\n':'')+'──▶ [Step '+curStep+'] '+SCENARIOS[curKind].steps[curStep-1].title+'\\n');
 }else if(data.kind==='step-done'){
  stepRunning=false;
  var demo=data.demo,step=Number(data.step),total=SCENARIOS[demo].steps.length;
  doneSet[demo][step]=true;
  renderVisualStep(demo,step);
  setStatus(step===total?'All 5 Verified ✓':'Step '+step+' Verified ✓','ok');
  resolveStepWaiters(true);
 }else if(data.kind==='step-error'){
  stepRunning=false;
  setStatus('Error','err');
  appendTerminal('\\n[Error] '+data.error+'\\n');
  renderTabsAndPills();
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
 appendTerminal((isHold?'✕ ESCALATED / HELD — '+r.title+'\\n':'')+r.outcome.replace(/^✓ /,'✓ PASS — ')+'\\nWhy: '+r.what+'\\n');
 setStatus('Probe Routed ✓','ok');
}

function closeLiveDemo(){
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
 if(notesOpen)toggleNotes(false);
 byId('live-demo').hidden=false;liveOpen=true;
 replayMode=!isLocalDemoHost();
 var k=preferredKind||'fusion',s=Number(preferredStep)||1;
 renderVisualStep(k,s);
 showInitialHint();
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

document.querySelectorAll('.sc-tab').forEach(function(btn){
 btn.addEventListener('click',function(){
  if(stepRunning||btn.dataset.kind===curKind)return;
  stopAutoPlay();
  displayLog='';hintShown=false;
  byId('live-demo-output').innerHTML='';
  renderVisualStep(btn.dataset.kind,1);
  showInitialHint();
  setStatus(idleModeLabel(),replayMode?undefined:'ok');
 });
});
byId('step-pills').addEventListener('click',function(ev){
 var pill=ev.target.closest('.step-pill');
 if(!pill||stepRunning)return;
 stopAutoPlay();
 var target=Number(pill.dataset.step)||1;
 runSingleStep(curKind,target);
});
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
byId('live-demo-close').addEventListener('click',closeLiveDemo);
})();
"""

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

def build(out, img_dir, maxw):
    D.validate_layout()
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)
    body = ''.join(slide_html(k, D.slides[k], img_dir, maxw) for k in sorted(D.slides))
    recorded_json = load_recorded_demo(img_dir)
    notes_json = json.dumps({str(k): v for k, v in D.notes.items()}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    doc = f"""<!DOCTYPE html>
<html lang="en" dir="ltr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>Auto-routing LLMs — Balancing Quality, Cost &amp; Latency with Decision Models and Microsoft Copilot</title>
<style>{CSS % (D.BG, D.INK, D.CY, D.CARD, D.CODEBG, D.EDGE, D.MUTED, D.AMB)}</style></head>
<body><div id="deck-progress" aria-hidden="true"></div><main id="stage">{body}</main>
{PRESENTER_UI}
{LIVE_DEMO}
<script>window.RECORDED_DEMO={recorded_json};window.SLIDE_NOTES={notes_json};</script>
<script>{JS}</script></body></html>"""
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(doc)
    print(f'Saved {out}  ({len(D.slides)} slides, {os.path.getsize(out)/1e6:.2f} MB)')

if __name__ == '__main__':
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = os.path.dirname(here)
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(root, 'dist', 'html', 'index.html'))
    ap.add_argument('--images', default=os.path.join(here, 'assets', 'images'))
    ap.add_argument('--maxw', type=int, default=1600, help='max image edge in px')
    a = ap.parse_args(); build(a.out, a.images, a.maxw)
