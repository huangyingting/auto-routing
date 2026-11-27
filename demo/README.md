# Auto-Routing LLMs Interactive Demos

这组 Demo 对应幻灯片第 20、21、22 页的三个核心生产场景，支持**静态网页回放**（GitHub Pages 零依赖运行）与**本机 Live Bridge 实时调用**。

## 1. Demo 1 · GitHub Copilot Fusion 与缓存复用（本机真实执行 `copilot` CLI）

运行：

```text
npm --prefix demo run demo:fusion
npm --prefix demo run demo:fusion:live
node demo/src/demo-cli.mjs --demo fusion --step 1 --live
```

当本机已安装并登录 GitHub Copilot CLI（`copilot`）时，4 个互不重复的场景会在隔离临时工作区中发起 **5 次真实 `copilot` CLI 调用**，并从 `--usage-output-file` 读取真实选中的模型、Token、缓存命中和 AI Credits（加 `--live` 则强制要求本机具备 `copilot`，绝不静默降级为回放）：

1. **Fusion `Single`（常规代码修改 + 真实 `node --test`）**：单次执行 `copilot --model fusion --fusion-tier high` 修复 `fixtures/format.mjs`，验证即使在 `high` 档位下，`session.fusion_resolved` 也会对常规任务自动选择 `pattern="single"`，不增加额外评审，并通过 3/3 宿主单测。
2. **Fusion `Cascade`（并发死锁修复）**：单次执行 `copilot --model fusion --fusion-tier high` 修复 `fixtures/token-bucket.ts`，由 `gpt-6.1-sol` 修复、`gpt-6-luna` 独立检查并给出 `5/5 accept`，因此跳过 `claude-opus-5.5` 重做；随后通过 500 次并发压测。
3. **Fusion `Critique`（50k RPS 支付网关架构 RFC）**：单次执行 `copilot --model fusion --fusion-tier high`，由 `claude-opus-5.5` 起草、`gpt-6-luna` 指出跨区域 RPO=0 前提不足，再交回 `claude-opus-5.5` 修订。
4. **缓存复用（`--resume` 99% 命中）**：首次运行时先执行一次真实 `copilot --model auto` 预热会话，再执行一次真实 `copilot --model auto --resume <sid>` 追问。原始日志同时保留两次调用，`usage.json` 显示追问有 **99%** 的 `cacheReadTokens` 命中率。

## 2. Demo 2 · Microsoft Foundry `Model Router` & 多子任务协同

运行：

```text
npm --prefix demo run demo:foundry
npm --prefix demo run demo:foundry:live
```

配置 `AZURE_FOUNDRY_ENDPOINT`（搭配 `AZURE_FOUNDRY_API_KEY`、`AZURE_ENTRA_TOKEN` 或 `az login`）后，全部 4 步均真实请求云端 `/openai/v1/chat/completions`（`Foundry-Features: ModelRouterControls=V1Preview`）：

1. **资格门槛与跨厂商参数自适应实测**：携带 `developer` 角色、`temperature=0.2` 与 `json_object` 发起真实请求，验证参数归一化与 `200 OK`。
2. **简单提取路由至轻量模型**：对 `fixtures/renewal-context.json` 中的发票文本发起 `mode: "balanced"` 提取，校验返回 JSON 与 `routing_trace` 毫秒耗时。
3. **复杂形式化推理升级 + 自适应会话亲和**：同一端点发送 Rust 无锁队列证明与第 2 轮追问，验证模型升级与 `session_affinity` 保持。
4. **客户续约多子任务协同**：依次以 `mode: "cost"` 检索信号、以 `mode: "quality"` 生成续约策略与幻灯片提纲。

## 3. Demo 3 · `Microsoft-Decision-1.1` 结构化决策与护栏

运行：

```text
npm --prefix demo run demo:decision
npm --prefix demo run demo:decision:live
```

配置 `AZURE_FOUNDRY_ENDPOINT`（及可选 `DECISION_DEPLOYMENT`，默认 `microsoft-decision-1.1`）后，5 个生产场景共对 `/providers/microsoft/v1/systemone` 发起 **8 次真实 HTTP 调用**（加 `--live` 强制要求云端连接）：

1. **收件箱前置分流（`choice`，4 次调用）**：分别处理致谢、退订、促销查询与跨系列质保对比；前三条无需高成本大模型。
2. **受伤投诉转人工（`choice` + `score` + `noul`，1 次调用）**：一次返回负责团队、紧急程度与重复投诉判断。
3. **发送前拦截竞品草稿（`noul`，1 次调用）**：检测推荐竞品 Fabrikam 的回复并在发送前转人工。
4. **缺失附件时先询问（`choice`，1 次调用）**：只有 `Contract A`、缺少 `Exhibit B` 时，停止比较并提示用户补充材料。
5. **货物破损判断（图片 + `noul`，1 次调用）**：把真实货损 JPEG 以 Base64 放入 `assets`，在 `state` 中通过 `image:cargo-damage.jpg` 引用，判断运输中的货物是否破损或发生严重位移，并在概率超过阈值时转人工验货。

## 命令行单步与自定义句子实时探测

```text
node demo/src/demo-cli.mjs --probe "Thanks! 👍"
node demo/src/demo-cli.mjs --demo fusion --step 1 --live
npm --prefix demo run demo:replay
```

## 网页交互式 Demo Studio

- **三视图切换与累计账本**：默认打开 **`✦ Visual`（可视化视图）**，直观展示真实文件代码修改对比、Judge/Critic 评审意见、两阶段请求卡片、智能客服收件箱分流与发送前拦截高亮，并在顶部实时累计“固定大模型 vs 自动路由”的成本与耗时；同时保留 **`Summary`** 与 **`{ } Raw Log`**。原始日志只显示当前步骤或刚刚执行的自定义输入，切换步骤时自动换成对应步骤的日志预览，不会把前面的记录一直累加。
- **本机 Live Bridge（真实执行）**：运行 `npm --prefix demo run demo:web` 后打开 `http://127.0.0.1:8787/#20`（中文版 `/zh/#20`），页面上的步骤按钮与底部自定义输入框都会实时驱动本机 `copilot` CLI 以及已配置的云端 Foundry / Decision-1.1 端点，并将实时补丁与返回结果同步渲染到可视化工作台。
- **静态离线回放（GitHub Pages）**：直接打开 `dist/html/index.html` 或 `dist/html/index.zh.html` 时无需后端，使用 `presentation/assets/demo-recordings.json` 离线回放（可通过 `node demo/src/record-web-demo.mjs --record-fusion` 重新录制真实轨迹）。

### 如何从服务器日志确认是真实调用

启动 `npm --prefix demo run demo:web` 后，终端会输出两类结构化日志：

```text
2026-11-26T05:00:00.000Z [DEMO] LIVE demo=foundry step=2 backend=foundry-router
2026-11-26T05:00:00.010Z [LIVE-CALL a1b2c3d4] START backend=foundry-router method=POST target=/openai/v1/chat/completions attempt=1 model=auto mode=balanced authSource=az-cli
2026-11-26T05:00:01.107Z [LIVE-CALL a1b2c3d4] COMPLETE backend=foundry-router status=200 wallMs=1097 attempt=1 responseModel=DeepSeek-V4.1-Flash
```

- `[DEMO] LIVE` 表示服务器选择了实时执行；`REPLAY` 或 `FALLBACK` 表示使用录制回放。
- `[LIVE-CALL] START/COMPLETE` 由实际 CLI 进程或 HTTP 请求函数输出，二者使用相同的 `callId`。
- 日志只打印请求路径、模型、状态码、耗时和认证来源，不打印 API Key、Bearer Token、完整端点或请求正文。
- 修改服务器代码后需要重新启动 `npm --prefix demo run demo:web` 才能看到新日志。
