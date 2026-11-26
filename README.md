# Auto-routing LLMs learning kit

“Auto-routing LLMs — Understand how the right model is selected automatically per task to balance quality, cost and latency, using a proper decision model and with Microsoft Copilot as example” 的完整学习与演示仓库，包含 26 页演示文稿、内联矢量图表与截图的单文件可部署网页，以及交互式路由回放与实时验证 Demo。

## 目录

| 目录 | 用途 |
|---|---|
| `presentation/src/` | PPTX/HTML 生成器和 26 页幻灯片源代码 |
| `presentation/assets/` | 手绘插图、原生矢量 `.svg` 图表与官方产品图，以及预录制交互轨迹 `demo-recordings.json` |
| `dist/pptx/` | 生成的 PowerPoint 文件（含完整中文讲者备注） |
| `dist/html/` | 生成的独立单文件 HTML 网页（集成交互式 Auto-Routing Studio） |
| `docs/` | GitHub Pages 发布目录，构建时自动同步 HTML |
| `demo/` | 命令行回放、本机 Live Bridge 服务与 Foundry / Decision-1.1 实时调用脚本 |
| `.github/workflows/pages.yml` | GitHub Pages 自动构建与部署 |

## 内容脉络（5 大模块 · 26 页）

1. **能力专精化（Slides 3–4）**：基于微软 Charles Lamanna 的白板拆解（>90% Copilot 请求已走 Auto），说明为何不存在“全能第一”的单一模型，以及如何把单次续约请求拆解为 SLM 检索、Claude 推理制表与 GPT Image 2.5 配图的跨实验室协同。
2. **成本压缩与缓存边界（Slides 5–6）**：引用 GenisisIQ 28 模型 × 8 多模态任务基准（前 14 名质量仅差 4.2 分，算力却相差 **163×**），证明常规工作无需动用昂贵旗舰，同时阐述 **10×–20×** 前缀缓存自然边界铁律。
3. **微软产品实战与官方截图（Slides 7–13）**：结合官方产品截图拆解 **Microsoft Copilot Home**、**Copilot Cowork Auto**、**GitHub Copilot Fusion**（`Single` / `Cascade` / `Critique` 三种执行拓扑，AA 指数接近满血但省费约 50%）与 **Microsoft Foundry Model Router 工作原理**（非 LLM 毫秒级专用 ML 排序器、1–2% / 5–6% 质量带与子集重校准、`Adaptive` 消息指纹缓存亲和、排序前资格过滤 + 跨厂商参数自动适配，以及 `PTU（$0 模型费） → PAYG → 托管 → 子集内第 2 顺位模型` 两级容量与故障转移）。
4. **底层架构：业界通用方案 vs. 微软方案（Slides 14–16）**：对比规则/向量路由、二分类偏好路由（如 RouteLLM 绑死模型 ID 的重训痛点）、级联 FrugalGPT 与生成式 LLM 路由；详解 GitHub **HyDRA（`arXiv:2605.17106`）** 4 头 `ModernBERT` 能力需求预测（86 ms CPU）+ 零重训配置短板匹配（等质量省费 **54.1%**）。
5. **Microsoft-Decision-1.1 与交互式 Demo（Slides 17–26）**：介绍基于 Gemma 4 26B-A4B MoE 与定制推理引擎的 **Microsoft-Decision-1.1**（`$0.042/1M` 输入、输出免费，支持文本/JSON/图片），先讲清 `/providers/microsoft/v1/systemone` 的 `choice`、`noul`、`score` 三大原语与四个生产模式，再用 102 项盲测第一的硬指标和获客成本降低 **7.2×**（`$13 → $1.81`）案例佐证，最后通过三个交互式 Demo 串联全流程。

## 快速开始

需要 Python 3.9+（运行 `demo` 需 Node.js 20+）。

```text
python -m pip install -r requirements.txt
python build.py --target all
```

Windows 可运行 `run.bat`，macOS/Linux 可运行 `./run.sh`。

单独构建与运行 Demo：

```text
python build.py --target pptx
python build.py --target html
python build.py --target demo

npm --prefix demo run demo:fusion:live
npm --prefix demo run demo:foundry
npm --prefix demo run demo:decision
npm --prefix demo run demo:replay
```

- **双语 PPTX（英文版配英文 Speaker Notes，中文版配中文 Speaker Notes）**：
  - 英文版：`dist/pptx/Auto-routing LLMs.pptx`（English slides + English speaker notes）
  - 中文版：`dist/pptx/Auto-routing LLMs (zh-CN).pptx`（中文幻灯片 + 自然口语中文讲者备注）
- **本地讲者版双语 HTML**（左下角一键 `EN | 中文` 同步页码切换，底部含讲者工具栏 `Notes N` / `Studio D` 及 `N`/`D` 快捷键，仅在本机 `file://` 或 `localhost` / `127.0.0.1` 下启用）：
  - 英文版：`dist/html/index.html`（英文课件 + 英文讲者备注）
  - 中文版：`dist/html/index.zh.html`（中文课件 + 中文讲者备注；Live Bridge 下可通过 `/zh/` 访问）
- **GitHub Pages 公开版双语 HTML**：`docs/index.html`（英文 `/`）与 `docs/zh/index.html`（中文 `/zh/`，左下角 `EN | 中文` 切换；保留右上角 Demo 入口按钮与录制回放工作台，不含底部 `Notes`、`Studio` 栏、讲者备注及 `N`/`D` 快捷键）
- **网页集成可视化 Auto-Routing Studio**：
  - **操作与备注快捷键**：方向键 / PageUp / PageDown / 空格翻页，Shift+Space 返回，Home/End 跳至首页/末页；`F` 全屏；本地运行 `dist/html/index.html` 时，`N` 或底部 `Notes` 按钮展开/收起中文讲者备注浮层，`Esc` 关闭，`D` 打开可视化路由决策台；`Ctrl+P` 导出 PDF。
  - **GitHub Pages / 静态离线回放**：打开在线 Pages 或本地 `dist/html/index.html`，在第 11、13、21 页对应产品处或第 22–24 页点击右上角按钮（本地版还可在任意页按 `D`），即可在可视化工作台中逐步运行或 `Auto-Play` **Demo 1（Coding Agent · Fusion Single / Cascade / Critique / 99% Cache，4 个独立场景、5 次真实 CLI 调用）**、**Demo 2（Cloud API · Foundry Model Router，4 个场景）** 与 **Demo 3（App Controller · Microsoft-Decision-1.1，4 个生产场景、7 次真实请求）**——全部 12 个场景均由真实 CLI / 云端 HTTP 调用实测抓包生成（零本地模拟、零客户端拼装）。Demo 1 的缓存场景包含一次真实预热和一次 `--resume` 追问。顶部实时汇总累计成本与耗时对比，工作台右上角支持一键切换 **`✦ Visual`（代码对比、评审意见与智能收件箱视图） | `Summary` | `{ } Raw Log`**；原始日志只显示当前步骤或当前自定义输入，切换步骤后不会混入前面的日志。
  - **本机 Live Bridge（真实执行）**：运行 `npm --prefix demo run demo:web` 后打开 `http://127.0.0.1:8787/#22`，会自动检测并驱动本机 `copilot` CLI（真实运行 Demo 1 的 4 个场景及自定义 Prompt 探测；缓存场景首次运行会执行预热 + `--resume` 两次调用），以及在配置 `AZURE_FOUNDRY_ENDPOINT`（及可选 `DECISION_DEPLOYMENT`）后真实请求云端 Foundry Model Router（Demo 2 全部 4 个场景）与 `/providers/microsoft/v1/systemone`（Demo 3 全部 4 个场景）。

## 视觉系统

- 展示标题与正文（HTML）：**Inter Tight**（紧凑窄比例现代无衬线；PPTX 采用 Windows 原生 **Segoe UI Variable Display** + **Calibri**）
- 代码与终端：**Inconsolata**（`wdth 90` 紧凑等宽；回退至 **Consolas** / Cascadia Mono）
- 配色：暖米色宣纸底、炭灰墨色、石板蓝强调色、圆角微阴影卡片与砖红警示色

## 演示框架

本仓库是 `mxc` HTML/PPTX 基础框架的参照，两套保持一致的主题字体、文本与代码间距、页眉页脚、图片 cover/contain、讲者工具栏、备注浮层、快捷键和打印样式。各自的幻灯片内容、逐项动画与 Demo Studio 独立维护；两个仓库均可独立构建，不依赖相邻目录。

HTML 与 PPTX 构建前都会检查元素边界、标题换行和文本框重叠。修改框架后，在两个仓库分别运行：

```text
python -m unittest discover -s presentation/tests
python build.py --target presentation
```

