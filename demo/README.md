# Auto-Routing LLMs Interactive Demos

这组 Demo 对应幻灯片第 22、23、24 页的三个核心生产场景，支持**静态网页回放**（GitHub Pages 零依赖运行）与**本机 Live Bridge 实时调用**。

## 1. Demo 1 · GitHub Copilot `Auto` & 多模型协同（本机真实执行 `copilot` CLI）

运行：

```text
npm --prefix demo run demo:fusion
npm --prefix demo run demo:fusion:live
node demo/src/demo-cli.mjs --demo fusion --step 1 --live
```

当本机已安装并登录 GitHub Copilot CLI（`copilot`）时，全部 5 个步骤都会在隔离临时工作区中对 `demo/fixtures/` 发起**真实 `copilot` CLI 调用**，并从 `--usage-output-file` 读取真实选中的模型、Token、缓存命中和 AI Credits（加 `--live` 则强制要求本机具备 `copilot`，绝不静默降级为回放）：

1. **Single（简单配置查询）**：对 `fixtures/config.ts` 执行 `copilot --model auto`，验证自动命中轻量模型（如 `MAI Code 2 Flash`）并输出真实 `AI Credits` 与延迟。
2. **Cascade · Judge 放行（常规修改 + 真实 `node --test`）**：主模型修复 `fixtures/format.mjs` 的 `\u00A0` / Tab 空白处理，宿主机真实运行 `node --test format.test.mjs` 通过后，交由只读 Judge 复核 `ACCEPT`，跳过昂贵重修。
3. **Cascade · Judge 升级（并发死锁缺陷）**：只读 Judge 审查 `fixtures/token-bucket.ts` 识别锁顺序反转并给出 `ESCALATE`，随后启动修复并运行宿主 500 次并发交错压测验证零死锁。
4. **Critique · 并行只读评审（50k RPS 分布式限流架构）**：主模型创建带 `--session-id` 的初稿，两个限制只读权限（`--deny-tool write --deny-tool shell`）的 Critic 通过 `Promise.all` 并行审查时钟漂移与热键分片，再恢复主会话综合修订。
5. **Cache-Boundary 护栏**：通过 `--resume` 在同一会话发起追问，对比前后 `usage.json` 验证真实 `cacheReadTokens` 命中率与单轮增量 Credits。

## 2. Demo 2 · Microsoft Foundry `Model Router` & 多子任务协同

运行：

```text
npm --prefix demo run demo:foundry
npm --prefix demo run demo:foundry:live
```

配置 `AZURE_FOUNDRY_ENDPOINT`（搭配 `AZURE_FOUNDRY_API_KEY`、`AZURE_ENTRA_TOKEN` 或 `az login`）后，第 1–4 步全部真实请求云端 `/openai/v1/chat/completions`（`Foundry-Features: ModelRouterControls=V1Preview`），第 5 步在无需云端配额的情况下也会真实拉起本机双端点 HTTP `429 -> 200` 故障转移验证：

1. **资格门槛与跨厂商参数自适应实测**：携带 `developer` 角色、`temperature=0.2` 与 `json_object` 发起真实请求，验证参数归一化与 `200 OK`。
2. **简单提取路由至轻量模型**：对 `fixtures/renewal-context.json` 中的发票文本发起 `mode: "balanced"` 提取，校验返回 JSON 与 `routing_trace` 毫秒耗时。
3. **复杂形式化推理升级 + 自适应会话亲和**：同一端点发送 Rust 无锁队列证明与第 2 轮追问，验证模型升级与 `session_affinity` 保持。
4. **客户续约多子任务协同**：依次以 `mode: "cost"` 检索信号、以 `mode: "quality"` 生成续约策略与幻灯片提纲。
5. **真实 HTTP `429 -> 200` 故障转移测试台**：在本机 `127.0.0.1` 启动主备两个 HTTP 端点，主端点真实返回 `HTTP 429 Too Many Requests`，验证客户端/路由层自动切换备选端点（若已配 `AZURE_FOUNDRY_ENDPOINT` 则备选端点转发至真实云端 Foundry）。

## 3. Demo 3 · `Microsoft-Decision-1.1` 结构化决策与护栏

运行：

```text
npm --prefix demo run demo:decision
npm --prefix demo run demo:decision:live
```

配置 `AZURE_FOUNDRY_ENDPOINT`（及可选 `DECISION_DEPLOYMENT`，默认 `microsoft-decision-1.1`）后，全部 5 步均对 `/providers/microsoft/v1/systemone` 发起**真实 HTTP 调用**（加 `--live` 强制要求云端连接）：

1. **5 次连续调用一致性与延迟实测（`noul`）**：真实连发 5 次请求，现场统计概率极差（spread）与中位延迟（p50）。
2. **收件箱前置路由器（`choice`）**：对致谢、退订、促销查询与跨系列质保对比连续发起 4 次真实 `choice` 分流。
3. **单次请求合并三问（`choice` + `score` + `noul`）**：对床架坍塌受伤工单一次返回团队分派、`P0–P3` 期望分与重复投诉判断。
4. **出站内容合规拦截（`noul`）**：实时检测推荐竞品 Fabrikam 的回复草稿并在发送前拦截。
5. **缺失附件校准弃权（`choice`）**：当上下文仅附带 `Contract A` 而缺少 `Exhibit B` 时，验证模型识别缺失材料并停下追问。

## 命令行单步与自定义句子实时探测

```text
node demo/src/demo-cli.mjs --probe "Thanks! 👍"
node demo/src/demo-cli.mjs --demo fusion --step 1 --live
npm --prefix demo run demo:replay
```

## 网页交互式 Demo Studio

- **本机 Live Bridge（真实执行）**：运行 `npm --prefix demo run demo:web` 后打开 `http://127.0.0.1:8787/#22`，页面上的步骤按钮与底部自定义输入框都会实时驱动本机 `copilot` CLI、本机 `429 -> 200` 测试台以及已配置的云端 Foundry / Decision-1.1 端点。
- **静态离线回放（GitHub Pages）**：直接双击打开 `dist/html/index.html` 时无需后端，使用 `presentation/assets/demo-recordings.json` 离线回放（可通过 `node demo/src/record-web-demo.mjs --record-fusion` 重新录制真实轨迹）。
