#!/usr/bin/env python3
"""
build_pptx.py - builds "Auto-routing LLMs" (26 slides, 16:9,
hand-drawn illustrations + product screenshots/charts, Chinese speaker notes)
as a standalone .pptx with build-time layout & overlap verification.

Usage:   pip install python-pptx pillow
         python -m presentation.src.build_pptx [--out "dist/pptx/Auto-routing LLMs.pptx"]
"""
import argparse, os
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from PIL import Image

# ===================== THEME & LAYOUT =====================
W,H=12192000,6858000; M=457200; CW=W-2*M
BG='F3EEE4'; CARD='E9E2D4'; CARD2='E9E2D4'; EDGE='C9C0AE'; INK='2B2B2B'; MUTED='57534C'; FOOT='6E685F'
CY='3F607E'; AMB='A84A35'; CODEBG='FAF7F1'; CODE='2F4B66'
HF='Plus Jakarta Sans'; BF='Plus Jakarta Sans'; MF='JetBrains Mono'

REFS_LEFT = [
    ('Charles Lamanna — Auto in Copilot (>90% queries)', 'https://www.linkedin.com/posts/charleslamanna_there-isnt-one-model-thats-the-best-at-ugcPost-7521988229508628480-GPoC/'),
    ('GenisisIQ — 28-Model Multimodal Benchmark (163×)', 'https://blog.genisisiq.com/github-copilot-creative-and-multimodal-benchmark/'),
    ('Microsoft 365 Copilot at Ignite 2026 (Home & Auto)', 'https://www.microsoft.com/en-us/copilot/blog/2026/11/17/copilot-at-microsoft-ignite-expanding-whats-possible-with-intelligence-built-for-work/'),
    ('Microsoft Learn — Copilot Cowork Auto & Effort', 'https://learn.microsoft.com/en-us/copilot/cowork/cowork-models#when-to-use-auto'),
    ('GitHub Docs — Copilot Fusion Orchestration', 'https://docs.github.com/en/copilot/concepts/models/copilot-fusion'),
]
REFS_RIGHT = [
    ('GitHub HyDRA Routing Paper (arXiv:2605.17106)', 'https://arxiv.org/abs/2605.17106'),
    ('GitHub Blog — Cache-Aware Model Routing', 'https://github.blog/ai-and-ml/github-copilot/getting-more-from-each-token-how-copilot-improves-context-handling-and-model-routing/'),
    ('Microsoft Learn — How Foundry Model Router Works', 'https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-router-how-it-works'),
    ('Command Line — Microsoft-Decision-1.1 GA', 'https://commandline.microsoft.com/microsoft-decision-model-ga/'),
    ('Microsoft Learn — Use Microsoft-Decision-1.1 API', 'https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/use-foundry-models-microsoft-decision'),
    ('GitHub — microsoftconnect/Decision-Benchmarks', 'https://github.com/microsoftconnect/Decision-Benchmarks'),
]

# ===================== HELPERS ===================
slides={}
notes={}
def P(s,op): slides.setdefault(s,[]).append(op)
WF={'Plus Jakarta Sans':0.55,'Newsreader':0.58,'JetBrains Mono':0.62,'Aptos Display':0.56,'Aptos':0.53,'Cascadia Code':0.62,'Georgia':0.6,'Arial':0.56,'Calibri':0.52,'Courier New':0.62}
def nlines(text,size,cx,font,bold):
    f=WF[font]*(1.08 if bold else 1)
    cpl=max(1,int((cx-240000)/(size*12700*f)))
    n=0
    for para in text.split('\n'):
        words=para.split(' '); line=0; cnt=1
        for w_ in words:
            L=len(w_)+(1 if line else 0)
            if line+L>cpl and line>0: cnt+=1; line=len(w_)
            else: line+=L
        n+=cnt
    return n
def hgt(paras,cx,font,space_after=6.5):
    t=0
    for idx,p in enumerate(paras):
        lh=1.48 if font==MF else (1.16 if p['sizePt']>=29 else 1.42)
        t+=nlines(p['text'],p['sizePt'],cx,font,p.get('bold',False))*p['sizePt']*12700*lh
        if idx<len(paras)-1:
            t+=p.get('spaceAfterPt',space_after)*12700
    return int(t+240000)
def tb(s,x,y,cx,text=None,size=16,color=INK,font=BF,bold=False,align='left',paras=None,ls=None,cy=None,name=None,space_after=None):
    default_sa = (2.0 if font==MF else 6.5) if space_after is None else space_after
    if paras is None:
        paras=[{'text':text,'sizePt':size,'bold':bold,'color':color}]
    else:
        paras=[dict({'sizePt':size,'bold':bold,'color':color},**p) for p in paras]
    h=cy or hgt(paras,cx,font,default_sa)
    op={'op':'add_text_box','slide':s,'x':int(x),'y':int(y),'cx':int(cx),'cy':int(h),'fontFamily':font,'align':align,'color':color,'spaceAfterPt':default_sa}
    if len(paras)==1 and ls is None and 'href' not in paras[0]:
        p=paras[0]; op.update(text=p['text'],sizePt=p['sizePt'],bold=p['bold'],color=p['color'])
    else:
        op['paragraphs']=[{k:v for k,v in p.items()} for p in paras]
        if ls is not None:
            if len(paras)==1 and 'href' not in paras[0]:
                p=paras[0]; del op['paragraphs']; op.update(text=p['text'],sizePt=p['sizePt'],bold=p['bold'],color=p['color'])
            op['letterSpacingPt']=ls
    if name: op['name']=name
    P(s,op); return int(y+h)
def rect(s,x,y,cx,cy,fill=CARD,line=None,lw=None,preset='rect',text=None,size=16,color=INK,bold=False,font=BF,align='center',shadow=None,rot=None):
    op={'op':'add_shape','slide':s,'preset':preset,'x':int(x),'y':int(y),'cx':int(cx),'cy':int(cy),'fill':fill}
    if line: op['line']=line; op['lineWidth']=lw or 12700
    if text is not None:
        op.update(text=text,sizePt=size,color=color,bold=bold,fontFamily=font,align=align)
    if shadow: op['shadow']=shadow
    if rot: op['rot']=rot
    P(s,op)
def img(s,path,x,y,cx,cy,alt,fit='cover'):
    P(s,{'op':'add_image','slide':s,'path':path,'x':int(x),'y':int(y),'cx':int(cx),'cy':int(cy),'fit':fit,'altText':alt})
def header(s,eyebrow,title,x=M,cx=CW,title_cy=None):
    tb(s,x,310000,cx,eyebrow,size=12,color=CY,font=HF,bold=True,ls=2,cy=280000,name='eyebrow')
    tb(s,x,640000,cx,title,size=29.5,color=INK,font=HF,bold=True,cy=title_cy or 640000,name='slide_title')
def footer(s,src,num,x=M,cx=CW):
    if src: tb(s,x,6260000,cx-900000,src,size=11.5,color=FOOT,cy=340000,name='footer_src')
    tb(s,x+cx-800000,6260000,800000,f'{num:02d}',size=11.5,color=FOOT,align='right',cy=340000,name='footer_num')
def note(s,t): notes[s]=t

def card_box(s,x,y,cx,cy,paras,fill=CARD,line=None,lw=19050,pad_x=240000,pad_y=120000,font=BF,space_after=6.5,align='left'):
    rect(s,x,y,cx,cy,fill=fill,line=line,lw=lw if line else None)
    tb(s,x+pad_x,y+pad_y,cx-2*pad_x,None,paras=paras,font=font,align=align,cy=cy-2*pad_y,space_after=space_after)

# ===================== SLIDES ====================
# ---------- 0 COVER
s=0
img(s,'hd-fork.jpg',W-M-5100000,1580000,5100000,3400000,'Hand-drawn illustration: robot dispatcher at a fork choosing between a fast courier bike and a heavy cargo van')
x=M+80000; cx=5800000
tb(s,x,960000,cx,'INTELLIGENT MODEL SELECTION & DECISION SYSTEMS',size=12,color=CY,font=HF,bold=True,ls=2,cy=300000)
tb(s,x,1340000,cx,'Auto-routing\nLLMs',size=45,color=INK,font=HF,bold=True,cy=1480000)
tb(s,x,2940000,cx,'Understand how the right model is selected automatically per task to balance quality, cost and latency — using a proper decision model and Microsoft Copilot as examples.',size=16.5,color=MUTED,cy=1340000)
tb(s,x,4560000,cx,'Yingting Huang  |  Sr. Cloud Solution Architect, Microsoft',size=15.5,color=INK,bold=True,cy=380000)
tb(s,x,5000000,cx,'November 2026  ·  45 minutes  ·  L300 → L400',size=13.5,color=MUTED,cy=340000)
note(s,'欢迎大家。今天分享的主题是《Auto-routing LLMs》：如何根据每个任务的特征自动选择最合适的模型与执行模式，在质量、成本和延迟三者之间取得工程最优解。\n我们将沿着五个核心维度展开：第一，从模型能力分化出发（参考微软 Charles Lamanna 分享的 Copilot 多模型实践）；第二，从真实基准测试看成本与人工等待时间的巨大差异；第三，拆解 Microsoft Copilot、GitHub Copilot Fusion 与 Foundry Model Router 在生产中的真实截图与机制；第四，深入模型底层架构对比业界做法与微软 HyDRA 的创新；第五，重点介绍专为结构化控制而生的 Microsoft-Decision-1.1，并通过三个可交互回放的 Demo 串联完整落地路径。')

# ---------- 1 AGENDA
s=1
header(s,'AGENDA','Our journey today')
items=[
    ('01','Capability gap','No single model wins all'),
    ('02','Cost & cache','163× spread & cache law'),
    ('03','MS products','Copilot, Fusion, Foundry'),
    ('04','Under the hood','Industry vs. MS HyDRA'),
    ('05','Decision-1.1','Typed choice, noul, score'),
    ('06','Live demos','3 interactive replays'),
    ('07','Takeaways','Ship your own router'),
]
col=CW/7; ry=2960000
rect(s,M,ry-19050,CW,38100,fill=EDGE)
for i,(n,t,d) in enumerate(items):
    cx0=M+col*i; bw=col-75000
    tb(s,cx0,1920000,bw,n,size=28,color=CY,font=HF,bold=True,cy=580000)
    rect(s,cx0+60000,ry-120000,240000,240000,fill=CY if i!=4 else AMB,preset='ellipse')
    tb(s,cx0,3280000,bw,t,size=16,color=INK,bold=True,cy=620000)
    tb(s,cx0,3980000,bw,d,size=13.5,color=MUTED,cy=780000)
footer(s,'Level: L300 → L400  ·  Press D anytime in web view to open Interactive Routing Studio',2)
note(s,'这是今天 45 分钟的路线图。前两部分回答“为什么要自动路由”（能力专精化与 163 倍成本差距）；第三部分通过真实产品界面截图看微软三大核心产品怎么路由；第四部分剖析底层算法（传统二分类路由 vs 微软能力向量解耦架构）；第五和第六部分聚焦 Microsoft-Decision-1.1 模型原语与三个交互式回放 Demo。')

# ---------- 2 PART 1: NO SINGLE BEST MODEL (CHARLES LAMANNA)
s=2
header(s,'01 · CAPABILITY SPECIALIZATION','No single model is best at everything')
cw_=4950000; cyy=1540000; ch=3800000
card_box(s,M,cyy,cw_,ch,[
    {'text':'Static single-model mindset','sizePt':20.5,'bold':True,'color':MUTED,'spaceAfterPt':7},
    {'text':'One model forced onto every turn','sizePt':14,'bold':True,'color':CY,'spaceAfterPt':11},
    {'text':'• Biggest model always → pay 2.5×–5× more & wait longer','sizePt':14,'color':MUTED,'spaceAfterPt':8},
    {'text':'• Small model always → fail when reasoning gets hard','sizePt':14,'color':MUTED,'spaceAfterPt':8},
    {'text':'• Users switch for one hard bug and forget to switch back','sizePt':14,'color':MUTED,'spaceAfterPt':8},
    {'text':'• Text-only models cannot generate diagrams or visuals','sizePt':14,'color':MUTED},
],fill=CARD,pad_x=250000,pad_y=140000)
rx=W-M-cw_
card_box(s,rx,cyy,cw_,ch,[
    {'text':'Task-routed multi-model Auto','sizePt':20.5,'bold':True,'color':INK,'spaceAfterPt':7},
    {'text':'>90% of Microsoft Copilot queries today','sizePt':14,'bold':True,'color':CY,'spaceAfterPt':11},
    {'text':'• Enforces tenant admin rules, subprocessors & geography','sizePt':14,'color':INK,'spaceAfterPt':8},
    {'text':'• Classifier matches sub-tasks via live eval scorecards','sizePt':14,'color':INK,'spaceAfterPt':8},
    {'text':'• Adopts newly shipped frontier models automatically','sizePt':14,'color':INK,'spaceAfterPt':8},
    {'text':'• Combines SLMs, reasoning LLMs & image models in one job','sizePt':14,'color':INK},
],fill=CARD2,line=CY,lw=25400,pad_x=250000,pad_y=140000)
rect(s,M+cw_+180000,cyy+ch/2-260000,W-2*M-2*cw_-360000,520000,fill=CY,preset='rightArrow')
tb(s,M,5480000,CW,'Shift from “which model is #1 overall?” to “which model fits this sub-task right now?”',size=19,bold=True,color=INK,cy=500000)
footer(s,'Source: Charles Lamanna (Microsoft), Whiteboarding Auto in Copilot, LinkedIn, Nov 2026',3)
note(s,'我们先从模型功能维度看为什么静态选模型已经过时。微软 Business & Industry Copilot 负责人 Charles Lamanna 在白板拆解中指出：今天已经不存在一个在所有任务上都排第一的万能模型。有的模型擅长深度推理与 Excel 建模，有的擅长高视觉表现力的幻灯片，有的专精图像生成，而检索邮件和提取字段用小模型（SLM）就能同样出色且快得多。\n更重要的是，在真实企业场景中，超过 90% 的 Microsoft Copilot 请求都已经通过 Auto 动态路由完成——模型选择不再是每次提问前强加给用户的心理负担，而变成了受企业合规策略约束的运行时调度系统。')

# ---------- 3 ONE PROMPT -> FOUR SPECIALIZED JOBS (LAMANNA WHITEBOARD)
s=3
header(s,'01 · CAPABILITY SPECIALIZATION','One prompt, four specialized jobs')
card_box(s,M,1520000,CW,920000,[
    {'text':'PROMPT  ·  “Customer renewal Thursday — expand, hold, or discount, and build a deck to make the case?”','sizePt':14.5,'bold':True,'color':CODE,'spaceAfterPt':6},
    {'text':'1. Org guardrails filter allowed providers (OpenAI / Anthropic / xAI), data residency & live endpoint health first.','sizePt':13,'color':MUTED},
],fill=CODEBG,line=EDGE,lw=12700,pad_x=240000,pad_y=100000)
gap=160000; cw4=(CW-3*gap)/4; y0=2620000; ch=3380000
jobs=[
    ('JOB 01 · RETRIEVE','Small Language Model','Scans Work IQ emails, Teams chats, meeting transcripts & contracts fast and cheaply.','SLM · Fast & cheap',CY),
    ('JOB 02 · REASON','Claude Opus 5.5','Main agentic loop evaluates expand / hold / discount economics; caches full context.','Main loop · Cached',CY),
    ('JOB 03 · VISUALIZE','GPT Image 2.5','Generates custom proposal graphics and infographics that text LLMs cannot render.','Image specialist',AMB),
    ('JOB 04 · ASSEMBLE','Claude Opus 5.5','Reuses warm context cache to build the finished PowerPoint proposal without re-reading.','Deck synthesis',CY),
]
for i,(kicker,model,desc,badge,col_) in enumerate(jobs):
    x=M+i*(cw4+gap)
    rect(s,x,y0,cw4,ch,fill=CARD)
    tb(s,x+180000,y0+160000,cw4-360000,kicker,size=11,color=col_,font=HF,bold=True,ls=1,cy=280000)
    tb(s,x+180000,y0+500000,cw4-360000,model,size=18.5,bold=True,color=INK,cy=580000)
    tb(s,x+180000,y0+1140000,cw4-360000,desc,size=13.5,color=MUTED,cy=1460000)
    rect(s,x+200000,y0+ch-580000,cw4-400000,380000,fill=col_,preset='roundRect',text=badge,size=12,bold=True,color=BG)
footer(s,'Adapted from Charles Lamanna’s renewal proposal walkthrough: OpenAI image synthesis + Claude reasoning + SLM retrieval',4)
note(s,'以 Charles Lamanna 演示的周四客户续约提案为例：“我该扩购、维持原价还是给折扣？帮我做一份汇报 PPT。”\n请求进入 Auto 后，首先经过组织管理员设定的供应商、子处理者与地域边界过滤；随后分类器基于大规模评测计分卡选出主循环模型（如 Claude Opus 5.5）。但第一次选型不是唯一选型：查找邮件纪要交给极快的 SLM；深度客户研究与幻灯片结构复用已经缓存上下文的 Claude Opus 5.5；而视觉配图则分派给图像生成最强的 GPT Image 2.5。跨实验室强强联合，每个子任务都跑在最擅长的模型上。')

# ---------- 4 PART 2: 163X COST COMPRESSION & RIGHT-SIZING
s=4
header(s,'02 · COST & LATENCY ECONOMICS','Compressed quality, 163× cost spread')
ix=M; iy=1540000; icw=6200000; ich=4400000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'bench-163x-frontier.svg',ix+60000,iy+60000,icw-120000,ich-120000,'Vector SVG chart: The 163x Cost Compression Frontier — Mean Creative Quality vs AI Credits and Wall-Clock Time across 28 models',fit='contain')
rx=ix+icw+280000; rw=W-M-rx
stats=[
    ('4.2-pt quality band, 163× cost gap','Top 14 models cluster within 86.2–90.4 across 8 tasks, yet cost spans $0.09 (auto) and $0.23 (Haiku 5.5) vs. $14.75 (Opus 5).',CY),
    ('Simple work → lightweight models win','24/28 models pass 98%–100% of structural checks; Haiku 5.5 even ranks #1 on KPI DataViz (92.5) at a fraction of frontier cost.',CY),
    ('Hard specs → escalate selectively','Reserve heavy reasoning (Opus 5.5, Sonnet 5.5, GPT-6 Sol) for complex specs where weak models burn minutes in retry loops.',AMB),
]
for i,(head_t,desc,col_) in enumerate(stats):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1360000,[
        {'text':head_t,'sizePt':16.2,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':desc,'sizePt':13.1,'color':MUTED},
    ],fill=CARD,pad_x=220000,pad_y=115000)
footer(s,'Source: blog.genisisiq.com/github-copilot-creative-and-multimodal-benchmark (28 models × 8 tasks = 224 runs)',5)
note(s,'再看第二个核心维度：成本与延迟。这张帕累托前沿图来自 28 个模型 × 8 类多模态工程任务的 224 次实测。\n结论非常直接：第一，排名前 14 的模型综合质量高度压缩在 86.2 到 90.4 分之间（仅差 4.2 分），但完成同样 8 个任务的成本从 auto 的 9 美分、Haiku 5.5 的 23 美分一直跨度到 14.75 美元，相差整整 163 倍；第二，简单或流程化任务根本没必要动用昂贵旗舰，例如轻量级 Haiku 5.5 在 KPI 数据看板上甚至拿到全场第一；第三，只有遇到深度架构或复杂边界条件时，才需要升级到旗舰推理模型，避免弱模型陷入反复重试。按任务难度自动分流，才能同时守住质量下限与成本上限。')

# ---------- 5 PREFIX CACHE LAW
s=5
header(s,'02 · COST & LATENCY ECONOMICS','Don’t break a warm prefix cache')
img(s,'hd-tradeoff.jpg',M,1740000,5040000,3360000,'Hand-drawn robot balancing stopwatch, coin, and quality checkmark')
rx=M+5040000+340000; rw=W-M-rx
cache_cards=[
    ('Warm prefix cache = 10×–20× cheaper','Once a main model caches contracts, emails, repo files and 80+ tool schemas, follow-up turns pay ~10% cache-read rates.',CY),
    ('Mid-session downgrades can cost MORE','Switching to a “cheaper” model on turn 5 invalidates the prefix cache and forces re-prefilling 50k+ tokens from scratch.',AMB),
    ('Route at natural cache boundaries','Pick on Turn 1, after context compaction, on isolated sub-agents, or only when task complexity shifts dramatically.',CY),
]
for i,(t,d,col_) in enumerate(cache_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':17,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13.6,'color':MUTED},
    ],fill=CARD,pad_x=240000,pad_y=120000)
footer(s,'Sources: Charles Lamanna (M365 Copilot Auto) & Joe Binder (GitHub Copilot cache-aware routing, Jun 2026)',6)
note(s,'在进入产品拆解前，必须强调一个极易被忽视的工程陷阱：Prompt Prefix Cache（前缀缓存）。\n无论在 Microsoft Copilot 还是 GitHub Copilot 中，主模型在第一轮读入合同、邮件、代码库和数十个 MCP 工具定义后，缓存命中的读取价格通常只有原价的十分之一（快且省 10–20 倍）。如果你在第 4 轮为了一句简单追问把模型切到另一个家族，缓存立刻失效，新模型必须全价重读几万个 Token，反而更慢更贵！因此微软的路由器遵循一条铁律：只在自然缓存边界（首轮、上下文压缩重置后、独立子 Agent、或复杂度剧变时）切换模型。')

# ---------- 6 PART 3: MICROSOFT ROUTING LANDSCAPE (4 CARDS + APPEAR)
s=6
header(s,'03 · MICROSOFT PRODUCTS IN ACTION','Four routing surfaces across Microsoft')
gap=170000; cw4=(CW-3*gap)/4; y0=1560000; ch=4360000
surfaces=[
    ('M365 Copilot & Cowork','Workplace Auto','Routes >90% of queries: Chat → Cowork handoff, multi-lab model pick (GPT / Claude / Grok), dynamic effort & sub-agents.'),
    ('GitHub Copilot Fusion','Coding Orchestrator','Combines HyDRA capability routing + runtime execution patterns: Single, Judge-gated Cascade, and parallel Critique.'),
    ('Foundry Model Router','Cloud API Router','Non-LLM ML ranker (~20 ms) across 45 models (7 labs): quality bands, adaptive cache affinity, param adaptation & PTU failover.'),
    ('Microsoft Decision-1.1','Software Controller','Purpose-built /systemone API returning calibrated choice, noul & score probabilities in ~123–180 ms at $0.042/1M.'),
]
for i,(prod,tag_,desc) in enumerate(surfaces):
    x=M+i*(cw4+gap)
    rect(s,x,y0,cw4,ch,fill=CARD)
    rect(s,x+200000,y0+240000,cw4-400000,380000,fill=EDGE,preset='roundRect',text=tag_,size=12,bold=True,color=INK)
    tb(s,x+200000,y0+760000,cw4-400000,f'0{i+1}',size=26,color=AMB if i==3 else CY,font=HF,bold=True,cy=460000)
    tb(s,x+200000,y0+1280000,cw4-400000,prod,size=18.5,bold=True,color=INK,cy=680000)
    tb(s,x+200000,y0+2060000,cw4-400000,desc,size=14,color=MUTED,cy=2060000)
footer(s,'“Auto” is a product promise, not a single monolithic backend — each surface optimizes for its workload',7)
note(s,'接下来我们看微软自己的产品是如何落地的。虽然界面上都叫 Auto 或 Router，但微软针对四类不同场景构建了各司其职的调度层：\n1. Microsoft 365 Copilot 与 Cowork：面向知识工作者，统筹体验切换（Chat 转 Cowork）、跨厂商主模型选择与多子任务协同；\n2. GitHub Copilot Auto 与 Fusion：面向软件工程，不仅选模型，还动态选择 Single、Cascade 或 Critique 工作流；\n3. Foundry Model Router：面向云原生应用 API，在 45 个模型池中按请求排序并优先消化企业已购买的 PTU 容量；\n4. Microsoft-Decision-1.1：把微软内部同款决策模型直接开放给开发者，嵌入你自己的业务代码。')

# ---------- 7 MICROSOFT COPILOT HOME SCREENSHOT
s=7
header(s,'03 · MICROSOFT PRODUCTS · MICROSOFT COPILOT','Microsoft Copilot Home: unified Auto')
ix=M; iy=1540000; icw=6400000; ich=3600000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'m365-copilot-home.png',ix+50000,iy+50000,icw-100000,ich-100000,'Official Microsoft screenshot: Microsoft Copilot Home composer unifying Chat and Cowork with Auto',fit='contain')
tb(s,ix,5260000,icw,'Official Microsoft Copilot Home UI: unified Auto composer across Chat, Cowork, and Office artifacts.',size=12.8,color=MUTED,cy=580000)
rx=ix+icw+280000; rw=W-M-rx
m365_pts=[
    ('1 · Experience handoff (Decision-1.1)','Detects when a prompt needs multi-step execution and suggests Chat → Cowork (2.2× faster, 4.4× cheaper).',CY),
    ('2 · Multi-lab within IT guardrails','Routes across OpenAI, Anthropic Claude & xAI Grok while enforcing EU Data Boundary & admin switches.',CY),
    ('3 · Work IQ + Hybrid local offload','Filters 19.5 EB of M365 signals via Work IQ, and offloads eligible work to local PC models on Windows.',AMB),
]
for i,(t,d,col_) in enumerate(m365_pts):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'Sources: Microsoft Ignite 2026 Copilot Blog & Command Line Decision-1.1 GA (84% cheaper than standalone Claude per GigaOm)',8)
note(s,'这是 Microsoft Copilot 全新 Home 界面的官方截图。以前用户要在不同入口切换，现在一个由 Auto 驱动的统一输入框就能承接所有工作。\n它在后台做了三层自动决策：第一，由 Microsoft-Decision-1.1 判断这是一个快速问答还是多步骤长任务，必要时建议从 Chat 无缝移交给 Cowork（用户确认后流转，比用通用大模型判断快 2.2 倍、省 4.4 倍成本）；第二，严格在租户管理员允许的模型池（如欧盟数据边界或 Anthropic 开关）中选路；第三，结合 Work IQ 精准裁剪邮件与文档上下文，并在支持的 Windows 设备上将合适任务卸载至本地模型。')

# ---------- 8 COPILOT COWORK AUTO SCREENSHOT
s=8
header(s,'03 · MICROSOFT PRODUCTS · COPILOT COWORK','Copilot Cowork: model lock & effort')
ix=M; iy=1540000; icw=6400000; ich=1660000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'m365-cowork-ui.png',ix+50000,iy+50000,icw-100000,ich-100000,'Official Microsoft Learn screenshot: Copilot Cowork composer with Chat/Cowork toggle and Auto Medium selector',fit='contain')
card_box(s,ix,3340000,icw,2640000,[
    {'text':'COWORK MODEL POOL  ·  ENABLED BY TENANT ADMIN','sizePt':11,'bold':True,'color':CY,'spaceAfterPt':7},
    {'text':'• Auto (Default)      → Picks best model on turn 1 & locks cache','sizePt':11.6,'color':INK,'spaceAfterPt':5},
    {'text':'• Microsoft / OpenAI  → GPT 6.1 Sol, GPT 6 Astra, GPT 5.6 Terra','sizePt':11.6,'color':INK,'spaceAfterPt':5},
    {'text':'• Anthropic / xAI     → Opus 5.5, Sonnet 5.5, Fable 5.2, Grok 4.7','sizePt':11.6,'color':INK,'spaceAfterPt':6},
    {'text':'• Effort (Decision-1.1) → Light · Medium · High · Extra High · Max','sizePt':11.6,'bold':True,'color':CODE},
],fill=CODEBG,line=EDGE,lw=12700,pad_x=200000,pad_y=95000,font=MF)
rx=ix+icw+280000; rw=W-M-rx
cw_pts=[
    ('Opening-message model lock','Auto inspects turn 1, picks from GPT 6.1 Sol, GPT 6 Astra, Opus 5.5, Sonnet 5.5, Fable 5.2 or Grok 4.7, and stays to keep cache.',CY),
    ('Decision-1.1 sets reasoning effort','Dynamically tunes effort (Light, Medium, High, Extra High, Max) so routine steps stay fast while hard tasks think deeper.',CY),
    ('Predictable spend guardrails','Agent 365 Cost Management tracks work completed and enforces team spending limits so frontier runs never surprise IT.',AMB),
]
for i,(t,d,col_) in enumerate(cw_pts):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.8,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'Source: Microsoft Learn, Choose a model for Copilot Cowork (updated Nov 18, 2026)',9)
note(s,'进入 Copilot Cowork 后（目前近 80% 的财富 500 强已在使用），Auto 的工作机制在官方文档中定义得非常清晰：\n第一，首轮锁定策略：Cowork 分析会话的第一条消息属于快速邮件、日程协调、跨表财务分析还是代码构建，从组织启用的 GPT 6.1 Sol、GPT 6 Astra、Claude Opus 5.5、Sonnet 5.5、Fable 5.2 或 Grok 4.7 中选出最匹配的主模型，并在后续轮次保持该模型以保护上下文缓存；用户随时可通过回复上的 Model Badge 查看实际服务模型。\n第二，Microsoft-Decision-1.1 动态调节推理投入档位（Light 到 Max），做到简事快办、难事深思。')

# ---------- 9 GITHUB COPILOT FUSION COMPOSER SCREENSHOT
s=9
header(s,'03 · MICROSOFT PRODUCTS · GITHUB COPILOT FUSION','Copilot Fusion: pick effort, not models')
ix=M; iy=1540000; icw=6200000; ich=3592000
rect(s,ix,iy,icw,ich,fill='11161D',line=EDGE,lw=12700)
img(s,'fusion-picker.png',ix+40000,iy+40000,icw-80000,ich-80000,'Official GitHub screenshot: Copilot Fusion composer menu showing Standard, High, and Max effort levels',fit='contain')
tb(s,ix,5260000,icw,'Official GitHub Copilot composer: hover the effort badge on any reply to inspect every model used.',size=12.8,color=MUTED,cy=580000)
rx=ix+icw+280000; rw=W-M-rx
fus_cards=[
    ('Standard · High · Max (+ Fast)','Standard routes 1 model per task (including local MAI Code 1.1 Flash / Qwen3.8 Flash); High & Max unlock orchestration.',CY),
    ('Frontier quality at ~50% cost','On AA Coding Agent Index, Fusion Max scores 60 (within 2 pts of Opus 5.5 Max) at ~50% lower API cost & ~40% less time.',CY),
    ('Cures “sticky flagship” waste','AT&T reported developers used to pick a heavy model for one bug and forget to switch back; Fusion automates right-sizing.',AMB),
]
for i,(t,d,col_) in enumerate(fus_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.8,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'Sources: GitHub Changelog (Oct 28, 2026) & GitHub Docs — About GitHub Copilot Fusion (Demo 1)',10)
note(s,'再看开发者每天使用的 GitHub Copilot Fusion（在 VS Code、Copilot CLI、GitHub App 与 JetBrains 中全面 GA）。这张官方截图展示了它的核心交互变革：你不再纠结选哪个具体模型，而是打开 Copilot Fusion 并选择努力档位（Standard、High、Max）。\n在 Artificial Analysis 编码 Agent 指数中，Fusion Max 拿到 60 分（距满血单跑 Opus 5.5 Max 仅 2 分），但平均每任务 API 成本降低约 50%、Token 消耗减半、耗时缩短约 40%！AT&T 工程团队反馈它彻底解决了“修复杂 Bug 切到大模型后忘了切回来”的普遍浪费；Standard 档甚至支持自动卸载到本机安装的 MAI Code 1.1 Flash。')

# ---------- 10 COPILOT FUSION EXECUTION PATTERNS SCREENSHOT
s=10
header(s,'03 · MICROSOFT PRODUCTS · FUSION ORCHESTRATION','Single, Cascade & Critique patterns',cx=CW-2300000)
ix=M; iy=1540000; icw=5420000; ich=4400000
rect(s,ix,iy,icw,ich,fill='0F141A',line=EDGE,lw=12700)
img(s,'fusion-patterns.png',ix+40000,iy+40000,icw-80000,ich-80000,'Official GitHub diagram: Three execution patterns in Copilot Fusion — Single, Cascade, and Critique',fit='contain')
rx=ix+icw+280000; rw=W-M-rx
pat_cards=[
    ('1 · Single  (Everyday tasks)','One right-sized primary model solves the request with tools. Zero extra review latency or AI credit overhead.',CY),
    ('2 · Cascade  (Draft → Judge → Repair)','Efficient primary drafts a solution; a secondary Judge inspects and accepts — or escalates to a fresh Repair model.',CY),
    ('3 · Critique  (Draft → Critics → Revise)','Primary drafts while read-only Critics review in parallel (cannot edit files, avoiding conflicts); Primary revises.',AMB),
]
for i,(t,d,col_) in enumerate(pat_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':16.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13.4,'color':MUTED},
    ],fill=CARD,pad_x=220000,pad_y=110000)
footer(s,'Source: GitHub Copilot Fusion architecture — patterns can change prompt-by-prompt within one session',11)
note(s,'这张官方架构图揭示了 Copilot Fusion 为什么既省钱又高质：它把“选模型”升级成了“选模型 + 选协作拓扑”。\n1. Single：直接任务只调一个高性价比模型，绝不浪费评审费；\n2. Cascade（级联短路）：先让高效模型打头阵，再由次级 Judge 检查——如果已经做对就直接采纳（短路省钱），只有遇到硬骨头才升级给更强的 Repair 模型重做；\n3. Critique（并行独立评审）：主模型起草后，多个只读 Critic 模型并行挑刺（注意 Critic 被严格限制为只读，不能直接改代码以免冲突），最后由主模型汇总反馈完成修订。我们稍后在 Demo 1 会完整回放这三种模式。')

# ---------- 11 FOUNDRY MODEL ROUTER: HOW IT RANKS & CACHES
s=11
header(s,'03 · MICROSOFT PRODUCTS · MICROSOFT FOUNDRY','Foundry Router: how it ranks & caches')
ix=M; iy=1540000; icw=6980000; ich=2708000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'foundry-overview.png',ix+40000,iy+40000,icw-80000,ich-80000,'Official Microsoft Learn diagram: Microsoft Foundry Model Router ranking prompts across 45 models with Balanced/Quality/Cost modes, session affinity and failover',fit='contain')
rect(s,ix,4400000,icw,1560000,fill=CODEBG,line=EDGE,lw=12700)
tb(s,ix+200000,4490000,icw-400000,'SCORING & AFFINITY ENGINE  ·  TRAINED ON BILLIONS OF INTERACTIONS',size=10.5,color=FOOT,font=MF,cy=260000)
ov_snip=(
    '1. Score q(m | sys, history, turn_t, tools) in ~20 ms\n'
    '2. Band  = { m : q(m) >= q(best) - Δ }  // 1–2% | 5–6% | 0%\n'
    '3. Pick  = m_prev if cache_warm && m_prev ∈ Band else cheapest'
)
tb(s,ix+200000,4800000,icw-400000,ov_snip,size=10.8,color=CODE,font=MF,cy=1060000)
rx=ix+icw+240000; rw=W-M-rx
fo_cards=[
    ('Non-LLM ML Ranker (~20 ms)','Purpose-built ML model (not an LLM!) reads system prompt, history & tool schemas, weighting the latest turn highest.',CY),
    ('Quality-Band Cost Selection','Balanced picks cheapest within 1–2% of #1 fit; Cost widens to 5–6%; Quality picks #1 — across 45 models from 7 labs.',CY),
    ('Adaptive Cache Affinity','Tracks sessions via ID, previous_response_id or message fingerprint — keeping the prior model while warm & in-band.',AMB),
]
for i,(t,d,col_) in enumerate(fo_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.2,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=105000)
footer(s,'Source: Microsoft Learn, How model router works in Microsoft Foundry ($0.14/1M input routing fee, $0 output)',12)
note(s,'进入 Microsoft Foundry Model Router，重点看它内部到底是怎么工作的（model: "auto" 只是免部署体验别名，底层跑的是完全同一套引擎）：\n第一，它本身不是大语言模型，而是在数十亿次问答、编码、数学推理与工具调用交互上训练出来的极速机器学习排序模型（耗时约 20 毫秒，绝不存储用户 Prompt）。它会同时读取系统提示词、多轮对话历史与工具定义（最新一轮权重最高），当企业配置了自定义模型子集时，它还会针对该子集动态重新校准预测分布。\n第二，质量带选路：先算出当前请求的第 1 名基准分，Balanced 模式在距第 1 名 1–2% 的高质候选里选最便宜的模型，Cost 放宽到 5–6%，Quality 直接选第 1 名。\n第三，Adaptive 会话亲和：通过会话 ID、previous_response_id 或历史消息指纹识别同一次多轮对话——只要前序消息未变（缓存仍热）且上一轮模型仍在当前质量带内，就自动保留原模型（retain）吃满前缀缓存折扣！')

# ---------- 12 FOUNDRY ROUTER: GATES, PARAMS & FAILOVER
s=12
header(s,'03 · MICROSOFT PRODUCTS · FOUNDRY PIPELINE','Foundry Router: gates, params & retry',cx=CW-2300000)
ix=M; iy=1540000; icw=6980000; ich=2708000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'foundry-router-flow.png',ix+40000,iy+40000,icw-80000,ich-80000,'Official Microsoft Learn diagram: Six-step Foundry Model Router execution flow from eligibility filtering and ranking to PTU/PAYG capacity waterfall and failover',fit='contain')
rect(s,ix,4400000,icw,1560000,fill=CODEBG,line=EDGE,lw=12700)
tb(s,ix+200000,4490000,icw-400000,'live-capture.json  ·  Foundry-Features: ModelRouterControls=V1Preview',size=11,color=FOOT,font=MF,cy=260000)
live_snip=(
    '// JSON -> DeepSeek-V4.1-Flash (23ms) | Rust -> gpt-5.6-luna (20ms)\n'
    '"session_affinity": {"strategy":"adaptive","decision":"retain"},\n'
    '"attempts": [{"model":"gpt-6-sol","status":429},{"status":200}]'
)
tb(s,ix+200000,4800000,icw-400000,live_snip,size=10.8,color=CODE,font=MF,cy=1060000)
rx=ix+icw+240000; rw=W-M-rx
f_cards=[
    ('1 · Pre-Rank Eligibility Gate','Filters by region, approved subset, tools / json_schema / image support, and valid reasoning_effort before ranking.',CY),
    ('2 · Cross-Lab Param Adaptation','Drops temperature/stop on reasoning models, strips reasoning_effort on non-reasoning, & maps developer → system.',CY),
    ('3 · Capacity-First & Failover','Drains Own PTU ($0 model fee) → Own PAYG → Managed on #1 model first, then next-ranked model inside your subset.',AMB),
]
for i,(t,d,col_) in enumerate(f_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.2,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=105000)
footer(s,'Source: Microsoft Learn, How model router works — Eligibility, Parameter Adaptation & Two-Tier Failover (Demo 2)',13)
note(s,'再看请求在 Foundry Model Router 里的完整工程执行流水线（左上官方六步图）：\n1. 排序前硬性资格过滤：先按区域、安全团队审批的模型白名单子集、是否支持函数工具/JSON Schema/图像输入以及特定 reasoning_effort 档位（如 xhigh）剔除不合格模型；\n2. 跨厂商参数自适应适配：不同模型支持的参数千差万别！选定模型后，路由器会自动剥离推理模型不支持的 temperature/stop，或剥离非推理模型不支持的 reasoning_effort，甚至把 developer 角色自动改写为 system 角色，保证跨 7 大厂商路由绝不报错（若需严格校验可设 require_parameters: true 提前过滤）；\n3. 两级容量瀑布与故障转移：选中第 1 名模型后，先依次尝试你的自有 OpenAI PTU（零额外模型费）→ 自有 PAYG → 平台托管容量；只有同一模型的三级容量全部触发 429/5xx 可重试错误时，才自动切换到白名单子集内的第 2 顺位模型（故障转移优先级高于会话亲和，且绝不越出你的合规子集）。')

# ---------- 13 PART 4: INDUSTRY ROUTING ARCHITECTURES (GENERAL APPROACHES)
s=13
header(s,'04 · MODEL-LEVEL IMPLEMENTATION','Four general routing architectures')
c1=M; w1=2650000; c2=c1+w1+110000; w2=1600000; c3=c2+w2+110000; w3=3350000; c4=c3+w3+110000; w4=W-M-c4
hy=1480000
for xx,ww,tt in [(c1,w1,'ARCHITECTURE'),(c2,w2,'OVERHEAD'),(c3,w3,'HOW IT WORKS'),(c4,w4,'KEY LIMITATION')]:
    tb(s,xx+150000,hy,ww-150000,tt,size=11.5,color=CY,font=HF,bold=True,ls=1,cy=280000)
approaches=[
    ('1 · Heuristic & Semantic','2 – 15 ms','Regex, token count, or embedding k-NN (e.g., Aurelio Semantic Router) against anchor prompts.','Surface topics ≠ reasoning difficulty; misses subtle traps.',CY),
    ('2 · Binary Preference','20 – 90 ms','Matrix factorization / BERT classifier (e.g., RouteLLM) predicting P(Strong beats Weak).','Coupled to fixed model IDs — must retrain when catalog changes!',CY),
    ('3 · Cascade (FrugalGPT)','+1× draft','Run cheap model first; a verifier scores the draft and escalates to strong if low.','Pays double latency on hard tasks; correlated judge blind spots.',INK),
    ('4 · Generative LLM Router','400 – 2000 ms','Prompt a general LLM to pick a tool/model and explain its reasoning in JSON/text.','Slow, expensive, and overconfident — RLHF hurts calibration!',AMB),
]
y=1840000; rh=960000
for a,lat,how,lim,col_ in approaches:
    rect(s,M,y,CW,rh,fill=CARD)
    tb(s,c1+160000,y+80000,w1-180000,a,size=15,bold=True,color=col_,cy=rh-160000)
    tb(s,c2+140000,y+80000,w2-160000,lat,size=13.5,bold=True,color=INK,font=MF,cy=rh-160000)
    tb(s,c3+150000,y+80000,w3-180000,how,size=13.2,color=INK,cy=rh-160000)
    tb(s,c4+150000,y+80000,w4-180000,lim,size=13.2,color=AMB if col_==AMB else MUTED,cy=rh-160000)
    y+=rh+95000
footer(s,'Industry evolution: Semantic Router → RouteLLM (ICLR 2025) → FrugalGPT Cascades → Catalog-decoupled & Decision models',14)
note(s,'进入第四部分：从模型与算法层面看，自动路由到底是怎么实现的？业界主要有四类通用做法：\n1. 规则与语义向量路由（如 Semantic Router）：算句向量与模板的距离，只需几毫秒，但它分不清“写个冒泡排序”和“写个无锁并发队列”在推理深度上的天壤之别；\n2. 二分类偏好路由（如开源代表 RouteLLM）：训练分类器预测“强模型赢弱模型的概率”，但致命痛点是模型身份写死在权重里——如今每个月都有新模型发布，模型池一换就得重训；\n3. 级联（FrugalGPT）：先跑小模型再验质量，缺点是难任务要串行跑两次；\n4. 通用大模型当路由：提示词零样本就能跑，但延迟高达几百到两千毫秒，而且生成式模型受 RLHF 奖励影响天生过度自信，概率严重失准。')

# ---------- 14 MICROSOFT'S APPROACH: GITHUB HYDRA (ARXIV:2605.17106)
s=14
header(s,'04 · MICROSOFT’S ARCHITECTURE · HYDRA','GitHub HyDRA: decouple demand & catalog')
ix=M; iy=1540000; icw=6040000; ich=3398000
rect(s,ix,iy,icw,ich,fill='111315',line=EDGE,lw=12700)
img(s,'hydra-pareto.png',ix+30000,iy+30000,icw-60000,ich-60000,'Official GitHub chart: HyDRA on the 5-model production pool — Peak (+1.2% > Sonnet at -12.9% cost), Cons (-54.1% cost), Agg (-72.5% cost)',fit='contain')
card_box(s,ix,5060000,icw,920000,[
    {'text':'ModernBERT (86 ms) → d(q) = [Reason, CodeGen, Debug, Tools]','sizePt':11.5,'bold':True,'color':CODE,'spaceAfterPt':7},
    {'text':'Pick argmin cost(m)  s.t.  shortfall(d(q), profile(m)) ≤ τ','sizePt':11.5,'color':INK},
],fill=CODEBG,line=EDGE,lw=12700,pad_x=200000,pad_y=90000,font=MF)
rx=ix+icw+260000; rw=W-M-rx
hy_cards=[
    ('4-Head Capability Encoder','ModernBERT with K=4 sigmoid heads scores Reasoning, CodeGen, Debugging & Tool Use in 86 ms median CPU latency.',CY),
    ('Zero-Retraining Catalog Updates','Models are config profiles, not output classes! Adding GPT-6 is a config edit — 6× more savings (54.1%) than binary routing.',CY),
    ('Language-Invariant (16 Families)','Trained on full multi-turn trajectories across 19 languages (including CJK), staying within 4 pts of English baseline.',AMB),
]
for i,(t,d,col_) in enumerate(hy_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.8,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'Source: Garg et al., HyDRA: Hybrid Dynamic Routing Architecture for Heterogeneous LLM Pools (arXiv:2605.17106, Jun 2026)',15)
note(s,'那微软是怎么解决“新模型频繁迭代导致路由器重训”这个行业难题的？来看看支撑 GitHub Copilot 的论文《HyDRA》（arXiv:2605.17106）：\n微软没有让分类器直接预测“选模型 A 还是模型 B”，而是用轻量级 ModernBERT 挂载 4 个独立的 Sigmoid 头，在 CPU 上仅用 86 毫秒中位延迟，预测当前请求在“推理深度、代码生成、调试难度、工具编排”四个维度的能力需求向量 d(q)！\n接着通过 Shortfall Matching（短板匹配算法），将需求向量与配置文件中定义的各模型能力画像比对，选出满足阈值 τ 且实时健康的最便宜模型。新模型上线只需改一行配置，零重训！在 SWE-Bench Verified 上，等质量下节省 54.1% 成本（是上一代二分类路由器的 6 倍），Peak 档甚至超越单跑 Sonnet 4.6（75.4% vs 74.2%）同时省钱 12.9%。')

# ---------- 15 MICROSOFT'S THREE-LAYER ROUTING STACK
s=15
header(s,'04 · MICROSOFT’S ARCHITECTURE · BLUEPRINT','Microsoft’s three-layer routing stack')
img(s,'hd-sorter.jpg',M,1780000,4980000,3320000,'Hand-drawn robot sorting incoming tasks into three policy-governed trays')
rx=M+4980000+320000; rw=W-M-rx
layers=[
    ('Layer 1 · Deterministic Policy & Cache Gate','Hard code filters tenant-allowed providers, data zones, required tool/schema capabilities, and warm prefix-cache state.',CY),
    ('Layer 2 · Fast Scorer / Decision Model (<180 ms)','Purpose-built encoder (HyDRA / Foundry ML ranker) or Microsoft-Decision-1.1 produces calibrated scores over allowed options.',CY),
    ('Layer 3 · Workflow Pattern & Output Verifier','Executes Single, Cascade or Critique, then runs deterministic schema, citation or Noul safety checks before acting.',AMB),
]
ch_=1320000; gap_=260000; y0_=1520000
for i,(t,d,col_) in enumerate(layers):
    yy=y0_+i*(ch_+gap_)
    card_box(s,rx,yy,rw,ch_,[
        {'text':t,'sizePt':16.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13.2,'color':MUTED},
    ],fill=CARD,pad_x=220000,pad_y=95000)
    if i<2:
        rect(s,rx+rw/2-100000,yy+ch_+45000,200000,170000,fill=CY if i==0 else AMB,preset='downArrow')
footer(s,'Core principle: models score bounded options; deterministic code enforces policy gates, thresholds, and fallbacks',16)
note(s,'把 M365 Copilot、GitHub Copilot Fusion 和 Foundry 放在一起，微软在模型路由上的工程哲学可以浓缩为这三层蓝图：\n第一层永远是确定性代码守门：租户合规边界、数据驻留、必需参数支持以及前缀缓存状态，绝不让模型去猜权限；\n第二层是毫秒级专用评分器（86–180 ms）：无论是内部多头能力编码器 HyDRA，还是开放给开发者的 Microsoft-Decision-1.1，只对合法候选做快速、校准过的打分；\n第三层是执行拓扑与后置验证：根据分差决定走单模型、级联还是并行评审，并在返回用户前完成结构与合规校验。那么，开发者如何把第二层和第三层的同款大脑装进自己的系统？这就引出了 Microsoft-Decision-1.1。')

# ---------- 16 PART 5: MEET MICROSOFT-DECISION-1.1
s=16
header(s,'05 · MICROSOFT DECISION-1.1','Meet Microsoft-Decision-1.1')
cw_=5480000; cy0=1520000; ch=2880000
card_box(s,M,cy0,cw_,ch,[
    {'text':'Generative LLMs as routers','sizePt':19.5,'bold':True,'color':MUTED,'spaceAfterPt':7},
    {'text':'Trained to sound helpful & complete tasks','sizePt':13.8,'bold':True,'color':AMB,'spaceAfterPt':10},
    {'text':'• Autoregressive tokens add 500–2,000 ms latency','sizePt':13.8,'color':MUTED,'spaceAfterPt':7},
    {'text':'• RLHF rewards confident guesses on missing info','sizePt':13.8,'color':MUTED,'spaceAfterPt':7},
    {'text':'• Fragile JSON parsing & option-order bias','sizePt':13.8,'color':MUTED},
],fill=CARD,pad_x=240000,pad_y=130000)
rx=W-M-cw_
card_box(s,rx,cy0,cw_,ch,[
    {'text':'Microsoft-Decision-1.1  (GA Nov 2026)','sizePt':19.5,'bold':True,'color':INK,'spaceAfterPt':7},
    {'text':'Trained from first principles for calibrated control','sizePt':13.8,'bold':True,'color':CY,'spaceAfterPt':10},
    {'text':'• Gemma 4 26B-A4B MoE + custom single-pass engine','sizePt':13.8,'color':INK,'spaceAfterPt':7},
    {'text':'• Multimodal (text, JSON, photos/UI), zero prose bloat','sizePt':13.8,'color':INK,'spaceAfterPt':7},
    {'text':'• Calibrated confidence + 1.3% shuffle flip rate','sizePt':13.8,'color':INK},
],fill=CARD2,line=CY,lw=25400,pad_x=240000,pad_y=130000)
gap4=160000; tw4=(CW-3*gap4)/4; ty=4560000; th4=1400000
facts=[
    ('$0.042 / 1M','Input tokens (Global Std); output tokens FREE!',CY),
    ('~123 ms','AA Decision Index time (2.2× faster than v1.0)',CY),
    ('35×–100×','Faster than frontier LLMs on routing & QC',CY),
    ('3 Clouds','Microsoft Foundry, OpenRouter & Vercel',AMB),
]
for i,(v,l,col_) in enumerate(facts):
    xx=M+i*(tw4+gap4)
    card_box(s,xx,ty,tw4,th4,[
        {'text':v,'sizePt':23,'bold':True,'color':col_,'spaceAfterPt':6},
        {'text':l,'sizePt':12.8,'color':INK},
    ],fill=CODEBG,line=EDGE,lw=12700,pad_x=180000,pad_y=120000)
footer(s,'Sources: Achint Srivastava, Command Line — Microsoft-Decision-1 (Oct 2026) & Microsoft-Decision-1.1 GA (Nov 17, 2026)',17)
note(s,'为什么微软要专门造一类新模型——Decision Model（决策模型）？\n生成式大模型是为了“写完回答、听起来自信”而训练的，逐个生成推理 Token 既慢又贵，而且面对信息缺失时倾向于自信地瞎猜。Microsoft-Decision-1（基于 Qwen3.5-9B 后训练）及其正式版 Microsoft-Decision-1.1（2026 年 11 月 17 日 GA，基于 Gemma 4 26B-A4B 混合专家架构，仅 4B 激活参数，配合定制单次前向决策推理引擎）彻底改变了范式：\n它不生成废话，直接对文本、JSON 甚至图片截图输出经过严格概率校准的结构化决策！Global Standard 输入仅 $0.042/百万 Token，输出 Token 完全免费，速度比上一代再快 2.2 倍，选项打乱或改写时翻转率仅 1.3%。')

# ---------- 17 DECISION-1.1 BENCHMARKS & INTERNAL WINS
s=17
header(s,'05 · MICROSOFT DECISION-1.1 · BENCHMARKS','#1 across 102 decision benchmarks')
ix=M; iy=1540000; icw=5950000; ich=3400000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'decision-aa-index.svg',ix+40000,iy+40000,icw-80000,ich-80000,'Vector SVG chart: Artificial Analysis Decision Index v2.1 vs Time per Task — Microsoft-Decision-1.1 scores 68 (+6 pts, 2.2x faster)',fit='contain')
card_box(s,ix,5080000,icw,920000,[
    {'text':'102-BENCHMARK BLIND EVAL  ·  385,246 QUESTIONS','sizePt':11,'bold':True,'color':CY,'spaceAfterPt':6},
    {'text':'#1 overall (78.8%): Tools & agents 86.6 · Routing 81.7 · Safety 85.6 · Consistency 91.8','sizePt':12,'color':INK},
],fill=CODEBG,line=EDGE,lw=12700,pad_x=200000,pad_y=95000,font=MF)
rx=ix+icw+240000; rw=W-M-rx
card_box(s,rx,1540000,rw,1240000,[
    {'text':'AA Decision Index v2.1: Score 68','sizePt':15.2,'bold':True,'color':CY,'spaceAfterPt':7},
    {'text':'+6 pts & 2.2× faster than Decision-1; ahead of Jev 1.14 (66), Gemini Decision 1 (66) & GPT-6 Luna Decisions (60).','sizePt':12.4,'color':MUTED},
],fill=CARD,pad_x=200000,pad_y=95000)
card_box(s,rx,2900000,rw,1240000,[
    {'text':'Generalizes Across 7 of 9 Domains','sizePt':15.2,'bold':True,'color':CY,'spaceAfterPt':7},
    {'text':'Leads classification, routing, tool selection, grounded rules, judging, safety & consistency with zero training overlap.','sizePt':12.4,'color':MUTED},
],fill=CARD,pad_x=200000,pad_y=95000)
card_box(s,rx,4260000,rw,1740000,[
    {'text':'Powering Microsoft & 4,000+ Customers','sizePt':15.2,'bold':True,'color':AMB,'spaceAfterPt':7},
    {'text':'• Copilot Chat→Cowork: 2.2× faster, 4.4× cheaper','sizePt':12.2,'color':INK,'spaceAfterPt':5},
    {'text':'• Cowork Auto effort + Foundry Evaluation judge','sizePt':12.2,'color':INK,'spaceAfterPt':5},
    {'text':'• Xbox Research: 14× faster, 200× cheaper than Sol','sizePt':12.2,'color':INK,'spaceAfterPt':5},
    {'text':'• Adopted by Epic, Equinor, Atos & Raiffeisen Bank','sizePt':12.2,'color':INK},
],fill=CARD,pad_x=200000,pad_y=90000)
footer(s,'Sources: Artificial Analysis Decision Index v2.1 (Nov 16, 2026) & Microsoft 102-Benchmark Report (Nov 14, 2026)',18)
note(s,'左边是从微软官方发布页提取的 Artificial Analysis Decision Index v2.1 实测散点图：横轴是单任务耗时（对数坐标），纵轴是综合质量与校准指数。Microsoft-Decision-1.1 跃升至 68 分，耗时仅约 123 ms，稳居左上角黄金象限，超越 Google Gemini Decision 1、Jev 1.14 和 OpenAI GPT-6 Luna Decisions。\n在包含 38.5 万道盲测题的 102 个基准测试中，它以 78.8% 的平均准确率夺冠，并在 9 个能力维度中的 7 个排名第一（工具与 Agent 达 86.6%、路由分类 81.7%、一致性 91.8%）。上线仅五周已有超 4000 家企业采用；在微软内部，它支撑了 Copilot 体验分流、Cowork 动态推理档位、Foundry 评估裁判，以及 Xbox Research（比 GPT-6 Sol 快 14 倍、便宜 200 倍）。')

# ---------- 18 DECISION-1.1 THREE TYPED PRIMITIVES
s=18
header(s,'05 · MICROSOFT DECISION-1.1 · API PRIMITIVES','Three primitives: choice, noul, score')
gap=180000; cw3=(CW-2*gap)/3; y0=1540000; ch=2360000
prims=[
    ('01 · choice','“Which option is it?”','Selects one label from criteria + calibrated probability per option.\nUse: model routing, ticket triage, tool pick.',CY),
    ('02 · noul','“Is this condition true?”','Returns a single probability in [0, 1] for true vs. false criteria.\nUse: safety gates, refund/rival checks, photo damage.',CY),
    ('03 · score','“How much on a scale?”','Probability-weighted expected index (0..N-1) on ordered levels.\nUse: P0–P3 incident scheduling, output grading.',AMB),
]
for i,(k,sub,desc,col_) in enumerate(prims):
    x=M+i*(cw3+gap)
    card_box(s,x,y0,cw3,ch,[
        {'text':k,'sizePt':19,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':sub,'sizePt':13.5,'bold':True,'color':INK,'spaceAfterPt':8},
        {'text':desc,'sizePt':12.8,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
rect(s,M,4060000,CW,1920000,fill=CODEBG,line=EDGE,lw=12700)
tb(s,M+220000,4150000,CW-440000,'POST <foundry-endpoint>/providers/microsoft/v1/systemone   ·   Combine multiple questions in ONE call!',size=11,color=FOOT,font=MF,cy=260000)
api_code=(
    '{ "model": "pi-decision-1.1", "state": {"msg": "Checkout is down in EU (3rd ping).", "contacts": 3},\n'
    '  "questions": {\n'
    '    "route":    {"type": "choice", "instructions": "Pick tier", "criteria": {"slm":"FAQ","sol":"Incident"}},\n'
    '    "severity": {"type": "score",  "instructions": "Severity",  "criteria": ["Cosmetic","Minor","Major","Critical"]},\n'
    '    "escalate": {"type": "noul",   "instructions": "Needs immediate human on-call?"} } }'
)
tb(s,M+220000,4460000,CW-440000,api_code,size=11.5,color=CODE,font=MF,cy=1420000)
footer(s,'Source: Microsoft Learn — Deploy and use Microsoft-Decision-1.1 in Microsoft Foundry',19)
note(s,'它的 API 设计极度干净，被命名为 systemone（对应人类直觉快思考 System 1）：向 `/providers/microsoft/v1/systemone` 发送一个 `state`（文本、JSON 或引用 base64 图片）和一组强类型 `questions`，支持三种原语：\n1. `choice`（多选一）：返回选中标签及每个候选的概率分布，最适合做模型路由——如果最高概率低于你设定的阈值（如 0.75），代码直接升级或转人工；\n2. `noul`（二元真假门）：返回 0 到 1 的单值概率，最适合做前置/后置护栏（是否承诺退款、是否包含注入、快递照片是否破损）；\n3. `score`（有序量表打分）：对 `0..N-1` 等级计算概率加权期望分，最适合排工单优先级或给大模型输出打分。\n最棒的是：同一个 `state` 可以把这三个问题打包在一次请求里同时返回！')

# ---------- 19 FOUR CONCRETE DECISION-1.1 EXAMPLES
s=19
header(s,'05 · MICROSOFT DECISION-1.1 · EXAMPLES','Four production Decision-1.1 patterns')
g=180000; tw=(CW-g)/2; th=2120000; y0=1540000
examples=[
    ('1 · Custom LLM & Agent Router (choice)',
     'state: prompt + token_count + attachment_meta',
     'criteria: { mai_flash, sonnet_5_5, opus_critique, ask_clarify }\n→ If max(p) < 0.75 or choice == ask_clarify, clarify before burning frontier credits!',CY),
    ('2 · Support Triage + SLA Queue (choice + score)',
     'state: {"msg": "Bed frame collapsed, hurt back!", "vip": true}',
     'Single call returns team = "safety_support" (0.95) AND priority.score = 2.94 / 3.0 → Math.round(score) == P3 pages immediate human.',CY),
    ('3 · Multimodal Photo & UI Gate (assets + noul)',
     'state: "Delivery photo: image:box.png" + base64 PNG',
     'questions.damaged = { type: "noul", instructions: "Shows physical damage?" }\n→ p >= 0.80 auto-replaces; 0.35–0.80 routes to claims adjuster.',CY),
    ('4 · Outbound LLM Guardrail Filter (noul)',
     'state: { customer_msg, agent_draft_reply }',
     'Independent noul checks: mentions_competitor, unapproved_discount, medical_claim.\n→ Hold draft if ANY noul >= 0.50; catches “Try Fabrikam for $749”!',AMB),
]
for i,(title_,st_,body_,col_) in enumerate(examples):
    x=M+(i%2)*(tw+g); yy=y0+(i//2)*(th+180000)
    card_box(s,x,yy,tw,th,[
        {'text':title_,'sizePt':16,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':st_,'sizePt':11.8,'bold':True,'color':CODE,'spaceAfterPt':7},
        {'text':body_,'sizePt':12.8,'color':INK},
    ],fill=CARD,pad_x=220000,pad_y=110000)
footer(s,'Best practice: tune instructions/criteria on labeled dev examples, randomize option order, and lock thresholds on holdout',20)
note(s,'这里给出四个可直接抄进生产架构的 Microsoft-Decision-1.1 实战例子：\n例 1（自定义大模型路由器）：用 `choice` 把请求分流到轻量 Flash、常规 Sonnet、深度 Critique 或“缺少信息需追问”，当最高置信度低于 0.75 时先追问，不白烧大模型算力；\n例 2（多问题合一客服分诊）：一次请求同时用 `choice` 分团队、用 `score` 定 P0–P3 紧急度，遇到人身伤害风险直接跳过 Bot 呼叫人工；\n例 3（多模态图片判定）：利用 1.1 新增的 `assets` 图片输入能力，毫秒级判断退货快递照片是否破损，或辅助 Computer Use 选下一步按钮；\n例 4（大模型出站合规网）：在生成式 Agent 回复发给客户前，用一组独立的 `noul` 规则检查是否提到了竞品、违规承诺折扣或医疗建议，任一达到 50% 即拦截转审。')

# ---------- 20 CONTOSO 7.2X CAC CASE STUDY VECTOR SVG
s=20
header(s,'05 · MICROSOFT DECISION-1.1 · IMPACT','Three $0.00019 checks cut CAC 7.2×',cx=CW-2300000)
ix=M; iy=1540000; icw=6100000; ich=4400000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'decision-cac-waterfall.svg',ix+50000,iy+50000,icw-100000,ich-100000,'Vector SVG chart: Contoso $10,000/mo sales agent Cost-per-Lead waterfall and 32-reply 100% accuracy router benchmark',fit='contain')
rx=ix+icw+260000; rw=W-M-rx
steps_cac=[
    ('Baseline: All-Sol + 100% review','$0.31 / lead  ·  CAC = $13.00','Every reply hits frontier Sol ($0.15) plus 100% human review ($0.24), capping a $10k budget.',MUTED),
    ('+ Check 1 (Router) + Check 2 (Score)','$0.07 / lead  ·  CAC = $2.63','100% accuracy (vs 88% regex): 57% skip Sol via no-reply & code replies; only P1–P3 hit humans.',CY),
    ('+ Check 3 (noul Filter) → Full Stack','$0.05 / lead  ·  CAC = $1.81','All 3 MD-1.1 checks cost ~$0.000189/msg — human review drops 100% → 8% for 7.2× more customers!',AMB),
]
for i,(t,sub,desc,col_) in enumerate(steps_cac):
    yy=1540000+i*1510000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15,'bold':True,'color':INK if col_==MUTED else col_,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':12.2,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.2,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=95000)
footer(s,'Source: Microsoft Command Line Interactive Architecture Demo (Illustrative Contoso $10k/mo sales agent model; Demo 3)',21)
note(s,'左边是我们运行微软官方 Decision-1.1 交互架构演示并截取的实况画面：在 32 条客户邮件分流测试中，手写关键词正则准确率只有 88%，而 Microsoft-Decision-1.1 达到 100% 准确率，P50 延迟 180 ms，跑完全部 32 条总计只花了 0.0004 美元！\n把三道检查串成流水线后，商业账本发生了质变：原本每条回复都调昂贵的 Sol 模型且 100% 人工复核，单线索成本 $0.31，获客成本（CAC）高达 $13；加上 Decision-1.1 的路由（省掉 57% 大模型调用）、优先级调度和竞品合规拦截后，三道决策检查加起来每条仅花 $0.000189，人工复核比例从 100% 降到 8%，同样 1 万美元月预算获客数从 764 飙升到 5,511，CAC 暴降 7.2 倍至 $1.81！')

# ---------- 21 LIVE DEMO 1: GITHUB COPILOT AUTO & FUSION
s=21
header(s,'05 · INTERACTIVE DEMO 1','Copilot Auto & Fusion replay',cx=CW-3400000)
cx_=5550000; cy0=1540000; chh=4420000
rect(s,M,cy0,cx_,chh,fill=CODEBG,line=EDGE,lw=12700)
tb(s,M+220000,cy0+140000,cx_-440000,'copilot-fusion-trace.jsonl  ·  HyDRA + Fusion',size=11,color=FOOT,font=MF,cy=280000)
d1_code=(
    '$ copilot -p "Extract default port" --model auto\n'
    '-> MAI Code 2 Flash (0.08 cr · 1.8s · Single)\n\n'
    '$ copilot -p "Fix deadlock in refill()" \\\n'
    '    --model copilot-fusion --reasoning-effort high\n'
    '-> Primary: gpt-5.6-luna\n'
    '-> Judge  : claude-sonnet-5.5 (ESCALATE)\n'
    '-> Repair : gpt-6.1-sol (500× stress PASS)'
)
tb(s,M+220000,cy0+480000,cx_-440000,d1_code,size=12,color=CODE,font=MF,cy=2600000)
card_box(s,M+220000,cy0+3260000,cx_-440000,960000,[
    {'text':'PS> npm --prefix demo run demo:fusion','sizePt':11.5,'bold':True,'color':INK,'spaceAfterPt':7},
    {'text':'Single → Cascade → Critique → Warm Cache','sizePt':11,'color':CY},
],fill=CARD2,line=EDGE,lw=12700,pad_x=180000,pad_y=90000,font=MF)
rx=M+cx_+320000; rw=W-M-rx
d1_cards=[
    ('✓  Single & Cascade short-circuit','MAI Flash (0.08 cr) & Haiku + Judge','Simple lookups and clean unit-tested patches finish fast at 52%–94% lower credit cost.',CY),
    ('↗  Judge-triggered escalation','Cascade Repair on subtle concurrency bug','When lock ordering is inverted, Judge escalates to GPT-6.1 Sol for a clean fresh-start repair.',AMB),
    ('⇄  Parallel Critique + Warm Cache','Read-only Critics & 90% cache_read discount','50k-RPS design audited by 2 Critics; follow-up turn stays on cached model (10× cheaper).',CY),
]
for idx,(t,sub,desc,col_) in enumerate(d1_cards):
    yy=1540000+idx*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':INK,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':11.8,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=95000)
footer(s,'Click “Launch Demo 1” (top right) or press D in web view to step through all 5 Copilot Fusion traces',22)
note(s,'现在进入激动人心的交互演示环节！在网页版点击右上角按钮（或按键盘 D 键），即可打开内置的 Interactive Routing Studio。\nDemo 1 回放我们在本机捕获的 GitHub Copilot CLI Auto 与 Copilot Fusion 五步完整轨迹：第 1 步简单提取命中 MAI Code 2 Flash 仅花 0.08 Credits；第 2 步常规改造走 Cascade 被 Judge 直接放行省下 52% 费用；第 3 步并发死锁被 Judge 精准识破并升级给 GPT-6.1 Sol 修复；第 4 步高优架构设计触发并行只读 Critique 揪出两个分布式隐患；第 5 步验证多轮前缀缓存保护（复用 64.2k Token，立省 90%）。')

# ---------- 22 LIVE DEMO 2: MICROSOFT COPILOT & FOUNDRY MODEL ROUTER
s=22
header(s,'05 · INTERACTIVE DEMO 2','Foundry Router & Copilot replay',cx=CW-3400000)
cx_=5550000; cy0=1540000; chh=4420000
rect(s,M,cy0,cx_,chh,fill=CODEBG,line=EDGE,lw=12700)
tb(s,M+220000,cy0+140000,cx_-440000,'foundry-v1preview.http  ·  ModelRouterControls=V1Preview',size=11,color=FOOT,font=MF,cy=280000)
d2_code=(
    'POST /openai/v1/chat/completions\n'
    'Foundry-Features: ModelRouterControls=V1Preview\n'
    '{\n'
    '  "model": "model-router",\n'
    '  "routing_config": {\n'
    '    "mode": "balanced",\n'
    '    "session_affinity": { "strategy": "adaptive" }\n'
    '  }\n'
    '}\n'
    '// Simple JSON -> DeepSeek-V4.1-Flash (23 ms)\n'
    '// Rust ABA    -> gpt-5.6-luna        (20 ms)'
)
tb(s,M+220000,cy0+480000,cx_-440000,d2_code,size=11.5,color=CODE,font=MF,cy=2640000)
card_box(s,M+220000,cy0+3260000,cx_-440000,960000,[
    {'text':'PS> npm --prefix demo run demo:foundry','sizePt':11.5,'bold':True,'color':INK,'spaceAfterPt':7},
    {'text':'Live Foundry endpoint or instant verified replay','sizePt':11,'color':CY},
],fill=CARD2,line=EDGE,lw=12700,pad_x=180000,pad_y=90000,font=MF)
rx=M+cx_+320000; rw=W-M-rx
d2_cards=[
    ('✓  20–23 ms ML routing overhead','DeepSeek-V4.1-Flash vs. gpt-5.6-luna','Real Foundry V1Preview traces show ~21 ms routing overhead separating simple JSON from formal proofs.',CY),
    ('⇄  M365 Copilot 4-job orchestration','Decision-1.1 + SLM + Opus 5.5 + GPT Image 2.5','Replays the full Thursday customer renewal workflow across retrieval, reasoning, visuals & deck.',CY),
    ('↺  Transparent 429 → 200 failover','PTU → PAYG → Managed → Next-ranked model','Simulates a rate-limit burst on gpt-6-sol and verifies 19 ms automatic failover to gpt-5.6-sol.',AMB),
]
for idx,(t,sub,desc,col_) in enumerate(d2_cards):
    yy=1540000+idx*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':INK,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':11.8,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=95000)
footer(s,'Click “Launch Demo 2” (top right) — or run npm --prefix demo run demo:web for live Foundry bridge',23)
note(s,'Demo 2 串联了云端 API 层的 Foundry Model Router 实测抓包与应用层的 Microsoft 365 Copilot 多模型协同：\n第 1 步检查租户数据边界与 PTU 容量优先级；第 2 步发送简单发票 JSON 提取，实测路由耗时仅 23 毫秒，自动落到零推理开销的 DeepSeek-V4.1-Flash；第 3 步换成高难度 Rust 无锁环形缓冲区 ABA 形式化分析，20 毫秒内自动升级至推理模型 gpt-5.6-luna；第 4 步完整回放 Microsoft Copilot 续约提案的四子任务跨模型接力；第 5 步演示主模型触发 429 限流时，19 毫秒无缝切至次优合格模型返回 200 OK。')

# ---------- 23 LIVE DEMO 3: MICROSOFT-DECISION-1.1 CONTROLLER
s=23
header(s,'05 · INTERACTIVE DEMO 3','Decision-1.1 agent controller',cx=CW-3400000)
cx_=5550000; cy0=1540000; chh=4420000
rect(s,M,cy0,cx_,chh,fill=CODEBG,line=EDGE,lw=12700)
rect(s,M+cx_-1480000,cy0+130000,1240000,320000,fill=CY,preset='roundRect',text='GA · Nov 2026',size=10.5,bold=True,color=BG)
tb(s,M+220000,cy0+130000,cx_-1800000,'decision-controller.ts  ·  /v1/systemone',size=11,color=FOOT,font=MF,cy=320000)
d3_code=(
    'const res = await systemOne({\n'
    '  model: "microsoft-decision-1.1",\n'
    '  state: { customer_msg, draft_reply },\n'
    '  questions: {\n'
    '    route:    { type: "choice", criteria: ROUTES },\n'
    '    priority: { type: "score",  criteria: P0_TO_P3 },\n'
    '    rival:    { type: "noul",   instructions: "Names rival?" }\n'
    '  }\n'
    '});\n'
    'if (res.priority.score >= 2.5) return pageHumanP3();\n'
    'if (res.rival.noul >= 0.50)    return holdDraft();'
)
tb(s,M+220000,cy0+490000,cx_-440000,d3_code,size=11.5,color=CODE,font=MF,cy=2640000)
card_box(s,M+220000,cy0+3260000,cx_-440000,960000,[
    {'text':'PS> npm --prefix demo run demo:decision','sizePt':11.5,'bold':True,'color':INK,'spaceAfterPt':7},
    {'text':'Click preset prompts or test your own in Studio!','sizePt':11,'color':CY},
],fill=CARD2,line=EDGE,lw=12700,pad_x=180000,pad_y=90000,font=MF)
rx=M+cx_+320000; rw=W-M-rx
d3_cards=[
    ('✓  choice Router + 0.0 pt spread','180 ms p50 · $0.000013/call · 57% skip Sol','Proves 5/5 identical probability stability and 100% inbox routing accuracy vs. 88% regex.',CY),
    ('!  score Scheduler (P0–P3)','Combined choice + score + noul in 1 call','“Bed frame collapsed, hurt back” scores 2.94/3.0 → bypasses bot for P3 Immediate Human.',AMB),
    ('✕  noul Guardrail + Safe Abstain','Blocks Fabrikam leak (0.964) & missing Exhibit B','Holds competitor-promoting drafts at ≥0.50, abstains when max(p)<0.75, and cuts CAC 7.2×.',CY),
]
for idx,(t,sub,desc,col_) in enumerate(d3_cards):
    yy=1540000+idx*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':INK,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':11.8,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=95000)
footer(s,'Click “Launch Demo 3” (top right) — and type your own custom prompt in the Studio input bar!',24)
note(s,'Demo 3 带大家亲手体验 Microsoft-Decision-1.1 如何作为 Agent 架构的控制中枢：\n第 1 步连续请求 5 次验证 0.0 pt 波动与 180 ms 极速响应；第 2 步用 `choice` 把致谢、退订、常规问答与复杂导购精准分流，省去 57% 昂贵大模型调用；第 3 步在单次请求中同时返回部门路由、P3 受伤紧急度打分（2.94）与重复联系判断；第 4 步用 `noul`（0.964）当场拦下大模型把客户推荐给竞品 Fabrikam 的翻车回复；第 5 步演示缺失合同附件时的低置信度安全弃权与 7.2 倍获客成本下降。此外，你还可以在 Studio 底部输入框现场输入任意自定义句子测试路由结果！')

# ---------- 24 CLOSER: KEY TAKEAWAYS
s=24
img(s,'hd-review.jpg',W-M-5040000,1620000,5040000,3360000,'Hand-drawn illustration: two friendly robots reviewing and approving a routed workflow together')
x=M+80000; cx=5850000
tb(s,x,420000,cx,'SUMMARY · KEY TAKEAWAYS',size=12,color=CY,font=HF,bold=True,ls=2,cy=260000)
tb(s,x,740000,cx,'Right-size the model,\nkeep the control',size=36,color=INK,font=HF,bold=True,cy=1200000)
tk=[
    '1   Route sub-tasks by capability — no single model wins all.',
    '2   Stop paying 100× for simple work — & keep prefix caches warm.',
    '3   Adopt Copilot Auto, Copilot Fusion & Foundry Router first.',
    '4   Embed Microsoft-Decision-1.1 for choice, noul & score gates.',
]
tb(s,x,2100000,cx,None,paras=[{'text':t,'spaceAfterPt':10} for t in tk],size=14.2,color=INK,cy=2380000)
tb(s,x,4660000,cx,None,paras=[
    {'text':'aka.ms/decision-1.1  ·  blog.genisisiq.com','spaceAfterPt':7},
    {'text':'github.com/microsoftconnect/Decision-Benchmarks'},
],size=12.5,color=CY,font=MF,cy=720000)
tb(s,x,5540000,cx,'Thank you  ·  Q&A',size=24,color=INK,font=HF,bold=True,cy=480000)
footer(s,'',25)
note(s,'最后总结四条可直接带回团队落地的建议：\n第一，告别“全公司绑死一个最强模型”的旧习惯，按子任务能力专长做多模型编排；\n第二，算总账（算力 Credits + 工程师等待时间），并严格在首轮或压缩等自然缓存边界路由，避免打碎 10 倍省钱的前缀缓存；\n第三，优先用好现成平台能力：日常办公开 Microsoft Copilot Auto，写代码开 GitHub Copilot Fusion，调云端推理用 Foundry Model Router；\n第四，当你的业务代码需要确定性的分类、分流、优先级调度或合规拦截时，用专门训练、毫秒级响应且概率校准的 Microsoft-Decision-1.1 替代缓慢昂贵的生成式提示词路由。感谢大家，欢迎提问！')

# ---------- 25 APPENDIX: PUBLIC REFERENCES
s=25
header(s,'APPENDIX · OFFICIAL SOURCES & BENCHMARKS','Public field guide')
gap=240000; colw=(CW-gap)/2; cy0=1540000; ch=4420000
app_cols=[
    ('Benchmarks & Product Routing','Capability specialization, 163× cost benchmarks, Microsoft Copilot Auto & GitHub Copilot Fusion.',REFS_LEFT,CY),
    ('Routing Architecture & Decision-1.1','HyDRA multi-head routing paper, Foundry Model Router internals, Decision-1.1 API & open benchmarks.',REFS_RIGHT,AMB),
]
for i,(t,sub,links,col_) in enumerate(app_cols):
    xx=M+i*(colw+gap)
    rect(s,xx,cy0,colw,ch,fill=CARD)
    tb(s,xx+240000,cy0+140000,colw-480000,None,paras=[
        {'text':t,'sizePt':18.5,'bold':True,'color':col_,'spaceAfterPt':6},
        {'text':sub,'sizePt':13,'color':MUTED},
    ],cy=980000)
    rect(s,xx+240000,cy0+1200000,colw-480000,14000,fill=EDGE)
    tb(s,xx+240000,cy0+1320000,colw-480000,None,paras=[
        {'text':f'↗  {label}','sizePt':12.8,'bold':True,'color':CY,'href':url,'spaceAfterPt':9}
        for label,url in links
    ],cy=ch-1460000)
footer(s,'All links above are clickable in both PowerPoint and the standalone HTML edition.',26)
note(s,'附录汇总了本次演讲引用的全部公开资料链接，包括 Charles Lamanna 的白板分享、GenisisIQ 的 28 模型创意与真实成本基准评测、Microsoft 365 Copilot Ignite 2026 公告与 Cowork 文档、GitHub Copilot Fusion 与 HyDRA 论文、Foundry Model Router 机制文档，以及 Microsoft-Decision-1.1 官方教程与开源评测集仓库。')


# ===================== BUILD-TIME LAYOUT VALIDATOR =====================
def validate_layout():
    errors=[]
    for k in sorted(slides):
        ops=slides[k]
        for o in ops:
            if o['cx']<=0 or o['cy']<=0 or o['x']<0 or o['y']<0 or o['x']+o['cx']>W or o['y']+o['cy']>H:
                errors.append(f'Slide {k+1}: {o["op"]} has invalid bounds')
        tbs=[o for o in ops if o['op']=='add_text_box']
        for o in tbs:
            if o.get('name')=='slide_title':
                txt=o.get('text') or o['paragraphs'][0]['text']
                if nlines(txt,o.get('sizePt',29.5),o['cx'],'Newsreader',True)>1:
                    errors.append(f'Slide {k+1}: header title wraps >1 line ({txt!r})')
        for i in range(len(tbs)):
            for j in range(i+1,len(tbs)):
                a,b=tbs[i],tbs[j]
                x_ov=min(a['x']+a['cx'],b['x']+b['cx'])-max(a['x'],b['x'])
                y_ov=min(a['y']+a['cy'],b['y']+b['cy'])-max(a['y'],b['y'])
                if x_ov>20000 and y_ov>0:
                    ta=(a.get('text') or a['paragraphs'][0]['text'])[:30]
                    tb_=(b.get('text') or b['paragraphs'][0]['text'])[:30]
                    errors.append(f'Slide {k+1}: textbox overlap ({y_ov} EMU) between {ta!r} and {tb_!r}')
    if errors:
        raise ValueError('Layout validation failed:\n  ' + '\n  '.join(errors))

# ===================== WRITER (python-pptx) =====================
PRESETS={'rect':MSO_SHAPE.RECTANGLE,'roundRect':MSO_SHAPE.ROUNDED_RECTANGLE,'ellipse':MSO_SHAPE.OVAL,
         'rightArrow':MSO_SHAPE.RIGHT_ARROW,'leftArrow':MSO_SHAPE.LEFT_ARROW,'downArrow':MSO_SHAPE.DOWN_ARROW,
         'chevron':MSO_SHAPE.CHEVRON,'homePlate':MSO_SHAPE.PENTAGON}
ALIGN={'left':PP_ALIGN.LEFT,'center':PP_ALIGN.CENTER,'right':PP_ALIGN.RIGHT}
rgb=lambda h:RGBColor.from_string(h)

def write_text(tf,o):
    tf.word_wrap=True; tf.vertical_anchor=MSO_ANCHOR.MIDDLE
    tf.margin_left=Emu(76200); tf.margin_right=Emu(76200)
    tf.margin_top=Emu(57150); tf.margin_bottom=Emu(57150)
    paras=o.get('paragraphs') or [{'text':o['text']}]
    raw_font=o.get('fontFamily',BF)
    default_sa=o.get('spaceAfterPt', 2.0 if raw_font==MF else 6.5)
    for i,p in enumerate(paras):
        para=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        para.alignment=ALIGN[p.get('align',o.get('align','center'))]
        sz=p.get('sizePt',o.get('sizePt',16))
        para.line_spacing=1.35 if raw_font==MF else (1.12 if sz>=29 else 1.24)
        if i<len(paras)-1:
            para.space_after=Pt(p.get('spaceAfterPt',default_sa))
        lines=p['text'].split('\n')
        for j,line in enumerate(lines):
            if j: para.add_line_break()
            r=para.add_run(); r.text=line
            if p.get('href'): r.hyperlink.address=p['href']
            f=r.font
            f.name=raw_font; f.size=Pt(sz)
            f.bold=p.get('bold',o.get('bold',False)); f.color.rgb=rgb(p.get('color',o.get('color',INK)))
            if o.get('letterSpacingPt'): r._r.get_or_add_rPr().set('spc',str(int(o['letterSpacingPt']*100)))

def add_picture(sl,o,img_dir):
    path=os.path.join(img_dir,os.path.basename(o['path']))
    if path.lower().endswith('.svg'):
        path=path[:-4]+'.png'
    with Image.open(path) as image:
        iw,ih=image.size
    x,y,cx,cy=o['x'],o['y'],o['cx'],o['cy']
    fr=cx/cy; ir=iw/ih
    if o.get('fit')=='contain':
        if ir>fr:
            nh=int(cx/ir); y=int(y+(cy-nh)/2); cy=nh
        else:
            nw=int(cy*ir); x=int(x+(cx-nw)/2); cx=nw
        pic=sl.shapes.add_picture(path,Emu(x),Emu(y),Emu(cx),Emu(cy))
    else:
        pic=sl.shapes.add_picture(path,Emu(x),Emu(y),Emu(cx),Emu(cy))
        if abs(ir-fr)>1e-4:
            if ir>fr: c=(1-fr/ir)/2; pic.crop_left=pic.crop_right=c
            else:     c=(1-ir/fr)/2; pic.crop_top=pic.crop_bottom=c
    pic._element.nvPicPr.cNvPr.set('descr',o.get('altText',''))

def add_appear_animation(sl,item_shapes):
    next_id=3
    item_nodes=[]
    for shapes in item_shapes:
        outer_id=next_id; inner_id=next_id+1; next_id+=2
        effects=[]
        for index,shape in enumerate(shapes):
            effect_id=next_id; behavior_id=next_id+1; next_id+=2
            node_type='clickEffect' if index==0 else 'withEffect'
            effects.append(
                f'<p:par><p:cTn id="{effect_id}" presetID="1" presetClass="entr" '
                f'presetSubtype="0" fill="hold" grpId="0" nodeType="{node_type}">'
                '<p:stCondLst><p:cond delay="0"/></p:stCondLst>'
                '<p:childTnLst><p:set><p:cBhvr>'
                f'<p:cTn id="{behavior_id}" dur="1" fill="hold">'
                '<p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                f'<p:tgtEl><p:spTgt spid="{shape.shape_id}"/></p:tgtEl>'
                '<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>'
                '</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
                '</p:childTnLst></p:cTn></p:par>'
            )
        item_nodes.append(
            f'<p:par><p:cTn id="{outer_id}" fill="hold">'
            '<p:stCondLst><p:cond delay="indefinite"/></p:stCondLst>'
            '<p:childTnLst><p:par>'
            f'<p:cTn id="{inner_id}" fill="hold">'
            '<p:stCondLst><p:cond delay="0"/></p:stCondLst>'
            f'<p:childTnLst>{"".join(effects)}</p:childTnLst>'
            '</p:cTn></p:par></p:childTnLst></p:cTn></p:par>'
        )
    build_nodes=[]
    for shapes in item_shapes:
        for index,shape in enumerate(shapes):
            anim_bg=' animBg="1"' if index==0 else ''
            build_nodes.append(f'<p:bldP spid="{shape.shape_id}" grpId="0"{anim_bg}/>')
    timing=parse_xml(
        f'<p:timing {nsdecls("p")}>'
        '<p:tnLst><p:par>'
        '<p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
        '<p:childTnLst><p:seq concurrent="1" nextAc="seek">'
        '<p:cTn id="2" dur="indefinite" nodeType="mainSeq">'
        f'<p:childTnLst>{"".join(item_nodes)}</p:childTnLst>'
        '</p:cTn>'
        '<p:prevCondLst><p:cond evt="onPrev" delay="0">'
        '<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0">'
        '<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
        '</p:seq></p:childTnLst></p:cTn>'
        '</p:par></p:tnLst>'
        f'<p:bldLst>{"".join(build_nodes)}</p:bldLst>'
        '</p:timing>'
    )
    sl._element.insert_element_before(timing,'p:extLst')

def build(out,img_dir):
    validate_layout()
    out_dir=os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir,exist_ok=True)
    prs=Presentation(); prs.slide_width,prs.slide_height=Emu(W),Emu(H)
    blank=prs.slide_layouts[6]
    for k in sorted(slides):
        sl=prs.slides.add_slide(blank)
        sl.background.fill.solid(); sl.background.fill.fore_color.rgb=rgb(BG)
        rendered=[]
        for o in slides[k]:
            op=o['op']
            if op=='add_image': add_picture(sl,o,img_dir)
            elif op=='add_text_box':
                sh=sl.shapes.add_textbox(Emu(o['x']),Emu(o['y']),Emu(o['cx']),Emu(o['cy'])); write_text(sh.text_frame,o)
                rendered.append(sh)
            elif op=='add_shape':
                sh=sl.shapes.add_shape(PRESETS[o['preset']],Emu(o['x']),Emu(o['y']),Emu(o['cx']),Emu(o['cy']))
                sh.shadow.inherit=False
                sh.fill.solid(); sh.fill.fore_color.rgb=rgb(o['fill'])
                if o.get('line'): sh.line.color.rgb=rgb(o['line']); sh.line.width=Emu(o.get('lineWidth',12700))
                else: sh.line.fill.background()
                if o.get('rot'): sh.rotation=o['rot']/60000
                if 'text' in o: write_text(sh.text_frame,o)
                rendered.append(sh)
        if k==3:
            add_appear_animation(sl,[rendered[start:start+5] for start in (4,9,14,19)])
        elif k==6:
            add_appear_animation(sl,[rendered[start:start+5] for start in (2,7,12,17)])
        if k in notes: sl.notes_slide.notes_text_frame.text=notes[k]
    prs.save(out); print(f'Saved {out}  ({len(prs.slides)} slides)')

if __name__=='__main__':
    here=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root=os.path.dirname(here)
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default=os.path.join(root,'dist','pptx','Auto-routing LLMs.pptx'))
    ap.add_argument('--images',default=os.path.join(here,'assets','images'))
    a=ap.parse_args(); build(a.out,a.images)
