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
5. **Microsoft-Decision-1.1 与交互式 Demo（Slides 17–26）**：介绍基于 Gemma 4 26B-A4B MoE 与定制推理引擎的 **Microsoft-Decision-1.1**（`$0.042/1M` 输入、输出免费，102 项盲测第一，支持文本/JSON/图片），详解 `/providers/microsoft/v1/systemone` 的 `choice`、`noul`、`score` 三大原语、四个生产示例、获客成本降低 **7.2×**（`$13 → $1.81`）案例，以及三个可逐步回放的交互式 Demo。

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

npm --prefix demo run demo:fusion
npm --prefix demo run demo:foundry
npm --prefix demo run demo:decision
```

- **PPTX**：`dist/pptx/Auto-routing LLMs.pptx`
- **HTML**：`dist/html/index.html`（同时复制到 `docs/index.html`）
- **网页集成可视化 Auto-Routing Studio**：
  - **操作与备注快捷键**：方向键 / PageUp / PageDown / 空格翻页，Shift+Space 返回，Home/End 跳至首页/末页；`F` 全屏；`N` 或底部 `Notes` 按钮展开/收起中文讲者备注浮层，`Esc` 关闭；翻页同步备注，打开 Studio 自动收起；`D` 打开可视化路由决策台；`Ctrl+P` 导出 PDF（不含工具栏和备注）。
  - **GitHub Pages / 静态离线回放**：直接打开 `dist/html/index.html`，在第 11、13、21 页对应产品处或第 22–24 页点击右上角按钮（或任意页按 `D`），即可在零滚动条的可视化路由决策台中逐步运行或 `Auto-Play` **Demo 1（Copilot Fusion）**、**Demo 2（Foundry Model Router & M365 Copilot）** 与 **Demo 3（Microsoft-Decision-1.1）**，支持一键点击预设测试胶囊或输入自定义提示词实时查看算分条、拓扑节点与省费账本（点击 `{ } Log` 可展开原始 CLI/HTTP 报文）。
  - **本机 Live Bridge**：运行 `npm --prefix demo run demo:web` 后打开 `http://127.0.0.1:8787/#22`（配置 `AZURE_FOUNDRY_ENDPOINT` 后自动切换为真实云端 Foundry / Decision-1.1 调用）。

## 视觉系统

- 展示大标题（HTML）：**Newsreader** 衬线字体，增强编辑感与叙事张力
- 标题与正文：**Plus Jakarta Sans**（回退至 Inter / Segoe UI）
- 代码与终端：**JetBrains Mono**（回退至 Cascadia Code / Consolas）
- 配色：暖米色宣纸底、炭灰墨色、石板蓝强调色、圆角微阴影卡片与砖红警示色

## 演示框架

本仓库是 `mxc` HTML/PPTX 基础框架的参照，两套保持一致的主题字体、文本与代码间距、页眉页脚、图片 cover/contain、讲者工具栏、备注浮层、快捷键和打印样式。各自的幻灯片内容、逐项动画与 Demo Studio 独立维护；两个仓库均可独立构建，不依赖相邻目录。

HTML 与 PPTX 构建前都会检查元素边界、标题换行和文本框重叠。修改框架后，在两个仓库分别运行：

```text
python -m unittest discover -s presentation/tests
python build.py --target presentation
```

