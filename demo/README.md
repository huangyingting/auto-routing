# Auto-Routing LLMs Interactive Demos

这组 Demo 对应幻灯片第 22、23、24 页的三个核心生产场景，支持**静态网页回放**（GitHub Pages 零依赖运行）与**本机 Live Bridge 实时调用**。

## 1. Demo 1 · GitHub Copilot `Auto` & `Copilot Fusion`

运行：

```text
npm --prefix demo run demo:fusion
```

逐步演示并回放 GitHub Copilot 的 `HyDRA` 能力预测与 `Copilot Fusion` 的三种执行模式：

1. **Single（简单配置查询）**：`HyDRA` 4 头编码器（86 ms CPU）判定低复杂度，路由至 `MAI Code 2 Flash`（`0.08 AI Credits`，成本降低 94%）。
2. **Cascade · Judge 放行（常规修改 + 单测）**：高效模型完成草稿并通过单测，次级 Judge 校验通过后直接短路返回，节省 52% Credits。
3. **Cascade · Judge 升级（并发死锁缺陷）**：Judge 识别锁顺序反转风险，升级至 `gpt-6.1-sol` 重新修复并通过压力测试。
4. **Critique · 并行只读评审（50k RPS 分布式限流架构）**：主模型起草方案，两个独立只读 Critic 并行指出时钟漂移与热键分片问题，主模型综合修订。
5. **Cache-Boundary 护栏**：第 2 轮追问保留主模型以复用 64.2k 已缓存前缀（90% 折扣），避免中途切模型导致 10× 重读开销。

## 2. Demo 2 · Microsoft Copilot `Auto` & Foundry `Model Router`

运行：

```text
npm --prefix demo run demo:foundry
```

回放或实时调用 Microsoft Copilot 多子任务编排与 Foundry `Model Router`（`Foundry-Features: ModelRouterControls=V1Preview`）：

1. **组织边界与容量优先级检查**：校验租户允许的模型池、区域数据边界与 `PTU -> PAYG -> Router-managed -> Failover` 顺序。
2. **简单提取路由至轻量模型**：发票 JSON 提取在 23 ms 路由开销内命中 `DeepSeek-V4.1-Flash`（0 推理 token）。
3. **复杂系统证明自动升级**：无锁环形缓冲区 ABA 证明在 20 ms 路由开销内自动升级至推理模型 `gpt-5.6-luna`。
4. **Microsoft Copilot 客户续约多模型协同**：`Decision-1.1` 推荐 `Chat -> Cowork`，拆分为 `SLM` 检索邮件合同 + `Claude Opus 5.5` 推理与幻灯片 + `GPT Image 2.5` 生成配图。
5. **高并发 `429 -> 200` 自动故障转移**：首选部署限流返回 429 时，路由器在 19 ms 内透明切换至次优合格模型。

## 3. Demo 3 · `Microsoft-Decision-1.1` 结构化决策与护栏

运行：

```text
npm --prefix demo run demo:decision
```

演示 `/providers/microsoft/v1/systemone` 的三类结构化原语（`choice`、`noul`、`score`）：

1. **5 次一致性与低延迟探测（`noul`）**：对非结构化客户邮件连续请求 5 次，`ready_to_buy = 0.9800`（0.0 pt 波动，平均 180 ms，`$0.000013`/次）。
2. **模型前置路由器（`choice`）**：在 `no_reply`、`code_template`、`fast_slm` 与 `frontier_sol` 间分流，32 条真实收件箱准确率 100%（手写正则 88%），省去 57% 昂贵大模型调用。
3. **单次请求合并路由 + 优先级调度（`choice` + `score` + `noul`）**：床架坍塌受伤工单一次返回 `safety_support` + `score = 2.94 (P3 Immediate Human)` + `repeat = 0.99`。
4. **出站内容合规拦截（`noul`）**：在大模型草稿发出前识别向竞品导流（`mentions_competitor = 0.964 >= 0.50`），当场拦截。
5. **校准弃权与端到端 ROI**：缺失附件时 `max(p) = 0.48 < 0.75` 触发安全弃权；三道检查合计仅 `$0.00019`/条，将获客成本从 `$13` 降至 `$1.81`（降低 `7.2×`）。

## 网页交互式 Demo Studio

- **静态回放**：直接打开 `dist/html/index.html`（或在线 GitHub Pages），在第 22、23、24 页点击右上角按钮（或在任意页按 `D`），即可逐步运行、一键 `Auto-Play`，甚至在底部输入框输入自定义提示词观察实时路由决策！
- **本机 Live Bridge**：运行 `npm --prefix demo run demo:web` 后打开 `http://127.0.0.1:8787/#22`（若配置 `AZURE_FOUNDRY_ENDPOINT` 则自动驱动真实云端 Foundry 端点）。
