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
        "cached prompt reads cost roughly 90% less and return much faster. Switching to a 'cheaper' model on Turn 5 invalidates that cache and forces a full-price re-prefill of 50,000 tokens, costing more time and money. "
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
        "Now let's open the interactive Demo Studio in the top-right corner and watch all three layers run for real. Demo 1 drives the native GitHub Copilot CLI across five steps—every single step is one native `copilot` command.\n"
        "Step 1 runs `--model auto` to read the default port from `config.ts`: all four demand scores land below 0.10, so it takes the fast single-model path to GPT-6 Luna for 0.055 credits and warms the session cache.\n"
        "Steps 2, 3, and 4 keep the exact same flag—`copilot --model fusion --fusion-tier high`—to show how the server switches patterns by task difficulty: "
        "on Step 2's whitespace fix, even on High tier, Fusion picks `single` on `gpt-6.1-terra` with zero review calls and passes 3/3 unit tests. "
        "On Step 3's ABBA lock-order deadlock, that single command expands into native `cascade`: `gpt-6.1-sol` fixes the lock order, `gpt-6-luna` Judge scores it 5/5 (`accept`), conditional Opus 5.5 repair is automatically skipped, and 500 concurrent stress runs pass. "
        "On Step 4's 50k-RPS payment failover RFC, one command runs 3-phase `critique`: Opus drafts, cross-lab Luna flags an Active-Active zero-RPO durability gap (`revise`), and Opus revises with nearly 8,000 cached tokens.\n"
        "Finally, Step 5 runs `--resume` for follow-up metrics, retaining warm Luna with a 99% `cacheReadTokens` hit for just 0.024 credits. Click `{ } Raw Log` anytime to inspect the verbatim CLI JSONL and `usage.json`."
    ),
    22: (
        "Demo 2 moves to the cloud API layer with Microsoft Foundry Model Router. All four steps hit the exact same `/openai/v1/chat/completions` endpoint with `model: \"auto\"` and `ModelRouterControls=V1Preview`.\n"
        "Step 1 tests pre-rank eligibility and cross-provider parameter cleanup—sending `developer` role, `temperature: 0.2`, and `json_object` together. Instead of tripping HTTP 400 mismatches across labs, Foundry normalizes the payload and routes to `gpt-5.6-luna` in 30 ms.\n"
        "Steps 2 and 3 send two starkly different tasks to the untouched `balanced` endpoint: Step 2 extracts invoice fields in 27 ms on cheap `DeepSeek-V4.1-Flash` with zero wasted reasoning tokens; "
        "Step 3 submits a formal Rust lock-free ring-buffer proof, automatically escalating in 30 ms to `gpt-6-luna`, and on Turn 2's short follow-up, message-fingerprint affinity returns `retain` so the warm model cache isn't broken.\n"
        "Step 4 splits account renewal into two sub-jobs on that same endpoint: `mode: \"cost\"` routes raw extraction to fast `grok-4-1-fast-reasoning` (28 ms), then `mode: \"quality\"` hands the compact bullets to flagship `gpt-5.6-terra` (29 ms) for game-theoretic NRR strategy. Switch to `{ } Raw Log` to inspect `routing_trace` directly."
    ),
    23: (
        "Demo 3 shows Microsoft-Decision-1.1 at `/providers/microsoft/v1/systemone` across five live cloud checks.\n"
        "Step 1 fires five consecutive `noul` calls on the same buyer message—returning `0.9835` all five times with `0.00` point spread in ~354 ms median latency and $0 output-token fee.\n"
        "Step 2 runs a pre-LLM `choice` inbox router across four customer messages ('Thanks!', 'STOP', promo lookup, and multi-line warranty comparison)—hitting ~1.00 confidence on all four so three out of four skip the frontier LLM.\n"
        "Step 3 packs `choice`, `score`, and `noul` into one 366 ms request on a collapsed-bed injury report—returning `safety_support` (0.998), urgency `1.97 / 3.0`, and `repeat = 0.998` to block the bot and page a human.\n"
        "Step 4 runs an outbound `noul` guardrail on an AI draft recommending rival 'Fabrikam for $749', scoring `0.970` in 347 ms and holding the draft before send.\n"
        "And Step 5 tests missing-evidence abstention: asked to compare Contract A against Exhibit B when Exhibit B isn't attached, it selects `request_missing_exhibit` at `0.9999` probability instead of hallucinating. Try typing any custom prompt into the bottom bar, or open `{ } Raw Log` to view the raw JSON."
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
    'Switching to a “cheaper” model on turn 5 invalidates the prefix cache and forces re-prefilling 50k+ tokens from scratch.': '如果在第 5 轮切换到另一个便宜模型，原有缓存就会失效，新模型需要按全价重新处理 5 万多个 Token。',
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
    'Copilot Auto &amp; Fusion · 5 steps': 'Copilot Auto 与 Fusion · 5 个步骤',
    'Foundry Model Router · 4 steps': 'Foundry Model Router · 4 个步骤',
    'Microsoft-Decision-1.1 · 5 steps': 'Microsoft-Decision-1.1 · 5 个步骤',
    'Run Step 1': '运行步骤 1',
    '>DEMO<': '>演示<',
    '>STEP<': '>步骤<',
    'Auto-Play': '自动播放',
    'Replay · Verified': '录制回放 · 已验证',
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
    'Routing flow': '路由流程',
    'ROUTING RULE / API CALL': '路由规则 / API 调用',
    'Chosen Model': '选中的模型',
    'Judge / Critic': '评审模型',
    'Bypassed': '未调用',
    'Primary Solver': '主模型',
    'Skipped when unwarranted': '任务简单时自动跳过',
    'Primary Draft': '主模型初稿',
    'Cross-Lab Critic': '跨厂商审校模型',
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
    'Cross-Lab Audit': '跨厂商交叉审校',
    'Audits failure modes, quorum math, and RPO/RTO claims across model families.': '使用另一家厂商的模型核查故障场景、多数派写入与 RPO/RTO 推导。',
    '3-Region Sync Quorum ✓': '三区域同步多数派提交 ✓',
    'Upgrades ledger storage to synchronous 3-region Raft quorum commit (Spanner / CockroachDB, 18–35 ms WAN budget) for true RPO = 0.': '将账本存储改为三区域同步 Raft 多数派提交（如 Spanner / CockroachDB，预留 18–35 ms 跨区延迟），真正满足 RPO = 0。',
    'WHY CROSS-LAB CRITIQUE MATTERS': '为什么需要跨厂商审校',
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
