#!/usr/bin/env python3
"""Bilingual (en + zh) slide text and English speaker notes for Auto-routing LLMs."""

EN_NOTES = {
    0: (
        "Welcome, everyone. Almost every team shipping AI today hits the same wall: new models drop every few weeks, "
        "capabilities keep shifting, and we have to keep quality high while bringing cost and latency down. That is what auto-routing solves.\n"
        "Over the next 45 minutes, I will share how we do this in production at Microsoft—starting with Microsoft Copilot, "
        "GitHub Copilot Fusion, and Foundry Model Router, then looking under the hood at our HyDRA architecture, and finally "
        "introducing Microsoft-Decision-1.1 with three live, end-to-end demos you can apply to your own stack."
    ),
    1: (
        "Here is our roadmap for today. First, why auto-routing matters: no single model wins every task, cost across top models "
        "spans more than 160x, and there is a critical prefix-cache rule that trips up many teams.\n"
        "Next, we will tour how Microsoft products route in production and compare common industry routers against GitHub's HyDRA design. "
        "In the second half, we will dive into Microsoft-Decision-1.1's three typed primitives and run all three live demos."
    ),
    2: (
        "Let me start with a quick gut check: how many teams here pick one flagship model and pin every single turn to it? "
        "If you pin the biggest model everywhere, you pay three to five times more and wait longer even on trivial summaries. "
        "If you pin a small model everywhere, it falls apart as soon as reasoning gets tricky. And in practice, developers switch to a heavy model "
        "for one gnarly bug and forget to switch back for the rest of the week.\n"
        "As Charles Lamanna put it, there is no longer one model that is #1 at everything—some lead in deep math and reasoning, others in image generation, "
        "while small models fly through email extraction. That is why over 90% of Microsoft Copilot traffic now runs on Auto, picking the right model per sub-task inside IT boundaries."
    ),
    3: (
        "Let's make sub-task specialization concrete with a real Tuesday-afternoon request: 'Customer renewal is Thursday—should we push expansion, "
        "hold flat, or offer a discount, and build me a deck to make the case?'\n"
        "First, a deterministic guardrail checks tenant-approved providers and data residency. Then Auto splits the work into four specialist jobs: "
        "a fast small model scans emails, Teams threads, and past contracts; Claude Opus 5.5 crunches the renewal economics and caches that full context; "
        "GPT Image 2.5 renders custom proposal graphics that text models simply cannot draw; and finally, Opus 5.5 reuses its warm context cache to assemble the finished PowerPoint without re-reading tens of thousands of tokens."
    ),
    4: (
        "Capability is half the story; cost compression is the other. This benchmark ran 28 leading models across 8 multimodal engineering tasks—224 runs in total.\n"
        "Look at how tight the top of the leaderboard is: the top 14 models all land within a 4.2-point quality band, between 86.2 and 90.4. "
        "For everyday work, they feel nearly indistinguishable. Yet the bill for those exact same tasks ranges from 9 cents with auto-routing and 23 cents on Haiku 5.5 "
        "all the way up to $14.75 on Opus 5—a 163x spread. Small models handle routine coding and dashboards effortlessly; you only want to pay for heavy reasoning when a complex spec would trap smaller models in retry loops.\n\n"
        "Source: GenisisIQ 28-model multimodal benchmark (blog.genisisiq.com)."
    ),
    5: (
        "When engineers see a 163x cost gap, their first instinct is often: 'Let's score every single turn and downgrade to a cheap model whenever the user asks an easy follow-up!' "
        "Don't do that—it is the #1 auto-routing trap: breaking a warm prefix cache.\n"
        "Modern agents load tens of thousands of tokens—contracts, repo files, and 80-plus tool schemas—on Turn 1. As long as follow-up turns stay on that same model, "
        "cached prompt reads cost roughly 90% less and return much faster. Switching to a 'cheaper' model mid-conversation invalidates that cache and forces a full-price re-prefill of 50,000 tokens, costing more time and money. "
        "Route only at natural cache boundaries: Turn 1, right after context compaction, on isolated sub-agents, or when task difficulty jumps dramatically.\n\n"
        "Source: Charles Lamanna (M365 Copilot Auto) & Joe Binder (GitHub Blog on cache-aware routing)."
    ),
    6: (
        "When we apply capability matching and cache discipline across Microsoft, it doesn't show up as one monolith—it shows up as four purpose-built routing surfaces.\n"
        "In workplace productivity, M365 Copilot and Cowork decide when to hand off from quick chat to multi-step execution and pick across approved labs. "
        "For developers, GitHub Copilot Fusion goes beyond picking a model—it switches execution topologies between Single pass, Cascade, and Critique. "
        "For cloud API builders, Foundry Model Router ranks 45 models in ~20 milliseconds while draining pre-paid PTU capacity first. "
        "And on the far right, Microsoft-Decision-1.1 exposes that same fast, calibrated decision brain directly as an API for your own software."
    ),
    7: (
        "Let's start on the workplace side with Microsoft Copilot Home. Users used to wonder whether to type in quick Chat or spin up a long-running workspace; "
        "now a single unified Auto composer handles both.\n"
        "Behind that prompt box, three things happen in roughly a hundred milliseconds: Microsoft-Decision-1.1 checks whether the prompt needs multi-step orchestration "
        "and suggests handing off to Cowork—2.2x faster and over four times cheaper than asking a generative LLM; IT tenant switches and EU Data Boundary rules filter eligible providers; "
        "and Work IQ pulls only the most relevant M365 context, even offloading light tasks to local models on supported Windows PCs."
    ),
    8: (
        "Once work moves into multi-step Copilot Cowork, you see prefix-cache protection front and center—lock the model, tune the effort.\n"
        "Auto inspects your opening prompt—whether it's a quick email, calendar coordination, or multi-sheet financial modeling—locks in the best fit from your tenant-enabled pool "
        "like GPT 6.1 Sol, Opus 5.5, or Grok 4.7, and stays on it to keep the context cache warm. Every response carries a transparent badge showing which model ran. "
        "Then, on each step, Decision-1.1 dynamically dials reasoning effort from Light all the way up to Max, while Agent 365 keeps team spend predictable."
    ),
    9: (
        "Now look at daily life inside an IDE with GitHub Copilot Fusion. Instead of forcing developers to pick from a constantly changing dropdown of model names, "
        "Fusion lets you pick an effort tier: Standard, High, or Max.\n"
        "The economics speak for themselves: on the Artificial Analysis Coding Agent Index, Fusion Max scores 60—right on the heels of pinning flagship Opus 5.5 Max on every turn—while cutting API cost by roughly half and wall-clock time by 40%. "
        "AT&T's engineering team shared how developers used to switch to a heavy model for one tough bug and leave it on all week; Fusion right-sizes every turn automatically, even routing lightweight edits to local Flash models."
    ),
    10: (
        "How does Fusion keep frontier quality at half the price? By upgrading routing from 'which single model?' to 'which multi-model workflow?'\n"
        "For everyday lookups and clean edits, it picks Single—one right-sized model with zero extra review overhead. "
        "When concurrency or subtle edge cases creep in, it runs Cascade: a cost-effective primary model writes the patch, and a Judge model reviews it—accepting clean work immediately, and escalating to a heavy Repair model only when needed. "
        "And for high-stakes architecture or complex debugging, Critique runs cross-lab read-only reviewers in parallel—read-only so they never clash on file edits—before the primary model synthesizes the final revision."
    ),
    11: (
        "If you are building your own cloud app rather than using Copilot out of the box, Microsoft Foundry Model Router gives you this directly on `/chat/completions`—and setting `model: \"auto\"` uses the exact same engine.\n"
        "People often ask if adding a router slows requests down. It doesn't, because the router is not a generative LLM—it is a dedicated ML ranker trained on billions of real interactions. "
        "It scores your system prompt, conversation history, and tool schemas in ~20 milliseconds without storing customer prompts. "
        "In Balanced mode, it picks the cheapest model within 1–2% of the top predicted quality; Cost mode widens that band to 5–6%. Across multi-turn chats, adaptive session affinity tracks message fingerprints so you keep reusing a warm model as long as it stays in band."
    ),
    12: (
        "Anyone who has wired up multiple model providers by hand knows ranking is the easy part—the real headaches are parameter mismatches and rate-limit spikes. Foundry handles all of that inline.\n"
        "Before ranking, an eligibility gate filters out models that miss your region, enterprise allow-list, tool calling, JSON schema, or vision requirements. "
        "Once a model is chosen, Foundry normalizes parameters on the fly—stripping `temperature` for reasoning models, dropping `reasoning_effort` for non-reasoning ones, and mapping `developer` to `system` so you don't hit random HTTP 400s. "
        "Finally, it drains your pre-paid PTU capacity at zero extra model fee before touching pay-as-you-go or router-managed capacity, and automatically fails over to the #2 approved model on 429 bursts."
    ),
    13: (
        "Stepping back from specific products, let's look at the four routing architectures the industry has tried—and where each one hits a ceiling.\n"
        "Heuristics and semantic embedding routers run in a few milliseconds, but surface keywords don't equal reasoning difficulty—'sort a list' and 'prove a lock-free ring buffer' can look dangerously similar in embedding space. "
        "Binary preference routers like RouteLLM improve accuracy, but they bake fixed model IDs right into classifier weights—so every time a new model ships, you have to collect fresh pairs and retrain. "
        "Serial cascades like FrugalGPT pay double latency whenever a hard prompt forces a draft-then-retry. And prompting a general LLM to act as your router adds up to two seconds of latency and suffers from RLHF overconfidence."
    ),
    14: (
        "How did GitHub solve the 'models ship monthly, we can't retrain monthly' problem? The HyDRA paper decouples task demand from the model catalog.\n"
        "Under the hood, a lightweight ModernBERT encoder with four prediction heads runs in 86 milliseconds median CPU time. Instead of predicting a model name, it scores how much Reasoning, Code Generation, Debugging, and Tool Use this specific turn demands. "
        "Meanwhile, each candidate model's 4D capability profile and price live in a plain config file. At runtime, HyDRA simply picks the cheapest healthy model whose profile covers all four demands within a small shortfall tolerance. "
        "When GPT-6 drops tomorrow, onboarding it is a config edit—zero retraining. On SWE-Bench, that delivered 54.1% cost savings at parity quality—six times the savings of binary routing.\n\n"
        "Source: Garg et al., HyDRA paper (arXiv:2605.17106)."
    ),
    15: (
        "Putting all of these products and papers together reveals one consistent three-layer blueprint across Microsoft.\n"
        "Layer 1 is always deterministic code: tenant allow-lists, data zones, required tool or schema capabilities, and warm prefix-cache state—compliance rules never rely on model guesses. "
        "Layer 2 is a sub-180ms purpose-built scorer that produces calibrated probabilities across the allowed candidates. "
        "And Layer 3 executes the right workflow—Single, Cascade, or Critique—followed by deterministic output checks.\n"
        "Which raises the natural question: Microsoft has internal encoders like HyDRA, so what can you drop into Layer 2 of your own agent?"
    ),
    16: (
        "That is exactly why Microsoft built and shipped Microsoft-Decision-1.1. Generative LLMs are trained to sound helpful and write fluent prose—even if you only ask for a binary routing check, "
        "they generate tokens one by one, burn hundreds of milliseconds, and guess confidently when context is missing.\n"
        "Decision-1.1 flips the paradigm. Built on a Mixture-of-Experts backbone with only 4B active parameters and a custom single-pass decision engine, it emits zero filler prose—reading text, JSON, and even UI screenshots or photos to return calibrated probabilities in ~123 milliseconds. "
        "Global Standard input costs just $0.042 per million tokens with zero output-token charge, and option-order variance is under 1.3%."
    ),
    17: (
        "Using it in code feels like calling a strongly typed function. The endpoint is called `systemone`—built for fast, intuitive system-one judgments. You pass your business context in `state` and ask multiple typed questions in a single round-trip using three primitives:\n"
        "Use `choice` to pick one path—like a model tier or support queue—complete with calibrated probabilities per option, so if the top confidence is below 0.75, your code can pause and ask a clarifying question. "
        "Use `noul` for any yes/no gate, returning a clean 0-to-1 probability for policy leaks or photo damage. "
        "And use `score` to compute a probability-weighted severity or quality rating across ordered levels like P0 through P3."
    ),
    18: (
        "With just those three primitives, the messy control glue around agents becomes clean and testable. Build your own router with `choice` across Flash, Sonnet, Opus Critique, and `ask_clarify`—catching missing exhibits before burning frontier credits.\n"
        "At support intake, combine `choice` and `score` in one call: when a customer reports a collapsed bed frame and a back injury, severity hits 2.94 out of 3, immediately bypassing the bot and paging a human safety specialist. "
        "For e-commerce claims, pass a delivery photo in `assets` with a `noul` damage check—auto-replacing above 0.80 and routing borderline cases to an adjuster. "
        "And right before an AI reply goes out the door, run parallel `noul` guardrails to hold any draft that promotes a competitor or promises an unapproved discount."
    ),
    19: (
        "With only 4B active parameters and a four-cent price tag, the obvious question is: how accurate is it really? Because narrow leaderboards are easy to overfit, Microsoft evaluated eight decision models across 102 blind benchmarks—41 public and 61 private enterprise tasks totaling 385,000 zero-overlap questions.\n"
        "Decision-1.1 ranked #1 overall at 78.8% mean accuracy and led seven out of nine capability categories—including routing, tool selection, safety, and consistency—while jumping 6 points to 68 on the Artificial Analysis Decision Index at 2.2x the speed. "
        "Within five weeks of launch, over 4,000 organizations adopted it alongside Microsoft Copilot, Cowork, Foundry Evaluation, and Xbox Research—where it runs 14x faster and 200x cheaper than flagship LLMs.\n\n"
        "Source: Microsoft Command Line — Microsoft-Decision-1.1 GA (Nov 17, 2026)."
    ),
    20: (
        "Let's translate accuracy and low cost into hard ROI with a $10,000-a-month sales inbox study. In the naive baseline, every customer reply hits a $0.15 frontier LLM, and because teams don't trust unguarded bots, a human reviews 100% of drafts at $0.24 each—capping monthly conversions at 764 customers, or $13 CAC.\n"
        "Dropping in Decision-1.1 changes the funnel at three points: first, a `choice` router hits 100% accuracy across 32 reply types (versus 88% with regex), letting 57% of routine 'thanks' or 'unsubscribe' emails skip the LLM entirely; "
        "second, `score` prioritizes high-intent leads; third, an outbound `noul` gate catches rival promotions automatically, cutting human review from 100% down to 8%. "
        "All three checks combined cost $0.00019 per email—converting 7.2x more customers on the same budget and dropping CAC from $13 to $1.81.\n\n"
        "Source: Microsoft Command Line blog ($10k/mo sales inbox case study)."
    ),
    21: (
        "Demo 1 now contains four distinct scenarios backed by five real Copilot CLI calls.\n"
        "Step 1 is Fusion Single: a routine whitespace fix stays on `gpt-6.1-terra`, adds no review call, and passes 3/3 unit tests. "
        "Step 2 is Cascade: `gpt-6.1-sol` fixes an ABBA lock-order deadlock, `gpt-6-luna` independently scores it 5/5, Opus repair is skipped, and 500 stress runs pass. "
        "Step 3 is Critique: Opus drafts a 50k-RPS payment failover RFC, Luna catches the missing cross-region durability behind the RPO=0 claim, and Opus revises it.\n"
        "Step 4 is the cache scenario, and it is deliberately two real calls: one Auto call warms the session, then `--resume` issues the measured follow-up. The second call reads 5,655 of 5,733 tokens from cache—a 99% hit—at 0.024 incremental AIU. Raw Log shows both the warm-up and resumed calls."
    ),
    22: (
        "Demo 2 moves to Microsoft Foundry Model Router: four scenarios and six real cloud requests, all through the same `/openai/v1/chat/completions` endpoint with `model: \"auto\"` and `ModelRouterControls=V1Preview`.\n"
        "Step 1 tests pre-rank eligibility and cross-provider parameter cleanup—sending `developer` role, `temperature: 0.2`, and `json_object` together. Instead of tripping HTTP 400 mismatches across labs, Foundry normalizes the payload and routes to `gpt-5.6-luna` in 30 ms.\n"
        "Steps 2 and 3 send two starkly different tasks to the untouched `balanced` endpoint: Step 2 extracts invoice fields in 27 ms on cheap `DeepSeek-V4.1-Flash` with zero wasted reasoning tokens; "
        "Step 3 submits a formal Rust lock-free ring-buffer proof, automatically escalating in 30 ms to `gpt-6-luna`, and on Turn 2's short follow-up, message-fingerprint affinity returns `retain` so the warm model cache isn't broken.\n"
        "Step 4 contributes the final two calls: `mode: \"cost\"` routes raw extraction to fast `grok-4-1-fast-reasoning` (28 ms), then `mode: \"quality\"` hands the compact bullets to `gpt-5.6-terra` (29 ms) for strategy. The count is 1 + 1 + 2 + 2 = 6. Switch to `{ } Raw Log` to inspect the current scenario's `routing_trace`."
    ),
    23: (
        "Demo 3 shows Microsoft-Decision-1.1 across five scenarios and twelve real `/providers/microsoft/v1/systemone` requests.\n"
        "Step 1 fires five consecutive `noul` calls on the same buyer message—returning `0.9835` all five times with `0.00` point spread in ~354 ms median latency and $0 output-token fee.\n"
        "Step 2 runs a pre-LLM `choice` inbox router across four customer messages ('Thanks!', 'STOP', promo lookup, and multi-line warranty comparison)—hitting ~1.00 confidence on all four so three out of four skip the frontier LLM.\n"
        "Step 3 packs `choice`, `score`, and `noul` into one 366 ms request on a collapsed-bed injury report—returning `safety_support` (0.998), urgency `1.97 / 3.0`, and `repeat = 0.998` to block the bot and page a human.\n"
        "Step 4 runs an outbound `noul` guardrail on an AI draft recommending rival 'Fabrikam for $749', scoring `0.970` in 347 ms and holding the draft before send.\n"
        "Steps 3, 4, and 5 each add one request: injury escalation, outbound competitor screening, and missing-evidence detection. That makes 5 + 4 + 1 + 1 + 1 = 12. Try a custom prompt in the bottom bar, or open `{ } Raw Log` to view the current operation's raw JSON."
    ),
    24: (
        "Let's wrap up with four practical takeaways you can bring back to your team on Monday:\n"
        "First, stop pinning one model to every turn—route sub-tasks by capability. Second, respect the prefix cache: switch models at Turn 1 or isolated sub-jobs, never mid-conversation for pennies. "
        "Third, adopt turnkey routers before building from scratch—turn on Copilot Auto at work, Copilot Fusion in your IDE, and Foundry Model Router on your cloud endpoints. "
        "Fourth, when your own application code needs fast triage, priority scoring, or outbound guardrails, plug in calibrated Microsoft-Decision-1.1. Thank you—let's open it up for Q&A!"
    ),
    25: (
        "This final reference slide collects all public benchmarks, product docs, the HyDRA paper, and Microsoft-Decision-1.1 quickstarts and open benchmark suites—every link is clickable in both the PowerPoint and web deck."
    ),
}

ZH_TEXT_MAP = {
    # Cover & Agenda
    'INTELLIGENT MODEL SELECTION & DECISION SYSTEMS': '智能模型选型与决策系统',
    'Auto-routing\nLLMs': '大模型自动路由\nAuto-routing',
    'Routing every task to the right model for quality, cost and speed — from Microsoft Copilot and Foundry to Microsoft-Decision-1.1.': '根据任务特点自动选择合适的模型，兼顾效果、成本和响应速度 —— 从 Microsoft Copilot、Foundry 到 Microsoft-Decision-1.1。',
    'SCAN FOR LIVE SLIDES & DEMO': '扫码查看在线幻灯片与交互演示',
    'AGENDA': '目录 · AGENDA',
    'Our journey today': '今天的内容安排',
    'Capability gap': '模型各有所长',
    'No single model wins all': '没有全能的单一模型',
    'Cost & cache': '成本与缓存机制',
    '163× gap & prefix cache': '163 倍价差与前缀缓存',
    'MS products': '微软产品方案',
    'Copilot, Fusion & Foundry': 'Copilot、Fusion 与 Foundry',
    'Under the hood': '路由实现原理',
    'Industry vs. MS HyDRA': '常见方案对比微软 HyDRA',
    'Decision-1.1': 'Decision-1.1',
    'Fast, calibrated control': '低延迟决策与输出控制',
    'Live demos': '现场演示',
    'Fusion, Foundry & Decision': 'Fusion、Foundry 与 Decision',
    'Takeaways': '总结与建议',
    'Ship your own router': '在项目中落地自动路由',

    # Slide 3 (idx 2)
    '01 · CAPABILITY SPECIALIZATION': '01 · 模型各有所长',
    'No single model is best at everything': '没有一个模型在所有任务上都是最好的',
    'PINNED MODEL': '固定单一模型',
    'Static single-model mindset': '所有请求固定用同一个模型',
    'One model forced onto every turn': '不管任务难易，每一轮都调同一个模型',
    '• Biggest model always → pay 2.5×–5× more & wait longer': '• 全程只用大模型 → 费用高出 2.5 到 5 倍，响应也更慢',
    '• Small model always → fail when reasoning gets hard': '• 全程只用小模型 → 遇到复杂推理任务质量明显下降',
    '• Users switch for one hard bug & forget to switch back': '• 排查难题时手动切到大模型，解决后经常忘了切回来',
    '• Text-only models cannot generate diagrams or visuals': '• 纯文本模型无法直接生成配图和可视化图表',
    'DYNAMIC ROUTING': '按任务动态路由',
    'Task-routed multi-model Auto': '按子任务自动选模型的 Auto 模式',
    '>90% of Microsoft Copilot queries today': '目前超过 90% 的 Microsoft Copilot 请求使用 Auto',
    '• Enforces tenant admin rules, subprocessors & geography': '• 自动遵循企业后台的模型开关、供应商范围与数据区域设置',
    '• Classifier matches sub-tasks via live eval scorecards': '• 根据评测表现，为每个子任务匹配合适的模型',
    '• Adopts newly shipped frontier models automatically': '• 新模型上线后可直接纳入调度，无需修改业务代码',
    '• Combines SLMs, reasoning LLMs & image models in one job': '• 在同一个任务里组合使用小模型、推理模型与生图模型',
    'Shift from “which model is #1 overall?” to “which model fits this sub-task right now?”': '思路转变：从“哪个模型综合排名第一？”转向“当前这一步用哪个模型最合适？”',

    # Slide 4 (idx 3)
    'One prompt, four specialized jobs': '一次提问，拆成四个子任务分工完成',
    'PROMPT  ·  “Customer renewal Thursday — expand, hold, or discount, and build a deck to make the case?”': '用户输入  ·  “周四谈客户续约 —— 该推增购、维持原价还是给折扣？请做一份汇报 PPT。”',
    'Guardrail gate first: filters tenant-allowed model providers, data residency, and live endpoint health.': '前置策略检查：先核对企业允许的模型提供商、数据存储区域和节点可用状态。',
    'JOB 01 · RETRIEVE': '步骤 01 · 检索资料',
    'Small Language Model': '轻量语言模型 (SLM)',
    'Scans M365 emails, Teams chats, meeting notes & prior contracts fast and cheaply.': '快速检索 M365 邮件、Teams 聊天、会议纪要和历史合同，成本低、速度快。',
    'SLM · Fast & cheap': 'SLM · 快速低成本',
    'JOB 02 · REASON': '步骤 02 · 方案测算',
    'Main agentic loop evaluates expand / hold / discount economics; caches full context.': '主流程评估增购、保价和折扣三种方案的收益，并缓存完整上下文。',
    'Main loop · Cached': '主流程 · 已缓存上下文',
    'JOB 03 · VISUALIZE': '步骤 03 · 生成配图',
    'Generates custom proposal graphics and infographics that text LLMs cannot render.': '生成文本模型无法处理的方案配图与数据图表。',
    'Image specialist': '图像生成模型',
    'JOB 04 · ASSEMBLE': '步骤 04 · 汇总生成 PPT',
    'Reuses warm context cache to build the finished PowerPoint proposal without re-reading.': '直接复用第 2 步已缓存的上下文生成完整 PPT，无需重复读取前文。',
    'Deck synthesis': '复用缓存生成文稿',

    # Slide 5 (idx 4)
    '02 · COST & LATENCY ECONOMICS': '02 · 成本与延迟对比',
    'Compressed quality, 163× cost spread': '前排模型得分接近，调用成本相差 163 倍',
    '4.2-pt quality band, 163× cost gap': '前 14 名得分只差 4.2 分，成本相差 163 倍',
    'Top 14 models cluster within 86.2–90.4 across 8 tasks, yet cost spans $0.09 (auto) and $0.23 (Haiku 5.5) vs. $14.75 (Opus 5).': '8 类多模态任务中前 14 个模型得分都在 86.2–90.4 之间，但费用从自动路由的 $0.09、Haiku 的 $0.23 到 Opus 5 的 $14.75。',
    'Routine work → small models win': '常规任务 → 轻量模型足够胜任',
    '24 of 28 models pass routine quality checks; Haiku 5.5 even ranks #1 on dashboard generation at a fraction of flagship cost.': '28 个模型里有 24 个达到了常规任务质量要求；Haiku 5.5 在看板生成任务上排名第一，成本仅为旗舰模型的零头。',
    'Hard problems → escalate selectively': '复杂难题 → 按需调用深度推理模型',
    'Save heavy reasoning models (Opus 5.5, Sonnet 5.5, GPT-6 Sol) for complex specs where small models stall in retry loops.': '把 Opus 5.5、Sonnet 5.5、GPT-6 Sol 留给复杂需求，避免小模型因能力不足而反复重试。',

    # Slide 6 (idx 5)
    'Don’t break a warm prefix cache': '多轮对话中不要轻易打断前缀缓存',
    'Rule of thumb: switch models only at Turn 1, after compaction, or on isolated sub-agents.': '经验法则：只在第一轮对话、上下文压缩后、或独立的子 Agent 任务中切换模型。',
    'Warm prefix cache = 10×–20× cheaper': '命中前缀缓存可节省 90% 左右输入成本',
    'Once a main model caches contracts, emails, repo files and 80+ tool schemas, follow-up turns pay ~10% cache-read rates.': '主模型在首轮缓存合同、代码文件和 80 多个工具定义后，后续轮次读取缓存的价格通常只有原价的约 10%。',
    'Mid-session downgrades can cost MORE': '对话中途换用小模型反而可能更贵',
    'Switching to a “cheaper” model mid-session invalidates the prefix cache and forces re-prefilling 50k+ tokens from scratch.':
        '如果在对话中途为了省一点费用切到另一个模型，原有缓存就会失效，新模型需要按全价重新处理前面 5 万多个 Token。',
    'Route at natural cache boundaries': '在自然的缓存边界处切换模型',
    'Pick on Turn 1, after context compaction, on isolated sub-agents, or only when task complexity shifts dramatically.': '只在会话开始、上下文压缩重置后、独立子任务，或任务难度明显变化时重新选择模型。',

    # Slide 7 (idx 6)
    '03 · MICROSOFT PRODUCTS IN ACTION': '03 · 微软产品中的自动路由',
    'Four routing surfaces across Microsoft': '微软不同产品层面的四类路由方案',
    'Workplace Auto': '日常办公路由',
    'Routes >90% of queries: Chat → Cowork handoff, multi-provider selection, dynamic effort & sub-agents.': '处理超过 90% 的办公提问：支持 Chat 转交 Cowork、跨厂商选型、推理档位调节与子任务拆分。',
    'Coding Orchestrator': '编程多模型协同',
    'Matches each coding task to one model or a team: Single pass, Judge-gated Cascade, or parallel Critique.': '按编码任务难度选择单模型或多模型组合：Single 单次执行、Cascade 评审级联、Critique 多模型审校。',
    'Cloud API Router': '云端 API 路由',
    '20 ms ML ranker across 45 models (7 providers): quality bands, cache affinity, param cleanup & PTU failover.': '约 20 ms 对 7 家厂商的 45 个模型排序：支持质量区间选型、缓存保持、参数适配与 PTU 故障切换。',
    'Software Controller': '应用层决策接口',
    'Purpose-built decision API that classifies, scores priority, and runs yes/no safety gates in ~123 ms at $0.042/1M.': '面向程序控制逻辑的决策 API：约 123 ms 完成分类、优先级打分与合规检查（每百万输入 Token $0.042）。',

    # Slide 8 (idx 7)
    '03 · MICROSOFT PRODUCTS · MICROSOFT COPILOT': '03 · 微软产品方案 · MICROSOFT COPILOT',
    'Microsoft Copilot Home: unified Auto': 'Microsoft Copilot 主界面：统一的 Auto 入口',
    'One unified prompt box: Auto answers quick questions in Chat or hands off multi-step work to Cowork.': '同一个输入框：简单问题直接在 Chat 回复，需要多步执行的任务自动提示转到 Cowork。',
    '1 · Chat → Cowork handoff': '1 · Chat 到 Cowork 的自动分流',
    'Decision-1.1 detects when a prompt needs multi-step execution and suggests Cowork (2.2× faster, 4.4× cheaper).': '用 Decision-1.1 判断提问是否需要多步执行并建议转入 Cowork，比用通用大模型判断快 2.2 倍、省 77% 成本。',
    '2 · Multi-provider within IT rules': '2 · 在企业策略范围内跨厂商选型',
    'Routes across OpenAI, Anthropic Claude & xAI Grok while enforcing EU Data Boundary & tenant admin switches.': '按照管理员开启的模型范围与欧盟数据边界设置，在 OpenAI、Claude 和 Grok 之间自动选择。',
    '3 · Scoped context & local offload': '3 · 按需提取上下文与本地模型分流',
    'Pulls only relevant M365 emails, chats & files via Work IQ — and offloads light tasks to local Windows PC models.': '通过 Work IQ 只提取相关的邮件和文档，在支持的 Windows 电脑上还能把轻量任务交给本地小模型。',

    # Slide 9 (idx 8)
    '03 · MICROSOFT PRODUCTS · COPILOT COWORK': '03 · 微软产品方案 · COPILOT COWORK',
    'Copilot Cowork: keep cache, tune effort': 'Copilot Cowork：保持模型缓存，按步调节推理强度',
    'COWORK MODEL POOL  ·  ENABLED BY TENANT ADMIN': 'COWORK 可选模型池  ·  由企业管理员配置启用',
    '• Auto (Default)      → Picks on turn 1 & keeps cache warm': '• Auto（默认）         → 首轮选定主模型，后续轮次复用缓存',
    '• Effort (Decision-1.1) → Light · Medium · High · Extra High · Max': '• 推理强度 (Decision-1.1) → Light · Medium · High · Extra High · Max',
    'Opening-message model lock': '首轮确定主模型以复用缓存',
    'Auto inspects turn 1, picks from GPT 6.1 Sol, GPT 6 Astra, Opus 5.5, Sonnet 5.5, Fable 5.2 or Grok 4.7, and stays to keep cache.': 'Auto 根据第一条提问从 GPT 6.1 Sol、Opus 5.5、Grok 4.7 等模型中选定主模型，并在整场会话中保持不变以复用缓存。',
    'Decision-1.1 sets reasoning effort': '用 Decision-1.1 动态调整推理强度',
    'Dynamically tunes effort (Light, Medium, High, Extra High, Max) so routine steps stay fast while hard tasks think deeper.': '每一步在 Light 到 Max 五档之间自动调整：常规步骤快速返回，复杂分析分配更多推理计算量。',
    'Predictable spend guardrails': '可控的团队用量与预算管理',
    'Agent 365 Cost Management tracks work completed and enforces team spending limits so frontier runs never surprise IT.': '通过 Agent 365 成本管理统计任务消耗并设置团队费用上限，避免复杂任务带来意外账单。',

    # Slide 10 (idx 9)
    '03 · MICROSOFT PRODUCTS · GITHUB COPILOT FUSION': '03 · 微软产品方案 · GITHUB COPILOT FUSION',
    'Copilot Fusion: pick effort, not models': 'Copilot Fusion：选择投入档位，不用逐个挑模型',
    'Pick Standard, High, or Max effort — hover the badge on any reply to see which models ran.': '只需选择 Standard、High 或 Max 档位 —— 鼠标悬停在回复标签上即可查看实际调用的模型。',
    'Standard · High · Max (+ Fast)': 'Standard · High · Max（另含 Fast）',
    'Standard routes 1 model per task (including local MAI Code 1.1 Flash / Qwen3.8 Flash); High & Max unlock orchestration.': 'Standard 每次选一个合适的模型（含本地 MAI Code 1.1 Flash 等）；High 和 Max 支持多模型组合执行。',
    'Frontier quality at ~50% cost': '接近旗舰模型效果，费用节省约一半',
    'On AA Coding Agent Index, Fusion Max scores 60 (within 2 pts of Opus 5.5 Max) at ~50% lower API cost & ~40% less time.': '在 AA 编程评测中 Fusion Max 得分 60（距 Opus 5.5 Max 仅差 2 分），API 费用降低约 50%，耗时减少约 40%。',
    'Fixes “forgot to switch back” waste': '避免“切到大模型后忘了切回”的浪费',
    'AT&T found developers picked a heavy model for one hard bug and left it on; Fusion right-sizes every turn automatically.': 'AT&T 团队发现开发者常为一个难 Bug 切到大模型后一直不改；Fusion 会在每一轮自动匹配合适的规模。',

    # Slide 11 (idx 10)
    '03 · MICROSOFT PRODUCTS · FUSION ORCHESTRATION': '03 · 微软产品方案 · FUSION 执行模式',
    'Single, Cascade & Critique patterns': 'Single、Cascade 与 Critique 三种执行模式',
    '1 · Single  (Everyday tasks)': '1 · Single 单模型模式（日常任务）',
    'One right-sized primary model solves the request with tools. Zero extra review latency or AI credit overhead.': '由一个匹配任务难度的主模型直接调用工具完成，不增加额外的评审耗时和额度开销。',
    '2 · Cascade  (Draft → Judge → Repair)': '2 · Cascade 级联模式（生成 → 评审 → 修复）',
    'Efficient primary drafts a solution; a secondary Judge inspects and accepts — or escalates to a fresh Repair model.': '先用高性价比模型完成修改，再由 Judge 模型检查；检查通过即结束，发现问题才交给更强的模型重修。',
    '3 · Critique  (Draft → Critics → Revise)': '3 · Critique 审校模式（初稿 → 多方审校 → 修订）',
    'Primary drafts while read-only Critics review in parallel (cannot edit files, avoiding conflicts); Primary revises.': '主模型起草方案，只读的 Critic 模型负责审阅挑错（只读权限可避免并发改乱文件），最后由主模型整合修订。',

    # Slide 12 (idx 11)
    '03 · MICROSOFT PRODUCTS · MICROSOFT FOUNDRY': '03 · 微软产品方案 · MICROSOFT FOUNDRY',
    'Foundry Router: how it ranks & caches': 'Foundry Model Router：排序逻辑与缓存保持',
    'SCORING & AFFINITY ENGINE  ·  TRAINED ON BILLIONS OF INTERACTIONS': '评分与会话保持机制  ·  基于海量真实交互数据训练',
    '1. Rank eligible models for this prompt (~20 ms ML scorer)\n2. Keep models within 1–2% of #1 quality  (5–6% in Cost mode)\n3. Reuse prior model if cache is warm & in band; else cheapest': '1. 为候选模型实时打分排序（专用机器学习模型，约 20 ms）\n2. 筛出与最高分差距在 1–2% 以内的模型（Cost 模式放宽到 5–6%）\n3. 如果上一轮模型缓存仍有效且得分达标就继续沿用，否则选最便宜的',
    'Non-LLM ML Ranker (~20 ms)': '非大模型的专用排序器（~20 ms）',
    'Purpose-built ML model (not an LLM!) reads system prompt, history & tool schemas, weighting the latest turn highest.': '使用专门训练的轻量机器学习模型（不是 LLM），约 20 ms 读完系统提示词、对话历史和工具定义，重点看最新一轮提问。',
    'Quality-Band Cost Selection': '在相近质量区间内选最低成本',
    'Balanced picks cheapest within 1–2% of #1 fit; Cost widens to 5–6%; Quality picks #1 — across 45 models from 7 labs.': 'Balanced 在最高分 1–2% 差距内选最便宜的；Cost 放宽至 5–6%；Quality 直接选最高分 —— 覆盖 7 家厂商共 45 个模型。',
    'Adaptive Cache Affinity': '多轮对话自动保持缓存',
    'Tracks sessions via ID, previous_response_id or message fingerprint — keeping the prior model while warm & in-band.': '通过会话 ID、响应 ID 或历史消息指纹识别同一轮对话，只要缓存未过期且质量达标，就继续使用原模型。',

    # Slide 13 (idx 12)
    '03 · MICROSOFT PRODUCTS · FOUNDRY PIPELINE': '03 · 微软产品方案 · FOUNDRY 请求处理流程',
    'Foundry: filters, params & failover': 'Foundry：条件筛选、参数适配与故障切换',
    '1 · Pre-Rank Eligibility Gate': '1 · 排序前先筛除不满足条件的模型',
    'Filters by region, approved allow-list, tools / json_schema / image support, and valid reasoning_effort before ranking.': '打分前先按区域、允许的模型列表，以及是否支持工具调用、JSON Schema、图片输入等条件过滤候选池。',
    '2 · Cross-Provider Param Cleanup': '2 · 跨厂商接口参数自动转换',
    'Drops temperature/stop on reasoning models, strips reasoning_effort on non-reasoning, & maps developer → system.': '对推理模型自动去掉 temperature/stop，对普通模型去掉 reasoning_effort，并把 developer 角色转为 system，避免 400 报错。',
    '3 · PTU Priority & Auto-Failover': '3 · 优先使用 PTU 配额与限流自动切换',
    'Uses your pre-paid PTU first ($0 extra model fee) → PAYG → Managed, then fails over to #2 inside your allow-list.': '优先使用已购买的 PTU 部署（不产生额外模型费），不足时再走按量部署和托管资源池；遇 429 限流自动切到备选模型。',

    # Slide 14 (idx 13)
    '04 · MODEL-LEVEL IMPLEMENTATION': '04 · 底层路由实现方式对比',
    'Four general routing architectures': '业界常见的四类模型路由方案',
    'ARCHITECTURE': '路由方案',
    'OVERHEAD': '额外耗时',
    'HOW IT WORKS': '实现方式',
    'KEY LIMITATION': '主要局限',
    '1 · Heuristic & Semantic': '1 · 规则与向量相似度路由',
    'Regex, token count, or embedding k-NN (e.g., Aurelio Semantic Router) against anchor prompts.': '用正则表达式、Token 长度或向量相似度（如 Semantic Router）匹配预设示例。',
    'Surface topics ≠ reasoning difficulty; misses subtle traps.': '字面话题相近不代表推理难度相同，容易低估复杂问题。',
    '2 · Binary Preference': '2 · 二分类偏好路由',
    'Matrix factorization / BERT classifier (e.g., RouteLLM) predicting P(Strong beats Weak).': '用矩阵分解或 BERT 分类器（如 RouteLLM）预测强模型表现优于弱模型的概率。',
    'Coupled to fixed model IDs — must retrain when catalog changes!': '分类器与特定模型绑定 —— 候选模型更新后需要重新采集数据训练。',
    '3 · Cascade (FrugalGPT)': '3 · 串行级联 (FrugalGPT)',
    '+1× draft': '+1 次试跑',
    'Run cheap model first; a verifier scores the draft and escalates to strong if low.': '先让小模型生成初稿，评分模型检查不达标时再换大模型重跑一遍。',
    'Pays double latency on hard tasks; correlated judge blind spots.': '遇到难题需要多等一轮初稿时间，而且评分模型本身也可能漏判。',
    '4 · Generative LLM Router': '4 · 生成式大模型路由',
    'Prompt a general LLM to pick a tool/model and explain its reasoning in JSON/text.': '通过提示词让通用大模型选择下游模型，并生成 JSON 格式的判断理由。',
    'Slow, expensive, and overconfident — RLHF hurts calibration!': '耗时长、成本高，且经过偏好微调的模型容易盲目自信，概率不够准确。',

    # Slide 15 (idx 14)
    '04 · MICROSOFT’S ARCHITECTURE · HYDRA': '04 · 微软路由架构 · GITHUB HYDRA',
    'GitHub HyDRA: decouple demand & catalog': 'GitHub HyDRA：把任务需求评估与模型列表解耦',
    '1. Score 4 demands (86 ms): [Reason, CodeGen, Debug, Tools]': '1. 评估四项能力需求 (86 ms)：[推理, 代码生成, 调试, 工具使用]',
    '2. Pick cheapest healthy model whose profile covers all 4': '2. 对照模型配置表，选出满足这四项要求且价格最低的可用模型',
    '4-Head Capability Scorer': '四维度能力需求评分器',
    'Lightweight ModernBERT scores Reasoning, CodeGen, Debugging & Tool Use in 86 ms median CPU latency.': '使用轻量 ModernBERT 同时评估推理、写代码、调试和工具调用四项需求，CPU 中位耗时 86 ms。',
    'Zero-Retraining Model Updates': '接入新模型无需重新训练',
    'Models live in config files, not classifier weights! Adding GPT-6 is a config edit — 6× more savings (54.1%) than binary routing.': '各模型的能力指标和单价写在配置文件里，不写进分类器权重。接入新模型只需改配置，同等质量下节省 54.1% 成本。',
    'Multilingual Across 19 Languages': '支持包括中文在内的 19 种语言',
    'Trained on full multi-turn coding sessions (including Chinese, Japanese & Korean) within 4 pts of English accuracy.': '基于真实多轮编程对话训练，涵盖中、日、韩等 19 种语言，准确率与英文差距在 4 个百分点以内。',

    # Slide 16 (idx 15)
    '04 · MICROSOFT’S ARCHITECTURE · BLUEPRINT': '04 · 微软路由架构 · 三层设计',
    'Microsoft’s three-layer routing stack': '微软采用的三层路由架构',
    'Models score bounded options; deterministic code enforces policy gates, thresholds & fallbacks.': '基本原则：由模型对可选范围打分，由确定性代码负责权限校验、阈值判断和异常兜底。',
    'Layer 1 · Deterministic Policy & Cache Gate': '第 1 层 · 代码级规则校验与缓存检查',
    'Hard code filters tenant-allowed providers, data zones, required tool/schema capabilities, and warm prefix-cache state.': '先用普通代码检查租户允许的厂商、数据区域、工具或结构化输出能力，以及当前前缀缓存是否有效。',
    'Layer 2 · Fast Scorer / Decision Model (<180 ms)': '第 2 层 · 快速评分器 / 专用决策模型 (<180 ms)',
    'Purpose-built encoder (HyDRA / Foundry ML ranker) or Microsoft-Decision-1.1 produces calibrated scores over allowed options.': '使用专用模型（HyDRA、Foundry 排序器或 Microsoft-Decision-1.1）对符合条件的选项输出校准后的概率。',
    'Layer 3 · Workflow Pattern & Output Verifier': '第 3 层 · 执行流程编排与结果检查',
    'Executes Single, Cascade or Critique, then runs deterministic schema, citation or policy safety checks before acting.': '根据分值选择 Single、Cascade 或 Critique 模式执行，并在返回前检查数据格式、引用与内容合规。',

    # Slide 17 (idx 16)
    '05 · MICROSOFT DECISION-1.1': '05 · MICROSOFT DECISION-1.1 决策模型',
    'Meet Microsoft-Decision-1.1': '认识 Microsoft-Decision-1.1',
    'Generative LLMs as routers': '用生成式大模型做判断的痛点',
    'Trained to sound helpful & complete tasks': '针对生成流畅回答而训练，不擅长输出准确概率',
    '• Autoregressive tokens add 500–2,000 ms latency': '• 逐字生成解释文本，额外增加 500–2,000 ms 延迟',
    '• RLHF rewards confident guesses on missing info': '• 缺少上下文时仍倾向于给出看似笃定的猜测',
    '• Fragile JSON parsing & option-order bias': '• 输出格式偶有解析失败，调换选项顺序容易影响结果',
    'Microsoft-Decision-1.1  (GA Nov 2026)': 'Microsoft-Decision-1.1（2026 年 11 月正式发布）',
    'Built specifically for fast, calibrated decisions': '专门针对快速、稳定的结构化决策而设计',
    '• Mixture-of-Experts (4B active) + single-pass engine': '• MoE 架构（每次仅激活 4B 参数）配合单次前向推理',
    '• Reads text, JSON & photos/UI with zero filler prose': '• 支持文本、JSON 与图片输入，不生成多余文字，直接返回概率',
    '• Calibrated probabilities; <1.3% variance on reordered options': '• 概率经过校准，打乱选项顺序后的结果差异低于 1.3%',
    'Input tokens (Global Std); output tokens FREE!': '输入 Token 单价；输出 Token 不收费',
    'Median decision latency (2.2× faster than v1.0)': '中位响应耗时（比 1.0 版本快 2.2 倍）',
    'Faster than frontier LLMs on routing & QC': '在路由和质检任务上明显快于通用旗舰模型',
    '3 Clouds': '3 个平台可用',
    'Microsoft Foundry, OpenRouter & Vercel': '支持 Foundry、OpenRouter 与 Vercel',

    # Slide 18 (idx 17)
    '05 · MICROSOFT DECISION-1.1 · API PRIMITIVES': '05 · MICROSOFT DECISION-1.1 · 接口类型',
    'Three primitives: choice, noul, score': '三种基本问题类型：choice、noul、score',
    '01 · choice  (Pick one)': '01 · choice（多项选一）',
    '“Which option fits best?”': '“应该走哪一个选项？”',
    'Picks one label and returns calibrated probabilities per candidate.\nUse: model routing, ticket triage, tool pick.': '选出最匹配的标签，并返回每个候选项的概率。\n适用：模型路由、工单分流、工具选择。',
    '02 · noul  (Yes / No gate)': '02 · noul（是 / 否判断）',
    '“Is this condition true?”': '“是否满足某个条件？”',
    'Returns a single [0, 1] probability for any true/false check.\nUse: safety gates, refund/rival checks, photo damage.': '针对是非问题返回一个 0 到 1 之间的概率值。\n适用：内容审核、竞品/折扣检查、照片破损识别。',
    '03 · score  (0–N scale)': '03 · score（等级评分）',
    '“How urgent or strong?”': '“紧急程度或质量排第几档？”',
    'Computes a probability-weighted score across ordered levels.\nUse: P0–P3 incident priority, output grading.': '按有序档位计算加权得分。\n适用：P0–P3 故障定级、客户意向评估与结果打分。',
    'POST <foundry-endpoint>/providers/microsoft/v1/systemone   ·   Ask all 3 in ONE call': 'POST <foundry-endpoint>/providers/microsoft/v1/systemone   ·   一次请求可同时提交多个问题',

    # Slide 19 (idx 18)
    '05 · MICROSOFT DECISION-1.1 · EXAMPLES': '05 · MICROSOFT DECISION-1.1 · 常见用法',
    'Four production Decision-1.1 patterns': 'Decision-1.1 的四种常见使用场景',
    '1 · Custom LLM & Agent Router (choice)': '1 · 自定义模型与 Agent 路由 (choice)',
    'criteria: { mai_flash, sonnet_5_5, opus_critique, ask_clarify }\n→ If max(p) < 0.75 or choice == ask_clarify, clarify before burning frontier credits!': 'criteria: { mai_flash, sonnet_5_5, opus_critique, ask_clarify }\n→ 最高概率 < 0.75 或命中 ask_clarify 时，先请用户补充信息，避免盲目调用大模型。',
    '2 · Support Triage + SLA Queue (choice + score)': '2 · 客服工单分组与紧急度评估 (choice + score)',
    'Single call returns team = "safety_support" (0.95) AND priority.score = 2.94 / 3.0 → Math.round(score) == P3 pages immediate human.': '一次调用同时返回 safety_support (0.95) 和紧急度 2.94 / 3.0 → 达到 P3 时直接转交人工客服处理。',
    '3 · Multimodal Photo & UI Gate (assets + noul)': '3 · 退货照片与界面截图检查 (assets + noul)',
    'questions.damaged = { type: "noul", instructions: "Shows physical damage?" }\n→ p >= 0.80 auto-replaces; 0.35–0.80 routes to claims adjuster.': 'questions.damaged = { type: "noul", instructions: "Shows physical damage?" }\n→ 破损概率 >= 0.80 自动换货；介于 0.35–0.80 之间转交人工审核。',
    '4 · Outbound LLM Guardrail Filter (noul)': '4 · AI 回复发送前的内容检查 (noul)',
    'Independent noul checks: mentions_competitor, unapproved_discount, medical_claim.\n→ Hold draft if ANY noul >= 0.50; catches “Try Fabrikam for $749”!': '同时检查多项条件：是否提及竞品、是否擅自承诺折扣、是否包含违规建议。\n→ 任一概率 >= 0.50 即暂停发送，例如拦下“推荐竞品 Fabrikam 只要 $749”。',

    # Slide 20 (idx 19)
    '05 · MICROSOFT DECISION-1.1 · BENCHMARKS': '05 · MICROSOFT DECISION-1.1 · 评测表现',
    '#1 across 102 decision benchmarks': '102 项盲测基准综合排名第一（共 38.5 万题）',
    '#1 Overall Across 102 Blind Benchmarks': '102 项未见测试集综合排名第 1',
    '78.8% mean accuracy over 385,246 zero-overlap questions — ahead of Jev 1.14 (78.1), Gemini Decision 1 (77.7) & GPT-6 Luna (73.4).': '在 385,246 道无训练集重叠的题目上平均准确率达 78.8%，高于 Jev 1.14 (78.1)、Gemini Decision 1 (77.7) 和 GPT-6 Luna (73.4)。',
    'Leads 7 of 9 Capabilities  ·  2.2× Faster': '9 个细分维度中 7 项第一  ·  速度提升 2.2 倍',
    '#1 in routing, tools, safety, rules, reasoning, judging & consistency — plus Score 68 (+6 pts, 123 ms) on AA Decision Index v2.1.': '在路由、工具选择、安全、规则、推理、评审和一致性上排名第一；AA 决策指数达 68 分（提升 6 分，中位耗时 123 ms）。',
    'Powering Microsoft & 4,000+ Customers': '已在微软内部及 4,000 多家企业落地',
    '• Copilot Chat→Cowork: 2.2× faster, 4.4× cheaper': '• Copilot Chat 转 Cowork 判断：提速 2.2 倍，成本降至 1/4.4',
    '• Cowork Auto effort + Foundry Evaluation judge': '• 用于 Cowork 推理强度调节与 Foundry 自动评测打分',
    '• Xbox Research: 14× faster, 200× cheaper than GPT-6 Sol': '• Xbox 数据分析流程：比 GPT-6 Sol 快 14 倍，成本降至 1/200',
    '• Adopted by Epic, Equinor, Atos & Raiffeisen Bank': '• 已被 Epic、Equinor、Atos 和 Raiffeisen 银行用于生产环境',

    # Slide 21 (idx 20)
    '05 · MICROSOFT DECISION-1.1 · IMPACT': '05 · MICROSOFT DECISION-1.1 · 成本收益测算',
    'Sales agent case: 7.2× lower CAC': '销售邮件场景案例：获客成本降低 7.2 倍',
    '1 · Baseline: Frontier LLM + 100% review': '1 · 初始方案：全部调用大模型 + 全量人工审核',
    '$0.31 per lead  ·  CAC = $13.00': '单条线索成本 $0.31  ·  获客成本 CAC = $13.00',
    'Every email calls a $0.15 frontier LLM plus $0.24 human review — capping $10k/mo at 764 customers.': '每封回信都花 $0.15 调大模型生成草稿，再花 $0.24 人工检查，每月 1 万美元预算最多转化 764 位客户。',
    '2 · Add choice router + score priority': '2 · 加入 choice 前置分流与 score 优先级排序',
    '$0.07 per lead  ·  CAC = $2.63': '单条线索成本 $0.07  ·  获客成本 CAC = $2.63',
    '100% routing accuracy (vs. 88% regex): 57% of simple replies skip the LLM; only P1–P3 go to humans.': '32 类邮件分流准确率达 100%（正则规则为 88%）：57% 的简单回信直接由规则处理，无需调用大模型。',
    '3 · Add noul outbound safety gate': '3 · 加入 noul 发送前内容检查',
    '$0.05 per lead  ·  CAC = $1.81 (7.2× lower)': '单条线索成本 $0.05  ·  CAC 降至 $1.81（降低 7.2 倍）',
    'All 3 Decision-1.1 checks cost $0.00019/email total — cutting human review 100% → 8% (5,511 customers).': '三项检查加起来每封信仅需 $0.00019，将人工抽检比例从 100% 降到 8%，同样预算可转化 5,511 位客户。',

    # Slide 22 (idx 21)
    '$ copilot --model fusion --fusion-tier high \\\n    -p "..." --output-format json --usage-output-file u.json\n\n// Server-resolved pattern per single CLI command:\n-> Routine fix  : pattern="single"   (gpt-6.1-terra, 0 review)\n-> Lock bug     : pattern="cascade"  (sol -> luna Judge 5/5)\n-> 50k RPS RFC  : pattern="critique" (opus -> luna -> revise)\n-> --resume <id>: 99% cacheReadTokens hit (5,655 / 5,733 tok)': '$ copilot --model fusion --fusion-tier high \\\n    -p "..." --output-format json --usage-output-file u.json\n\n// 单条命令由服务端按题目难度自动选择模式:\n-> 常规代码修改 : pattern="single"   (gpt-6.1-terra, 无额外评审)\n-> 并发死锁修复 : pattern="cascade"  (sol -> luna 评审 5/5)\n-> 高并发容灾方案: pattern="critique" (opus -> luna 审校 -> 修订)\n-> --resume <id>: 99% 缓存命中 (5,655 / 5,733 tok)',
    'POST /openai/v1/chat/completions\nFoundry-Features: ModelRouterControls=V1Preview\n{\n  "model": "auto",\n  "routing_config": {\n    "mode": "balanced",\n    "session_affinity": { "strategy": "adaptive" }\n  }\n}\n// Invoice JSON -> DeepSeek-V4.1-Flash (28 ms)\n// Rust MPMC    -> gpt-6-luna          (27 ms, retain)': 'POST /openai/v1/chat/completions\nFoundry-Features: ModelRouterControls=V1Preview\n{\n  "model": "auto",\n  "routing_config": {\n    "mode": "balanced",\n    "session_affinity": { "strategy": "adaptive" }\n  }\n}\n// 简单发票提取 -> DeepSeek-V4.1-Flash (27 ms)\n// Rust 并发证明 -> gpt-6-luna          (30 ms, retain)',
    '// Easy JSON -> DeepSeek-V4.1-Flash (23 ms) | Hard Rust -> gpt-5.6-luna (20 ms)\n"session_affinity": { "strategy": "adaptive", "decision": "retain" },\n"attempts": [ {"model":"gpt-6-sol","status":429}, {"model":"gpt-5.6-sol","status":200} ]': '// 简单提取 -> DeepSeek-V4.1-Flash (23 ms) | 复杂证明 -> gpt-5.6-luna (20 ms)\n"session_affinity": { "strategy": "adaptive", "decision": "retain" },\n"attempts": [ {"model":"gpt-6-sol","status":429}, {"model":"gpt-5.6-sol","status":200} ]',
    '06 · LIVE DEMO 1': '06 · 演示 1',
    'Copilot CLI Auto & Fusion live': 'Copilot CLI Auto 与 Fusion 实测演示',
    'Auto → Single → Native Cascade → Native Critique → 99% Cache': 'Auto → Single → 原生 Cascade → 原生 Critique → 99% 缓存复用',
    '✓  Auto & Fusion Single fast path': '✓  Auto 与 Fusion Single 单模型执行',
    'categoryScores ≤ 0.10 & pattern="single"': '四项需求分 ≤ 0.10 且自动选择 pattern="single"',
    'Even on Fusion High, simple lookups & routine patches run 1 solver with zero review calls (3/3 node --test).': '即使开启 Fusion High，简单的配置读取与常规代码修改也只调一个模型完成（通过 3/3 单元测试）。',
    '↗  1-command native Cascade': '↗  单命令原生 Cascade 级联评审',
    'gpt-6.1-sol → gpt-6-luna Judge → Opus skipped': 'gpt-6.1-sol 修复 → gpt-6-luna 评审通过 → 跳过 Opus',
    'One CLI call fixes ABBA lock order; native Judge scores 5/5 (accept) & skips conditional Opus 5.5 repair.': '一条命令修复双锁死锁，Judge 给出 5/5 通过并自动跳过后续 Opus 返工，通过 500 次并发测试。',
    '⇄  1-command Critique + 99% Cache': '⇄  单命令原生 Critique 审校 + 99% 缓存命中',
    'Opus draft → Luna Critic → Opus revise': 'Opus 起草 → Luna 审校提议修改 → Opus 修订',
    'Native Critic flags Active-Active zero-RPO gap for Opus to revise; --resume hits 99% cacheReadTokens.': 'Critic 指出多活方案里数据零丢失的前提漏洞并交回 Opus 修订；--resume 追问实测 99% 命中缓存。',

    # Slide 23 (idx 22)
    '06 · LIVE DEMO 2': '06 · 演示 2',
    'Foundry Model Router live': 'Foundry Model Router 云端接口演示',
    '4 live Foundry V1Preview cloud traces (0 local mocks)': '4 组真实 Foundry V1Preview 云端接口调用',
    '✓  Pre-rank gate & param normalization': '✓  条件筛选与跨厂商参数自动转换',
    'developer role + json_object → gpt-5.6-luna': 'developer 角色 + json_object → gpt-5.6-luna',
    'One V1Preview endpoint normalizes cross-provider params and serves valid JSON in 30 ms router overhead.': '同一个接口自动处理不同模型的参数差异，路由耗时 30 ms 并返回合法 JSON。',
    '⚡  27–30 ms ML routing & retain affinity': '⚡  27–30 ms 路由选型与多轮缓存保持',
    'DeepSeek-V4.1-Flash (JSON) vs. gpt-6-luna (Rust)': 'DeepSeek-V4.1-Flash（发票提取）对比 gpt-6-luna（Rust 证明）',
    'Routes simple JSON to Flash (0 reason tok) and escalates Rust proofs to Luna with retain affinity on Turn 2.': '简单提取分配给 Flash（0 推理 Token）；复杂并发证明自动升级到 Luna，第 2 轮追问保持原模型不变。',
    '⇄  Two-stage cost → quality routing': '⇄  按步骤切换 cost 与 quality 模式',
    'grok-4-1-fast (cost) → gpt-5.6-terra (quality)': 'grok-4-1-fast (cost 提取) → gpt-5.6-terra (quality 分析)',
    'Splits renewal analysis into two live calls: cheap extraction in cost mode followed by strategy in quality mode.': '将续约分析拆成两次调用：先用 cost 模式低成本提取关键数据，再用 quality 模式交由强模型制定策略。',

    # Slide 24 (idx 23)
    '06 · LIVE DEMO 3': '06 · 演示 3',
    'Decision-1.1 agent controller': 'Decision-1.1 应用控制与检查演示',
    'GA · Nov 2026': '2026.11 正式版',
    '5 live /v1/systemone traces + custom prompt tester': '5 组真实 /v1/systemone 调用 + 自定义输入测试',
    '✓  Zero-spread routing (choice & noul)': '✓  输出稳定一致与前置分流',
    '5/5 identical 0.9835 · 4/4 inbox p=1.00': '连续 5 次返回 0.9835 · 4 条客服消息准确分流',
    '5 consecutive live calls return 0.00 pt spread; 3 of 4 routine inbox messages skip the frontier LLM.': '同一输入连测 5 次结果完全一致；4 条客服消息中有 3 条常规消息无需调用大模型。',
    '!  3-in-1 safety triage (choice+score+noul)': '!  一次请求同时完成三项判断',
    'safety_support (0.998) + score 1.97 + repeat 1.00': '安全团队 (0.998) + 紧急度 1.97 + 重复反馈 1.00',
    'One 348 ms call classifies injury risk, scores urgency & flags 3rd repeat contact — blocking bot reply.': '单次三百多毫秒调用同时完成分组、定级和重复投诉识别，及时停用自动回复并转交人工。',
    '✕  Outbound guardrail & missing-doc abstain': '✕  发送前竞品拦截与缺失文件提醒',
    'Rival promo noul=0.970 & missing Exhibit B p=0.9999': '提及竞品 noul=0.970 拦截 · 缺少附件 B 概率 0.9999',
    'Holds a draft recommending rival Fabrikam (0.970) and stops to ask when Exhibit B is missing from state.': '拦下推荐竞品 Fabrikam 的回复草稿 (0.970)；发现未提供附件 B 时主动提示补充，不凭空编造。',

    # Slide 25 (idx 24)
    'SUMMARY · KEY TAKEAWAYS': '总结 · 落地建议',
    'Right-size the model,\nkeep the control': '按任务选对模型，\n把控成本与质量',
    '1   Route sub-tasks by capability — no single model wins all.': '1   按子任务特点分配模型 —— 不要用一个模型处理所有请求。',
    '2   Stop paying 100× for simple work — & keep prefix caches warm.': '2   简单任务用轻量模型，多轮对话注意保持前缀缓存。',
    '3   Adopt Copilot Auto, Copilot Fusion & Foundry Router first.': '3   优先使用现成能力：Copilot Auto、Fusion 与 Foundry Router。',
    '4   Use Microsoft-Decision-1.1 for fast routing, priority & safety gates.': '4   业务代码里的分流、定级和内容检查，可接入 Decision-1.1。',
    'Thank you  ·  Q&A': '谢谢大家  ·  问答交流',

    # Slide 26 (idx 25)
    'APPENDIX · OFFICIAL SOURCES & BENCHMARKS': '附录 · 参考文档与评测报告',
    'Public field guide': '公开资料链接',
    'Benchmarks & Product Routing': '评测报告与微软产品文档',
    'Capability specialization, 163× cost benchmarks, Microsoft Copilot Auto & GitHub Copilot Fusion.': '模型能力对比、163 倍成本评测、Microsoft Copilot Auto 与 GitHub Copilot Fusion 文档。',
    'Routing Architecture & Decision-1.1': '路由架构论文与 Decision-1.1 指南',
    'HyDRA multi-head routing paper, Foundry Model Router internals, Decision-1.1 API & open benchmarks.': 'HyDRA 路由论文、Foundry Model Router 原理说明、Decision-1.1 接口文档与开源测试集。',
    '↗  Charles Lamanna — Auto in Copilot (>90% queries)': '↗  Charles Lamanna — Copilot Auto 介绍（>90% 请求采用）',
    '↗  GenisisIQ — 28-Model Multimodal Benchmark (163×)': '↗  GenisisIQ — 28 个模型多模态评测（163 倍成本差距）',
    '↗  Microsoft 365 Copilot at Ignite 2026 (Home & Auto)': '↗  Microsoft 365 Copilot Ignite 2026（主页与 Auto）',
    '↗  Microsoft Learn — Copilot Cowork Auto & Effort': '↗  Microsoft Learn — Copilot Cowork 模型与推理强度说明',
    '↗  GitHub Docs — Copilot Fusion Orchestration': '↗  GitHub 文档 — Copilot Fusion 多模型模式说明',
    '↗  GitHub HyDRA Routing Paper (arXiv:2605.17106)': '↗  GitHub HyDRA 路由论文 (arXiv:2605.17106)',
    '↗  GitHub Blog — Cache-Aware Model Routing': '↗  GitHub 博客 — 兼顾前缀缓存的模型路由实践',
    '↗  Microsoft Learn — How Foundry Model Router Works': '↗  Microsoft Learn — Foundry Model Router 工作原理',
    '↗  Command Line — Microsoft-Decision-1.1 GA': '↗  Command Line 博客 — Microsoft-Decision-1.1 发布介绍',
    '↗  Microsoft Learn — Use Microsoft-Decision-1.1 API': '↗  Microsoft Learn — Microsoft-Decision-1.1 接口使用指南',
    '↗  GitHub — microsoftconnect/Decision-Benchmarks': '↗  GitHub 仓库 — microsoftconnect/Decision-Benchmarks',
}

ZH_DEMO_LAUNCHERS = {
    10: ('fusion', '1', '打开 Fusion 演示'),
    12: ('foundry', '1', '打开 Foundry 演示'),
    20: ('decision', '1', '打开 Decision-1.1 演示'),
    21: ('fusion', '1', '启动 Demo 1 · Copilot CLI & Fusion'),
    22: ('foundry', '1', '启动 Demo 2 · Foundry 路由器'),
    23: ('decision', '1', '启动 Demo 3 · Decision-1.1'),
}

ZH_DEMO_TEXT_MAP = {
    'Demo 1 · Coding Agent': '演示 1 · 编码 Agent',
    'Demo 2 · Cloud API': '演示 2 · 云端 API',
    'Demo 3 · App Controller': '演示 3 · 应用控制',
    'Copilot Fusion &amp; Cache · 4 scenarios / 5 calls':
        'Copilot Fusion 与缓存 · 4 个场景 / 5 次调用',
    'Foundry Model Router · 4 steps': 'Foundry Model Router · 4 个步骤',
    'Microsoft-Decision-1.1 · 5 steps': 'Microsoft-Decision-1.1 · 5 个步骤',
    'Run Step 1': '运行步骤 1',
    '>DEMO<': '>演示<',
    '>STEP<': '>步骤<',
    'Auto-Play': '自动播放',
    'Replay · Verified': '录制回放 · 已验证',
    'Connecting to Demo Server…': '正在连接本地演示服务…',
    'Live · Copilot + Foundry': '实时模式 · Copilot + Foundry',
    'Live · Foundry Cloud': '实时模式 · Foundry 云端',
    'Live · Copilot CLI': '实时模式 · Copilot CLI',
    'Live · Running Step ': '实时执行 · 正在运行步骤 ',
    'Replay · Running Step ': '录制回放 · 正在播放步骤 ',
    'Live · Step ': '实时执行完成 · 步骤 ',
    'Replay · Step ': '回放完成 · 步骤 ',
    'Live · All ': '实时执行完成 · ',
    'Replay · All ': '回放完成 · ',
    'Live Backend · Running Step ': '实时执行 · 正在运行步骤 ',
    '… Calling backend &amp; verifying response': '… 正在调用后端并核对返回结果',
    'Recorded Replay · Running Step ': '录制回放 · 正在播放步骤 ',
    '… Playing captured response': '… 正在播放已录制的返回结果',
    'Reset': '重置',
    'DEMO 1 GOAL': '演示 1 目标',
    'Coding Agent Orchestration': '编码 Agent 的模型调度',
    'See how GitHub Copilot Auto &amp; Fusion picks 1 fast model for easy edits, escalates hard bugs via Judge/Critics, and protects warm caches.': '观察 GitHub Copilot Auto 与 Fusion 如何为简单修改选择单模型、为复杂问题增加评审，并在多轮对话中复用缓存。',
    'GitHub Copilot CLI · Auto &amp; Fusion': 'GitHub Copilot CLI · Auto 与 Fusion',
    'SINGLE · NO REVIEW OVERHEAD': 'SINGLE · 无额外评审开销',
    'Color legend': '颜色说明',
    'Config': '配置',
    'Request': '请求',
    '✓ Pass': '✓ 通过',
    '✕ Hold': '✕ 暂停',
    'Source': '来源',
    'Summary': '摘要',
    '{ } Raw Log': '{ } 原始日志',
    'Inspect verbatim CLI JSONL / HTTP JSON and provenance': '查看未经改写的 CLI JSONL / HTTP JSON 与来源',
    "Inspect the current step's verbatim CLI JSONL / HTTP JSON and provenance":
        '查看当前步骤未经改写的 CLI JSONL / HTTP JSON 与来源',
    'Routing flow': '路由流程',
    'ROUTING RULE / API CALL': '路由规则 / API 调用',
    'Chosen Model': '选中的模型',
    'Judge / Critic': '评审模型',
    'Bypassed': '未调用',
    'Primary Solver': '主模型',
    'Skipped when unwarranted': '任务简单时自动跳过',
    'Primary Draft': '主模型初稿',
    'Cross-Lab Critic': '换一个模型复核',
    'Handoff Revision': '交回主模型修订',
    'Resumed Session': '恢复原会话',
    'Cold Model Switch': '中途切换冷模型',
    'Avoided': '已避免',
    'Retained Model': '继续使用原模型',
    'Request Gate': '请求条件检查',
    'ML Router': '模型排序器',
    'Selected Model': '选中的模型',
    'JSON Output': 'JSON 输出',
    'Turn 1 Ranker': '第 1 轮模型排序',
    'Turn 2 Affinity': '第 2 轮保持原模型',
    'Structured Handoff': '传递精简后的结果',
    'Customer Message': '客户消息',
    'Deterministic Gate': '业务代码判断',
    'Pinned Opus 5.5': '固定使用 Opus 5.5',
    'Pays frontier tokens on a 1-line config lookup': '读取一行配置也按大模型费用计费',
    '1 CLI call · auto_v2 fast path': '1 次 CLI 调用 · auto_v2 快速路径',
    'Model: ': '模型：',
    'Scores: ': '需求分：',
    'Credits: ': '额度：',
    'Test any custom prompt or draft reply live (e.g. &quot;Thanks!&quot;, &quot;Fix Rust ABA race&quot;, &quot;Try rival Fabrikam for $749&quot;)...': '输入任意问题或回复草稿进行实时测试（例如“谢谢”、“修复 Rust 并发问题”、“推荐竞品”）...',
    'Route ▶': '判断 ▶',
    'STEP 1 / 5': '步骤 1 / 5',
    'Payoff vs. Naive Baseline': '与固定方案对比',
    'Cost, latency &amp; safety': '成本、延迟与安全',
    'WITHOUT ROUTING': '不使用自动路由',
    'WITH AUTO-ROUTING': '使用自动路由',
    'Auto Fast Path: 1-Line Config Lookup': 'Auto 快速路径：读取一行配置',
    'auto_v2 Fast Path': 'auto_v2 快速路径',
    'One copilot --model auto call emits session.auto_mode_resolved with 4D categoryScores (all ≤ 0.10) and routes straight to GPT-6 Luna.': '一次 copilot --model auto 调用即可得到四项需求分（都不高于 0.10），并直接选择 GPT-6 Luna。',
    'Fusion High: Picks pattern="single" on Routine Patch': 'Fusion High：常规修改选择 Single 模式',
    'Fusion Single Pattern': 'Fusion Single 模式',
    'Even on Fusion High, Copilot Fusion checks 4D capability scores first and picks pattern="single" (phasePlan: []) when 1 solver is sufficient.': '即使选择 Fusion High，系统仍会先判断任务难度；一个模型足够时就使用 Single 模式，不增加额外评审。',
    'Fusion High: Native pattern="cascade" (Solver + Judge)': 'Fusion High：原生 Cascade（修改 + 评审）',
    'Native 1-Call Cascade': '单命令原生 Cascade',
    'One copilot --model fusion --fusion-tier high command orchestrates Solver (gpt-6.1-sol) + Judge (gpt-6-luna) server-side, skipping conditional Opus 5.5 repair when Judge returns verdict="accept".': '一条 Fusion High 命令在服务端完成代码修改和评审；评审通过后自动跳过备用的 Opus 5.5 修复阶段。',
    'Fusion High: Native pattern="critique" (Draft → Critic → Revise)': 'Fusion High：原生 Critique（起草 → 审校 → 修订）',
    'Native 1-Call Critique': '单命令原生 Critique',
    'On high-stakes architecture prompts, one --model fusion --fusion-tier high call drafts on Opus 5.5, critiques on cross-family GPT-6 Luna, and hands off via session.fusion_handoff for a high-effort Opus 5.5 revision.': '对于复杂架构问题，一条 Fusion High 命令先由 Opus 5.5 起草，再由 GPT-6 Luna 审校，最后交回 Opus 5.5 修订。',
    'Prefix-Cache Guard: 99% Cache Hit via --resume': '前缀缓存：通过 --resume 命中 99% 缓存',
    'Warm Prefix Retention': '保留已预热的前缀缓存',
    'usage.json exposes exact cacheReadTokens and cacheExpiresAt. Keeping the session model on follow-up turns reuses 99% of prompt tokens instead of paying full prefill on a cold model.': 'usage.json 会给出实际缓存读取量和过期时间。后续轮次沿用同一模型，可复用 99% 的输入内容。',
    'Eligibility Gate & Cross-Provider Param Normalization': '条件筛选与跨厂商参数转换',
    'Pre-Rank + Param Adapt': '排序前筛选与参数适配',
    'Foundry filters deployments by required capabilities (tools / json_object) before ranking, adapts cross-provider parameters automatically, and drains pre-paid PTU capacity first.': 'Foundry 在排序前先筛掉不支持工具或 JSON 输出的模型，自动转换各厂商参数，并优先使用已购买的 PTU 配额。',
    'Simple JSON Extraction Routed to DeepSeek Flash in 27 ms': '简单 JSON 提取在 27 ms 内选择 DeepSeek Flash',
    '1–2% Balanced Band': 'Balanced 质量区间 1–2%',
    'For straightforward JSON extraction, DeepSeek-V4.1-Flash scores within 1–2% of frontier quality — so Balanced mode selects it automatically at a fraction of frontier cost.': '对于简单的 JSON 提取，DeepSeek-V4.1-Flash 的预测质量与最高分非常接近，因此 Balanced 模式会自动选择成本更低的模型。',
    'Same Endpoint Escalates Rust Proof & Retains Session': '同一接口为 Rust 证明升级模型并保持会话模型',
    'Difficulty Escalation + Affinity': '按难度升级与会话保持',
    'Without changing endpoint or code, formal concurrency proofs trigger automatic escalation to gpt-6-luna, and Turn 2 retains the same model via derived_fingerprint.': '无需改接口或业务代码，复杂并发证明会自动升级到 gpt-6-luna；第二轮通过消息指纹继续沿用同一模型。',
    'Two-Stage Routing: mode="cost" Extraction → mode="quality" Strategy': '两阶段路由：cost 提取 → quality 策略分析',
    'Two-Stage Sub-Job Routing': '按子任务分两阶段路由',
    'Instead of running an entire multi-step workflow on one expensive model, each sub-job passes its own routing_config.mode ("cost" vs "quality") to the same Foundry endpoint.': '不用让一个高成本模型完成全部流程，每个子任务都可以在同一 Foundry 接口上选择 cost 或 quality 模式。',
    '5× Live Repeat Probe: 0.9835 with 0.00 pt Spread': '连续调用 5 次：结果均为 0.9835',
    'Calibrated System-One': '稳定的概率输出',
    'Unlike generative LLM judges that drift across runs and bill for output prose, Decision-1.1 returns deterministic calibrated probabilities in a single forward pass.': '与每次结果可能波动的生成式模型不同，Decision-1.1 通过单次前向计算直接返回稳定的概率值。',
    'Check 1 (choice): 4/4 Live Inbox Triage (3/4 Skip Frontier)': '检查 1（choice）：4 条消息准确分流，3 条无需大模型',
    'Pre-LLM Inbox Filter': '调用大模型前的消息分流',
    'Spending ~$0.000013 on a calibrated choice check filters out acknowledgements, opt-outs, and simple FAQ lookups before they ever touch a $15/1M frontier LLM.': '一次低成本的 choice 判断，可以在调用大模型前处理感谢、退订和简单查询等常规消息。',
    'Check 2 (choice + score + noul): Live Injury Triage & Escalation': '检查 2（choice + score + noul）：受伤投诉分流与人工升级',
    '3-in-1 Multi-Question Call': '一次请求回答三个问题',
    'Packing choice, score, and noul into a single /v1/systemone request classifies the team, computes calibrated urgency, and flags repeat complaints in one round-trip.': '在一次 /v1/systemone 请求里同时提交 choice、score 和 noul，可一次返回负责团队、紧急程度和是否重复投诉。',
    'Check 3 (noul): Live Outbound Guardrail Blocks Rival Promo': '检查 3（noul）：发送前拦截推荐竞品的草稿',
    'Pre-Send Guardrail': '发送前内容检查',
    'A $0.00006 pre-send noul check catches competitor promotions or unauthorized discounts automatically so clean drafts ship without 100% manual human review.': '发送前使用 noul 检查是否推荐竞品或擅自承诺折扣，只有命中风险的草稿才需要人工处理。',
    'Missing Document Caught: Abstains Instead of Hallucinating': '发现缺少文件：提示补充材料而不是猜测',
    'Missing-Context Guard': '缺少上下文检查',
    'Before calling an expensive frontier model to compare legal clauses, Decision-1.1 verifies all referenced exhibits exist in state — stopping to ask when one is missing.': '在调用大模型比较合同条款前，Decision-1.1 先检查引用的附件是否都已提供，缺少时先提示用户补充。',
    'DEMO 1 · CODING AGENT': '演示 1 · 编码 Agent',
    'Fast Single pass on easy code, Judge/Critic teams on hard bugs, and warm-cache retention.': '简单代码使用单模型，复杂问题增加评审，并在多轮对话中复用缓存。',
    'DEMO 2 · CLOUD API': '演示 2 · 云端 API',
    'One /chat/completions endpoint: param normalization, cheap Flash on easy JSON, auto-escalation, and cost→quality sub-jobs.': '同一个 /chat/completions 接口完成参数转换、简单任务低成本路由、复杂任务升级和子任务分流。',
    'DEMO 3 · APP CONTROLLER': '演示 3 · 应用控制',
    'Replace slow LLM router prompts with 180 ms calibrated choice, score & noul gates ($0.042/1M).': '使用低延迟的 choice、score 和 noul 判断替代生成式大模型路由提示词。',
    'All 4 Verified ✓': '4 个步骤全部验证通过 ✓',
    'All 5 Verified ✓': '5 个步骤全部验证通过 ✓',
    'Step ': '步骤 ',
    ' Verified ✓': ' 验证通过 ✓',
    'Running Step ': '正在回放步骤 ',
    'Running Live Step ': '正在运行步骤 ',
    'Error': '错误',
    'Stop': '停止',
    'Next: Step ': '下一步：步骤 ',
    'Run Step ': '运行步骤 ',
    'STEP ': '步骤 ',
    '# Click "Run Step 1" or "Auto-Play" above — or click "{ } Raw Log" to inspect verbatim CLI JSONL / HTTP JSON & provenance.': '# 请选择一个步骤运行，或点击“自动播放”；点击“原始日志”可查看未经改写的 CLI JSONL / HTTP JSON。',
    'Visual Auto-Routing Studio': '可视化自动路由工作台',
    'CUMULATIVE LEDGER': '累计成本与耗时',
    'Pinned Baseline': '固定大模型',
    'Auto-Routed': '自动路由',
    'Preview · Step ': '预览 · 步骤 ',
    'Completed: ': '已完成：',
    '% Cost · ': '% 成本 · ',
    '× Speed': '× 速度',
    '-88% Cost': '节省 88% 成本',
    '✦ Visual': '✦ 可视化',
    'Interactive Diff, Review &amp; Smart Inbox view': '交互式代码对比、评审与消息分流视图',
    'CODE DIFF &amp; REVIEW': '代码对比与评审',
    'CODE DIFF & REVIEW': '代码对比与评审',
    'API & SESSION INSPECTOR': '接口与会话检查',
    'SMART INBOX & GUARDRAILS': '客服收件箱与安全检查',
    '… Routing &amp; verifying telemetry': '… 正在路由并验证遥测数据',
    'IN PROGRESS': '运行中',
    'READY · CLICK RUN ▶': '待运行 · 点击运行 ▶',
    'GUARDRAIL TRIGGERED': '已触发拦截',
    'VERIFIED ✓': '已验证 ✓',
    'AUDIENCE / CUSTOM INPUT': '自定义测试输入',
    'CALIBRATED ROUTING SIGNALS': '路由评分结果',
    'CUSTOM PROBE': '自定义测试',
    'PROBING LIVE…': '正在实时判断…',
    'LIVE PROBE ✓': '实时判断完成 ✓',
    'RULE PREVIEW ✓': '规则预览 ✓',
    'Inspecting demo/fixtures/config.ts — Click Run Step 1 to route via Copilot Auto': '查看 demo/fixtures/config.ts —— 点击“运行步骤 1”通过 Copilot Auto 路由',
    '✓ GPT-6 Luna answered in 1 CLI call (0.055 AIU) & warmed 5,655 prefix tokens': '✓ GPT-6 Luna 通过 1 次 CLI 调用返回结果（0.055 AIU），并写入 5,655 个缓存 token',
    'Read-Only Lookup': '只读查询',
    '4D CAPABILITY DEMAND (≤ 0.10 FAST PATH)': '四项能力需求分（≤ 0.10 走快速路径）',
    'VERIFIED CLI OUTPUT': 'CLI 实际输出',
    'EXPECTED CLI OUTPUT': '待获取 CLI 输出',
    'Waiting for copilot --model auto...': '等待执行 copilot --model auto...',
    '0 Judge Overhead': '0 次额外评审',
    '5,655 Cache Write': '写入 5,655 缓存 token',
    'Bug in format.mjs: space-only regex misses \\t and Unicode NBSP (\\u00A0)': 'format.mjs 中的问题：正则只匹配普通空格，漏掉了制表符 \\t 和不换行空格 \\u00A0',
    '✓ Patched in 1 Single-pattern pass by ': '✓ 由单模型一次修复完成：',
    'PATCHED · 3/3 TESTS PASS': '已修复 · 3/3 测试通过',
    'BUGGY INPUT · 2/3 TESTS FAILING': '待修复代码 · 2/3 测试失败',
    'FUSION ORCHESTRATOR · PATTERN = "SINGLE"': 'FUSION 调度结果 · PATTERN = "SINGLE"',
    'Even with --fusion-tier high enabled, capability demand stayed bounded (0.231), so Fusion skipped Judge/Critic calls and verified 3/3 unit tests in one pass.': '即使开启了 --fusion-tier high，任务需求分仍然不高（0.231），因此系统跳过了额外评审，一次完成修改并通过全部 3 项测试。',
    'Fusion High will inspect 4D capability scores first before deciding whether multi-model review is worth paying for.': 'Fusion High 会先评估四项能力需求分，再决定是否有必要增加多模型评审。',
    'Judge Calls: 0': '评审调用：0 次',
    'Concurrency Deadlock in token-bucket.ts: refill() locks drain→state while close() locks state→drain': 'token-bucket.ts 并发死锁：refill() 先拿 drain 再拿 state，与 close() 顺序相反',
    '✓ Cascade Complete: Solver patched lock order, Judge accepted (5/5), Opus 5.5 repair skipped!': '✓ Cascade 完成：主模型修正加锁顺序，评审模型给出 5/5 通过，跳过了 Opus 5.5 修复步骤',
    'DEADLOCK FIXED · 500/500 RACES PASS': '死锁已修复 · 500/500 并发压测通过',
    'ABBA LOCK-ORDER INVERSION': 'ABBA 加锁顺序反转',
    'NATIVE JUDGE ANNOTATION · ': '原生评审结果 · ',
    'AWAITING SOLVER PATCH': '等待主模型提交补丁',
    'Native Cascade runs Primary Solver (gpt-6.1-sol) then cross-checks with Judge (gpt-6-luna), triggering claude-opus-5.5 repair ONLY if Judge rejects.': '原生 Cascade 先由主模型（gpt-6.1-sol）修复，再由评审模型（gpt-6-luna）检查；只有评审不通过时才调用 claude-opus-5.5 修复。',
    'SKIPPED ($ Saved)': '已跳过（节省调用）',
    'Architecture RFC Task: 50k RPS multi-region payment gateway with strict RPO = 0': '架构设计任务：50k RPS 多区域支付网关，要求严格满足 RPO = 0',
    '✓ Cross-Lab Critic (gpt-6-luna) caught an Active-Active RPO=0 data-loss gap & Opus 5.5 revised!': '✓ 跨厂商审校模型（gpt-6-luna）指出双活方案的 RPO=0 丢数隐患，Opus 5.5 完成修订',
    'Active-Active Shard Leases': '按商户分片租约的双活方案',
    'Proposes per-merchant shard leases with monotonic <code>fencing_token</code> checks and claims Active-Active achieves <strong>RPO = 0</strong>.': '提出用分片租约配合递增 <code>fencing_token</code> 避免写冲突，并声称该双活方案满足 <strong>RPO = 0</strong>。',
    'Cross-Lab Audit': '换一个模型交叉检查',
    'Audits failure modes, quorum math, and RPO/RTO claims across model families.': '换一个模型检查故障场景、多数派写入，以及 RPO/RTO 的结论是否成立。',
    '3-Region Sync Quorum ✓': '三区域同步多数派提交 ✓',
    'Upgrades ledger storage to synchronous 3-region Raft quorum commit (Spanner / CockroachDB, 18–35 ms WAN budget) for true RPO = 0.': '将账本存储改为三区域同步 Raft 多数派提交（如 Spanner / CockroachDB，预留 18–35 ms 跨区延迟），真正满足 RPO = 0。',
    'WHY CROSS-LAB CRITIQUE MATTERS': '为什么要换一个模型复核',
    '7,917 CACHED TOKENS REUSED': '复用 7,917 个缓存 token',
    'A single model rarely catches its own blind spot on distributed consensus vs. lease fencing — pairing Claude Opus 5.5 with GPT-6 Luna caught a real RPO=0 production flaw in one CLI command.': '单一模型很难发现自己在“租约防重”与“跨区域持久化”上的概念混淆；将 Claude Opus 5.5 与 GPT-6 Luna 组合，在一条命令内找出了这个线上隐患。',
    'Resuming warm session (--resume) to add Prometheus metrics without switching models': '恢复同一会话（--resume）补充 Prometheus 指标，不切换模型以保留缓存',
    'PROMPT PREFIX CACHE RETENTION (': '前缀缓存复用率（',
    'New Turn Tokens: ': '本轮新增 token：',
    'metrics.prom (Generated Output)': 'metrics.prom（生成结果）',
    '7.5 s · Warm Session': '7.5 秒 · 复用原会话',
    '# Click Run Step 5 to generate Prometheus metrics using cached context...': '# 点击“运行步骤 5”，在复用缓存的前提下生成 Prometheus 指标...',
    'Sending OpenAI-style developer role + json_object + temperature=0.2 to Foundry model="auto"': '向 Foundry model="auto" 发送包含 developer 角色、json_object 和 temperature=0.2 的请求',
    'UNIFIED REQUEST PAYLOAD': '统一请求参数',
    'PRE-RANK CAPABILITY GATE &amp; RESPONSE': '排序前条件筛选与响应',
    '1. Filtered out pool models lacking strict <code>json_object</code><br>2. Normalized <code>role="developer"</code> &amp; <code>temperature</code><br>3. Ranked eligible pool in <strong>': '1. 先筛除不支持严格 <code>json_object</code> 的模型<br>2. 自动转换 <code>role="developer"</code> 与采样参数<br>3. 在候选池中完成排序耗时 <strong>',
    'Incoming EU Invoice: Simple 2-field JSON extraction under mode="balanced"': '收到欧洲客户账单：在 mode="balanced" 下提取两个 JSON 字段',
    'INCOMING DOCUMENT': '原始单据文本',
    'Northwind EU Invoice Text': 'Northwind 欧洲账单内容',
    'STRUCTURED EXTRACTION CARD': '提取出的结构化结果',
    '1–2% BALANCED QUALITY BAND': 'Balanced 1–2% 质量区间',
    '~96% CHEAPER THAN FRONTIER': '成本比前沿大模型低约 96%',
    'Because Flash scores within 1–2% of the #1 frontier model on structured field extraction, Balanced mode picks Flash automatically without burning reasoning tokens.': '在字段提取任务上，Flash 模型与最高分大模型的预测质量差距在 1–2% 以内，因此 Balanced 模式自动选择 Flash，不消耗额外推理 token。',
    'Same /chat/completions endpoint now receives a 2-turn Rust lock-free concurrency proof': '同一个 /chat/completions 接口随后收到两轮 Rust 无锁并发队列设计请求',
    'ESCALATED · LUNA': '已升级 · LUNA',
    'AFFINITY: RETAIN ✓': '会话保持：RETAIN ✓',
    'TURN 2 VERIFIED INVARIANTS': '第 2 轮输出的关键约束',
    'Click Run Step 3 to execute both live turns on Foundry Model Router...': '点击“运行步骤 3”在 Foundry Model Router 上执行两轮请求...',
    'Enterprise Account Workflow on demo/fixtures/renewal-context.json (Northwind Logistics · $432K ARR)': '企业续约分析任务（基于 demo/fixtures/renewal-context.json · 年合同额 $432K）',
    'Extracts compact renewal facts from raw JSON at minimal token cost...': '先用低成本模型从原始 JSON 中整理关键续约数据...',
    'Synthesizes executive pricing & negotiation playbook from compact Stage 1 facts...': '再由高质量模型基于第一阶段摘要制定续约报价方案...',
    'Customer Sales Message: Testing 5 consecutive /v1/systemone calls for probability drift': '客户售前咨询：连续调用 5 次 /v1/systemone 检验概率是否稳定',
    'INBOUND CUSTOMER MESSAGE': '收到的客户消息',
    'CALIBRATED SYSTEM-ONE PRIMITIVE': '单次前向概率判断',
    'SPREAD: 0.00 PT · 54 IN TOK · 0 OUT TOK': '极差：0.00 · 54 输入 token · 0 输出 token',
    'Deterministic single forward-pass log-prob scoring: no sampling temperature drift, no JSON formatting retries, and $0 output token charges.': '通过单次前向计算直接输出校准概率：没有随机采样波动，不需要重试 JSON 格式，也没有输出 token 费用。',
    'Smart Support Inbox: 4 incoming customer messages waiting for tier assignment': '智能客服收件箱：对 4 条不同类型的客户消息进行分流',
    '✓ Routed 4/4 messages with p = 1.00 confidence — 3 of 4 bypassed the $15/1M Frontier LLM!': '✓ 4 条消息全部分流完成（置信度 1.00）—— 其中 3 条无需调用高成本大模型',
    '$0 LLM · Auto-acknowledge & close': '$0 大模型费用 · 自动归档关闭',
    '$0 LLM · Deterministic opt-out handler': '$0 大模型费用 · 业务代码处理退订',
    'Cheap SLM · Promo FAQ lookup': '轻量小模型 · 促销规则查询',
    'Escalated · Multi-clause cross-border warranty analysis': '升级到大模型 · 跨国多条款质保对比',
    'Urgent Inbound Ticket: Evaluating team + priority[0..3] + repeat_complaint in 1 HTTP call': '紧急客诉工单：在 1 次 HTTP 调用中同时判断负责团队、紧急程度与是否重复投诉',
    'HUMAN PAGED ✕': '已转人工专员 ✕',
    'HIGH RISK': '高风险',
    'SIMULTANEOUS 3-PRIMITIVE READOUT (': '单次调用同时返回三项结果（',
    'Auto-Bot Permitted': '允许机器人自动回复',
    '0% — Blocked': '0% — 已拦截',
    'Screening AI-generated outbound reply before customer delivery (threshold ≥ 0.50)': '在发送给客户前检查 AI 生成的回复草稿（阈值 ≥ 0.50）',
    'OUTBOUND AGENT DRAFT COMPOSER (PRE-SEND GATE)': '待发送回复草稿（发送前检查）',
    'Without pre-send <code>noul</code> screening, either unsafe replies leak to customers or humans must review 100% of drafts ($0.24/msg).': '如果不做发送前 <code>noul</code> 检查，要么不当回复直接发给客户，要么所有草稿都得人工逐条审核（约 $0.24/条）。',
    'PARALLEL POLICY GATES (': '并行策略检查（',
    'Legal Comparison Request: Checking attached_documents completeness before Frontier call': '合同对比请求：在调用大模型前先检查附件是否齐全',
    'LEGAL WORKSPACE STATE': '合同工作区附件状态',
    '📄 Contract_A.pdf · Attached (Sec 9.2: 60 days)': '📄 Contract_A.pdf · 已上传（第 9.2 条：提前 60 天通知）',
    '⚠️ Exhibit_B.pdf · MISSING FROM STATE ✕': '⚠️ Exhibit_B.pdf · 未上传 ✕',
    'ACTION PROBABILITIES': '下一步动作概率',
    'SAFE ASSISTANT ACTION': '安全处理方式',
    '<strong>Asked Customer:</strong> "Contract A specifies 60 days prior written notice, but <strong>Exhibit B is not attached</strong>. Please upload Exhibit B so I can compare both clauses accurately."': '<strong>向用户提示：</strong>“已读取主合同 A（第 9.2 条规定需提前 60 天书面通知），但当前<strong>尚未上传附件 Exhibit B</strong>。请先补充上传后再为您对比两份条款。”',
    'Instead of letting a frontier LLM guess missing Exhibit B terms, Decision-1.1 catches missing context upfront.': '与其让大模型在缺少附件时凭空猜测条款，不如先用 Decision-1.1 发现缺失文件并提示用户补充。',
    '✓ Retained ': '✓ 继续使用原模型 ',
    ' — 99% prefix cache hit (': ' —— 复用 99% 前缀缓存（',
    '✓ Pre-rank gate filtered candidates & normalized params in ': '✓ 排序前完成条件筛选与参数转换，耗时 ',
    '✓ Routed in ': '✓ 路由耗时 ',
    ' with 0 wasted reasoning tokens!': '，未消耗额外推理 token',
    '✓ Auto-escalated Turn 1 to ': '✓ 第 1 轮自动升级至 ',
    ' & retained session on Turn 2!': '，第 2 轮保持同一模型',
    '✓ Stage 1 extracted facts via ': '✓ 第一阶段提取数据使用 ',
    ' → Stage 2 synthesized 129.2% NRR strategy via ': ' → 第二阶段生成 129.2% NRR 方案使用 ',
    '✓ 5/5 live HTTP calls returned noul = 0.9835 with 0.0000 pt spread ($0 output tokens)!': '✓ 连续 5 次 HTTP 调用均返回 noul = 0.9835（极差 0.0000，输出 token 费用 $0）',
    '✕ AUTO-BOT BLOCKED in ': '✕ 自动回复已拦截（耗时 ',
    ' ms — Routed to safety_support & paged human specialist!': ' ms）—— 已转交安全支持团队并通知人工专员',
    '✕ SEND INTERCEPTED in ': '✕ 发送前已拦截（耗时 ',
    ' ms — Competitor promo (0.970 ≥ 0.50) held for human review!': ' ms）—— 检测到推荐竞品（0.970 ≥ 0.50），已转人工审核',
    '✕ ABSTAINED in ': '✕ 已暂停对比（耗时 ',
    ' ms — Missing Exhibit B caught (p = 0.99994); zero hallucination!': ' ms）—— 识别出缺少附件 Exhibit B（概率 0.99994），避免凭空猜测',
}

# 中文版按演讲语境重新表达，不照搬英文句式。产品名、模型名、API、
# 参数名和代码字段保留英文，便于现场与日志逐项对应。
ZH_TEXT_MAP.update({
    '4 scenarios · 5 real Copilot CLI calls':
        '4 个场景 · 5 次真实 Copilot CLI 调用（缓存场景包含预热和 resume）',
    'warm-up + copilot --model auto --resume <sid> (2 real CLI calls on first run)':
        '预热 + copilot --model auto --resume <sid>（首次运行共 2 次真实 CLI 调用）',
    'warm-up + resumed follow-up': '预热调用 + resume 追问',
    '# Click Run Step 4 to create a warm session and verify the resumed cache hit...':
        '# 点击“运行步骤 4”，先建立缓存，再通过 --resume 验证命中率...',
    'Routing every task to the right model for quality, cost and speed — from Microsoft Copilot and Foundry to Microsoft-Decision-1.1.':
        '根据每项任务的难度和特点自动选择模型，在效果、成本和响应速度之间取得平衡——从 Microsoft Copilot、Foundry 到 Microsoft-Decision-1.1。',
    'AGENDA': '内容安排',
    'Fast, calibrated control': '快速、稳定的程序判断',
    'Our journey today': '今天主要讲七件事',
    'One prompt, four specialized jobs': '一个需求，交给四类模型分工完成',
    'Guardrail gate first: filters tenant-allowed model providers, data residency, and live endpoint health.':
        '开始执行前，先按企业设置检查可用的模型提供商、数据处理区域和服务状态。',
    'Compressed quality, 163× cost spread': '效果差距不大，调用成本却相差 163 倍',
    '4.2-pt quality band, 163× cost gap': '前 14 名只差 4.2 分，费用相差 163 倍',
    'Routine work → small models win': '常规任务：轻量模型更划算',
    'Hard problems → escalate selectively': '复杂任务：需要时再升级模型',
    'Don’t break a warm prefix cache': '多轮对话中，别轻易换掉已经建立缓存的模型',
    'Warm prefix cache = 10×–20× cheaper': '复用前缀缓存，输入费用通常可降到原来的十分之一左右',
    'Route at natural cache boundaries': '只在合适的时机重新选模型',
    'Four routing surfaces across Microsoft': '微软四类产品如何自动选择模型',
    'Coding Orchestrator': '编程任务的多模型协作',
    'Software Controller': '业务流程判断接口',
    'Purpose-built decision API that classifies, scores priority, and runs yes/no safety gates in ~123 ms at $0.042/1M.':
        '面向业务流程的专用判断接口：约 123 ms 完成分类、优先级评分和发送前检查，每百万输入 Token 费用为 $0.042。',
    'Microsoft Copilot Home: unified Auto': 'Microsoft Copilot：一个入口处理问答和多步任务',
    '1 · Chat → Cowork handoff': '1 · 判断留在 Chat 还是转到 Cowork',
    '2 · Multi-provider within IT rules': '2 · 在企业允许的范围内选择模型提供商',
    '3 · Scoped context & local offload': '3 · 只读取相关资料，简单任务可交给本地模型',
    'Copilot Cowork: keep cache, tune effort': 'Copilot Cowork：主模型保持不变，每一步按需调整推理强度',
    'Opening-message model lock': '根据第一条消息选定主模型',
    'Decision-1.1 sets reasoning effort': '每一步单独决定需要多少推理',
    'Predictable spend guardrails': '团队费用可以预估，也可以设上限',
    'Copilot Fusion: pick effort, not models': 'Copilot Fusion：只选投入档位，不必逐个挑模型',
    'Frontier quality at ~50% cost': '接近固定旗舰模型的效果，费用约省一半',
    'Fixes “forgot to switch back” waste': '避免解决难题后一直忘记切回轻量模型',
    'Single, Cascade & Critique patterns': '三种执行方式：Single、Cascade 和 Critique',
    '1 · Single  (Everyday tasks)': '1 · Single（日常任务由一个模型完成）',
    '2 · Cascade  (Draft → Judge → Repair)': '2 · Cascade（先完成，再检查；有问题才重做）',
    '3 · Critique  (Draft → Critics → Revise)': '3 · Critique（先起草，多方审阅后再修订）',
    'Foundry Router: how it ranks & caches': 'Foundry Model Router：如何选模型并保持会话缓存',
    'SCORING & AFFINITY ENGINE  ·  TRAINED ON BILLIONS OF INTERACTIONS':
        '模型评分与会话保持机制  ·  基于海量真实交互训练',
    'Quality-Band Cost Selection': '在效果接近的模型里选择成本最低的',
    'Adaptive Cache Affinity': '多轮对话尽量沿用原模型',
    'Foundry: filters, params & failover': 'Foundry：先筛选，再适配参数，异常时自动换模型',
    '1 · Pre-Rank Eligibility Gate': '1 · 排序前先排除不符合要求的模型',
    '2 · Cross-Provider Param Cleanup': '2 · 自动处理不同厂商的参数差异',
    '3 · PTU Priority & Auto-Failover': '3 · 优先使用 PTU，遇到限流自动切换',
    'GitHub HyDRA: decouple demand & catalog': 'GitHub HyDRA：先判断任务需要什么，再从模型列表中选择',
    '4-Head Capability Scorer': '同时评估四项能力需求',
    'Zero-Retraining Model Updates': '新增模型只改配置，不必重新训练路由器',
    'Microsoft’s three-layer routing stack': '微软自动路由的三层结构',
    'Models score bounded options; deterministic code enforces policy gates, thresholds & fallbacks.':
        '模型只负责给允许的选项打分；权限、阈值和失败后的处理仍由普通代码控制。',
    'Layer 1 · Deterministic Policy & Cache Gate': '第 1 层 · 用普通代码检查权限、能力和缓存状态',
    'Hard code filters tenant-allowed providers, data zones, required tool/schema capabilities, and warm prefix-cache state.':
        '先检查企业允许的模型提供商、数据处理范围、工具或结构化输出能力，以及当前会话缓存是否还能复用。',
    'Layer 2 · Fast Scorer / Decision Model (<180 ms)': '第 2 层 · 用快速评分器判断哪个选项更合适（<180 ms）',
    'Layer 3 · Workflow Pattern & Output Verifier': '第 3 层 · 执行对应流程，并在提交结果前做确定性检查',
    'Meet Microsoft-Decision-1.1': 'Microsoft-Decision-1.1：把“判断”单独交给专用模型',
    'Generative LLMs as routers': '让生成式大模型负责判断，问题在哪里',
    'Built specifically for fast, calibrated decisions': '专门用于快速、稳定地比较有限选项',
    'Three primitives: choice, noul, score': '三种问题类型：多选一、是非判断和等级评分',
    '01 · choice  (Pick one)': '01 · choice（从候选项中选一个）',
    '02 · noul  (Yes / No gate)': '02 · noul（判断某个条件是否成立）',
    '03 · score  (0–N scale)': '03 · score（按等级计算分数）',
    'Four production Decision-1.1 patterns': 'Decision-1.1 在业务系统里的四种典型用法',
    '1 · Custom LLM & Agent Router (choice)': '1 · 自定义模型或 Agent 分流（choice）',
    '2 · Support Triage + SLA Queue (choice + score)': '2 · 客服工单分组与紧急程度排序（choice + score）',
    '3 · Multimodal Photo & UI Gate (assets + noul)': '3 · 检查退货照片或界面截图（assets + noul）',
    '4 · Outbound LLM Guardrail Filter (noul)': '4 · AI 回复发送前检查（noul）',
    '#1 across 102 decision benchmarks': '在 102 项判断类盲测中综合排名第一',
    '#1 Overall Across 102 Blind Benchmarks': '102 项盲测综合排名第 1',
    'Powering Microsoft & 4,000+ Customers': '已用于微软产品和 4,000 多家客户',
    'Sales agent case: 7.2× lower CAC': '销售邮件案例：获客成本降至约七分之一',
    '1 · Baseline: Frontier LLM + 100% review': '1 · 原方案：每封邮件都调用大模型，并全部人工审核',
    '2 · Add choice router + score priority': '2 · 先做消息分流，再按优先级处理',
    '3 · Add noul outbound safety gate': '3 · 发送前只检查可能有问题的草稿',
    'Decision-1.1 agent controller': 'Decision-1.1 业务流程判断演示',
    '✓  Zero-spread routing (choice & noul)': '✓  同一输入结果稳定，普通消息先分流',
    '!  3-in-1 safety triage (choice+score+noul)': '!  一次请求同时完成分组、定级和重复投诉判断',
    '✕  Outbound guardrail & missing-doc abstain': '✕  发送前拦下不当回复，缺少材料时先向用户询问',
    'Right-size the model,\nkeep the control': '任务交给合适的模型，\n关键控制仍放在代码里',
})

ZH_DEMO_LAUNCHERS = {
    10: ('fusion', '1', '打开演示 1：Copilot Auto 与 Fusion'),
    12: ('foundry', '1', '打开演示 2：Foundry Model Router'),
    20: ('decision', '1', '打开演示 3：Decision-1.1'),
    21: ('fusion', '1', '打开演示 1：Copilot Auto 与 Fusion'),
    22: ('foundry', '1', '打开演示 2：Foundry Model Router'),
    23: ('decision', '1', '打开演示 3：Decision-1.1'),
}

ZH_DEMO_TEXT_MAP.update({
    'Demo 1 · Coding Agent': '演示 1 · 编程 Agent',
    'Demo 3 · App Controller': '演示 3 · 业务流程判断',
    'Coding Agent Orchestration': '编程任务的多模型协作',
    'See how GitHub Copilot Auto &amp; Fusion picks 1 fast model for easy edits, escalates hard bugs via Judge/Critics, and protects warm caches.':
        '简单修改只用一个模型；复杂问题再增加评审；连续追问尽量复用原会话缓存。',
    'Payoff vs. Naive Baseline': '与固定使用大模型相比',
    'Cost, latency &amp; safety': '成本、耗时与风险',
    'WITHOUT ROUTING': '固定方案',
    'WITH AUTO-ROUTING': '自动选择模型',
    'Pinned Baseline': '固定使用大模型',
    'Auto-Routed': '自动选择模型',
    'CODE DIFF &amp; REVIEW': '代码修改与评审',
    'API & SESSION INSPECTOR': '接口返回与多轮会话',
    'SMART INBOX & GUARDRAILS': '客服消息分流与发送前检查',
    '… Routing &amp; verifying telemetry': '… 正在执行并核对实际返回数据',
    'CALIBRATED ROUTING SIGNALS': '各候选项的评分',
    'CUSTOM PROBE': '自定义输入',
    'AUDIENCE / CUSTOM INPUT': '现场输入',
    'Probe Routed ✓': '判断完成 ✓',
    'Router (~21ms)': '快速评分',
    'Crossed Band': '超出轻量模型适用范围',
    'Cheap models excluded': '不再选择轻量模型',
    'Primary': '主模型',
    'Deep reasoning tier': '进入深度推理',
    'Verifier': '复核模型',
    'Read-Only Critic': '只读审阅',
    'Audits edge cases': '检查边界情况',
    'Reasoning Demand': '推理难度',
    'Debugging / Formal': '调试与形式化推理',
    'Flash / Haiku Fit': '轻量模型匹配度',
    'Frontier + Critic Fit': '大模型加复核的匹配度',
    'Out of band': '不适合',
    'SELECTED': '已选择',
    'Selective Frontier Escalation': '只在难题上升级',
    'Hard Spec Escalated to Frontier + Critic Verification': '复杂需求升级到大模型，并增加独立复核',
    'Weak models burn minutes in retry loops on hard specs. The router reserves frontier reasoning + critique strictly for prompts like this.':
        '复杂需求如果交给能力不足的模型，往往会反复修改。这里直接升级到更强模型，并增加一次独立复核。',
    'Weak Model Loop': '轻量模型反复重试',
    'Retries & Bugs ✕': '多次返工，仍可能出错 ✕',
    'Fails subtle edge invariants': '容易漏掉隐藏的边界条件',
    'Frontier + Critic': '大模型 + 独立复核',
    'Verified First Pass': '一次完成并通过复核',
    'Right-sized for hard task': '只在难题上投入更多资源',
    'Escalated: Frontier ✓': '已升级到大模型 ✓',
    'Critic Verified ✓': '独立复核通过 ✓',
    'Zero Retry Loop ✓': '没有反复重试 ✓',
    'Pinned Opus 5.5': '固定使用 Opus 5.5',
    'Always Opus 5.5': '始终使用 Opus 5.5',
    'Pays frontier tokens on a 1-line config lookup': '读取一行配置也要支付大模型费用',
    'Blind Multi-Agent': '每次都调用多个模型',
    '2–3× Calls Always': '每次都要调用 2–3 个模型',
    'Wastes Judge/Critic tokens on routine fixes': '常规修改也产生额外评审费用',
    'Unreviewed Single Pass': '只改不查',
    'Race Risk / Full Opus': '可能漏掉并发问题，或一开始就用最贵模型',
    'Either skips concurrency review or pays full Opus up front': '要么没有独立检查，要么从一开始就支付最高档费用',
    'Single-Model Draft': '只用一个模型起草',
    'Zero-RPO Blind Spot ✕': '没有发现 RPO=0 的前提漏洞 ✕',
    'Conflates writer fencing with cross-region commit durability': '把防止重复写入误当成跨区域持久化',
    'Cold Mid-Turn Switch': '对话中途切换模型',
    '0% Cache · Full Price': '缓存失效 · 按全价重新处理',
    'Invalidates warm prefix & re-prefills full context': '原有缓存无法复用，需要重新读取全部上下文',
    'Manual Multi-SDK': '业务代码分别适配多个 SDK',
    '400 Param Errors ✕': '容易遇到参数不兼容和 400 错误 ✕',
    'Breaks on role/temperature differences across labs': '不同厂商对 role、temperature 的支持并不一致',
    'Pinned Frontier': '固定使用高成本大模型',
    '~25× Token Cost': 'Token 费用约高 25 倍',
    'Burns frontier reasoning tokens on simple JSON': '简单字段提取也会消耗高价推理 Token',
    'Pinned Cheap Flash': '固定使用轻量模型',
    'Missed ABA Invariant ✕': '可能漏掉 ABA 等并发约束 ✕',
    'Under-powered on formal memory-ordering proofs': '不足以稳定完成内存序等形式化推导',
    'Monolithic Frontier Call': '整个流程只调用一次大模型',
    'High Cost on Raw Docs': '原始材料全部进入高价模型',
    'Feeds raw unstructured JSON straight to top tier': '未经整理的数据直接占用高价模型上下文',
    'Generative LLM Judge': '用生成式大模型做判断',
    '340× pricier + non-deterministic prose': '费用高约 340 倍，输出还可能波动',
    'All-Frontier Inbox': '所有消息都交给大模型',
    'Wastes frontier LLM calls on "Thanks!" & "STOP"': '“谢谢”和“退订”也要调用高成本大模型',
    'Unchecked Auto-Bot': '机器人直接自动回复',
    'Liability Risk ✕': '受伤投诉处理不当的风险 ✕',
    'Sends generic AI troubleshooting to injury report': '面对受伤投诉仍发送普通排障话术',
    '100% Human Review': '所有草稿都人工审核',
    '$0.24 / msg labor': '人工审核约 $0.24/条',
    'Reviewing every AI draft manually kills ROI': '逐条人工检查会抵消自动化带来的收益',
    'Direct Frontier Call': '直接调用大模型',
    'Hallucinated Terms ✕': '可能编造缺失条款 ✕',
    'Guesses missing Exhibit B clauses confidently': '附件没提供时仍可能给出看似确定的结论',
    '4 Live Messages': '4 条客户消息',
    'p = 1.00 Confidence': '每条结果概率接近 1.00',
    '~338 ms per HTTP call': '每次 HTTP 调用约 338 ms',
    '3/4 Short-Circuit': '3/4 不调用高成本大模型',
    'Zero frontier LLM spend': '这三条没有大模型费用',
    '1/4 Complex Only': '只有 1/4 需要升级',
    'Multi-line warranty compare': '跨产品、跨地区的质保条款对比',
    'LLM Draft Reply': 'AI 生成的回复草稿',
    'Rival "Fabrikam"': '提到了竞品 Fabrikam',
    'Recommends $749 rival sofa': '向客户推荐 $749 的竞品沙发',
    'Live noul Gate': '发送前 noul 检查',
    'Safe Action': '系统处理',
    'HELD Before Send': '发送前暂停',
    'Evaluated in 341 ms': '341 ms 完成检查',
    'Draft HELD ✓': '草稿已暂停 ✓',
    'Rival: ': '竞品提及概率：',
    'Latency: ': '耗时：',
    'Missing File Caught ✓': '发现缺少附件 ✓',
    'Zero Frontier Waste ✓': '未调用高成本大模型 ✓',
    'Attached State': '当前已上传材料',
    'Contract A Only': '只有主合同 A',
    'Exhibit B missing!': '缺少附件 B',
    'Abstain & Ask User': '先向用户索取缺失材料',
    'Zero frontier hallucination': '避免在材料不全时猜测',
    'DEMO 1 · CODING AGENT': '演示 1 · 编程 Agent',
    'DEMO 3 · APP CONTROLLER': '演示 3 · 业务流程判断',
    'Fast Single pass on easy code, Judge/Critic teams on hard bugs, and warm-cache retention.':
        '简单修改只用一个模型；复杂问题增加独立评审；连续追问尽量复用原会话缓存。',
    'Replace slow LLM router prompts with 180 ms calibrated choice, score & noul gates ($0.042/1M).':
        '用快速的 choice、score 和 noul 判断替代生成式大模型提示词，每百万输入 Token 费用为 $0.042。',
    '~0.45 AIU · Heavy': '约 0.45 AIU · 高成本',
    '0.055 AIU · Single': '0.055 AIU · Single 单模型',
    'pattern: single · 3/3 PASS': 'pattern: single · 3/3 测试通过',
    '1 CLI call · 0 review calls': '1 次 CLI 调用 · 0 次额外评审',
    'Native Cascade · 2.651 cr': '修复并检查 · 2.651 AIU',
    '1 CLI call · Opus repair skipped': '1 次 CLI 调用 · 跳过 Opus 修复',
    'Native Critique · 3 phases': '原生 Critique · 3 个阶段',
    '1 CLI call · Cross-lab review': '1 次 CLI 调用 · 跨模型审阅',
    'GPT-6 Luna (Warm)': 'GPT-6 Luna（沿用原会话）',
    '99% Hit · 0.024 AIU': '99% 缓存命中 · 0.024 AIU',
    '5,655 cached tok · 1 CLI call': '复用 5,655 个 Token · 1 次 CLI 调用',
    '3 · Repair (Cond.)': '3 · 修复（按需）',
    'SKIPPED (phaseCount=2)': '已跳过（实际执行 2 个阶段）',
    'DRAFT ·': '初稿 ·',
    'CRITIC ·': '审阅 ·',
    'REVISION ·': '修订 ·',
    'Handoff Revision': '根据审阅意见修订',
    'Applies Critic JSON via session.fusion_handoff while reusing warm prompt cache.':
        '通过 session.fusion_handoff 把审阅意见交回主模型，并继续复用原有上下文缓存。',
    'PROMPT PREFIX CACHE RETENTION (': '前缀缓存复用（',
    'cacheReadTokens: 5,655 warm (98.6%)': 'cacheReadTokens：5,655（98.6% 来自缓存）',
    'Cost: 0.024 AIU (vs ~0.45 cold)': '费用：0.024 AIU（重新读取全部上下文约 0.45 AIU）',
    '30 ms Router · 200 OK': '路由 30 ms · HTTP 200',
    'JSON mode & params normalized': 'JSON 输出与跨厂商参数适配完成',
    '27 ms Router · 0 Reason': '路由 27 ms · 0 推理 Token',
    'Valid JSON · HTTP 200 OK': 'JSON 格式正确 · HTTP 200',
    '30 ms · Affinity: retain': '路由 30 ms · 第 2 轮沿用原模型',
    '2-turn live escalation + cache affinity': '两轮真实调用 · 保持原模型与缓存',
    '28 ms + 29 ms Route': '两次路由分别为 28 ms 和 29 ms',
    'Multi-Job Cost + Quality': '提取阶段省成本，分析阶段保质量',
    '<strong>Turn 1:</strong> Design a lock-free MPMC ring buffer in Rust with Acquire/Release &amp; ABA epoch invariants.':
        '<strong>第 1 轮：</strong>设计 Rust 无锁 MPMC 环形队列，并说明 Acquire/Release 和 ABA 约束。',
    'Flash drops below 1–2% band → Router escalates in ':
        '轻量模型不再满足 1–2% 的效果要求，路由耗时 ',
    " ms to '+escHtml": " ms，升级到 '+escHtml",
    '<strong>Turn 2 Follow-up:</strong> Add a 3-bullet check for wrap-around index overflow when <code>head - tail == capacity</code>.':
        '<strong>第 2 轮追问：</strong>补充 3 点说明，检查 <code>head - tail == capacity</code> 时的下标回绕问题。',
    'Adaptive session_affinity hashes conversation prefix to avoid mid-thread model thrashing':
        '系统根据对话内容识别连续会话，避免追问时无意义地切换模型',
    'derived_fingerprint matched → session_affinity.decision = "':
        '识别为同一段对话 → session_affinity.decision = "',
    '" (KV cache preserved)': '"（继续复用模型缓存）',
    'AFFINITY: RETAIN ✓': '继续使用原模型：RETAIN ✓',
    'JOB 1 · mode = "cost" (': '任务 1 · mode = "cost"（',
    'JOB 2 · mode = "quality" (': '任务 2 · mode = "quality"（',
    '0.0 pt spread · 353 ms': '5 次结果无波动 · 中位耗时 353 ms',
    '5/5 live HTTP · $0 output fee': '5/5 真实 HTTP 调用 · 输出 Token 免费',
    'Purchase Timeline': '给出了明确购买时间',
    '"before the 20th"': '“希望 20 号前送到”',
    '5× Live /systemone': '连续 5 次 /systemone',
    '0.00 pt spread · p50 353 ms': '结果无波动 · 中位耗时 353 ms',
    '54 in tok · $0 out charge': '54 个输入 Token · 输出 Token 免费',
    'Spread: 0.0 pt ✓': '5 次结果无波动 ✓',
    'p50: 353 ms ✓': '中位耗时：353 ms ✓',
    '5/5 Live HTTP ✓': '5/5 真实 HTTP 调用 ✓',
    '"Is the Harbor sectional still 15% off? We’d love it before my in-laws visit on the 20th."':
        '“Harbor 转角沙发现在还有 15% 折扣吗？家人 20 号要来，希望能在那之前送到。”',
    'Question: <code>ready_to_buy (type: "noul")</code> — Does customer show concrete purchase timeline &amp; buying intent?':
        '判断项：<code>ready_to_buy（type: "noul"）</code>——客户是否给出了明确购买时间并表现出购买意愿？',
    'RUN #': '第 ',
    'PENDING': '待运行',
    'choice · 3/4 skip Frontier': 'choice · 3/4 无需大模型',
    '4/4 Routed (p=1.00)': '4/4 分流完成（p=1.00）',
    'Live /v1/systemone · $0 out tok': '真实 /v1/systemone 调用 · 输出 Token 免费',
    "'ready'": "'待运行'",
    "val:done?'p = 0.998':'pending'": "val:done?'p = 0.998':'待运行'",
    "val:done?(scVal.toFixed(2)+' / 3.0'):'pending'":
        "val:done?(scVal.toFixed(2)+' / 3.0'):'待运行'",
    "val:done?'noul = 0.998':'pending'": "val:done?'noul = 0.998':'待运行'",
    "val:done?'0.9999 · SELECTED':'pending'": "val:done?'0.9999 · 已选择':'待运行'",
    "val:done?'0.0001':'pending'": "val:done?'0.0001':'待运行'",
    "val:done?'0.0000':'pending'": "val:done?'0.0000':'待运行'",
    'Thanks! 👍': '谢谢！👍',
    'Please unsubscribe me / STOP': '请帮我退订 / STOP',
    'Is the 15% spring promo valid on the Aspen king frame?':
        'Aspen 特大床架还能使用春季 15% 折扣吗？',
    'Compare the 10-year structural warranty on Harbor vs CloudSlope if we move overseas.':
        '如果我们搬到海外，Harbor 和 CloudSlope 的十年结构质保有什么区别？',
    '3 Answers in 348 ms': '348 ms 返回 3 项结果',
    'Bot blocked · human paged': '自动回复已停用 · 已通知人工专员',
    'Single /v1/systemone call evaluates 3 typed questions simultaneously':
        '一次 /v1/systemone 调用同时判断负责团队、紧急程度和是否重复投诉',
    '"The bed frame collapsed last night and my husband hurt his back. This is the third time I’m writing in!"':
        '“昨晚床架塌了，我丈夫伤到了背。这已经是我第三次来反馈！”',
    'team: safety_support': '负责团队：safety_support',
    'priority (0..3 score)': '紧急程度（0–3 分）',
    'repeat_complaint': '是否重复投诉',
    '341 ms Pre-Send Gate': '发送前检查耗时 341 ms',
    'Blocked rival leak · 8% review rate': '拦下竞品推荐 · 仅风险草稿转人工',
    'threshold 0.50': '阈值 0.50',
    '"Honestly, ': '“说实话，',
    'Fabrikam has a similar sofa for $749': 'Fabrikam 有一款类似沙发，只要 $749',
    '. Here’s the link."': '。这是链接。”',
    'Abstain · Ask User': '先请用户补充材料',
    'Missing file caught · 7.2× CAC stack': '发现缺少附件 · 不调用大模型猜测',
    'Ask user for Exhibit B': '请用户补充附件 B',
    '"Compare the renewal termination notice window in Contract A vs Exhibit B."':
        '“请对比主合同 A 和附件 B 里的续约终止通知期限。”',
    'READY · CLICK RUN ▶': '待运行 · 点击“运行” ▶',
    'IN PROGRESS': '正在运行',
    'VERIFIED ✓': '实际结果已核对 ✓',
    'GUARDRAIL TRIGGERED': '已暂停发送',
    'Pattern: single ✓': '模式：single ✓',
    '3/3 Tests PASS ✓': '3/3 测试通过 ✓',
    'Pattern: cascade ✓': '模式：cascade ✓',
    'Judge: ACCEPT (5/5) ✓': '评审：5/5 通过 ✓',
    '500× Stress PASS ✓': '500 次并发测试通过 ✓',
    'Pattern: critique ✓': '模式：critique ✓',
    'Critic: revise ✕': '审阅结果：需要修订 ✕',
    'Phases: 3 run ✓': '3 个阶段均已执行 ✓',
    'Cache Hit: 99% ✓': '缓存命中：99% ✓',
    'Model Retained ✓': '继续使用原模型 ✓',
    'JSON Mode ✓': 'JSON 输出 ✓',
    'Params Normalized ✓': '参数适配完成 ✓',
    'JSON Valid ✓': 'JSON 格式正确 ✓',
    '0 Reason Tok ✓': '0 推理 Token ✓',
    'Affinity: retain ✓': '第 2 轮沿用原模型 ✓',
    '2-Turn Live ✓': '两轮真实调用 ✓',
    'Job 1: grok-4-1-fast ✓': '任务 1：grok-4-1-fast ✓',
    'Job 2: gpt-5.6-terra ✓': '任务 2：gpt-5.6-terra ✓',
    'Live Multi-Job ✓': '两阶段真实调用 ✓',
    '4/4 Routed Live ✓': '4/4 真实分流完成 ✓',
    'Skipped LLM: 3/4 ✓': '3/4 无需调用大模型 ✓',
    '$0 Output Tokens ✓': '输出 Token 费用 $0 ✓',
    'Team: safety_support ✓': '负责团队：safety_support ✓',
    'Human Escalated ✕': '已转人工专员 ✕',
    'Repeat: 1.00 ✓': '重复投诉概率：1.00 ✓',
    'Draft HELD ✓': '草稿已暂停发送 ✓',
    'Cost: $0.00004 ✓': '费用：$0.00004 ✓',
    'Team: safety ✓': '负责团队：安全支持 ✓',
    'Priority: P3 ✕': '紧急程度：P3 ✕',
    'Bot Bypassed ✓': '已停用自动回复 ✓',
    'Choice: 0.97 ✓': '分流概率：0.97 ✓',
    'LLM Cost: $0 ✓': '大模型费用：$0 ✓',
    'Savings: -99.9% ✓': '费用节省 99.9% ✓',
    'Handoff: Cowork ✓': '已转到 Cowork ✓',
    '3 Labs Used ✓': '调用 3 类专用模型 ✓',
    'Cost: -68% ✓': '费用节省 68% ✓',
    'Router: 22 ms ✓': '路由耗时：22 ms ✓',
    'Cost: -92% ✓': '费用节省 92% ✓',
    'Speed: 4× faster ✓': '速度提升 4 倍 ✓',
    '$0.15 / message': '$0.15 / 条',
    'Incoming EU Invoice: Simple 2-field JSON extraction under mode="balanced"':
        '收到一张欧洲客户账单，只需提取两个 JSON 字段（mode="balanced"）',
    'Same /chat/completions endpoint now receives a 2-turn Rust lock-free concurrency proof':
        '同一个 /chat/completions 接口，接着处理两轮 Rust 无锁并发问题',
    'Enterprise Account Workflow on demo/fixtures/renewal-context.json (Northwind Logistics · $432K ARR)':
        '企业续约分析：Northwind Logistics，当前 ARR 为 $432K',
    'Customer Sales Message: Testing 5 consecutive /v1/systemone calls for probability drift':
        '客户售前消息：连续调用 5 次 /v1/systemone，检查结果是否稳定',
    'Smart Support Inbox: 4 incoming customer messages waiting for tier assignment':
        '客服收件箱：先判断 4 条消息该由业务代码、小模型还是大模型处理',
    'Urgent Inbound Ticket: Evaluating team + priority[0..3] + repeat_complaint in 1 HTTP call':
        '紧急投诉：一次 HTTP 调用同时判断负责团队、紧急程度和是否重复投诉',
    'Screening AI-generated outbound reply before customer delivery (threshold ≥ 0.50)':
        'AI 回复发给客户之前，先检查是否提到竞品或承诺未批准的折扣（阈值 ≥ 0.50）',
    'Legal Comparison Request: Checking attached_documents completeness before Frontier call':
        '合同对比请求：先确认引用的附件是否都已上传，再决定是否调用大模型',
})

# Demo 2 采用更适合现场讲解的中文：先说发生了什么，再保留技术字段供核对。
ZH_TEXT_MAP.update({
    'Foundry Model Router live': 'Foundry Model Router：自动选模型',
    '✓  Pre-rank gate & param normalization': '✓  一套请求参数，Foundry 自动处理模型差异',
    'One V1Preview endpoint normalizes cross-provider params and serves valid JSON in 30 ms router overhead.':
        '业务代码只发一套请求；Foundry 会先排除不支持 JSON 的模型，再把参数调整成目标模型能接受的格式，30 ms 后返回正确结果。',
    '⚡  27–30 ms ML routing & retain affinity': '⚡  简单任务用轻量模型，难题自动升级',
    'DeepSeek-V4.1-Flash (JSON) vs. gpt-6-luna (Rust)':
        '发票字段提取用 DeepSeek Flash；Rust 并发推导改用 gpt-6-luna',
    'Routes simple JSON to Flash (0 reason tok) and escalates Rust proofs to Luna with retain affinity on Turn 2.':
        '接口和配置都不变：简单提取选便宜快速的 Flash；复杂并发推导升级到 Luna，第二轮追问继续沿用同一模型。',
    '⇄  Two-stage cost → quality routing': '⇄  一个流程拆成两步：整理数据省成本，制定方案保质量',
    'grok-4-1-fast (cost) → gpt-5.6-terra (quality)':
        'grok-4-1-fast 整理数据 → gpt-5.6-terra 制定方案',
    'Splits renewal analysis into two live calls: cheap extraction in cost mode followed by strategy in quality mode.':
        '先让低成本模型从原始材料中整理关键数字，再把精简后的结果交给更强模型制定续约方案。',
})

ZH_DEMO_TEXT_MAP.update({
    'One /chat/completions endpoint: param normalization, cheap Flash on easy JSON, auto-escalation, and cost→quality sub-jobs.':
        '业务代码只调用一个 /chat/completions 接口：简单任务选轻量模型，任务变难自动升级，连续追问尽量沿用原模型。',

    'Eligibility Gate & Cross-Provider Param Normalization':
        '一套请求参数，Foundry 自动处理模型差异',
    'Pre-Rank + Param Adapt': '先排除不兼容模型，再处理参数差异',
    'Foundry filters deployments by required capabilities (tools / json_object) before ranking, adapts cross-provider parameters automatically, and drains pre-paid PTU capacity first.':
        '业务代码不必分别适配各家模型。Foundry 先排除不支持 JSON 输出的模型，再把 role、temperature 等参数调整成目标模型能接受的格式。',
    'Manual Multi-SDK': '业务代码分别适配每家模型',
    '400 Param Errors ✕': '参数不兼容，容易返回 400 ✕',
    'Breaks on role/temperature differences across labs':
        '不同模型对 role 和 temperature 的支持方式并不一样',
    'JSON mode & params normalized': '30 ms 完成选模和参数转换',
    'Sending OpenAI-style developer role + json_object + temperature=0.2 to Foundry model="auto"':
        '向 model="auto" 发送常见的 OpenAI 格式请求',
    'UNIFIED REQUEST PAYLOAD': '业务代码发出的请求',
    'PRE-RANK CAPABILITY GATE &amp; RESPONSE': 'Foundry 会先做三件事',
    '1. Filtered out pool models lacking strict <code>json_object</code><br>2. Normalized <code>role="developer"</code> &amp; <code>temperature</code><br>3. Ranked eligible pool in <strong>':
        '1. 只保留支持 <code>json_object</code> 的模型<br>2. 把 <code>developer</code> 角色和采样参数转换成目标模型支持的格式<br>3. 在可用模型中完成选择，耗时 <strong>',
    '1 · Request Gate': '1 · 检查请求要求',
    'json_object + temp': '需要 JSON 输出和 temperature',
    'developer role normalized': '自动处理 developer 角色',
    '2 · ML Router': '2 · 从可用模型中选择',
    '30 ms Overhead': '耗时 30 ms',
    'mode: "balanced"': '使用 balanced 模式',
    '3 · Selected Model': '3 · 实际调用的模型',

    'Simple JSON Extraction Routed to DeepSeek Flash in 27 ms':
        '只提取两个字段，自动选择便宜的 DeepSeek Flash',
    '1–2% Balanced Band': '简单任务不必使用高成本大模型',
    'For straightforward JSON extraction, DeepSeek-V4.1-Flash scores within 1–2% of frontier quality — so Balanced mode selects it automatically at a fraction of frontier cost.':
        '这里只是从发票里提取编号和币种。Flash 的效果已经足够，因此 Balanced 模式会自动选它，既快又省。',
    'Pinned Frontier': '固定使用高成本大模型',
    '~25× Token Cost': 'Token 费用约高 25 倍',
    'Burns frontier reasoning tokens on simple JSON': '提取两个字段也要支付大模型推理费用',
    '27 ms Router · 0 Reason': '27 ms 选定模型 · 0 推理 Token',
    'Incoming EU Invoice: Simple 2-field JSON extraction under mode="balanced"':
        '收到一张账单，只需要提取发票编号和币种',
    'INCOMING DOCUMENT': '原始账单',
    'Northwind EU Invoice Text': 'Northwind 发票内容',
    'STRUCTURED EXTRACTION CARD': '提取结果',
    '1–2% BALANCED QUALITY BAND': '为什么选择 Flash',
    '~96% CHEAPER THAN FRONTIER': '费用比固定大模型低约 96%',
    'Because Flash scores within 1–2% of the #1 frontier model on structured field extraction, Balanced mode picks Flash automatically without burning reasoning tokens.':
        '在字段提取这类任务上，Flash 与最高分模型的预测效果只差 1–2%，没必要为大模型支付更高费用。',
    'ML Ranker': '快速选模',
    'Top 1–2% quality band': '效果已经足够接近最高分',
    'reasoning_tokens = 0': '推理 Token = 0',
    'Valid 200 OK': '返回正确结果',

    'Same Endpoint Escalates Rust Proof & Retains Session':
        '任务变难时自动升级，追问时继续使用原模型',
    'Difficulty Escalation + Affinity': '难题自动升级，连续对话不乱换模型',
    'Without changing endpoint or code, formal concurrency proofs trigger automatic escalation to gpt-6-luna, and Turn 2 retains the same model via derived_fingerprint.':
        '接口和配置都没有改变。任务从字段提取变成 Rust 并发推导后，系统自动升级到 gpt-6-luna；第二轮追问继续使用它，避免重新建立上下文。',
    'Pinned Cheap Flash': '固定使用轻量模型',
    'Missed ABA Invariant ✕': '可能漏掉 ABA 等并发约束 ✕',
    'Under-powered on formal memory-ordering proofs': '复杂的内存序推导超出了轻量模型的能力',
    'Turn 1 Ranker': '第 1 轮判断任务难度',
    '30 ms Escalation': '30 ms 内升级模型',
    'Flash drops below band': '轻量模型不再满足要求',
    'Turn 2 Affinity': '第 2 轮继续使用原模型',
    'decision: "retain"': 'decision: "retain"',
    'derived_fingerprint matched': '识别为同一段对话',
    'Same /chat/completions endpoint now receives a 2-turn Rust lock-free concurrency proof':
        '同一个接口，接着处理两轮 Rust 无锁并发问题',
    'Flash drops below 1–2% band → Router escalates in ':
        '轻量模型已经不够用，路由耗时 ',
    'Adaptive session_affinity hashes conversation prefix to avoid mid-thread model thrashing':
        '系统识别出这是同一段对话，因此第二轮继续使用原模型，不重新读取全部上下文',
    'TURN 2 VERIFIED INVARIANTS': '第 2 轮补充的关键约束',

    'Two-Stage Routing: mode="cost" Extraction → mode="quality" Strategy':
        '把续约分析拆成两步：先省成本，再保质量',
    'Two-Stage Sub-Job Routing': '不同步骤使用不同档位',
    'Instead of running an entire multi-step workflow on one expensive model, each sub-job passes its own routing_config.mode ("cost" vs "quality") to the same Foundry endpoint.':
        '第一步只是整理数字，用低成本模式；第二步需要制定谈判方案，再切到质量优先。高价模型只处理真正复杂的部分。',
    'Monolithic Frontier Call': '整份材料直接交给大模型',
    'High Cost on Raw Docs': '原始材料全部占用高价模型上下文',
    'Feeds raw unstructured JSON straight to top tier': '连整理数据这一步也由大模型完成',
    'Multi-Job Cost + Quality': '整理数据省成本，制定方案保质量',
    'Enterprise Account Workflow on demo/fixtures/renewal-context.json (Northwind Logistics · $432K ARR)':
        '续约分析：Northwind Logistics，当前 ARR 为 $432K',
    'JOB 1 · mode="cost"': '第 1 步 · 低成本整理数据',
    '28 ms route · fast extraction': '28 ms 选定模型 · 提取关键数字',
    '2 Compact Bullets': '整理成两条摘要',
    'Trimmed context passed on': '只把关键数据交给下一步',
    'JOB 2 · mode="quality"': '第 2 步 · 高质量制定方案',
    '29 ms route · NRR strategy': '29 ms 选定模型 · 制定续约方案',
    'JOB 1 · mode = "cost" (': '第 1 步 · 低成本整理数据（',
    'JOB 2 · mode = "quality" (': '第 2 步 · 高质量制定方案（',
    'Extracts compact renewal facts from raw JSON at minimal token cost...':
        '从原始 JSON 中整理续约的关键数字...',
    'Synthesizes executive pricing & negotiation playbook from compact Stage 1 facts...':
        '根据精简后的数据制定报价和谈判方案...',

    'Router: 30 ms ✓': '选模耗时：30 ms ✓',
    'Router: 27 ms ✓': '选模耗时：27 ms ✓',
})

ZH_TEXT_MAP.update({
    'Copilot CLI Auto & Fusion live':
        'Copilot Auto 与 Fusion：按任务难度执行',
    'Auto → Single → Native Cascade → Native Critique → 99% Cache':
        '简单任务单模型 → 难题增加检查 → 方案先审后改 → 连续追问复用 99% 缓存',
    '✓  Auto & Fusion Single fast path': '✓  简单任务只用一个模型',
    'categoryScores ≤ 0.10 & pattern="single"':
        '四项任务难度都很低，因此选择 pattern="single"',
    'Even on Fusion High, simple lookups & routine patches run 1 solver with zero review calls (3/3 node --test).':
        '即使开启 Fusion High，读取配置和常规修改也只调用一个模型；不增加评审费用，并通过 3 项单元测试。',
    '↗  1-command native Cascade': '↗  并发难题：先修复，再独立检查',
    'gpt-6.1-sol → gpt-6-luna Judge → Opus skipped':
        'gpt-6.1-sol 修复 → gpt-6-luna 检查 → 无需调用 Opus 重做',
    'One CLI call fixes ABBA lock order; native Judge scores 5/5 (accept) & skips conditional Opus 5.5 repair.':
        '一条命令先修正两把锁的顺序，再由另一个模型检查；结果 5/5 通过，因此不再调用 Opus 重做。',
    '⇄  1-command Critique + 99% Cache': '⇄  架构方案先审后改，追问继续复用缓存',
    'Opus draft → Luna Critic → Opus revise':
        'Opus 写初稿 → Luna 找问题 → Opus 根据意见修订',
    'Native Critic flags Active-Active zero-RPO gap for Opus to revise; --resume hits 99% cacheReadTokens.':
        'Luna 指出双活方案并不能自动保证 RPO=0；Opus 补上跨区域同步方案。随后用 --resume 追问时，99% 的输入直接从缓存读取。',

    'Decision-1.1 agent controller':
        'Decision-1.1：先判断，再决定',
    '✓  Zero-spread routing (choice & noul)': '✓  同一个问题连续跑 5 次，结果没有波动',
    '5/5 identical 0.9835 · 4/4 inbox p=1.00':
        '5 次都返回 0.9835 · 4 条客服消息全部正确分流',
    '5 consecutive live calls return 0.00 pt spread; 3 of 4 routine inbox messages skip the frontier LLM.':
        '同一条消息连续调用 5 次，结果完全一致；4 条客服消息里有 3 条不用调用高成本大模型。',
    '!  3-in-1 safety triage (choice+score+noul)':
        '!  受伤投诉：一次请求完成分组、定级并转人工',
    'safety_support (0.998) + score 1.97 + repeat 1.00':
        '负责团队 safety_support (0.998) · 紧急程度 1.97 · 重复投诉 1.00',
    'One 348 ms call classifies injury risk, scores urgency & flags 3rd repeat contact — blocking bot reply.':
        '一次调用同时判断负责团队、紧急程度和是否重复投诉，并立即停用自动回复、转交人工专员。',
    '✕  Outbound guardrail & missing-doc abstain':
        '✕  不当回复发送前拦下，资料不全时先向用户询问',
    'Rival promo noul=0.970 & missing Exhibit B p=0.9999':
        '推荐竞品概率 0.970 · 缺少附件 B 的概率 0.9999',
    'Holds a draft recommending rival Fabrikam (0.970) and stops to ask when Exhibit B is missing from state.':
        '草稿里推荐了竞品 Fabrikam，因此发送前暂停；合同附件 B 没上传时，先请用户补充，不让模型猜。',
})

ZH_DEMO_TEXT_MAP.update({
    'warm-up + copilot --model auto --resume <sid> (2 real CLI calls on first run)':
        '预热 + copilot --model auto --resume <sid>（首次运行共 2 次真实 CLI 调用）',
    'warm-up + resumed follow-up': '预热调用 + resume 追问',
    '# Click Run Step 4 to create a warm session and verify the resumed cache hit...':
        '# 点击“运行步骤 4”，先建立缓存，再通过 --resume 验证命中率...',
    '99% cacheReadTokens hit!': '99% 的输入直接来自缓存',
    'Preserves 30m cache TTL ✓': '继续使用 30 分钟有效的缓存 ✓',
    'Delta: 0.024 cr ✓': '本轮增量：0.024 AIU ✓',
    'Fast Single pass on easy code, Judge/Critic teams on hard bugs, and warm-cache retention.':
        '简单任务只用一个模型；遇到难题再增加独立检查；连续追问继续使用原模型和缓存。',

    'Auto Fast Path: 1-Line Config Lookup': '简单任务只用一个模型：读取一行配置',
    'auto_v2 Fast Path': '任务很简单，直接走单模型',
    'One copilot --model auto call emits session.auto_mode_resolved with 4D categoryScores (all ≤ 0.10) and routes straight to GPT-6 Luna.':
        '这里只是读取端口号，不需要额外检查。Auto 判断任务很简单，直接交给 GPT-6 Luna，一次返回结果。',
    'Pays frontier tokens on a 1-line config lookup': '读取一行配置也要支付高成本模型费用',
    '1 CLI call · auto_v2 fast path': '1 次 CLI 调用 · 没有额外评审',
    'auto_mode_resolved': 'Auto 判断任务难度',
    'categoryScores ≤ 0.10': '四项任务难度都很低',
    'reason=0.100 · debug=0.002': '推理 0.100 · 调试 0.002',
    'Chosen Model': '实际调用的模型',
    'Judge / Critic': '额外检查',
    'Bypassed': '无需调用',
    '$0 review overhead': '没有额外评审费用',
    'Inspecting demo/fixtures/config.ts — Click Run Step 1 to route via Copilot Auto':
        '读取 demo/fixtures/config.ts 中的默认端口；点击“运行步骤 1”查看 Auto 会选择哪个模型',
    'Read-Only Lookup': '只读取配置，不修改文件',
    '4D CAPABILITY DEMAND (≤ 0.10 FAST PATH)': '系统判断这项任务有多难（四项都很低）',
    'VERIFIED CLI OUTPUT': '实际返回结果',
    'EXPECTED CLI OUTPUT': '运行后会在这里显示结果',
    'Waiting for copilot --model auto...': '等待执行 copilot --model auto...',
    '0 Judge Overhead': '没有额外检查',
    '5,655 Cache Write': '同时写入 5,655 个缓存 Token',

    'Fusion High: Picks pattern="single" on Routine Patch':
        '常规修改：Fusion High 也只用一个模型',
    'Fusion Single Pattern': '一个模型已经足够',
    'Even on Fusion High, Copilot Fusion checks 4D capability scores first and picks pattern="single" (phasePlan: []) when 1 solver is sufficient.':
        '虽然开启了 Fusion High，但这项修改并不复杂。系统判断一个模型就够了，因此不会为了“多模型”而增加额外调用。',
    'Blind Multi-Agent': '不管难度，每次都调用多个模型',
    '2–3× Calls Always': '每次固定调用 2–3 个模型',
    'Wastes Judge/Critic tokens on routine fixes': '常规修改也要多付评审费用',
    'Fusion Orchestrator · pattern = "single"': 'Fusion 判断：一个模型就够了',
    'FUSION ORCHESTRATOR · PATTERN = "SINGLE"': 'Fusion 判断：一个模型就够了',
    'Even with --fusion-tier high enabled, capability demand stayed bounded (0.231), so Fusion skipped Judge/Critic calls and verified 3/3 unit tests in one pass.':
        '即使开启 --fusion-tier high，这项任务的难度也只有 0.231。Fusion 没有增加额外检查，一次修改就通过了 3 项测试。',
    'Fusion High will inspect 4D capability scores first before deciding whether multi-model review is worth paying for.':
        'Fusion High 会先判断任务难度；只有确实需要时，才会增加第二个模型检查。',
    'Judge Calls: 0': '额外检查：0 次',

    'Fusion High: Native pattern="cascade" (Solver + Judge)':
        '并发死锁：先修复，再由另一个模型检查',
    'Native 1-Call Cascade': '发现并发风险后增加独立检查',
    'One copilot --model fusion --fusion-tier high command orchestrates Solver (gpt-6.1-sol) + Judge (gpt-6-luna) server-side, skipping conditional Opus 5.5 repair when Judge returns verdict="accept".':
        '同一条命令先让 gpt-6.1-sol 修复加锁顺序，再让 gpt-6-luna 独立检查。检查通过后，不再调用 Opus 重做。',
    'Unreviewed Single Pass': '只修改，不检查',
    'Race Risk / Full Opus': '可能漏掉并发问题，或直接使用最贵模型',
    'Either skips concurrency review or pays full Opus up front':
        '要么没有独立检查，要么从一开始就支付最高档费用',
    '1 · Primary Solver': '1 · 先修复代码',
    '2 · Native Judge': '2 · 另一个模型检查',
    '3 · Repair (Cond.)': '3 · 有问题才重做',
    'DEADLOCK FIXED · 500/500 RACES PASS': '死锁已修复 · 500 次并发测试全部通过',
    'NATIVE JUDGE ANNOTATION · ': '独立检查结果 · ',
    'Native Cascade runs Primary Solver (gpt-6.1-sol) then cross-checks with Judge (gpt-6-luna), triggering claude-opus-5.5 repair ONLY if Judge rejects.':
        '先由 gpt-6.1-sol 修改，再由 gpt-6-luna 检查；只有检查不通过时，才会调用 claude-opus-5.5 重做。',
    '1 · Solver: ': '1 · 修改：',
    '2 · Judge: ACCEPT ✓': '2 · 检查通过 ✓',
    '3 · Repair (claude-opus-5.5):': '3 · 重做（claude-opus-5.5）：',

    'Fusion High: Native pattern="critique" (Draft → Critic → Revise)':
        '架构方案：一个模型起草，另一个模型专门找问题',
    'Native 1-Call Critique': '初稿 → 独立审阅 → 修订',
    'On high-stakes architecture prompts, one --model fusion --fusion-tier high call drafts on Opus 5.5, critiques on cross-family GPT-6 Luna, and hands off via session.fusion_handoff for a high-effort Opus 5.5 revision.':
        'Opus 5.5 先写初稿，GPT-6 Luna 专门找漏洞，再把意见交回 Opus 修订。整个过程仍然只需一条 Fusion 命令。',
    'Single-Model Draft': '只让一个模型从头写到尾',
    'Zero-RPO Blind Spot ✕': '没有发现 RPO=0 的前提漏洞 ✕',
    'Conflates writer fencing with cross-region commit durability':
        '把“避免重复写入”误当成“跨区域数据不会丢”',
    'Cross-Lab Audit': '换一个模型专门找问题',
    'Audits failure modes, quorum math, and RPO/RTO claims across model families.':
        '重点检查故障场景、多数派写入，以及 RPO/RTO 的结论是否成立。',
    'WHY CROSS-LAB CRITIQUE MATTERS': '为什么要换一个模型检查',
    'A single model rarely catches its own blind spot on distributed consensus vs. lease fencing — pairing Claude Opus 5.5 with GPT-6 Luna caught a real RPO=0 production flaw in one CLI command.':
        '一个模型很难发现自己的概念混淆。这里让 GPT-6 Luna 单独检查，找出了“防止重复写入并不等于跨区域数据零丢失”这个关键问题。',

    'Prefix-Cache Guard: 99% Cache Hit via --resume':
        '连续追问不换模型：99% 的输入直接复用缓存',
    'Warm Prefix Retention': '沿用原会话和原模型',
    'usage.json exposes exact cacheReadTokens and cacheExpiresAt. Keeping the session model on follow-up turns reuses 99% of prompt tokens instead of paying full prefill on a cold model.':
        '通过 --resume 继续原会话，5,655 个 Token 直接从缓存读取。这样不用换模型后重新处理全部上下文。',
    'Cold Mid-Turn Switch': '追问时切到另一个模型',
    '0% Cache · Full Price': '原缓存失效 · 全部重新读取',
    'Invalidates warm prefix & re-prefills full context':
        '新模型无法使用原缓存，需要重新处理全部上下文',
    'Resumed Session': '继续原会话',
    'Cold Model Switch': '切换到新模型',
    'Avoided': '没有发生',
    'Retained Model': '继续使用原模型',
    'PROMPT PREFIX CACHE RETENTION (': '前缀缓存复用情况（',
    'New Turn Tokens: ': '本轮新增加的 Token：',
    'Cost: 0.024 AIU (vs ~0.45 cold)':
        '本轮费用：0.024 AIU（重新读取全部上下文约 0.45 AIU）',

    'Replace slow LLM router prompts with 180 ms calibrated choice, score & noul gates ($0.042/1M).':
        '先用 choice、score 和 noul 做分流、定级和发送前检查；只有真正需要生成内容时才调用大模型。',
    '5× Live Repeat Probe: 0.9835 with 0.00 pt Spread':
        '同一个问题连续跑 5 次，结果都为 0.9835',
    'Calibrated System-One': '同一输入结果稳定',
    'Unlike generative LLM judges that drift across runs and bill for output prose, Decision-1.1 returns deterministic calibrated probabilities in a single forward pass.':
        '同一个问题连续运行 5 次都返回 0.9835。程序可以直接用这个数做判断，不必解析一段可能变化的生成式文字。',
    'Generative LLM Judge': '用生成式大模型做判断',
    '340× pricier + non-deterministic prose': '费用高约 340 倍，结果还可能变化',
    'Customer Sales Message: Testing 5 consecutive /v1/systemone calls for probability drift':
        '同一条购买咨询连续提交 5 次，检查结果会不会变化',
    'CALIBRATED SYSTEM-ONE PRIMITIVE': '为什么结果稳定',
    'Deterministic single forward-pass log-prob scoring: no sampling temperature drift, no JSON formatting retries, and $0 output token charges.':
        '一次前向计算直接返回概率，不受随机采样影响，也不用为了 JSON 格式反复重试；输出 Token 费用为 $0。',

    'Check 1 (choice): 4/4 Live Inbox Triage (3/4 Skip Frontier)':
        '4 条客户消息，3 条不需要调用大模型',
    'Pre-LLM Inbox Filter': '先把常规消息挡在大模型前面',
    'Spending ~$0.000013 on a calibrated choice check filters out acknowledgements, opt-outs, and simple FAQ lookups before they ever touch a $15/1M frontier LLM.':
        '“谢谢”、退订和简单促销咨询不需要大模型。先做一次低成本判断，只把真正复杂的问题交给高成本模型。',

    'Check 2 (choice + score + noul): Live Injury Triage & Escalation':
        '受伤投诉：一次请求完成分组、定级并转人工',
    '3-in-1 Multi-Question Call': '一次请求同时返回三项判断',
    'Packing choice, score, and noul into a single /v1/systemone request classifies the team, computes calibrated urgency, and flags repeat complaints in one round-trip.':
        '一次 /v1/systemone 请求同时返回负责团队、紧急程度和是否重复投诉，业务代码可以马上停用自动回复并通知人工专员。',

    'Check 3 (noul): Live Outbound Guardrail Blocks Rival Promo':
        '回复发出前，拦下推荐竞品的草稿',
    'Pre-Send Guardrail': '发送前再检查一次',
    'A $0.00006 pre-send noul check catches competitor promotions or unauthorized discounts automatically so clean drafts ship without 100% manual human review.':
        '发送前只检查是否提到竞品或承诺未批准的折扣。只有命中风险的草稿才转人工，不必逐条审核所有回复。',

    'Missing Document Caught: Abstains Instead of Hallucinating':
        '缺少附件时停下来问，不让模型猜',
    'Missing-Context Guard': '资料不全时先向用户询问',
    'Before calling an expensive frontier model to compare legal clauses, Decision-1.1 verifies all referenced exhibits exist in state — stopping to ask when one is missing.':
        '用户要求对比合同条款，但附件 B 没有上传。系统先请用户补充材料，不把不完整的内容交给大模型猜测。',

    'Smart Support Inbox: 4 incoming customer messages waiting for tier assignment':
        '客服收件箱：先判断 4 条消息该由业务代码、小模型还是大模型处理',
    'Urgent Inbound Ticket: Evaluating team + priority[0..3] + repeat_complaint in 1 HTTP call':
        '受伤投诉：一次请求同时判断负责团队、紧急程度和是否重复投诉',
    'Screening AI-generated outbound reply before customer delivery (threshold ≥ 0.50)':
        'AI 回复发给客户前，先检查是否提到竞品或承诺未批准的折扣',
    'Legal Comparison Request: Checking attached_documents completeness before Frontier call':
        '比较合同前先检查引用的附件是否都已上传',

    'Outbound Policy Gate': '发送前内容检查',
    'Competitor / Policy Leak Intercepted': '回复中推荐了竞品，发送前已拦下',
    'Decision-1.1 noul check caught a rival recommendation in 165 ms for $0.00004, holding the unsafe draft automatically.':
        'Decision-1.1 用 165 ms 发现草稿在推荐竞品，费用 $0.00004；系统在发送前暂停，并转人工确认。',
    'Unchecked Auto-Send': '未经检查直接发送',
    'Lost Lead ✕': '可能把客户推给竞品 ✕',
    'Sends customer to rival': '草稿会把客户引向竞品',
    'MD-1.1 noul Gate': 'Decision-1.1 发送前检查',
    '$0.00004 · HELD': '$0.00004 · 已暂停',
    '165 ms pre-send block': '165 ms 完成发送前检查',

    'Calibrated P0–P3 Score': 'P0–P3 紧急程度',
    'High-Severity Injury / Dispute Escalated to Human': '发现受伤或严重争议，立即转人工',
    'Combined choice + score call detects physical harm or severe dispute risk in one pass and skips autonomous bot replies.':
        '一次请求同时判断负责团队和紧急程度；发现人身伤害或严重争议后，立即停用自动回复并通知人工专员。',
    'Generic Chatbot': '普通自动回复机器人',
    'PR / Legal Risk ✕': '可能带来客诉或法律风险 ✕',
    'Tone-deaf automated reply': '对严重投诉仍发送普通话术',
    'P3 Human Specialist': 'P3 人工专员',
    '178 ms Escalation': '178 ms 完成人工升级',
    '$0.00003 triage check': '判断费用 $0.00003',

    'Zero-LLM Short-Circuit': '不调用大模型',
    'Trivial Turn Handled Without Burning LLM Credits': '“谢谢”和“退订”直接由业务代码处理',
    'Acknowledgements and opt-outs never need a $15/1M frontier model. Decision-1.1 routes them to deterministic code for $0.000013.':
        '感谢和退订不需要大模型。Decision-1.1 先判断消息类型，再交给业务代码处理，费用只有 $0.000013。',
    'Always Frontier': '所有消息都调用大模型',
    '$0.150 · 3.8 s': '$0.150 · 3.8 秒',
    '11,500× pricier overkill': '简单消息也支付高价模型费用',
    'Code Short-Circuit': '业务代码直接处理',
    '$0.000013 · 0.14 s': '$0.000013 · 0.14 秒',
    'Zero LLM tokens generated': '没有生成式大模型 Token',

    'Sub-Task Specialization': '按工作内容分工',
    'Multi-Modal Deliverable Split Across Specialist Models': '检索、写作和配图分别交给合适的模型',
    'Instead of forcing one model to search, write, and draw, Auto dispatches each sub-task to the lab that leads that capability.':
        '不让一个模型同时负责检索、写作和配图；Auto 把每一部分交给更合适的模型。',
    'Single General Model': '全部交给一个通用模型',
    'Slow · Weak Art': '检索慢，配图也弱',
    'Overpays on search & visuals': '检索和配图也支付高价模型费用',
    'SLM + Opus + Image': 'SLM + Opus + 图像模型',
    '-68% Cost · Best Fit': '费用降低 68% · 各做所长',
    '3 specialist models combined': '三类模型分工完成',

    '1–2% Quality Band Win': '效果接近时选择更便宜的模型',
    'Everyday Prompt Served Fast at 1/12th Frontier Cost': '常规请求用轻量模型快速完成',
    'When lightweight models score within 1–2% of frontier quality, Balanced routing picks the fast model automatically.':
        '当轻量模型与最高分模型的预测效果只差 1–2% 时，Balanced 会自动选择更快、更便宜的模型。',
    'Single Fast Pass · Balanced Band': '一次完成 · 轻量模型已经够用',
    'Always Frontier': '所有请求都用大模型',
    '$0.045 · 3.4 s': '$0.045 · 3.4 秒',
    '12× unnecessary spend': '多花约 12 倍费用',
    'Flash / Haiku 5.5': 'Flash / Haiku 5.5',
    '$0.003 · 0.8 s': '$0.003 · 0.8 秒',
    '22 ms router · Single pass': '22 ms 选模 · 一次完成',

    '✓ Blocked competitor promotion before customer saw it (mentions_competitor.noul = 0.964 ≥ 0.50)!':
        '✓ 发现草稿在推荐竞品，已在发送给客户前暂停（mentions_competitor.noul = 0.964 ≥ 0.50）',
    'Microsoft-Decision-1.1 Outbound Guardrail · 165 ms ($0.00004)':
        'Microsoft-Decision-1.1 · 165 ms 完成发送前检查（$0.00004）',
    'Draft Input': '待发送草稿',
    'Outbound Reply': 'AI 生成的客户回复',
    'Rival reference spotted': '发现竞品推荐',
    'MD-1.1 noul': 'Decision-1.1 检查',
    'Action': '系统处理',
    'Routed to human queue': '转到人工审核队列',
    'mentions_competitor (noul)': '是否提到竞品（noul）',
    'policy_violation': '是否需要暂停发送',
    'Auto-Send Allowed': '是否允许自动发送',

    '✓ Scored P3 Immediate Human (2.92 / 3.0) in 178 ms — bypassed generative bot and paged safety specialist!':
        '✓ 178 ms 内判断为 P3，需要立即人工处理（2.92 / 3.0）；已停用自动回复并通知安全专员',
    'Microsoft-Decision-1.1 Combined choice + score · 178 ms':
        'Microsoft-Decision-1.1 · 一次请求同时分组和定级（178 ms）',
    'Inbound Msg': '收到的客户消息',
    'High-Risk Signal': '发现受伤或严重争议信号',
    'Injury / legal / repeat': '受伤、法律风险或重复投诉',
    'MD-1.1 score': 'Decision-1.1 紧急程度',
    '178 ms single call': '一次调用耗时 178 ms',
    'Page Human P3': '立即通知 P3 人工专员',
    'Bot bypassed immediately': '自动回复已停用',
    'team: safety_support': '负责团队：safety_support',
    'priority (P0..P3 score)': '紧急程度（P0–P3）',
    'human_escalation (noul)': '是否需要立即转人工',
    'Bot Reply Permitted': '是否允许机器人回复',

    '✓ Short-circuited in 142 ms ($0.000013) — handled in deterministic code with $0 generative LLM cost!':
        '✓ 142 ms 内完成判断（$0.000013），随后由业务代码直接处理，大模型费用为 $0',
    'Microsoft-Decision-1.1 choice Router · 142 ms ($0.000013)':
        'Microsoft-Decision-1.1 · 142 ms 完成消息分流（$0.000013）',
    'Routine Ack / Opt-Out': '感谢或退订等常规消息',
    'Zero reasoning needed': '不需要生成式推理',
    'MD-1.1 choice': 'Decision-1.1 分流',
    'Execution': '后续处理',
    'Code Handler ($0)': '业务代码处理（$0）',
    '100% LLM skipped': '无需调用生成式大模型',
    'code_or_no_reply': '业务代码处理或无需回复',
    'LLM Tokens Spent': '生成式大模型 Token',
    '0 tokens ($0)': '0 Token（$0）',

    '✓ Split into 3 specialized sub-jobs: SLM retrieval + Claude Opus 5.5 narrative + GPT Image 2.5 visuals!':
        '✓ 将任务拆成三部分：SLM 查资料、Claude Opus 5.5 整理内容、GPT Image 2.5 生成配图',
    'Microsoft Copilot Auto · Experience Gate + Sub-Agent Router':
        'Microsoft Copilot Auto · 按工作内容拆分任务',
    '1 · Grounding': '1 · 查找相关资料',
    'Fast SLM': '快速 SLM',
    'Emails, Teams & files': '邮件、Teams 和文件',
    '2 · Reasoning': '2 · 整理分析内容',
    'Strategy & slide structure': '策略和幻灯片结构',
    '3 · Visuals': '3 · 生成配图',
    'Charts & hero graphics': '图表与主视觉',
    'Chat → Cowork Handoff': '是否转到 Cowork',
    'Work IQ Search (SLM)': 'Work IQ 检索（SLM）',
    'Narrative & Deck (Opus 5.5)': '内容与幻灯片（Opus 5.5）',
    'Visuals (GPT Image 2.5)': '配图（GPT Image 2.5）',
    'Assigned ✓': '已分配 ✓',

    '✓ Detected deep formal/concurrency complexity — escalated to Frontier reasoning + read-only Critic audit!':
        '✓ 发现任务包含复杂并发和形式化推导，已升级到更强模型，并增加一次只读复核',
    'HyDRA / Foundry Ranker · High Reasoning & Verification Demand':
        'HyDRA / Foundry · 任务需要较强推理和独立复核',
    'Router (~21ms)': '快速判断（约 21 ms）',
    'Crossed Band': '轻量模型不再够用',
    'Cheap models excluded': '不再选择轻量模型',
    'Primary': '主模型',
    'Deep reasoning tier': '使用深度推理',
    'Verifier': '复核模型',
    'Read-Only Critic': '只读复核',
    'Audits edge cases': '专门检查边界情况',
    'Reasoning Demand': '推理难度',
    'Debugging / Formal': '调试与形式化推导',
    'Flash / Haiku Fit': '轻量模型匹配度',
    'Frontier + Critic Fit': '强模型加复核的匹配度',
    '0.93 (High)': '0.93（高）',
    '0.88 (High)': '0.88（高）',
    '64% (Out of band)': '64%（不够用）',
    '97% · SELECTED': '97% · 已选择',

    '✓ Bounded task complexity — served in one fast pass on Flash/Haiku within 1% of frontier quality (-92% cost)!':
        '✓ 任务难度不高，使用轻量模型一次完成；预测效果与最高分只差约 1%，费用降低 92%',
    'Foundry / HyDRA Ranker · 22 ms Overhead (Within 1–2% Band)':
        'Foundry / HyDRA · 22 ms 完成判断（与最高分差距在 1–2% 以内）',
    '22 ms Check': '22 ms 完成判断',
    'Within 1–2% of #1': '与最高分差距在 1–2% 以内',
    'Fast single pass': '轻量模型一次完成',
    'Frontier Tier': '高成本大模型',
    'Saved!': '无需调用',
    '-92% token cost': 'Token 费用降低 92%',
    '98.8% fit · WINNER': '匹配度 98.8% · 已选择',
    '99.4% fit (20× cost)': '匹配度 99.4%（费用高约 20 倍）',
    '0.19 (Bounded)': '0.19（较低）',
    'Router Latency': '判断耗时',
})

# These short words also occur inside JavaScript identifiers such as
# EventSource, liveSource, and the Error constructor. Translate only the
# visible string/HTML forms so localization cannot break live execution.
ZH_DEMO_TEXT_MAP.pop('Source', None)
ZH_DEMO_TEXT_MAP.pop('Error', None)
ZH_DEMO_TEXT_MAP.update({
    '>Source<': '>来源<',
    "'Error'": "'错误'",
    '[Error]': '[错误]',
})

ZH_TEXT_MAP.update({
    'Workplace Auto': '办公场景',
    'Coding Orchestrator': '编程协作',
    'Cloud API Router': '云端接口',
    'Software Controller': '业务判断',
    'Routes >90% of queries: Chat → Cowork handoff, multi-provider selection, dynamic effort & sub-agents.':
        '超过 90% 的办公请求由 Auto 处理：判断留在 Chat 还是转到 Cowork，在企业允许的范围内选模型，并按任务调整投入。',
    'Matches each coding task to one model or a team: Single pass, Judge-gated Cascade, or parallel Critique.':
        '简单任务由一个模型完成；并发问题先修复再检查；架构方案先起草，再让另一个模型专门找问题。',
    '20 ms ML ranker across 45 models (7 providers): quality bands, cache affinity, param cleanup & PTU failover.':
        '约 20 ms 在可用模型中完成选择；简单任务优先低成本模型，多轮追问尽量沿用原模型，遇到限流自动切换。',
    'Purpose-built decision API that classifies, scores priority, and runs yes/no safety gates in ~123 ms at $0.042/1M.':
        '直接为业务代码返回分类、优先级和是非概率，典型耗时约 123 ms，每百万输入 Token 费用为 $0.042。',
})

ZH_TEXT_MAP.update({
    'Steps 1–2 · Easy work stays single-model': '步骤 1–2 · 简单任务都只用一个模型',
    'Auto: Luna 0.055 AIU · Fusion Single: Terra, 3/3 tests':
        'Auto：Luna 0.055 AIU · Fusion Single：Terra，3/3 测试通过',
    'Two separate one-command runs prove both Auto and Fusion High avoid extra review when one model is enough.':
        '前两步各运行一条命令：Auto 负责读取配置，Fusion High 负责常规修改；一个模型足够时都不会增加额外检查。',
    'Step 3 · Fix, then verify independently': '步骤 3 · 先修复并发死锁，再换一个模型检查',
    'gpt-6.1-sol fix → gpt-6-luna check → Opus skipped':
        'gpt-6.1-sol 修复 → gpt-6-luna 检查 → 无需调用 Opus 重做',
    'One command fixes ABBA lock order, Judge accepts 5/5, and all 500 stress runs pass.':
        '一条命令修正加锁顺序，独立检查结果为 5/5 通过，随后 500 次并发测试全部通过。',
    'Steps 4–5 · Review architecture, then reuse cache':
        '步骤 4–5 · 架构方案先审后改，连续追问继续复用缓存',
    'Opus draft → Luna finds RPO gap → Opus revises · 99% cache':
        'Opus 写初稿 → Luna 找出 RPO 漏洞 → Opus 修订 · 99% 缓存命中',
    'Critique catches missing cross-region durability; the resumed follow-up reads 5,655 / 5,733 tokens from cache.':
        '第 4 步发现跨区域持久化前提不足；第 5 步通过 --resume 继续追问，5,655 / 5,733 个 Token 直接从缓存读取。',

    '4 steps · 6 live Foundry requests (0 local mocks)':
        '4 个步骤 · 6 次真实 Foundry 云端请求（无本地模拟）',
    'Step 1 · One request format across providers':
        '步骤 1 · 一套请求参数，Foundry 自动处理模型差异',
    'developer + json_object → gpt-5.6-luna · 30 ms':
        'developer + json_object → gpt-5.6-luna · 30 ms',
    'Foundry removes incompatible candidates and adapts parameters before returning valid JSON.':
        'Foundry 先排除不兼容的模型，再把参数转换成目标模型支持的格式，最后返回正确 JSON。',
    'Steps 2–3 · Easy stays cheap; hard escalates':
        '步骤 2–3 · 简单任务用轻量模型，难题自动升级',
    'Invoice → DeepSeek Flash (27 ms, 0 reason) · Rust → Luna (30 ms, retain)':
        '发票提取 → DeepSeek Flash（27 ms，0 推理 Token）· Rust 推导 → Luna（30 ms，第二轮沿用）',
    'The endpoint and code stay unchanged; Turn 2 keeps Luna so the context does not need rebuilding.':
        '接口和业务代码都不变；Rust 任务变难后自动升级到 Luna，第二轮继续沿用，不必重建上下文。',
    'Step 4 · Split extraction from strategy':
        '步骤 4 · 把整理数据和制定方案拆成两次请求',
    'grok fast (cost) → 2 bullets → terra (quality)':
        'grok fast（cost）→ 两条摘要 → terra（quality）',
    'First organize the raw data cheaply, then use the stronger model only for renewal strategy.':
        '先用低成本模型整理原始材料，再只让更强模型处理续约策略。',

    '5 steps · 12 live /v1/systemone requests + custom probe':
        '5 个步骤 · 12 次真实 /v1/systemone 请求 + 自定义输入',
    'Steps 1–2 · Stable scores and inbox routing':
        '步骤 1–2 · 同一输入结果稳定，4 条消息先分流',
    '5× 0.9835 · 4 messages routed · 3 skip frontier':
        '连续 5 次都是 0.9835 · 4 条消息全部分流 · 3 条不用大模型',
    'Nine calls prove repeatability and filter routine messages before the generative LLM.':
        '前两步一共 9 次请求：5 次验证结果不波动，4 次把常规消息挡在大模型前面。',
    'Step 3 · One call returns team, urgency, and repeat':
        '步骤 3 · 一次请求同时返回负责团队、紧急程度和重复投诉',
    'safety_support 0.998 · score 1.97 · repeat 0.998':
        'safety_support 0.998 · 紧急程度 1.97 · 重复投诉 0.998',
    'The bot stops immediately and a human safety specialist is notified.':
        '业务代码立即停用自动回复，并通知人工安全专员。',
    'Steps 4–5 · Hold unsafe draft; ask for missing file':
        '步骤 4–5 · 拦下不当草稿，缺少附件时先询问',
    'competitor 0.970 · request_missing_exhibit 0.99994':
        '提及竞品 0.970 · 请求补充附件 0.99994',
    'Two more calls block the rival draft and prevent a made-up contract comparison.':
        '最后两次请求分别拦下推荐竞品的草稿，并在附件 B 缺失时停止对比，避免模型猜测。',
})

ZH_TEXT_MAP.update({
    'Step 1 · Routine patch stays single-model':
        '步骤 1 · 常规修改只用一个模型',
    'Fusion Single · gpt-6.1-terra · 3/3 tests':
        'Fusion Single · gpt-6.1-terra · 3/3 测试通过',
    'Fusion High still uses one model when the task is simple.':
        '即使开启 Fusion High，任务简单时仍不会增加额外检查。',
    'Step 2 · Fix, then verify independently':
        '步骤 2 · 先修复并发死锁，再换一个模型检查',
    'gpt-6.1-sol fix → gpt-6-luna check':
        'gpt-6.1-sol 修复 → gpt-6-luna 检查',
    'Judge accepts 5/5; Opus repair is skipped; 500 stress runs pass.':
        '检查结果为 5/5 通过，无需调用 Opus 重做；500 次并发测试全部通过。',
    'Step 3 · Draft, critique, revise':
        '步骤 3 · 一个模型起草，另一个模型找问题，再交回修订',
    'Opus draft → Luna finds RPO gap → Opus revises':
        'Opus 写初稿 → Luna 找出 RPO 漏洞 → Opus 修订',
    'The independent review catches missing cross-region durability.':
        '独立检查发现初稿没有真正解决跨区域数据持久化问题。',
    'Step 4 · Warm up, then resume':
        '步骤 4 · 先建立缓存，再用 --resume 追问',
    'Auto warm-up → --resume · 5,655 / 5,733 cached':
        'Auto 预热 → --resume · 5,655 / 5,733 个 Token 来自缓存',
    'Two real calls prove a 99% cache hit on the follow-up.':
        '两次真实调用证明：第二次追问的缓存命中率为 99%。',
})

ZH_TEXT_MAP.update({
    'Step 2 · Simple extraction stays on Flash':
        '步骤 2 · 简单提取直接使用 Flash',
    'Invoice → DeepSeek Flash · 27 ms · 0 reasoning tokens':
        '发票提取 → DeepSeek Flash · 27 ms · 0 推理 Token',
    'Balanced mode avoids paying for a larger model when Flash is already good enough.':
        'Flash 已经足够完成字段提取，Balanced 不会再为更大的模型付费。',
    'Step 3 · Hard Rust task escalates and retains':
        '步骤 3 · Rust 任务变难后自动升级，追问继续沿用',
    'Rust → gpt-6-luna · 30 ms · Turn 2 retain':
        'Rust 推导 → gpt-6-luna · 30 ms · 第 2 轮 retain',
    'The same endpoint upgrades for harder reasoning and keeps Luna for the follow-up.':
        '同一个接口在任务变难时升级到 Luna，第二轮追问继续使用原模型。',

    'Step 1 · Five repeats, zero probability drift':
        '步骤 1 · 同一输入连续调用 5 次，结果没有波动',
    '5× 0.9835 · 0.00-pt spread · p50 343 ms':
        '连续 5 次都是 0.9835 · 极差 0.00 · 中位耗时 343 ms',
    'Five real calls prove the same input returns the same score.':
        '5 次真实调用证明：相同输入会得到相同分数。',
    'Step 2 · Route four messages before the LLM':
        '步骤 2 · 4 条客服消息先分流，再决定是否调用大模型',
    '4 routed · 3 skip frontier · p≈1.00':
        '4 条全部分流 · 3 条不用大模型 · 概率约 1.00',
    'Four calls keep thanks, opt-outs, and FAQ traffic away from the expensive model.':
        '4 次调用把感谢、退订和简单咨询挡在高成本模型之前。',
    'Step 4 · Hold competitor draft before send':
        '步骤 4 · 回复发出前，拦下推荐竞品的草稿',
    'mentions_competitor 0.970 · 347 ms':
        '提及竞品 0.970 · 347 ms',
    'One call blocks the rival recommendation and sends it to human review.':
        '一次调用发现竞品推荐，在发送前暂停并转人工审核。',
    'Step 5 · Ask for the missing Exhibit B':
        '步骤 5 · 缺少附件 B，先请用户补充',
    'request_missing_exhibit 0.99994 · 347 ms':
        '请求补充附件 0.99994 · 347 ms',
    'One call stops the comparison instead of inventing missing contract terms.':
        '一次调用停止合同对比，避免模型编造缺失条款。',
})

# 第 22–24 页用于现场讲解，中文先说清结论，再保留模型名和指标。
ZH_TEXT_MAP.update({
    'Copilot CLI Auto & Fusion live':
        'Copilot CLI：四种执行场景',
    '4 scenarios · 5 real Copilot CLI calls':
        '4 个场景 · 5 次真实 CLI 调用（缓存场景含两次调用）',
    'Step 1 · Routine patch stays single-model':
        '场景 1 · 常规修改，一个模型就够了',
    'Fusion Single · gpt-6.1-terra · 3/3 tests':
        'Fusion Single · gpt-6.1-terra · 3 项测试全部通过',
    'Fusion High still uses one model when the task is simple.':
        '虽然选择了 Fusion High，但任务并不复杂，因此没有额外调用评审模型。',
    'Step 2 · Fix, then verify independently':
        '场景 2 · 并发问题改完后，再换一个模型检查',
    'gpt-6.1-sol fix → gpt-6-luna check':
        'gpt-6.1-sol 修复 → gpt-6-luna 独立检查',
    'Judge accepts 5/5; Opus repair is skipped; 500 stress runs pass.':
        '检查结果为 5/5 通过，因此不用 Opus 重做；500 次并发测试也全部通过。',
    'Step 3 · Draft, critique, revise':
        '场景 3 · 架构方案先写初稿，再找问题、再修订',
    'Opus draft → Luna finds RPO gap → Opus revises':
        'Opus 起草 → Luna 指出 RPO 漏洞 → Opus 修订',
    'The independent review catches missing cross-region durability.':
        'Luna 发现初稿只解决了写入冲突，却没有说明跨区域提交后如何保证数据不丢。',
    'Step 4 · Warm up, then resume':
        '场景 4 · 连续追问沿用原会话，直接复用缓存',
    'Auto warm-up → --resume · 5,655 / 5,733 cached':
        '先建立会话 → --resume 追问 · 5,655 / 5,733 个 Token 来自缓存',
    'Two real calls prove a 99% cache hit on the follow-up.':
        '这个场景有两次真实调用：第一次建立缓存，第二次追问的缓存命中率为 99%。',

    'Foundry Model Router live':
        'Foundry Router：自动选择模型',
    '4 steps · 6 live Foundry requests (0 local mocks)':
        '4 个场景 · 6 次真实 Foundry 请求（没有本地模拟）',
    'Step 1 · One request format across providers':
        '场景 1 · 业务代码只发一套参数，Foundry 负责适配',
    'developer + json_object → gpt-5.6-luna · 30 ms':
        'developer + json_object → gpt-5.6-luna · 选模耗时 30 ms',
    'Foundry removes incompatible candidates and adapts parameters before returning valid JSON.':
        'Foundry 先排除不支持 JSON 输出的模型，再处理各家模型的参数差异，最后返回正确 JSON。',
    'Step 2 · Simple extraction stays on Flash':
        '场景 2 · 只提取两个字段，用 Flash 就够了',
    'Invoice → DeepSeek Flash · 27 ms · 0 reasoning tokens':
        '发票字段提取 → DeepSeek Flash · 27 ms · 0 推理 Token',
    'Balanced mode avoids paying for a larger model when Flash is already good enough.':
        'Flash 已经能把发票编号和币种提取正确，没必要再调用成本更高的模型。',
    'Step 3 · Hard Rust task escalates and retains':
        '场景 3 · 任务变难就升级；继续追问不再换模型',
    'Rust → gpt-6-luna · 30 ms · Turn 2 retain':
        'Rust 并发推导 → gpt-6-luna · 30 ms · 第 2 轮继续沿用',
    'The same endpoint upgrades for harder reasoning and keeps Luna for the follow-up.':
        '接口和业务代码都没有改变；系统先升级到 Luna，第二轮追问继续使用它，避免重新建立上下文。',
    'Step 4 · Split extraction from strategy':
        '场景 4 · 先整理数据，再制定方案，两步分别选模型',
    'grok fast (cost) → 2 bullets → terra (quality)':
        'grok fast 整理数据 → 两条摘要 → terra 制定方案',
    'First organize the raw data cheaply, then use the stronger model only for renewal strategy.':
        '整理原始材料时用低成本模型；真正需要分析和制定续约策略时，才调用更强的模型。',

    'Decision-1.1 agent controller':
        'Decision-1.1：先判断，再处理',
    '5 steps · 12 live /v1/systemone requests + custom probe':
        '5 个场景 · 12 次真实 /v1/systemone 请求 · 支持现场输入',
    'Step 1 · Five repeats, zero probability drift':
        '场景 1 · 同一条消息连续判断 5 次，结果完全一致',
    '5× 0.9835 · 0.00-pt spread · p50 343 ms':
        '5 次都是 0.9835 · 没有波动 · 中位耗时 343 ms',
    'Five real calls prove the same input returns the same score.':
        '相同输入连续调用 5 次，返回的概率完全相同，程序可以放心按阈值处理。',
    'Step 2 · Route four messages before the LLM':
        '场景 2 · 先给 4 条客服消息分流，只把难题交给大模型',
    '4 routed · 3 skip frontier · p≈1.00':
        '4 条全部分流 · 3 条不用大模型 · 结果概率接近 1.00',
    'Four calls keep thanks, opt-outs, and FAQ traffic away from the expensive model.':
        '“谢谢”、退订和简单促销咨询都由更便宜的方式处理，只有复杂质保对比才调用大模型。',
    'Step 3 · One call returns team, urgency, and repeat':
        '场景 3 · 受伤投诉一次完成分组、定级和转人工',
    'safety_support 0.998 · score 1.97 · repeat 0.998':
        '负责团队 safety_support 0.998 · 紧急程度 1.97 · 重复投诉 0.998',
    'The bot stops immediately and a human safety specialist is notified.':
        '程序立即停用自动回复，并通知人工安全专员处理。',
    'Step 4 · Hold competitor draft before send':
        '场景 4 · 回复发送前，拦下推荐竞品的草稿',
    'mentions_competitor 0.970 · 347 ms':
        '提及竞品的概率 0.970 · 耗时 347 ms',
    'One call blocks the rival recommendation and sends it to human review.':
        '草稿命中竞品检查，因此不会自动发给客户，而是转交人工确认。',
    'Step 5 · Ask for the missing Exhibit B':
        '场景 5 · 缺少附件 B，就停下来请用户补充',
    'request_missing_exhibit 0.99994 · 347 ms':
        '请求补充附件的概率 0.99994 · 耗时 347 ms',
    'One call stops the comparison instead of inventing missing contract terms.':
        '材料不完整时不继续比较，也不让模型猜测缺失的合同条款。',
})
