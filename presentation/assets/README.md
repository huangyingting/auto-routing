# Presentation visual assets & demo recordings

## 1. Hand-drawn comic illustrations (`images/hd-*.jpg`)

Shared style suffix:
> Style: loose hand-drawn pen-and-ink doodle with light pencil hatching and a very light, sparse watercolor wash, like a notebook sketch. Plain off-white paper background (#F7F4EE). Muted, restrained palette: charcoal ink lines (#333333), soft slate blue (#4A6C8C), warm grey, and only a tiny touch of muted brick red (#B5533C). No glow, no neon, no gradients. No text, no words, no letters, no numbers, no watermarks, no logos.

| File | Size | Subject |
|---|---|---|
| `hd-fork.jpg` | 3:2 | Robot dispatcher at a fork holding a clipboard, pointing between a fast bicycle courier and a heavy cargo van |
| `hd-sorter.jpg` | 3:2 | Robot sorting incoming documents into three policy-governed trays |
| `hd-tradeoff.jpg` | 3:2 | Robot weighing a stopwatch in one hand and a coin in the other above a quality checkmark sheet |
| `hd-review.jpg` | 3:2 | Two robots at a desk reviewing and marking up a shared draft document together |

## 2. Vector SVG charts & official product images (`images/*.svg`, `images/*.png`)

HTML embeds `.svg` files directly as native vector graphics (`data:image/svg+xml;base64,...`); PPTX embeds their offscreen-rendered `2×` companion `.png` files (zero browser chrome or scrollbars).

| File | Source | Slide |
|---|---|---|
| `bench-163x-frontier.svg` (`.png`) | GenisisIQ 28-model Creative & Multimodal Benchmark (`163×` Cost Compression Frontier) | Slide 5 |
| `m365-copilot-home.png` | Official Microsoft Blog — Microsoft Copilot Home unified `Auto` composer (`Chat` + `Cowork`) | Slide 8 |
| `m365-cowork-ui.png` | Official Microsoft Learn — Copilot Cowork `Chat / Cowork` + `Auto Medium` composer | Slide 9 |
| `fusion-picker.png` | Official GitHub Changelog — GitHub Copilot Fusion composer (`Standard` / `High` / `Max`) | Slide 10 |
| `fusion-patterns.png` | Official GitHub Changelog — Three execution patterns in Copilot Fusion (`Single` / `Cascade` / `Critique`) | Slide 11 |
| `foundry-overview.png` | Official Microsoft Learn — Microsoft Foundry Auto (`"model": "auto"`) & Model Router overview across 40+ models & coding/agent SDKs | Slide 12 |
| `foundry-router-flow.png` | Official Microsoft Learn — Foundry Model Router request flow (`Pool → Rank → PTU/PAYG → Failover`) | Slide 13 |
| `hydra-pareto.png` | Official GitHub Blog — HyDRA 5-model production pool Pareto frontier (`arXiv:2605.17106`) | Slide 15 |
| `decision-102-benchmarks.svg` (`.png`) | Official Microsoft Command Line (`Microsoft Decision benchmark report`, Nov 14, 2026) — `#1` overall (`78.8%`) across 102 blind benchmarks (385,246 questions) & leading 7 of 9 capability categories | Slide 20 |

## 3. Recorded interactive demo traces (`demo-recordings.json`)

Embedded automatically into `dist/html/index.html` and `docs/index.html` by `build_html.py` so the Interactive Auto-Routing Studio works offline and on GitHub Pages across all 3 scenarios (`fusion`, `foundry`, `decision`).

