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
    'INTELLIGENT MODEL SELECTION & DECISION SYSTEMS': '智能模型路由与决策系统',
    'Auto-routing\nLLMs': '大模型自动路由\nAuto-routing',
    'Routing every task to the right model for quality, cost and speed — from Microsoft Copilot and Foundry to Microsoft-Decision-1.1.': '为每项子任务自动匹配兼顾质量、成本与延迟的最佳模型 —— 从 Microsoft Copilot、Foundry 到 Microsoft-Decision-1.1。',
    'Yingting Huang  |  Sr. Cloud Solution Architect, Microsoft': '黄颖庭 (Yingting Huang)  |  微软高级云解决方案架构师',
    'SCAN FOR LIVE SLIDES & DEMO': '扫码打开在线课件与交互 Demo',
    'AGENDA': '议程 · AGENDA',
    'Our journey today': '今日分享脉络',
    'Capability gap': '能力专精分工',
    'No single model wins all': '没有全能单一模型',
    'Cost & cache': '成本与缓存铁律',
    '163× gap & prefix cache': '163× 价差与前缀缓存',
    'MS products': '微软产品实战',
    'Copilot, Fusion & Foundry': 'Copilot、Fusion 与 Foundry',
    'Under the hood': '底层路由架构',
    'Industry vs. MS HyDRA': '业界方案对比微软 HyDRA',
    'Decision-1.1': 'Decision-1.1',
    'Fast, calibrated control': '毫秒级校准决策控制',
    'Live demos': '三组真机实测',
    'Fusion, Foundry & Decision': 'Fusion、Foundry 与决策控制',
    'Takeaways': '总结与落地建议',
    'Ship your own router': '四步带回团队落地',

    # Slide 3 (idx 2)
    '01 · CAPABILITY SPECIALIZATION': '01 · 模型能力专精化',
    'No single model is best at everything': '没有哪个单一模型能包打天下',
    'PINNED MODEL': '固定单一模型',
    'Static single-model mindset': '全程绑死同一个模型的静态思维',
    'One model forced onto every turn': '无论难易，每轮对话都硬塞给同一个模型',
    '• Biggest model always → pay 2.5×–5× more & wait longer': '• 全程绑死旗舰大模型 → 多花 2.5×–5× 成本且响应更慢',
    '• Small model always → fail when reasoning gets hard': '• 全程只用轻量小模型 → 遇到复杂逻辑推理立刻掉链子',
    '• Users switch for one hard bug & forget to switch back': '• 查疑难 Bug 手动切到大模型，修完忘了切回白烧算力',
    '• Text-only models cannot generate diagrams or visuals': '• 纯文本大模型无法直接生成架构配图与汇报视觉素材',
    'DYNAMIC ROUTING': '按任务动态路由',
    'Task-routed multi-model Auto': '按子任务智能调度的多模型 Auto',
    '>90% of Microsoft Copilot queries today': '如今超过 90% 的 Microsoft Copilot 请求已走 Auto',
    '• Enforces tenant admin rules, subprocessors & geography': '• 严格执行租户白名单、合规子处理器与数据驻留边界',
    '• Classifier matches sub-tasks via live eval scorecards': '• 基于实时评测记分卡，为每步子任务匹配最契合模型',
    '• Adopts newly shipped frontier models automatically': '• 新一代前沿模型发布后自动纳入调度，无需改业务代码',
    '• Combines SLMs, reasoning LLMs & image models in one job': '• 单次任务内无缝串联轻量 SLM、深度推理与生图专精模型',
    'Shift from “which model is #1 overall?” to “which model fits this sub-task right now?”': '核心思维转变：从“哪个模型总榜第一？”转向“眼下这步子任务最适合派谁上？”',

    # Slide 4 (idx 3)
    'One prompt, four specialized jobs': '一句话需求，后台拆成四棒专精接力',
    'PROMPT  ·  “Customer renewal Thursday — expand, hold, or discount, and build a deck to make the case?”': '用户输入  ·  “周四谈客户续约 —— 该推增购、保原价还是给折扣？帮我做一份汇报 PPT。”',
    'Guardrail gate first: filters tenant-allowed model providers, data residency, and live endpoint health.': '合规护栏先行：先按租户允许的模型供应商、数据驻留地与节点健康度做硬过滤。',
    'JOB 01 · RETRIEVE': '第 1 棒 · 快速检索',
    'Small Language Model': '轻量语言模型 (SLM)',
    'Scans M365 emails, Teams chats, meeting notes & prior contracts fast and cheaply.': '低成本毫秒级扫完 M365 邮件、Teams 聊天、会议纪要与历史合同。',
    'SLM · Fast & cheap': 'SLM · 又快又省',
    'JOB 02 · REASON': '第 2 棒 · 深度算账',
    'Main agentic loop evaluates expand / hold / discount economics; caches full context.': '主循环推演增购、保价与折扣经济账，并将完整上下文写入热缓存。',
    'Main loop · Cached': '主推理循环 · 已缓存',
    'JOB 03 · VISUALIZE': '第 3 棒 · 视觉配图',
    'Generates custom proposal graphics and infographics that text LLMs cannot render.': '生成文字大模型无法绘制的定制提案插图与数据信息图。',
    'Image specialist': '视觉生图专家',
    'JOB 04 · ASSEMBLE': '第 4 棒 · 汇总成稿',
    'Reuses warm context cache to build the finished PowerPoint proposal without re-reading.': '直接复用第 2 棒预热的上下文缓存一气呵成生成 PPT，免去重读开销。',
    'Deck synthesis': '复用热缓存成稿',

    # Slide 5 (idx 4)
    '02 · COST & LATENCY ECONOMICS': '02 · 成本与延迟经济学',
    'Compressed quality, 163× cost spread': '头部质量高度收敛，成本却相差 163 倍',
    '4.2-pt quality band, 163× cost gap': '前 14 名仅差 4.2 分，账单却差 163 倍',
    'Top 14 models cluster within 86.2–90.4 across 8 tasks, yet cost spans $0.09 (auto) and $0.23 (Haiku 5.5) vs. $14.75 (Opus 5).': '8 类多模态任务前 14 名全挤在 86.2–90.4 分之间，但成本从自动路由 $0.09、Haiku $0.23 跨到 Opus 5 的 $14.75。',
    'Routine work → small models win': '常规任务 → 轻量模型完全够用',
    '24 of 28 models pass routine quality checks; Haiku 5.5 even ranks #1 on dashboard generation at a fraction of flagship cost.': '28 款模型中有 24 款轻松通过常规质量线；Haiku 5.5 在看板生成上甚至力压昂贵旗舰拿下全场第一。',
    'Hard problems → escalate selectively': '硬核难题 → 按需精准升级重型推理',
    'Save heavy reasoning models (Opus 5.5, Sonnet 5.5, GPT-6 Sol) for complex specs where small models stall in retry loops.': '把 Opus 5.5、Sonnet 5.5、GPT-6 Sol 留给复杂架构与疑难杂症，避免小模型陷入死循环重试。',

    # Slide 6 (idx 5)
    'Don’t break a warm prefix cache': '切忌在对话中途打碎预热好的前缀缓存',
    'Rule of thumb: switch models only at Turn 1, after compaction, or on isolated sub-agents.': '实战铁律：只在首轮对话、上下文压缩后、或独立子 Agent 边界才切换模型。',
    'Warm prefix cache = 10×–20× cheaper': '命中的热前缀缓存 = 便宜 10 到 20 倍',
    'Once a main model caches contracts, emails, repo files and 80+ tool schemas, follow-up turns pay ~10% cache-read rates.': '主模型首轮缓存好几万字合同、代码库与 80+ 工具定义后，后续轮次读取仅需约 10% 的缓存折扣价。',
    'Mid-session downgrades can cost MORE': '对话中途盲目切“便宜模型”反而更贵',
    'Switching to a “cheaper” model on turn 5 invalidates the prefix cache and forces re-prefilling 50k+ tokens from scratch.': '第 5 轮为省小钱切到别家模型会令缓存当场作废，被迫按全价把 5 万+ Token 从头预填充一遍。',
    'Route at natural cache boundaries': '守住自然的缓存切换边界',
    'Pick on Turn 1, after context compaction, on isolated sub-agents, or only when task complexity shifts dramatically.': '仅在会话首轮、上下文压缩重置后、派发独立子任务、或任务难度剧变时切换模型。',

    # Slide 7 (idx 6)
    '03 · MICROSOFT PRODUCTS IN ACTION': '03 · 微软核心产品路由实战',
    'Four routing surfaces across Microsoft': '微软体系内的四层自动路由形态',
    'Workplace Auto': '日常办公调度',
    'Routes >90% of queries: Chat → Cowork handoff, multi-provider selection, dynamic effort & sub-agents.': '承载 >90% 办公请求：Chat 转 Cowork 分流、合规跨厂商选型、动态推理力度与子任务协同。',
    'Coding Orchestrator': '编程多模型编排',
    'Matches each coding task to one model or a team: Single pass, Judge-gated Cascade, or parallel Critique.': '按编码任务难度自动匹配单兵或团队阵型：Single 直通、Cascade 裁判级联、Critique 跨厂互审。',
    'Cloud API Router': '云端 API 路由器',
    '20 ms ML ranker across 45 models (7 providers): quality bands, cache affinity, param cleanup & PTU failover.': '20 ms 专用 ML 排序器横跨 7 厂商 45 款模型：质量带选优、缓存亲和、参数自适应与 PTU 容灾。',
    'Software Controller': '软件控制决策引擎',
    'Purpose-built decision API that classifies, scores priority, and runs yes/no safety gates in ~123 ms at $0.042/1M.': '专为程序控制打造的决策 API：约 123 ms 完成分类路由、优先级打分与合规门控（$0.042/百万输入）。',

    # Slide 8 (idx 7)
    '03 · MICROSOFT PRODUCTS · MICROSOFT COPILOT': '03 · 微软产品实战 · MICROSOFT COPILOT',
    'Microsoft Copilot Home: unified Auto': 'Microsoft Copilot 主页：统一入口 Auto',
    'One unified prompt box: Auto answers quick questions in Chat or hands off multi-step work to Cowork.': '统一输入框：简单问答直接在 Chat 秒回，复杂多步任务自动提示移交 Cowork。',
    '1 · Chat → Cowork handoff': '1 · Chat → Cowork 智能移交',
    'Decision-1.1 detects when a prompt needs multi-step execution and suggests Cowork (2.2× faster, 4.4× cheaper).': '由 Decision-1.1 毫秒级识别多步长任务并建议转入 Cowork，比通用 LLM 判断快 2.2 倍、省费 4.4 倍。',
    '2 · Multi-provider within IT rules': '2 · 合规边界内的跨厂商调度',
    'Routes across OpenAI, Anthropic Claude & xAI Grok while enforcing EU Data Boundary & tenant admin switches.': '在严格遵循欧盟数据边界与租户管理员开关的前提下，跨 OpenAI、Claude 与 Grok 智能选型。',
    '3 · Scoped context & local offload': '3 · 精准上下文与本机算力分流',
    'Pulls only relevant M365 emails, chats & files via Work IQ — and offloads light tasks to local Windows PC models.': '借助 Work IQ 仅拉取相关邮件文档，并在受支持的 Windows 电脑上将轻任务分流至本地小模型。',

    # Slide 9 (idx 8)
    '03 · MICROSOFT PRODUCTS · COPILOT COWORK': '03 · 微软产品实战 · COPILOT COWORK',
    'Copilot Cowork: keep cache, tune effort': 'Copilot Cowork：锁住热缓存，动态调力度',
    'COWORK MODEL POOL  ·  ENABLED BY TENANT ADMIN': 'COWORK 模型池  ·  由企业租户管理员按需开启',
    '• Auto (Default)      → Picks on turn 1 & keeps cache warm': '• Auto（默认）         → 首轮选定主模型并全程保持前缀缓存温热',
    '• Effort (Decision-1.1) → Light · Medium · High · Extra High · Max': '• 推理力度 (Decision-1.1) → Light · Medium · High · Extra High · Max',
    'Opening-message model lock': '首轮锁定主模型，守护前缀缓存',
    'Auto inspects turn 1, picks from GPT 6.1 Sol, GPT 6 Astra, Opus 5.5, Sonnet 5.5, Fable 5.2 or Grok 4.7, and stays to keep cache.': 'Auto 分析首轮意图后从 GPT 6.1 Sol、Opus 5.5、Grok 4.7 等模型中选定主模型，后续轮次稳守热缓存。',
    'Decision-1.1 sets reasoning effort': 'Decision-1.1 逐轮动态调节推理力度',
    'Dynamically tunes effort (Light, Medium, High, Extra High, Max) so routine steps stay fast while hard tasks think deeper.': '在 Light 到 Max 五档间按步调节思考预算：常规步骤秒回，复杂测算给足深度推理算力。',
    'Predictable spend guardrails': '可预期的团队成本护栏',
    'Agent 365 Cost Management tracks work completed and enforces team spending limits so frontier runs never surprise IT.': '结合 Agent 365 成本管理追踪任务产出并执行团队预算上限，杜绝账单失控。',

    # Slide 10 (idx 9)
    '03 · MICROSOFT PRODUCTS · GITHUB COPILOT FUSION': '03 · 微软产品实战 · GITHUB COPILOT FUSION',
    'Copilot Fusion: pick effort, not models': 'Copilot Fusion：只选投入档位，告别选型纠结',
    'Pick Standard, High, or Max effort — hover the badge on any reply to see which models ran.': '只需选择 Standard、High 或 Max 档位 —— 悬停回复徽标即可查看实际参与的模型。',
    'Standard · High · Max (+ Fast)': 'Standard · High · Max（含 Fast 档）',
    'Standard routes 1 model per task (including local MAI Code 1.1 Flash / Qwen3.8 Flash); High & Max unlock orchestration.': 'Standard 单任务路由最佳单模型（含本机 MAI Code 1.1 Flash 等）；High 与 Max 解锁多模型协同编排。',
    'Frontier quality at ~50% cost': '逼近顶尖旗舰质量，成本直降约 50%',
    'On AA Coding Agent Index, Fusion Max scores 60 (within 2 pts of Opus 5.5 Max) at ~50% lower API cost & ~40% less time.': 'AA 编程评测 Fusion Max 拿 60 分（紧咬 Opus 5.5 Max），API 成本省约一半、端到端耗时缩短约 40%。',
    'Fixes “forgot to switch back” waste': '根治“切到大模型忘了切回”的算力浪费',
    'AT&T found developers picked a heavy model for one hard bug and left it on; Fusion right-sizes every turn automatically.': 'AT&T 发现工程师常为查一个难 Bug 切到重型模型后一直忘关；Fusion 每轮自动按需伸缩算力。',

    # Slide 11 (idx 10)
    '03 · MICROSOFT PRODUCTS · FUSION ORCHESTRATION': '03 · 微软产品实战 · FUSION 多模型拓扑',
    'Single, Cascade & Critique patterns': 'Single、Cascade 与 Critique 三种协作阵型',
    '1 · Single  (Everyday tasks)': '1 · Single 单模型直通（日常任务）',
    'One right-sized primary model solves the request with tools. Zero extra review latency or AI credit overhead.': '派一个量体裁衣的主模型配合工具一步搞定，零额外评审延迟、零多余额度开销。',
    '2 · Cascade  (Draft → Judge → Repair)': '2 · Cascade 裁判级联（初稿 → 裁判 → 返工）',
    'Efficient primary drafts a solution; a secondary Judge inspects and accepts — or escalates to a fresh Repair model.': '高性价比主模型先写补丁，Judge 模型审查通过即放行；抓出隐患才升级重型 Repair 模型重修。',
    '3 · Critique  (Draft → Critics → Revise)': '3 · Critique 跨厂互审（起草 → 挑刺 → 修订）',
    'Primary drafts while read-only Critics review in parallel (cannot edit files, avoiding conflicts); Primary revises.': '主模型起草，跨厂商只读 Critic 模型并行挑刺（只读权限防改乱文件），最后交回主模型吸收定稿。',

    # Slide 12 (idx 11)
    '03 · MICROSOFT PRODUCTS · MICROSOFT FOUNDRY': '03 · 微软产品实战 · MICROSOFT FOUNDRY',
    'Foundry Router: how it ranks & caches': 'Foundry 路由器：毫秒级排序与缓存亲和',
    'SCORING & AFFINITY ENGINE  ·  TRAINED ON BILLIONS OF INTERACTIONS': '打分与缓存亲和引擎  ·  基于数十亿次真实交互训练',
    '1. Rank eligible models for this prompt (~20 ms ML scorer)\n2. Keep models within 1–2% of #1 quality  (5–6% in Cost mode)\n3. Reuse prior model if cache is warm & in band; else cheapest': '1. 对合规候选模型实时打分排序（~20 ms 专用 ML 排序器）\n2. 保留紧贴第 1 名 1–2% 质量带的梯队（Cost 模式放宽至 5–6%）\n3. 若上轮模型缓存仍热且未掉出质量带则留用，否则挑最便宜款',
    'Non-LLM ML Ranker (~20 ms)': '非 LLM 专用排序器（~20 ms）',
    'Purpose-built ML model (not an LLM!) reads system prompt, history & tool schemas, weighting the latest turn highest.': '轻量专用机器学习模型（并非生成式 LLM），20 ms 扫完系统提示词、历史与工具定义，最新一轮权重最高。',
    'Quality-Band Cost Selection': '质量容忍带内的最低成本选优',
    'Balanced picks cheapest within 1–2% of #1 fit; Cost widens to 5–6%; Quality picks #1 — across 45 models from 7 labs.': 'Balanced 在顶尖 1–2% 分差内挑最便宜款；Cost 放宽至 5–6%；Quality 直取第 1 —— 横跨 7 厂 45 模型。',
    'Adaptive Cache Affinity': '自适应前缀缓存亲和',
    'Tracks sessions via ID, previous_response_id or message fingerprint — keeping the prior model while warm & in-band.': '通过会话 ID、响应 ID 或历史消息指纹识别同会话，只要缓存未冷且质量达标就稳守原模型。',

    # Slide 13 (idx 12)
    '03 · MICROSOFT PRODUCTS · FOUNDRY PIPELINE': '03 · 微软产品实战 · FOUNDRY 工程管线',
    'Foundry: filters, params & failover': 'Foundry：资格过滤、参数清洗与容灾切换',
    '1 · Pre-Rank Eligibility Gate': '1 · 排序前硬性资格过滤',
    'Filters by region, approved allow-list, tools / json_schema / image support, and valid reasoning_effort before ranking.': '打分前先按数据区域、企业模型白名单、工具/JSON/视觉能力与推理档位筛掉不合格模型。',
    '2 · Cross-Provider Param Cleanup': '2 · 跨厂商参数自动清洗适配',
    'Drops temperature/stop on reasoning models, strips reasoning_effort on non-reasoning, & maps developer → system.': '推理模型自动剔除 temperature/stop，非推理模型剥离 reasoning_effort，自动映射 developer → system。',
    '3 · PTU Priority & Auto-Failover': '3 · PTU 优先消化与限流自动容灾',
    'Uses your pre-paid PTU first ($0 extra model fee) → PAYG → Managed, then fails over to #2 inside your allow-list.': '优先消耗已预付费 PTU（$0 额外模型费）→ 按量部署 → 托管池；遇 429 高峰自动切白名单第 2 顺位。',

    # Slide 14 (idx 13)
    '04 · MODEL-LEVEL IMPLEMENTATION': '04 · 模型路由底层算法对比',
    'Four general routing architectures': '业界常见的四类模型路由技术路线',
    'ARCHITECTURE': '技术路线',
    'OVERHEAD': '路由耗时',
    'HOW IT WORKS': '核心工作原理',
    'KEY LIMITATION': '核心工程短板',
    '1 · Heuristic & Semantic': '1 · 规则与语义向量路由',
    'Regex, token count, or embedding k-NN (e.g., Aurelio Semantic Router) against anchor prompts.': '基于正则、Token 长度或句向量 k-NN（如 Semantic Router）匹配锚点示例。',
    'Surface topics ≠ reasoning difficulty; misses subtle traps.': '表面字眼 ≠ 推理难度，极易漏判隐蔽并发或逻辑陷阱。',
    '2 · Binary Preference': '2 · 二分类偏好路由',
    'Matrix factorization / BERT classifier (e.g., RouteLLM) predicting P(Strong beats Weak).': '用矩阵分解或 BERT 分类器（如 RouteLLM）预测强模型胜过弱模型的概率。',
    'Coupled to fixed model IDs — must retrain when catalog changes!': '权重绑死固定模型 ID —— 模型池一更新就得重采重训！',
    '3 · Cascade (FrugalGPT)': '3 · 串行级联 (FrugalGPT)',
    '+1× draft': '+1 轮试错',
    'Run cheap model first; a verifier scores the draft and escalates to strong if low.': '先让便宜小模型试写初稿，验证器打分过低再升级重跑强模型。',
    'Pays double latency on hard tasks; correlated judge blind spots.': '遇到难题白交双倍等待延迟，且小裁判易漏看同类盲点。',
    '4 · Generative LLM Router': '4 · 生成式大模型路由',
    'Prompt a general LLM to pick a tool/model and explain its reasoning in JSON/text.': '写提示词让通用生成式 LLM 选择下游模型并逐词输出 JSON 理由。',
    'Slow, expensive, and overconfident — RLHF hurts calibration!': '慢且贵，且 RLHF 微调导致过度自信、概率校准度极差！',

    # Slide 15 (idx 14)
    '04 · MICROSOFT’S ARCHITECTURE · HYDRA': '04 · 微软底层架构 · GITHUB HYDRA',
    'GitHub HyDRA: decouple demand & catalog': 'GitHub HyDRA：将任务需求与模型目录彻底解耦',
    '1. Score 4 demands (86 ms): [Reason, CodeGen, Debug, Tools]': '1. 预测四维能力需求 (86 ms)：[推理, 代码生成, 调试, 工具编排]',
    '2. Pick cheapest healthy model whose profile covers all 4': '2. 对照静态配置表，挑出能覆盖四项需求的最便宜健康模型',
    '4-Head Capability Scorer': '四头轻量能力预测器',
    'Lightweight ModernBERT scores Reasoning, CodeGen, Debugging & Tool Use in 86 ms median CPU latency.': '轻量 ModernBERT 同时给推理、写代码、调试、调工具打需求分，CPU 中位耗时仅 86 ms。',
    'Zero-Retraining Model Updates': '新模型零重训即插即用',
    'Models live in config files, not classifier weights! Adding GPT-6 is a config edit — 6× more savings (54.1%) than binary routing.': '模型画像与单价写在配置文件而非分类器权重里！上新 GPT-6 只需改配置，等质量省费 54.1%（二分类的 6 倍）。',
    'Multilingual Across 19 Languages': '原生覆盖 19 种自然语言',
    'Trained on full multi-turn coding sessions (including Chinese, Japanese & Korean) within 4 pts of English accuracy.': '基于真实多轮编程会话训练，原生支持中、日、韩等 19 种语言，与英文准确率差距不到 4 个百分点。',

    # Slide 16 (idx 15)
    '04 · MICROSOFT’S ARCHITECTURE · BLUEPRINT': '04 · 微软底层架构 · 三层工程蓝图',
    'Microsoft’s three-layer routing stack': '微软统一的三层模型路由工程栈',
    'Models score bounded options; deterministic code enforces policy gates, thresholds & fallbacks.': '分工铁律：模型只管在合规集合内客观打分；确定性代码负责守住红线、阈值与兜底。',
    'Layer 1 · Deterministic Policy & Cache Gate': '第 1 层 · 确定性合规与缓存门控',
    'Hard code filters tenant-allowed providers, data zones, required tool/schema capabilities, and warm prefix-cache state.': '硬代码先行过滤租户白名单、数据驻留区、必需的工具/JSON 能力以及当前前缀缓存冷热状态。',
    'Layer 2 · Fast Scorer / Decision Model (<180 ms)': '第 2 层 · 毫秒级打分器 / 专用决策模型 (<180 ms)',
    'Purpose-built encoder (HyDRA / Foundry ML ranker) or Microsoft-Decision-1.1 produces calibrated scores over allowed options.': '由专用编码器（HyDRA / Foundry 排序器）或 Microsoft-Decision-1.1 对合规候选项输出校准概率。',
    'Layer 3 · Workflow Pattern & Output Verifier': '第 3 层 · 协作拓扑执行与出站校验',
    'Executes Single, Cascade or Critique, then runs deterministic schema, citation or policy safety checks before acting.': '按分差执行 Single、Cascade 或 Critique，并在动作生效前完成格式、引用或安全合规门控。',

    # Slide 17 (idx 16)
    '05 · MICROSOFT DECISION-1.1': '05 · MICROSOFT DECISION-1.1 决策模型',
    'Meet Microsoft-Decision-1.1': '认识 Microsoft-Decision-1.1',
    'Generative LLMs as routers': '拿生成式大模型客串路由器',
    'Trained to sound helpful & complete tasks': '训练目标是把话写通顺，而非客观打分',
    '• Autoregressive tokens add 500–2,000 ms latency': '• 逐词自回归生成白白增加 500–2,000 ms 延迟',
    '• RLHF rewards confident guesses on missing info': '• RLHF 偏好微调鼓励模型在缺失信息时自信瞎猜',
    '• Fragile JSON parsing & option-order bias': '• JSON 解析易碎，调换选项顺序结果就会乱飘',
    'Microsoft-Decision-1.1  (GA Nov 2026)': 'Microsoft-Decision-1.1（2026 年 11 月正式版）',
    'Built specifically for fast, calibrated decisions': '专为极速、概率校准的程序控制而生',
    '• Mixture-of-Experts (4B active) + single-pass engine': '• MoE 混合专家架构（仅激活 4B 参数）+ 单次前向引擎',
    '• Reads text, JSON & photos/UI with zero filler prose': '• 原生读文本、JSON 与图片/界面，零废话直出概率',
    '• Calibrated probabilities; <1.3% variance on reordered options': '• 严格概率校准，打乱选项顺序翻转率低于 1.3%',
    'Input tokens (Global Std); output tokens FREE!': '每百万输入 Token 单价；输出 Token 完全免费！',
    'Median decision latency (2.2× faster than v1.0)': '中位决策延迟（比 1.0 版本快 2.2 倍）',
    'Faster than frontier LLMs on routing & QC': '在路由与质检场景远快于旗舰生成式模型',
    '3 Clouds': '3 大云平台',
    'Microsoft Foundry, OpenRouter & Vercel': '支持 Foundry、OpenRouter 与 Vercel',

    # Slide 18 (idx 17)
    '05 · MICROSOFT DECISION-1.1 · API PRIMITIVES': '05 · MICROSOFT DECISION-1.1 · 三大接口原语',
    'Three primitives: choice, noul, score': '三大强类型原语：choice、noul、score',
    '01 · choice  (Pick one)': '01 · choice（多选一分流）',
    '“Which option fits best?”': '“哪条路径最合适？”',
    'Picks one label and returns calibrated probabilities per candidate.\nUse: model routing, ticket triage, tool pick.': '选出最佳标签并返回每个候选项的校准概率。\n适用：模型路由、工单分派、工具选择。',
    '02 · noul  (Yes / No gate)': '02 · noul（是非安检门）',
    '“Is this condition true?”': '“这个条件成立吗？”',
    'Returns a single [0, 1] probability for any true/false check.\nUse: safety gates, refund/rival checks, photo damage.': '针对任意是非判断返回单个 [0, 1] 校准概率。\n适用：合规护栏、竞品/折扣拦截、退货照片验损。',
    '03 · score  (0–N scale)': '03 · score（有序等级打分）',
    '“How urgent or strong?”': '“有多紧急 / 质量几分？”',
    'Computes a probability-weighted score across ordered levels.\nUse: P0–P3 incident priority, output grading.': '在有序档位上计算概率加权期望分。\n适用：P0–P3 故障定级、销售意向与质量评分。',
    'POST <foundry-endpoint>/providers/microsoft/v1/systemone   ·   Ask all 3 in ONE call': 'POST <foundry-endpoint>/providers/microsoft/v1/systemone   ·   单次请求可同时合并三类问题',

    # Slide 19 (idx 18)
    '05 · MICROSOFT DECISION-1.1 · EXAMPLES': '05 · MICROSOFT DECISION-1.1 · 四大落地模式',
    'Four production Decision-1.1 patterns': 'Decision-1.1 的四个典型生产控制模式',
    '1 · Custom LLM & Agent Router (choice)': '1 · 自建大模型与 Agent 路由器 (choice)',
    'criteria: { mai_flash, sonnet_5_5, opus_critique, ask_clarify }\n→ If max(p) < 0.75 or choice == ask_clarify, clarify before burning frontier credits!': 'criteria: { mai_flash, sonnet_5_5, opus_critique, ask_clarify }\n→ 若最高概率 < 0.75 或命中 ask_clarify，先向用户追问补齐材料，不白烧旗舰算力！',
    '2 · Support Triage + SLA Queue (choice + score)': '2 · 客服工单分派 + SLA 紧急度定级 (choice + score)',
    'Single call returns team = "safety_support" (0.95) AND priority.score = 2.94 / 3.0 → Math.round(score) == P3 pages immediate human.': '单次调用同时返回 safety_support (0.95) 与严重度 2.94 / 3.0 → 命中 P3 当场跳过机器人并呼人工专员。',
    '3 · Multimodal Photo & UI Gate (assets + noul)': '3 · 多模态实物照片与界面质检 (assets + noul)',
    'questions.damaged = { type: "noul", instructions: "Shows physical damage?" }\n→ p >= 0.80 auto-replaces; 0.35–0.80 routes to claims adjuster.': 'questions.damaged = { type: "noul", instructions: "Shows physical damage?" }\n→ 概率 >= 0.80 自动秒批换货；0.35–0.80 灰区交人工理赔核验。',
    '4 · Outbound LLM Guardrail Filter (noul)': '4 · 生成式回复出站合规护栏 (noul)',
    'Independent noul checks: mentions_competitor, unapproved_discount, medical_claim.\n→ Hold draft if ANY noul >= 0.50; catches “Try Fabrikam for $749”!': '并行跑多道独立 noul 检查：推荐竞品、私自承诺折扣、违规医疗建议。\n→ 任一概率 >= 0.50 立即扣下草稿，精准拦下“推荐竞品 Fabrikam 只要 $749”！',

    # Slide 20 (idx 19)
    '05 · MICROSOFT DECISION-1.1 · BENCHMARKS': '05 · MICROSOFT DECISION-1.1 · 权威盲测榜单',
    '#1 across 102 decision benchmarks': '102 项盲测基准总榜第一（38.5 万题）',
    '#1 Overall Across 102 Blind Benchmarks': '102 项零重叠盲测基准总榜第 1',
    '78.8% mean accuracy over 385,246 zero-overlap questions — ahead of Jev 1.14 (78.1), Gemini Decision 1 (77.7) & GPT-6 Luna (73.4).': '在 385,246 道盲测题上以 78.8% 平均准确率夺冠，领先 Jev 1.14 (78.1)、Gemini Decision 1 (77.7) 与 GPT-6 Luna (73.4)。',
    'Leads 7 of 9 Capabilities  ·  2.2× Faster': '九大能力维度领跑七项  ·  提速 2.2 倍',
    '#1 in routing, tools, safety, rules, reasoning, judging & consistency — plus Score 68 (+6 pts, 123 ms) on AA Decision Index v2.1.': '路由、工具选择、安全、规则、推理、裁判与一致性全部第 1；AA 决策指数涨 6 分达 68 分（中位 123 ms）。',
    'Powering Microsoft & 4,000+ Customers': '驱动微软核心产品与 4,000+ 企业客户',
    '• Copilot Chat→Cowork: 2.2× faster, 4.4× cheaper': '• Copilot Chat→Cowork 分流：快 2.2 倍、省费 4.4 倍',
    '• Cowork Auto effort + Foundry Evaluation judge': '• 驱动 Cowork 推理力度调节与 Foundry 评测裁判',
    '• Xbox Research: 14× faster, 200× cheaper than GPT-6 Sol': '• Xbox 分析管线：比 GPT-6 Sol 快 14 倍、便宜 200 倍',
    '• Adopted by Epic, Equinor, Atos & Raiffeisen Bank': '• 已获 Epic、Equinor、Atos 与 Raiffeisen 银行投产采用',

    # Slide 21 (idx 20)
    '05 · MICROSOFT DECISION-1.1 · IMPACT': '05 · MICROSOFT DECISION-1.1 · 商业回报测算',
    'Sales agent case: 7.2× lower CAC': '销售线索 Agent 实战：获客成本直降 7.2 倍',
    '1 · Baseline: Frontier LLM + 100% review': '1 · 传统基线：全量旗舰 LLM + 100% 人工复核',
    '$0.31 per lead  ·  CAC = $13.00': '单线索成本 $0.31  ·  获客成本 CAC = $13.00',
    'Every email calls a $0.15 frontier LLM plus $0.24 human review — capping $10k/mo at 764 customers.': '每封回信都调 $0.15 旗舰模型再加 $0.24 人工审核，一万美元月预算最多只能转化 764 单。',
    '2 · Add choice router + score priority': '2 · 接入 choice 前置分流 + score 意向定级',
    '$0.07 per lead  ·  CAC = $2.63': '单线索成本 $0.07  ·  获客成本 CAC = $2.63',
    '100% routing accuracy (vs. 88% regex): 57% of simple replies skip the LLM; only P1–P3 go to humans.': '32 类邮件分流准确率达 100%（正则仅 88%）：57% 简单回信直接免调大模型，仅高优线索进人工。',
    '3 · Add noul outbound safety gate': '3 · 加上 noul 出站合规护栏',
    '$0.05 per lead  ·  CAC = $1.81 (7.2× lower)': '单线索成本 $0.05  ·  CAC 降至 $1.81（降低 7.2 倍）',
    'All 3 Decision-1.1 checks cost $0.00019/email total — cutting human review 100% → 8% (5,511 customers).': '三道检查合计每封仅花 $0.00019，将人工复核率从 100% 压到 8%，同等预算转化 5,511 单！',

    # Slide 22 (idx 21)
    '$ copilot --model fusion --fusion-tier high \\\n    -p "..." --output-format json --usage-output-file u.json\n\n// Server-resolved pattern per single CLI command:\n-> Routine fix  : pattern="single"   (gpt-6.1-terra, 0 review)\n-> Lock bug     : pattern="cascade"  (sol -> luna Judge 5/5)\n-> 50k RPS RFC  : pattern="critique" (opus -> luna -> revise)\n-> --resume <id>: 99% cacheReadTokens hit (5,655 / 5,733 tok)': '$ copilot --model fusion --fusion-tier high \\\n    -p "..." --output-format json --usage-output-file u.json\n\n// 单条命令在服务端按难度自动切换阵型:\n-> 常规修改     : pattern="single"   (gpt-6.1-terra, 零评审)\n-> 并发死锁     : pattern="cascade"  (sol -> luna 裁判 5/5)\n-> 五万并发 RFC : pattern="critique" (opus -> luna -> 修订)\n-> --resume <id>: 99% 缓存命中 (5,655 / 5,733 tok)',
    'POST /openai/v1/chat/completions\nFoundry-Features: ModelRouterControls=V1Preview\n{\n  "model": "auto",\n  "routing_config": {\n    "mode": "balanced",\n    "session_affinity": { "strategy": "adaptive" }\n  }\n}\n// Invoice JSON -> DeepSeek-V4.1-Flash (28 ms)\n// Rust MPMC    -> gpt-6-luna          (27 ms, retain)': 'POST /openai/v1/chat/completions\nFoundry-Features: ModelRouterControls=V1Preview\n{\n  "model": "auto",\n  "routing_config": {\n    "mode": "balanced",\n    "session_affinity": { "strategy": "adaptive" }\n  }\n}\n// 简单发票提取 -> DeepSeek-V4.1-Flash (27 ms)\n// Rust 并发证明 -> gpt-6-luna          (30 ms, retain)',
    '// Easy JSON -> DeepSeek-V4.1-Flash (23 ms) | Hard Rust -> gpt-5.6-luna (20 ms)\n"session_affinity": { "strategy": "adaptive", "decision": "retain" },\n"attempts": [ {"model":"gpt-6-sol","status":429}, {"model":"gpt-5.6-sol","status":200} ]': '// 简单提取 -> DeepSeek-V4.1-Flash (23 ms) | 复杂证明 -> gpt-5.6-luna (20 ms)\n"session_affinity": { "strategy": "adaptive", "decision": "retain" },\n"attempts": [ {"model":"gpt-6-sol","status":429}, {"model":"gpt-5.6-sol","status":200} ]',
    '06 · LIVE DEMO 1': '06 · 现场实测 DEMO 1',
    'Copilot CLI Auto & Fusion live': 'Copilot CLI Auto 与 Fusion 单命令实测',
    'Auto → Single → Native Cascade → Native Critique → 99% Cache': 'Auto 直通 → Single → 原生 Cascade → 原生 Critique → 99% 缓存命中',
    '✓  Auto & Fusion Single fast path': '✓  Auto 与 Fusion Single 快速通道',
    'categoryScores ≤ 0.10 & pattern="single"': '四维需求分 ≤ 0.10 且自动选 pattern="single"',
    'Even on Fusion High, simple lookups & routine patches run 1 solver with zero review calls (3/3 node --test).': '即使开启 Fusion High，简单查配置与常规修补仍自动走单模型零评审开销（宿主 3/3 单测全过）。',
    '↗  1-command native Cascade': '↗  单命令原生 Cascade 裁判级联',
    'gpt-6.1-sol → gpt-6-luna Judge → Opus skipped': 'gpt-6.1-sol 修复 → gpt-6-luna 裁判 5/5 → 自动省掉 Opus',
    'One CLI call fixes ABBA lock order; native Judge scores 5/5 (accept) & skips conditional Opus 5.5 repair.': '单条命令修好双锁死锁，原生 Judge 打出 5 分满分放行，自动跳过 Opus 返工并通过 500 次并发压测。',
    '⇄  1-command Critique + 99% Cache': '⇄  单命令原生 Critique 互审 + 99% 热缓存',
    'Opus draft → Luna Critic → Opus revise': 'Opus 起草 → 跨厂 Luna 挑刺 → Opus 修订定稿',
    'Native Critic flags Active-Active zero-RPO gap for Opus to revise; --resume hits 99% cacheReadTokens.': '跨厂 Critic 抓出双活零数据丢失漏洞交回 Opus 修订；--resume 追问实测命中 99% 前缀缓存。',

    # Slide 23 (idx 22)
    '06 · LIVE DEMO 2': '06 · 现场实测 DEMO 2',
    'Foundry Model Router live': 'Foundry Model Router 云端实测',
    '4 live Foundry V1Preview cloud traces (0 local mocks)': '4 步真实 Foundry V1Preview 云端抓包（零本地模拟）',
    '✓  Pre-rank gate & param normalization': '✓  资格过滤与跨厂商参数自适应',
    'developer role + json_object → gpt-5.6-luna': 'developer 角色 + json_object → gpt-5.6-luna',
    'One V1Preview endpoint normalizes cross-provider params and serves valid JSON in 30 ms router overhead.': '单一 V1Preview 接口自动清洗跨厂不兼容参数，30 ms 路由耗时稳定返回合法 JSON。',
    '⚡  27–30 ms ML routing & retain affinity': '⚡  27–30 ms 极速路由与会话缓存亲和',
    'DeepSeek-V4.1-Flash (JSON) vs. gpt-6-luna (Rust)': 'DeepSeek-V4.1-Flash（简单提取）vs. gpt-6-luna（Rust 证明）',
    'Routes simple JSON to Flash (0 reason tok) and escalates Rust proofs to Luna with retain affinity on Turn 2.': '简单发票提取走零推理开销 Flash；Rust 无锁证明自动升级 Luna，第 2 轮追问返回 retain 锁住热缓存。',
    '⇄  Two-stage cost → quality routing': '⇄  cost → quality 双阶段子任务协同',
    'grok-4-1-fast (cost) → gpt-5.6-terra (quality)': 'grok-4-1-fast (cost 提取) → gpt-5.6-terra (quality 推演)',
    'Splits renewal analysis into two live calls: cheap extraction in cost mode followed by strategy in quality mode.': '同一端点拆成两棒实测：先用 cost 模式便宜提取关键续约数字，再用 quality 模式交旗舰推演博弈策略。',

    # Slide 24 (idx 23)
    '06 · LIVE DEMO 3': '06 · 现场实测 DEMO 3',
    'Decision-1.1 agent controller': 'Decision-1.1 业务控制与护栏实测',
    'GA · Nov 2026': '2026.11 正式版',
    '5 live /v1/systemone traces + custom prompt tester': '5 步真实 /v1/systemone 云端调用 + 实时输入探测',
    '✓  Zero-spread routing (choice & noul)': '✓  零漂移稳定输出与前置分流',
    '5/5 identical 0.9835 · 4/4 inbox p=1.00': '连调 5 次全为 0.9835（极差 0） · 4 条收件箱全中',
    '5 consecutive live calls return 0.00 pt spread; 3 of 4 routine inbox messages skip the frontier LLM.': '连续 5 次云端请求极差 0.00 pt；4 条真实客服消息分流中 3 条直接省掉昂贵旗舰模型调用。',
    '!  3-in-1 safety triage (choice+score+noul)': '!  单次请求三问合一安全熔断',
    'safety_support (0.998) + score 1.97 + repeat 1.00': '安全团队 (0.998) + 严重度 1.97 + 重复投诉 1.00',
    'One 348 ms call classifies injury risk, scores urgency & flags 3rd repeat contact — blocking bot reply.': '一次三百多毫秒请求同时完成分组、定级与重复投诉识别 —— 当场拦停机器人并转人工专员。',
    '✕  Outbound guardrail & missing-doc abstain': '✕  出站竞品拦截与缺件主动追问',
    'Rival promo noul=0.970 & missing Exhibit B p=0.9999': '推荐竞品 noul=0.970 扣留 · 漏挂附件 B 概率 0.9999',
    'Holds a draft recommending rival Fabrikam (0.970) and stops to ask when Exhibit B is missing from state.': '精准扣下推荐竞品 Fabrikam 的回复草稿 (0.970)；发现漏挂附件 B 时主动停下追问而非瞎编条款。',

    # Slide 25 (idx 24)
    'SUMMARY · KEY TAKEAWAYS': '总结 · 核心落地建议',
    'Right-size the model,\nkeep the control': '量体裁衣选模型，\n稳守边界控全局',
    '1   Route sub-tasks by capability — no single model wins all.': '1   按子任务能力拆解分工 —— 别再拿单一模型硬扛全场。',
    '2   Stop paying 100× for simple work — & keep prefix caches warm.': '2   别为简单活付百倍溢价 —— 守住自然边界别打碎热缓存。',
    '3   Adopt Copilot Auto, Copilot Fusion & Foundry Router first.': '3   优先用好现成轮子：Copilot Auto、Fusion 与 Foundry Router。',
    '4   Use Microsoft-Decision-1.1 for fast routing, priority & safety gates.': '4   自建分流、定级与合规护栏，直接嵌入 Microsoft-Decision-1.1。',
    'Thank you  ·  Q&A': '谢谢大家  ·  问答交流 (Q&A)',

    # Slide 26 (idx 25)
    'APPENDIX · OFFICIAL SOURCES & BENCHMARKS': '附录 · 官方文档、论文与基准评测',
    'Public field guide': '公开参考资料索引',
    'Benchmarks & Product Routing': '权威评测与微软产品路由文档',
    'Capability specialization, 163× cost benchmarks, Microsoft Copilot Auto & GitHub Copilot Fusion.': '能力专精分工、163 倍成本评测、Microsoft Copilot Auto 与 GitHub Copilot Fusion。',
    'Routing Architecture & Decision-1.1': '底层路由论文与 Decision-1.1 实战指南',
    'HyDRA multi-head routing paper, Foundry Model Router internals, Decision-1.1 API & open benchmarks.': 'HyDRA 多头路由论文、Foundry Model Router 机制详解、Decision-1.1 接口与开源题库。',
    '↗  Charles Lamanna — Auto in Copilot (>90% queries)': '↗  Charles Lamanna — Copilot Auto 解析（>90% 请求采用）',
    '↗  GenisisIQ — 28-Model Multimodal Benchmark (163×)': '↗  GenisisIQ — 28 模型多模态工程评测（163× 成本差）',
    '↗  Microsoft 365 Copilot at Ignite 2026 (Home & Auto)': '↗  Microsoft 365 Copilot Ignite 2026（主页与 Auto）',
    '↗  Microsoft Learn — Copilot Cowork Auto & Effort': '↗  Microsoft Learn — Copilot Cowork 模型与力度调节',
    '↗  GitHub Docs — Copilot Fusion Orchestration': '↗  GitHub 官方文档 — Copilot Fusion 多模型编排',
    '↗  GitHub HyDRA Routing Paper (arXiv:2605.17106)': '↗  GitHub HyDRA 多头路由架构论文 (arXiv:2605.17106)',
    '↗  GitHub Blog — Cache-Aware Model Routing': '↗  GitHub 技术博客 — 前缀缓存感知模型路由解析',
    '↗  Microsoft Learn — How Foundry Model Router Works': '↗  Microsoft Learn — Foundry Model Router 工作原理',
    '↗  Command Line — Microsoft-Decision-1.1 GA': '↗  Command Line 博客 — Microsoft-Decision-1.1 正式发布',
    '↗  Microsoft Learn — Use Microsoft-Decision-1.1 API': '↗  Microsoft Learn — Microsoft-Decision-1.1 接口接入指南',
    '↗  GitHub — microsoftconnect/Decision-Benchmarks': '↗  GitHub 开源库 — microsoftconnect/Decision-Benchmarks',
}

ZH_DEMO_LAUNCHERS = {
    10: ('fusion', '1', '打开 Fusion 演示'),
    12: ('foundry', '1', '打开 Foundry 演示'),
    20: ('decision', '1', '打开 Decision-1.1 演示'),
    21: ('fusion', '1', '启动 Demo 1 · Copilot CLI & Fusion'),
    22: ('foundry', '1', '启动 Demo 2 · Foundry 路由器'),
    23: ('decision', '1', '启动 Demo 3 · Decision-1.1'),
}
