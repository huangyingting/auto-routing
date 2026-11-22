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
HF='Segoe UI Variable Display'; BF='Calibri'; MF='Consolas'

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
WF={'Inter Tight':0.50,'Segoe UI Variable Display':0.51,'Segoe UI Variable Text':0.50,'Calibri':0.50,'Consolas':0.55,'Inconsolata':0.50,'Plus Jakarta Sans':0.55,'Newsreader':0.58,'JetBrains Mono':0.62,'Aptos Display':0.56,'Aptos':0.53,'Cascadia Code':0.62,'Georgia':0.6,'Arial':0.56,'Courier New':0.62}
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
    tb(s,x,310000,cx,eyebrow,size=12,color=CY,font=HF,bold=True,ls=0.9,cy=280000,name='eyebrow')
    tb(s,x,640000,cx,title,size=29.5,color=INK,font=HF,bold=True,cy=title_cy or 640000,name='slide_title')
def footer(s,src,num,x=M,cx=CW):
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
tb(s,x,860000,cx,'INTELLIGENT MODEL SELECTION & DECISION SYSTEMS',size=12,color=CY,font=HF,bold=True,ls=0.9,cy=280000)
tb(s,x,1220000,cx,'Auto-routing\nLLMs',size=45,color=INK,font=HF,bold=True,cy=1460000)
tb(s,x,2800000,cx,'Routing every task to the right model for quality, cost and speed — from Microsoft Copilot and Foundry to Microsoft-Decision-1.1.',size=16.5,color=MUTED,cy=1300000)
tb(s,x,4280000,cx,'Yingting Huang  |  Sr. Cloud Solution Architect, Microsoft',size=15.5,color=INK,bold=True,cy=380000)
note(s,'大家好，欢迎来到今天的分享。今天我们聊一个几乎所有做 AI 应用的团队都绕不开的问题：市面上的模型越来越多、换代越来越快，我们怎么在保证效果不掉的前提下，把调用成本和等待时间都压下来？答案就是自动路由 Auto-routing。\n接下来这 45 分钟，我会结合微软自己的工程实践，从大家熟悉的 Microsoft Copilot、GitHub Copilot Fusion 和 Foundry Model Router 讲起，拆开看看它们底层到底是怎么选模型的，再重点介绍微软专门为程序控制打造的决策模型 Microsoft-Decision-1.1，最后通过三组真实的交互 Demo，看看怎么把这套能力用到你自己的系统里。')

# ---------- 1 AGENDA
s=1
header(s,'AGENDA','Our journey today')
items=[
    ('01','Capability gap','No single model wins all'),
    ('02','Cost & cache','163× gap & prefix cache'),
    ('03','MS products','Copilot, Fusion, Foundry'),
    ('04','Under the hood','Industry vs. MS HyDRA'),
    ('05','Decision-1.1','Fast, calibrated control'),
    ('06','Live demos','Fusion, Foundry, Decision'),
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
footer(s,'',2)
note(s,'这是今天整场分享的脉络。我们先聊明白为什么要做自动路由——一方面没有哪个模型样样通吃，另一方面不同模型干同一件活儿成本能差出一百多倍，而且这里面还藏着一条很容易踩坑的前缀缓存铁律。接着我们看微软自家的几款核心产品是怎么在生产环境里做调度的，再往下深挖一层，对比业界常见的路由算法和微软 HyDRA 架构的思路差异。后半程我们聚焦在 Microsoft-Decision-1.1 的三个控制原语上，并现场跑完三组真实链路。')

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
footer(s,'',3)
note(s,'先问大家一个很现实的问题：你们团队现在用大模型，是不是还在挑一个综合表现最好的型号，然后所有请求从头绑到尾？如果全程绑死最贵的旗舰模型，账单翻几倍不说，连最简单的提取摘要也得跟着等半天；可要是全换成轻量小模型，稍微绕一点的逻辑推理又撑不住。更常见的是，大家为了查一个疑难杂症手动切到了最强模型，问题解决完根本想不起来切回去，后面一礼拜干杂活都在烧最贵的算力。\n微软 Copilot 负责人 Charles Lamanna 分享过一个很实在的判断：今天已经没有哪个模型能在所有任务上都排第一了，有的强在深度推理和算表，有的强在视觉生图，而翻邮件提字段用小模型又快又省。所以在今天的 Microsoft Copilot 里，超过九成的请求都已经交给了后台的 Auto，在企业管理员划定的合规范围里，按每一步子任务自动挑最合适的模型。')

# ---------- 3 ONE PROMPT -> FOUR SPECIALIZED JOBS (LAMANNA WHITEBOARD)
s=3
header(s,'01 · CAPABILITY SPECIALIZATION','One prompt, four specialized jobs')
card_box(s,M,1520000,CW,920000,[
    {'text':'PROMPT  ·  “Customer renewal Thursday — expand, hold, or discount, and build a deck to make the case?”','sizePt':14.5,'bold':True,'color':CODE,'spaceAfterPt':6},
    {'text':'Guardrail gate first: filters tenant-allowed model providers, data residency, and live endpoint health.','sizePt':13,'color':MUTED},
],fill=CODEBG,line=EDGE,lw=12700,pad_x=240000,pad_y=100000)
gap=160000; cw4=(CW-3*gap)/4; y0=2620000; ch=3380000
jobs=[
    ('JOB 01 · RETRIEVE','Small Language Model','Scans M365 emails, Teams chats, meeting notes & prior contracts fast and cheaply.','SLM · Fast & cheap',CY),
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
footer(s,'',4)
note(s,'我们拿一个真实办公场景来看看什么叫按子任务分工。假设周二下午你跟 Copilot 说：“周四要谈客户续约了，帮我算算该推扩购、维持原价还是给折扣，再做一份汇报用的 PPT。”\n这句话进了 Auto 之后，系统先按企业的供应商白名单和数据驻留要求过一道合规筛子，然后把整件事拆成了四棒接力：先派响应极快的小模型去邮件、会议纪要和老合同里把关键背景捞出来；接着把真正烧脑的续约经济账交给擅长深度推理的 Claude Opus 5.5 去算，顺手把整套上下文热缓存在那儿；等需要给方案配定制插图的时候，文字模型干不了这活，系统就自动切给专门做图的 GPT Image 2.5；最后汇总生成整套幻灯片，再回到刚才缓存还热着的 Opus 5.5 一气呵成，不用把几万字资料重读一遍。')

# ---------- 4 PART 2: 163X COST COMPRESSION & RIGHT-SIZING
s=4
header(s,'02 · COST & LATENCY ECONOMICS','Compressed quality, 163× cost spread')
ix=M; iy=1540000; icw=6200000; ich=4400000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'bench-163x-frontier.svg',ix+60000,iy+60000,icw-120000,ich-120000,'Vector SVG chart: The 163x Cost Compression Frontier — Mean Creative Quality vs AI Credits and Wall-Clock Time across 28 models',fit='contain')
rx=ix+icw+280000; rw=W-M-rx
stats=[
    ('4.2-pt quality band, 163× cost gap','Top 14 models cluster within 86.2–90.4 across 8 tasks, yet cost spans $0.09 (auto) and $0.23 (Haiku 5.5) vs. $14.75 (Opus 5).',CY),
    ('Routine work → small models win','24 of 28 models pass routine quality checks; Haiku 5.5 even ranks #1 on dashboard generation at a fraction of flagship cost.',CY),
    ('Hard problems → escalate selectively','Save heavy reasoning models (Opus 5.5, Sonnet 5.5, GPT-6 Sol) for complex specs where small models stall in retry loops.',AMB),
]
for i,(head_t,desc,col_) in enumerate(stats):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1360000,[
        {'text':head_t,'sizePt':16.2,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':desc,'sizePt':13.1,'color':MUTED},
    ],fill=CARD,pad_x=220000,pad_y=115000)
footer(s,'',5)
note(s,'除了能力各有专攻，更直接的动力来自成本和延迟的巨大剪刀差。这项基准评测拿 28 个主流模型跑了 8 类多模态工程任务，一共实测了 224 轮。\n跑出来的数据非常震撼：排在最前面的 14 个模型，综合质量分全都挤在 86.2 到 90.4 这短短 4.2 分里，日常体验差距其实微乎其微；但跑完同样这组任务的账单，从自动路由的 9 美分、Haiku 5.5 的 23 美分，一直拉到 Opus 5 的 14.75 美元，足足差出了 163 倍。实际上，绝大多数常规编码和结构化任务，轻量模型完全拿得下，像 Haiku 5.5 在数据看板任务上甚至拿了全场第一；只有碰到需求极其绕、弱模型容易陷进死循环反复重试的复杂架构题，才真正值得把重型推理模型请出来兜底。\n\n参考来源：GenisisIQ 28 模型多模态工程基准评测（blog.genisisiq.com）。')

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
footer(s,'',6)
note(s,'看到成本差出一百多倍，很多工程师的第一反应往往是：那我每一轮对话都实时算一下难度，哪句话简单就立刻切去便宜模型，岂不是省到极致？千万别这么干——这是做自动路由最容易踩的大坑，叫打碎前缀缓存。\n现在的 Agent 在第一轮启动时，往往已经把几万字的合同、代码库文件和七八十个工具定义全喂给了主模型。只要后续轮次继续留在这个模型家族，命中前缀缓存的读取单价通常只有原价的十分之一，延迟也低得多。要是你在第五轮为了省一句简单追问的钱，中途切到了别家的所谓便宜模型，缓存当场失效，新模型得按全价把那五万多个 Token 重新预填充一遍，算下来反而更慢、更贵。所以真正成熟的路由器都守着一条铁律：只在会话首轮、上下文压缩重置之后、派发独立子 Agent，或者任务难度发生剧变这些自然边界上才切换模型。\n\n参考来源：Charles Lamanna（M365 Copilot Auto）与 Joe Binder（GitHub Blog 前缀缓存感知路由技术解析）。')

# ---------- 6 PART 3: MICROSOFT ROUTING LANDSCAPE (4 CARDS + APPEAR)
s=6
header(s,'03 · MICROSOFT PRODUCTS IN ACTION','Four routing surfaces across Microsoft')
gap=170000; cw4=(CW-3*gap)/4; y0=1560000; ch=4360000
surfaces=[
    ('M365 Copilot & Cowork','Workplace Auto','Routes >90% of queries: Chat → Cowork handoff, multi-provider selection, dynamic effort & sub-agents.'),
    ('GitHub Copilot Fusion','Coding Orchestrator','Matches each coding task to one model or a team: Single pass, Judge-gated Cascade, or parallel Critique.'),
    ('Foundry Model Router','Cloud API Router','20 ms ML ranker across 45 models (7 providers): quality bands, cache affinity, param cleanup & PTU failover.'),
    ('Microsoft Decision-1.1','Software Controller','Purpose-built decision API that classifies, scores priority, and runs yes/no safety gates in ~123 ms at $0.042/1M.'),
]
for i,(prod,tag_,desc) in enumerate(surfaces):
    x=M+i*(cw4+gap)
    rect(s,x,y0,cw4,ch,fill=CARD)
    rect(s,x+200000,y0+240000,cw4-400000,380000,fill=EDGE,preset='roundRect',text=tag_,size=12,bold=True,color=INK)
    tb(s,x+200000,y0+760000,cw4-400000,f'0{i+1}',size=26,color=AMB if i==3 else CY,font=HF,bold=True,cy=460000)
    tb(s,x+200000,y0+1280000,cw4-400000,prod,size=18.5,bold=True,color=INK,cy=680000)
    tb(s,x+200000,y0+2060000,cw4-400000,desc,size=14,color=MUTED,cy=2060000)
footer(s,'',7)
note(s,'把能力分工和缓存铁律放进微软自己的产品体系里，你会发现虽然前台看着都很像一个 Auto 选项，但针对不同场景，微软在底层其实搭了四套各有专攻的调度系统。\n面向日常办公的 M365 Copilot 和 Cowork，核心管的是什么时候从普通聊天转入多步长任务、怎么在合规范围内跨厂商挑模型和派子任务；面向研发写代码的 GitHub Copilot Fusion，不仅挑模型，还会按题目轻重动态切换单跑、级联和并行互审这几种协作阵型；面向企业云端接口调用的 Foundry Model Router，在 45 个模型池里做 20 毫秒级的极速排序，顺带帮你优先消化买好的 PTU 容量并自动做限流容灾；而最右边的 Microsoft-Decision-1.1，则是把这套做分流、做风控的专用决策大脑直接做成开放接口，让你嵌进自家的业务代码里。')

# ---------- 7 MICROSOFT COPILOT HOME SCREENSHOT
s=7
header(s,'03 · MICROSOFT PRODUCTS · MICROSOFT COPILOT','Microsoft Copilot Home: unified Auto')
ix=M; iy=1540000; icw=6400000; ich=3600000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'m365-copilot-home.png',ix+50000,iy+50000,icw-100000,ich-100000,'Official Microsoft screenshot: Microsoft Copilot Home composer unifying Chat and Cowork with Auto',fit='contain')
tb(s,ix,5260000,icw,'One unified prompt box: Auto answers quick questions in Chat or hands off multi-step work to Cowork.',size=12.8,color=MUTED,cy=580000)
rx=ix+icw+280000; rw=W-M-rx
m365_pts=[
    ('1 · Chat → Cowork handoff','Decision-1.1 detects when a prompt needs multi-step execution and suggests Cowork (2.2× faster, 4.4× cheaper).',CY),
    ('2 · Multi-provider within IT rules','Routes across OpenAI, Anthropic Claude & xAI Grok while enforcing EU Data Boundary & tenant admin switches.',CY),
    ('3 · Scoped context & local offload','Pulls only relevant M365 emails, chats & files via Work IQ — and offloads light tasks to local Windows PC models.',AMB),
]
for i,(t,d,col_) in enumerate(m365_pts):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'',8)
note(s,'我们先看办公侧的 Microsoft Copilot 主界面。以前用户经常拿不准一件事该在聊天框里随口问，还是专门开个长任务工作区；现在一个统一的 Auto 输入框全接住了。\n当你发出一句话，后台其实在百毫秒内做完了三件事：先用 Microsoft-Decision-1.1 判断这是个快问快答，还是需要拆解执行的多步长任务，如果是后者就主动建议移交给 Cowork，比拿通用大模型做判断快了 2.2 倍、省下四分之三以上的成本；接着严格在企业管理员勾选的模型开关和欧盟数据边界之内挑人选；同时靠 Work IQ 从海量的企业邮件文档里只捞最相关的上下文，在支持的 Windows 电脑上甚至能把合适的轻活儿直接分给本地小模型处理。')

# ---------- 8 COPILOT COWORK AUTO SCREENSHOT
s=8
header(s,'03 · MICROSOFT PRODUCTS · COPILOT COWORK','Copilot Cowork: keep cache, tune effort')
ix=M; iy=1540000; icw=6400000; ich=1660000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'m365-cowork-ui.png',ix+50000,iy+50000,icw-100000,ich-100000,'Official Microsoft Learn screenshot: Copilot Cowork composer with Chat/Cowork toggle and Auto Medium selector',fit='contain')
card_box(s,ix,3340000,icw,2640000,[
    {'text':'COWORK MODEL POOL  ·  ENABLED BY TENANT ADMIN','sizePt':11,'bold':True,'color':CY,'spaceAfterPt':7},
    {'text':'• Auto (Default)      → Picks on turn 1 & keeps cache warm','sizePt':11.6,'color':INK,'spaceAfterPt':5},
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
footer(s,'',9)
note(s,'任务一旦进入多步执行的 Copilot Cowork，它的调度设计就非常典型地体现了缓存保护。系统会先分析你开口的第一条需求到底是写封快信、协调日程，还是要跨好几张财务报表做深度测算，然后从企业开通的 GPT 6.1 Sol、GPT 6 Astra、Opus 5.5、Sonnet 5.5 或 Grok 4.7 里挑出最契合的主模型，接下来整场会话就稳稳锁住它，绝不轻易换人把热缓存废掉；用户在每条回复的小标签上都能清楚看到当前是哪个模型在干活。\n主模型锁定了，怎么兼顾快慢呢？靠的是每一轮用 Decision-1.1 动态调节推理力度，从最轻快的 Light 一路调到深度思考的 Max，简单步骤秒回，碰到硬骨头再给足思考预算，外面再由 Agent 365 守住团队的整体花费上限。')

# ---------- 9 GITHUB COPILOT FUSION COMPOSER SCREENSHOT
s=9
header(s,'03 · MICROSOFT PRODUCTS · GITHUB COPILOT FUSION','Copilot Fusion: pick effort, not models')
ix=M; iy=1540000; icw=6200000; ich=3592000
rect(s,ix,iy,icw,ich,fill='11161D',line=EDGE,lw=12700)
img(s,'fusion-picker.png',ix+40000,iy+40000,icw-80000,ich-80000,'Official GitHub screenshot: Copilot Fusion composer menu showing Standard, High, and Max effort levels',fit='contain')
tb(s,ix,5260000,icw,'Pick Standard, High, or Max effort — hover the badge on any reply to see which models ran.',size=12.8,color=MUTED,cy=580000)
rx=ix+icw+280000; rw=W-M-rx
fus_cards=[
    ('Standard · High · Max (+ Fast)','Standard routes 1 model per task (including local MAI Code 1.1 Flash / Qwen3.8 Flash); High & Max unlock orchestration.',CY),
    ('Frontier quality at ~50% cost','On AA Coding Agent Index, Fusion Max scores 60 (within 2 pts of Opus 5.5 Max) at ~50% lower API cost & ~40% less time.',CY),
    ('Fixes “forgot to switch back” waste','AT&T found developers picked a heavy model for one hard bug and left it on; Fusion right-sizes every turn automatically.',AMB),
]
for i,(t,d,col_) in enumerate(fus_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.8,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'',10)
note(s,'再看研发每天泡在里面的 GitHub Copilot Fusion。以前大家在编辑器里点开模型菜单，面对一长串不断更新的模型名字很容易选择困难；Fusion 直接把交互改成了选投入档位：Standard、High 和 Max。\n跑出来的实测账本非常漂亮：在 Artificial Analysis 的编程 Agent 评测里，Fusion Max 拿到了 60 分，紧咬着全程单跑最贵旗舰 Opus 5.5 Max 的水平，但平均每个任务省下了大概一半的接口费用，连端到端耗时都缩短了四成。之前 AT&T 的研发团队就吐槽过，工程师为了修一个难缠的 Bug 切到大模型，之后写普通业务代码就再也没切回来过；现在交给 Fusion 自动按需伸缩，日常简单任务甚至能顺滑落到本机装好的 MAI Code 1.1 Flash 上。')

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
footer(s,'',11)
note(s,'Fusion 凭什么能做到质量不掉、成本砍半？关键在于它把“选哪个模型”升级成了“选哪套多模型协作方式”，而且同一场对话里每一句提问都可以动态换阵型。\n日常查配置、改个小函数，它直接走 Single 单模型路线，派个轻快模型一步到位，不花一分钱额外评审费。遇到常规功能开发，它走 Cascade 级联：先让高性价比模型把代码改出来、单测跑通，再请一个裁判模型做复核——没问题就直接放行省下算力，只有真抓出隐患时，才升级请重型模型从头修干净。而到了高风险的复杂架构设计，它会切到 Critique 模式：主模型起草方案的同时，拉起多个不同厂商的只读评审模型并行挑刺，因为限制了只读权限所以绝不会把文件改乱，最后由主模型汇总各方盲点拿出一版扎实的设计。')

# ---------- 11 FOUNDRY MODEL ROUTER: HOW IT RANKS & CACHES
s=11
header(s,'03 · MICROSOFT PRODUCTS · MICROSOFT FOUNDRY','Foundry Router: how it ranks & caches')
ix=M; iy=1540000; icw=6980000; ich=2708000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'foundry-overview.png',ix+40000,iy+40000,icw-80000,ich-80000,'Official Microsoft Learn diagram: Microsoft Foundry Model Router ranking prompts across 45 models with Balanced/Quality/Cost modes, session affinity and failover',fit='contain')
rect(s,ix,4400000,icw,1560000,fill=CODEBG,line=EDGE,lw=12700)
tb(s,ix+200000,4490000,icw-400000,'SCORING & AFFINITY ENGINE  ·  TRAINED ON BILLIONS OF INTERACTIONS',size=10.5,color=FOOT,font=MF,cy=260000)
ov_snip=(
    '1. Rank eligible models for this prompt (~20 ms ML scorer)\n'
    '2. Keep models within 1–2% of #1 quality  (5–6% in Cost mode)\n'
    '3. Reuse prior model if cache is warm & in band; else cheapest'
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
footer(s,'',12)
note(s,'如果你们团队不是直接用现成的 Copilot，而是自己调云端接口开发 AI 应用，那最趁手的就是 Microsoft Foundry 里的 Model Router——顺带一提，接口里直接写 model 为 auto 调的也是完全同一套底座。\n很多人好奇路由器自己会不会很慢，其实它本身根本不是大语言模型，而是在几十亿次真实问答、编码和工具调用记录上专门训练出来的机器学习排序器。它把系统提示词、历史对话和工具定义全扫一遍只要大约 20 毫秒，而且不存储客户的提示词内容。打完分之后怎么挑呢？默认的 Balanced 模式会在紧贴第一名 1% 到 2% 分差的第一梯队里选最便宜的模型，Cost 模式会把容忍度放宽到 5% 到 6%；而在多轮对话里，它会通过会话标识或历史消息指纹开启自适应亲和——只要前文没变、缓存还热，且上一轮模型没掉出当前质量带，就继续留用原模型吃满缓存红利。')

# ---------- 12 FOUNDRY ROUTER: GATES, PARAMS & FAILOVER
s=12
header(s,'03 · MICROSOFT PRODUCTS · FOUNDRY PIPELINE','Foundry: filters, params & failover',cx=CW-2300000)
ix=M; iy=1540000; icw=6980000; ich=2708000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'foundry-router-flow.png',ix+40000,iy+40000,icw-80000,ich-80000,'Official Microsoft Learn diagram: Six-step Foundry Model Router execution flow from eligibility filtering and ranking to PTU/PAYG capacity waterfall and failover',fit='contain')
rect(s,ix,4400000,icw,1560000,fill=CODEBG,line=EDGE,lw=12700)
tb(s,ix+200000,4490000,icw-400000,'live-capture.json  ·  Foundry-Features: ModelRouterControls=V1Preview',size=11,color=FOOT,font=MF,cy=260000)
live_snip=(
    '// Easy JSON -> DeepSeek-V4.1-Flash (23 ms) | Hard Rust -> gpt-5.6-luna (20 ms)\n'
    '"session_affinity": { "strategy": "adaptive", "decision": "retain" },\n'
    '"attempts": [ {"model":"gpt-6-sol","status":429}, {"model":"gpt-5.6-sol","status":200} ]'
)
tb(s,ix+200000,4800000,icw-400000,live_snip,size=10.8,color=CODE,font=MF,cy=1060000)
rx=ix+icw+240000; rw=W-M-rx
f_cards=[
    ('1 · Pre-Rank Eligibility Gate','Filters by region, approved allow-list, tools / json_schema / image support, and valid reasoning_effort before ranking.',CY),
    ('2 · Cross-Provider Param Cleanup','Drops temperature/stop on reasoning models, strips reasoning_effort on non-reasoning, & maps developer → system.',CY),
    ('3 · PTU Priority & Auto-Failover','Uses your pre-paid PTU first ($0 extra model fee) → PAYG → Managed, then fails over to #2 inside your allow-list.',AMB),
]
for i,(t,d,col_) in enumerate(f_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.2,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=105000)
footer(s,'',13)
note(s,'自己写过跨厂商模型接入的同学肯定深有体会，打分选型只是第一步，真正让人掉头发的全是工程兼容和线上限流。Foundry Model Router 把这几件脏活全包在了管线里。\n打分之前它会先过一道硬门槛，按所在区域、安全团队审批的模型白名单、还有这次请求带没带工具定义、JSON Schema 或图片，把不具备资格的模型提前剔除。选完模型之后还有一层自动参数适配：比如推理模型不认 temperature 和 stop，非推理模型不认 reasoning_effort，系统角色有的叫 developer 有的叫 system，路由器在转发时会自动帮你转换或剥离，彻底告别莫名其妙的 400 报错。最后是容量消化与无感容灾：选中首选模型后，先优先消耗你自己买好的零模型费预留 PTU，不够再走按量付费和托管容量；万一遇上突发高峰连吃 429 限流，几十毫秒内就会自动切到白名单里的第二顺位模型，业务代码连重试都不用自己写。')

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
footer(s,'',14)
note(s,'看完了产品实践，我们往算法底层退一步看：业界做模型路由大体走过四条技术路线，每条都有很明显的局限。\n最早大家爱用正则规则或者句向量相似度匹配，几毫秒就能跑完，但它只看表面字眼，根本分不清“写个简单排序”和“写个无锁并发环形队列”在推理难度上的天壤之别。后来像开源界很有名的 RouteLLM，改用矩阵分解或 BERT 训练二分类器去预测强模型赢过弱模型的概率，准度上去了，但把具体模型名字焊死在了分类器权重里——现在几乎每个月都有新模型发布，候选池一换就得重采数据重训。第三种 FrugalGPT 式的串行级联，一碰到难题就得白交一次小模型的试错延迟。至于直接拿通用大模型写提示词当路由，动辄多等一两秒不说，经过人类偏好强化学习的大模型天生爱装自信，给出的概率校准度很差，很难拿来做精准的工程阈值。')

# ---------- 14 MICROSOFT'S APPROACH: GITHUB HYDRA (ARXIV:2605.17106)
s=14
header(s,'04 · MICROSOFT’S ARCHITECTURE · HYDRA','GitHub HyDRA: decouple demand & catalog')
ix=M; iy=1540000; icw=6040000; ich=3398000
rect(s,ix,iy,icw,ich,fill='111315',line=EDGE,lw=12700)
img(s,'hydra-pareto.png',ix+30000,iy+30000,icw-60000,ich-60000,'Official GitHub chart: HyDRA on the 5-model production pool — Peak (+1.2% > Sonnet at -12.9% cost), Cons (-54.1% cost), Agg (-72.5% cost)',fit='contain')
card_box(s,ix,5060000,icw,920000,[
    {'text':'1. Score 4 demands (86 ms): [Reason, CodeGen, Debug, Tools]','sizePt':11.3,'bold':True,'color':CODE,'spaceAfterPt':7},
    {'text':'2. Pick cheapest healthy model whose profile covers all 4','sizePt':11.3,'color':INK},
],fill=CODEBG,line=EDGE,lw=12700,pad_x=200000,pad_y=90000,font=MF)
rx=ix+icw+260000; rw=W-M-rx
hy_cards=[
    ('4-Head Capability Scorer','Lightweight ModernBERT scores Reasoning, CodeGen, Debugging & Tool Use in 86 ms median CPU latency.',CY),
    ('Zero-Retraining Model Updates','Models live in config files, not classifier weights! Adding GPT-6 is a config edit — 6× more savings (54.1%) than binary routing.',CY),
    ('Multilingual Across 19 Languages','Trained on full multi-turn coding sessions (including Chinese, Japanese & Korean) within 4 pts of English accuracy.',AMB),
]
for i,(t,d,col_) in enumerate(hy_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.8,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'',15)
note(s,'那微软是怎么解开“模型月月换、路由器总不能月月重训”这个死结的？答案就在支撑 GitHub Copilot 的这篇 HyDRA 架构论文里：把“判断这道题需要什么能力”和“手头现在有哪些模型”彻底拆开。\n它在底层用了一个很轻巧的 ModernBERT 编码器，上面挂四个独立的预测头，在普通 CPU 上跑一次中位耗时只要 86 毫秒。注意它的输出不是某个模型的名字，而是当前请求在推理深度、代码生成、调试难度和工具编排这四个维度上的能力需求分。与此同时，候选池里每个模型的四维能力长短板和调用单价都写在一份静态配置表里，运行时只要算一下哪些模型的短板在安全阈值之内，挑最便宜且健康的那个就行。明天就算上线了全新的 GPT-6，改一行配置立刻生效，完全不用重新训练模型。在 SWE-Bench 实测里，这套办法在同等解决率下省掉了 54.1% 的成本，省钱效率是传统二分类路由的六倍。\n\n参考来源：Garg et al., HyDRA 论文（arXiv:2605.17106）。')

# ---------- 15 MICROSOFT'S THREE-LAYER ROUTING STACK
s=15
header(s,'04 · MICROSOFT’S ARCHITECTURE · BLUEPRINT','Microsoft’s three-layer routing stack')
img(s,'hd-sorter.jpg',M,1780000,4980000,3320000,'Hand-drawn robot sorting incoming tasks into three policy-governed trays')
rx=M+4980000+320000; rw=W-M-rx
layers=[
    ('Layer 1 · Deterministic Policy & Cache Gate','Hard code filters tenant-allowed providers, data zones, required tool/schema capabilities, and warm prefix-cache state.',CY),
    ('Layer 2 · Fast Scorer / Decision Model (<180 ms)','Purpose-built encoder (HyDRA / Foundry ML ranker) or Microsoft-Decision-1.1 produces calibrated scores over allowed options.',CY),
    ('Layer 3 · Workflow Pattern & Output Verifier','Executes Single, Cascade or Critique, then runs deterministic schema, citation or policy safety checks before acting.',AMB),
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
footer(s,'',16)
note(s,'把前面聊的所有产品和底层算法放到一张图上，微软做路由的工程哲学其实非常统一，就是清晰的三层分工。\n最上面永远是确定性的硬代码，管租户权限、数据驻留、接口能力门槛和前缀缓存状态，合规红线绝不交给概率模型去猜；中间这一层是百毫秒级的专用评估器，只管在合法的候选集里给出校准过的客观打分；最下面再根据分差决定走单模型、级联还是并行评审，并在结果发出去之前做好格式与安全校验。\n讲到这儿，大家自然会问：微软内部有 HyDRA 和专用排序器，那我们自己写业务 Agent 的时候，去哪儿找中间这一层又快、又便宜、概率还准的控制大脑呢？')

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
    {'text':'Built specifically for fast, calibrated decisions','sizePt':13.8,'bold':True,'color':CY,'spaceAfterPt':10},
    {'text':'• Mixture-of-Experts (4B active) + single-pass engine','sizePt':13.8,'color':INK,'spaceAfterPt':7},
    {'text':'• Reads text, JSON & photos/UI with zero filler prose','sizePt':13.8,'color':INK,'spaceAfterPt':7},
    {'text':'• Calibrated probabilities; <1.3% variance on reordered options','sizePt':13.8,'color':INK},
],fill=CARD2,line=CY,lw=25400,pad_x=240000,pad_y=130000)
gap4=160000; tw4=(CW-3*gap4)/4; ty=4560000; th4=1400000
facts=[
    ('$0.042 / 1M','Input tokens (Global Std); output tokens FREE!',CY),
    ('~123 ms','Median decision latency (2.2× faster than v1.0)',CY),
    ('35×–100×','Faster than frontier LLMs on routing & QC',CY),
    ('3 Clouds','Microsoft Foundry, OpenRouter & Vercel',AMB),
]
for i,(v,l,col_) in enumerate(facts):
    xx=M+i*(tw4+gap4)
    card_box(s,xx,ty,tw4,th4,[
        {'text':v,'sizePt':23,'bold':True,'color':col_,'spaceAfterPt':6},
        {'text':l,'sizePt':12.8,'color':INK},
    ],fill=CODEBG,line=EDGE,lw=12700,pad_x=180000,pad_y=120000)
footer(s,'',17)
note(s,'这正是微软专门研发并开放 Microsoft-Decision-1.1 的初衷。我们平时熟悉的生成式大模型，训练目标是把回答写得通顺完整、讨人喜欢；你让它做个简单的路由选择或者合规判断，它也得逐词生成一堆解释，不仅动辄大几百毫秒，遇到缺失信息还特别容易自信地乱拍板。\n刚刚正式发布的 Decision-1.1 从根上换了思路：它基于 Gemma 4 的混合专家架构，每次推理只激活 4B 参数，配上专门定制的单次前向决策引擎，不吐一句多余的客套话，直接读进文本、JSON 甚至界面和实物照片，返回严格校准过的概率分布。标准输入一百万 Token 只要 4.2 美分，输出 Token 完全免费，平均一百二十多毫秒就能拿回结果；哪怕你故意把选项顺序打乱或者换种问法，它的判断翻转率也只有 1.3%，稳得像一个确定性的软件模块。')

# ---------- 17 DECISION-1.1 THREE TYPED PRIMITIVES
s=17
header(s,'05 · MICROSOFT DECISION-1.1 · API PRIMITIVES','Three primitives: choice, noul, score')
gap=180000; cw3=(CW-2*gap)/3; y0=1540000; ch=2360000
prims=[
    ('01 · choice  (Pick one)','“Which option fits best?”','Picks one label and returns calibrated probabilities per candidate.\nUse: model routing, ticket triage, tool pick.',CY),
    ('02 · noul  (Yes / No gate)','“Is this condition true?”','Returns a single [0, 1] probability for any true/false check.\nUse: safety gates, refund/rival checks, photo damage.',CY),
    ('03 · score  (0–N scale)','“How urgent or strong?”','Computes a probability-weighted score across ordered levels.\nUse: P0–P3 incident priority, output grading.',AMB),
]
for i,(k,sub,desc,col_) in enumerate(prims):
    x=M+i*(cw3+gap)
    card_box(s,x,y0,cw3,ch,[
        {'text':k,'sizePt':18,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':sub,'sizePt':13.5,'bold':True,'color':INK,'spaceAfterPt':8},
        {'text':desc,'sizePt':12.8,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
rect(s,M,4060000,CW,1920000,fill=CODEBG,line=EDGE,lw=12700)
tb(s,M+220000,4150000,CW-440000,'POST <foundry-endpoint>/providers/microsoft/v1/systemone   ·   Ask all 3 in ONE call',size=11,color=FOOT,font=MF,cy=260000)
api_code=(
    '{ "model": "microsoft-decision-1.1", "state": {"msg": "Checkout is down in EU (3rd ping).", "contacts": 3},\n'
    '  "questions": {\n'
    '    "route":    {"type": "choice", "instructions": "Pick tier", "criteria": {"slm":"FAQ","sol":"Incident"}},\n'
    '    "severity": {"type": "score",  "instructions": "Severity",  "criteria": ["Cosmetic","Minor","Major","Critical"]},\n'
    '    "escalate": {"type": "noul",   "instructions": "Needs immediate human on-call?"} } }'
)
tb(s,M+220000,4460000,CW-440000,api_code,size=11.5,color=CODE,font=MF,cy=1420000)
footer(s,'',18)
note(s,'那这个专门做决策的模型，在代码里到底长什么样？它的接口起名叫 systemone，意思就是替你的系统做直觉式的毫秒级快判断。你只需要把当前的业务上下文塞进 state，针对这一份状态可以同时提好几个强类型问题，一共就三种基础原语：\n想在好几条路径里挑一条，比如决定调哪个模型、分给哪个支持团队，就用 choice，它会同时返回每个候选项的校准概率——一旦最高概率连 0.75 都不到，你的代码就可以立刻停下来先向用户追问，绝不硬着头皮瞎猜；想设一道是非安检门，比如查草稿有没有违规许诺退款、买家拍的包装盒破没破，就用 noul，拿回一个 0 到 1 的单值概率；想给工单紧急度或者生成质量排个高低档位，就用 score，它会在有序等级上算出概率加权的期望分。最省事的是，这三种问题可以装进同一个请求里一次拿回全部结果。')

# ---------- 18 FOUR CONCRETE DECISION-1.1 EXAMPLES
s=18
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
footer(s,'',19)
note(s,'有了这三个基础原语，平时写 Agent 最让人头疼的外围控制逻辑基本都能优雅解决。比如搭一套自己的模型路由器，用 choice 把轻快提取、常规编码、深度评审和“信息不全需追问”列成四个选项，遇到缺附件或指令含糊的情况直接停下来问清楚，省得白烧旗舰模型的算力。\n再比如做客服工单入口，一次请求同时跑 choice 分组和 score 定级，看到客户投诉“床架塌了扭伤了腰”，严重度直接打到接近满分的 2.94，系统当场绕过自动回复、直接呼叫真人专员。做电商售后时，把退货照片传进 assets 跑个 noul，破损概率超过八成自动秒批换货，拿不准的再转人工核赔。甚至在你的生成式大模型写好草稿、发给客户之前，还能并排挂几道独立的 noul 做出口把关——一旦测出草稿里居然出现了推荐竞品或者私自打折的表述，过半数直接扣下重审。')

# ---------- 19 DECISION-1.1 BENCHMARKS & INTERNAL WINS
s=19
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
    {'text':'• Xbox Research: 14× faster, 200× cheaper than GPT-6 Sol','sizePt':12.2,'color':INK,'spaceAfterPt':5},
    {'text':'• Adopted by Epic, Equinor, Atos & Raiffeisen Bank','sizePt':12.2,'color':INK},
],fill=CARD,pad_x=200000,pad_y=90000)
footer(s,'',20)
note(s,'看到接口这么轻巧、每次只激活 4B 参数、价格还只要几美分，大家心里肯定会问一句：它判断得够准吗？跟满血旗舰模型比会不会掉点？我们直接看硬指标。在第三方机构 Artificial Analysis 的决策指数评测里，Decision-1.1 拿到了全场最高的 68 分，平均耗时才 123 毫秒左右，把一众专用决策模型和通用旗舰都甩在了后面。\n在完全没有训练集重叠的 102 项公开基准、超过 38.5 万道盲测题里，它在工具调用、路由分流、安全风控、质量评判和一致性等七个核心领域全部排在榜首。上线才五周就已经有四千多家企业接进了生产环境；在微软内部，前面聊到的 Copilot 聊天转长任务、Cowork 动态调推理力度、Foundry 评测打分，还有比旗舰模型快 14 倍、便宜 200 倍的 Xbox 研究分析管线，底层全靠它在驱动。')

# ---------- 20 CONTOSO 7.2X CAC CASE STUDY VECTOR SVG
s=20
header(s,'05 · MICROSOFT DECISION-1.1 · IMPACT','Sales agent case: 7.2× lower CAC',cx=CW-2300000)
ix=M; iy=1540000; icw=6100000; ich=4400000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'decision-cac-waterfall.svg',ix+50000,iy+50000,icw-100000,ich-100000,'Vector SVG chart: Contoso $10,000/mo sales agent Cost-per-Lead waterfall and 32-reply 100% accuracy router benchmark',fit='contain')
rx=ix+icw+260000; rw=W-M-rx
steps_cac=[
    ('1 · Baseline: Frontier LLM + 100% review','$0.31 per lead  ·  CAC = $13.00','Every email calls a $0.15 frontier LLM plus $0.24 human review — capping $10k/mo at 764 customers.',MUTED),
    ('2 · Add choice router + score priority','$0.07 per lead  ·  CAC = $2.63','100% routing accuracy (vs. 88% regex): 57% of simple replies skip the LLM; only P1–P3 go to humans.',CY),
    ('3 · Add noul outbound safety gate','$0.05 per lead  ·  CAC = $1.81 (7.2× lower)','All 3 Decision-1.1 checks cost $0.00019/email total — cutting human review 100% → 8% (5,511 customers).',AMB),
]
for i,(t,sub,desc,col_) in enumerate(steps_cac):
    yy=1540000+i*1510000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':14.6,'bold':True,'color':INK if col_==MUTED else col_,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':12.2,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.1,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=95000)
footer(s,'',21)
note(s,'既有接近满分的判断准度，单次调用又几乎不花钱，把它串进真实业务里能带来多大的商业回报？我们看这个月预算一万美元的销售线索跟进测算：如果按传统粗放做法，每封客户回信都直接扔给昂贵的旗舰 Sol 模型写回复，再因为怕大模型乱说话安排全量人工复核，算下来处理一条线索要花 3 毛 1，每签下一单的获客成本高达 13 美元。\n把 Decision-1.1 放进去之后，先守住入口分流——在 32 类真实客户邮件测试里，手写正则只能认对 88%，而它做到了 100% 全对，先把 57% 像单纯说声谢谢或者退订的邮件用零成本规则直接处理掉，根本不惊动大模型；接着用 score 给高意向客户排优先级，最后在出口用 noul 拦住乱提竞品的草稿。这三道检查加在一块儿，每封信的决策成本还不到万分之二美元，却把需要人工介入复核的比例从 100% 降到了 8%。同样一万块钱月预算，能转化出来的客户数翻了七倍多，获客成本直接从 13 美元压到了 1.81 美元。\n\n参考来源：Microsoft Command Line 博客（$10k/月销售收件箱架构测算案例）。')

# ---------- 21 LIVE DEMO 1: GITHUB COPILOT AUTO & FUSION
s=21
header(s,'06 · LIVE DEMO 1','Copilot CLI Auto & multi-agent',cx=CW-3400000)
cx_=5550000; cy0=1540000; chh=4420000
rect(s,M,cy0,cx_,chh,fill=CODEBG,line=EDGE,lw=12700)
tb(s,M+220000,cy0+140000,cx_-440000,'copilot --output-format json  ·  Live CLI telemetry',size=11,color=FOOT,font=MF,cy=280000)
d1_code=(
    '$ copilot -p "Read config.ts..." --model auto \\\n'
    '    --output-format json --usage-output-file usage.json\n'
    '-> session.auto_mode_resolved: mai-code-2-flash (0.019 AIU)\n\n'
    '// Cascade & Critique harness over live Copilot CLI:\n'
    '-> Judge (--deny-tool write): ESCALATE lock inversion\n'
    '-> Repair (gpt-6.1-terra)   : 500/500 stress PASS\n'
    '-> --resume <sid>           : 96% cacheReadTokens hit!'
)
tb(s,M+220000,cy0+480000,cx_-440000,d1_code,size=11.5,color=CODE,font=MF,cy=2600000)
card_box(s,M+220000,cy0+3260000,cx_-440000,960000,[
    {'text':'PS> npm --prefix demo run demo:fusion:live','sizePt':11.5,'bold':True,'color':INK,'spaceAfterPt':7},
    {'text':'Single → Cascade → Escalate → Critique → 96% Cache','sizePt':11,'color':CY},
],fill=CARD2,line=EDGE,lw=12700,pad_x=180000,pad_y=90000,font=MF)
rx=M+cx_+320000; rw=W-M-rx
d1_cards=[
    ('✓  Single & Cascade short-circuit','MAI Code 2 Flash (0.019 AIU) + node --test','Real session.auto_mode_resolved scores route easy lookups & clean patches to Flash without heavy repair.',CY),
    ('↗  Judge-triggered escalation','Catches ABBA lock inversion in token-bucket.ts','Read-only Judge flags refill()/close() deadlock; GPT-6.1 Terra fixes it and passes 500× concurrent stress.',AMB),
    ('⇄  Parallel Critique + 96% Cache','2× read-only Critics & --resume warm prefix','Parallel --deny-tool write Critics audit 50k-RPS design; follow-up turn hits 96% cacheReadTokens.',CY),
]
for idx,(t,sub,desc,col_) in enumerate(d1_cards):
    yy=1540000+idx*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':INK,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':11.8,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=95000)
footer(s,'',22)
note(s,'账算清楚了，接下来我们通过三组 100% 真实跑通并抓包的交互 Demo，一步步看清这些机制在运行时到底是怎么工作的。\n第一个 Demo 直接调用本机 GitHub Copilot CLI 的 JSONL 事件流。第一步去配置文件里读默认端口，从原始日志的 auto_mode_resolved 事件里能直接看到四个维度的打分全在 0.1 以下，自动命中轻量的 MAI Code 2 Flash；第二步做代码修改，小模型改完跑过本机三项 Node 单测，只读裁判复核放行，省掉重型返工；第三步面对隐蔽的并发双锁死锁，只读裁判当场抓出加锁顺序反转并触发升级，由 GPT-6.1 Terra 修复并通过五百次并发压测；第四步两个只读评审模型并行挑出限流方案的故障切换和分片热点漏洞；第五步用 resume 追问监控指标，usage.json 显示高达 96% 的输入 Token 直接命中热缓存。')

# ---------- 22 LIVE DEMO 2: MICROSOFT FOUNDRY MODEL ROUTER
s=22
header(s,'06 · LIVE DEMO 2','Foundry Model Router live',cx=CW-3400000)
cx_=5550000; cy0=1540000; chh=4420000
rect(s,M,cy0,cx_,chh,fill=CODEBG,line=EDGE,lw=12700)
tb(s,M+220000,cy0+140000,cx_-440000,'foundry-v1preview.http  ·  ModelRouterControls=V1Preview',size=11,color=FOOT,font=MF,cy=280000)
d2_code=(
    'POST /openai/v1/chat/completions\n'
    'Foundry-Features: ModelRouterControls=V1Preview\n'
    '{\n'
    '  "model": "auto",\n'
    '  "routing_config": {\n'
    '    "mode": "balanced",\n'
    '    "session_affinity": { "strategy": "adaptive" }\n'
    '  }\n'
    '}\n'
    '// Invoice JSON -> DeepSeek-V4.1-Flash (28 ms)\n'
    '// Rust MPMC    -> gpt-6-luna          (27 ms, retain)'
)
tb(s,M+220000,cy0+480000,cx_-440000,d2_code,size=11.5,color=CODE,font=MF,cy=2640000)
card_box(s,M+220000,cy0+3260000,cx_-440000,960000,[
    {'text':'PS> npm --prefix demo run demo:foundry:live','sizePt':11.5,'bold':True,'color':INK,'spaceAfterPt':7},
    {'text':'Live Foundry V1Preview traces + 429→200 failover','sizePt':11,'color':CY},
],fill=CARD2,line=EDGE,lw=12700,pad_x=180000,pad_y=90000,font=MF)
rx=M+cx_+320000; rw=W-M-rx
d2_cards=[
    ('✓  27–28 ms ML routing & affinity','DeepSeek-V4.1-Flash vs. gpt-6-luna','Live V1Preview traces route simple JSON to Flash (0 reason tok) and escalate Rust proofs to Luna with retain affinity.',CY),
    ('⇄  Two-stage cost → quality routing','grok-4-1-fast (cost) → gpt-5.6-terra (quality)','Splits renewal analysis into two live calls: cheap extraction in cost mode followed by strategy in quality mode.',CY),
    ('↺  Transparent HTTP 429 → 200 failover','Primary 429 burst → live fallback 200 OK','Fires a real HTTP 429 on primary and verifies automatic failover to the next approved model with zero caller error.',AMB),
]
for idx,(t,sub,desc,col_) in enumerate(d2_cards):
    yy=1540000+idx*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':INK,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':11.8,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=95000)
footer(s,'',23)
note(s,'第二个 Demo 全部来自云端 Foundry Model Router 的真实接口抓包。第一步带上 developer 角色和 JSON 模式请求，验证参数自动归一并在 27 毫秒内完成路由。\n接着往同一个 balanced 接口连发两道难度悬殊的题：提取发票编号和币种时，排序器花 28 毫秒挑中了零推理开销的 DeepSeek-V4.1-Flash；换成 Rust 无锁队列的形式化证明时，27 毫秒内自动升级到 gpt-6-luna，并且在第二轮追问时通过消息指纹返回 retain 锁住热缓存。第四步演示怎么把续约分析拆成两棒实测调用：第一棒设成 cost 模式让 grok-4-1-fast 便宜捞出关键数字，第二棒设成 quality 模式交给 gpt-5.6-terra 做博弈策略推演。最后拉起真实主备服务，模拟主节点返回 429 限流并自动切到备选节点拿回 200 成功响应。')

# ---------- 23 LIVE DEMO 3: MICROSOFT-DECISION-1.1 CONTROLLER
s=23
header(s,'06 · LIVE DEMO 3','Decision-1.1 agent controller',cx=CW-3400000)
cx_=5550000; cy0=1540000; chh=4420000
rect(s,M,cy0,cx_,chh,fill=CODEBG,line=EDGE,lw=12700)
rect(s,M+cx_-1480000,cy0+130000,1240000,320000,fill=CY,preset='roundRect',text='GA · Nov 2026',size=10.5,bold=True,color=BG)
tb(s,M+220000,cy0+130000,cx_-1800000,'decision-controller.ts  ·  /v1/systemone',size=11,color=FOOT,font=MF,cy=320000)
d3_code=(
    'const res = await systemOne({\n'
    '  model: "microsoft-decision-1.1",\n'
    '  state: { customer_msg, draft_reply },\n'
    '  questions: {\n'
    '    team:     { type: "choice", criteria: TEAMS },\n'
    '    priority: { type: "score",  criteria: P0_TO_P3 },\n'
    '    rival:    { type: "noul",   instructions: "Names rival?" }\n'
    '  }\n'
    '});\n'
    'if (res.team.choice === "safety_support") return pageHuman();\n'
    'if (res.rival.noul >= 0.50)               return holdDraft();'
)
tb(s,M+220000,cy0+490000,cx_-440000,d3_code,size=11.5,color=CODE,font=MF,cy=2640000)
card_box(s,M+220000,cy0+3260000,cx_-440000,960000,[
    {'text':'PS> npm --prefix demo run demo:decision:live','sizePt':11.5,'bold':True,'color':INK,'spaceAfterPt':7},
    {'text':'5 live /v1/systemone traces + custom prompt tester','sizePt':11,'color':CY},
],fill=CARD2,line=EDGE,lw=12700,pad_x=180000,pad_y=90000,font=MF)
rx=M+cx_+320000; rw=W-M-rx
d3_cards=[
    ('✓  Zero-spread routing (choice & noul)','5/5 identical 0.9835 · 4/4 inbox p=1.00','5 consecutive live calls return 0.00 pt spread; 3 of 4 routine inbox messages skip the frontier LLM.',CY),
    ('!  3-in-1 safety triage (choice+score+noul)','safety_support (0.998) + score 1.97 + repeat 1.00','One 348 ms call classifies injury risk, scores urgency & flags 3rd repeat contact — blocking bot reply.',AMB),
    ('✕  Outbound guardrail & missing-doc abstain','Rival promo noul=0.970 & missing Exhibit B p=0.9999','Holds a draft recommending rival Fabrikam (0.970) and stops to ask when Exhibit B is missing from state.',CY),
]
for idx,(t,sub,desc,col_) in enumerate(d3_cards):
    yy=1540000+idx*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':INK,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':11.8,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.4,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=95000)
footer(s,'',24)
note(s,'第三个 Demo 展示 Microsoft-Decision-1.1 在真实云端接口上的五组实测表现。第一步拿同一封询价邮件连调五次，实测五次全部精准返回 0.9835、极差为零；第二步对致谢、退订、促销咨询和复杂质保对比四条消息做前置分流，四条全部以接近满分的置信度命中对应通道，直接帮大模型省掉四分之三的开销；第三步在一次三百多毫秒的请求里同时塞进团队分类、紧急度打分和重复投诉判断三个问题，识别出床架坍塌伤人事件后当场阻断机器人回复并转交人工；第四步用 noul 打出 0.970 的高概率，把一段推荐竞品 Fabrikam 的回复草稿在发出前稳稳拦下；第五步模拟上下文里只挂了合同 A 却漏了附件 B，模型以 0.9999 的概率精准选择停下来向用户追问缺失文件，彻底杜绝瞎编条款。')

# ---------- 24 CLOSER: KEY TAKEAWAYS
s=24
img(s,'hd-review.jpg',W-M-5040000,1620000,5040000,3360000,'Hand-drawn illustration: two friendly robots reviewing and approving a routed workflow together')
x=M+80000; cx=5850000
tb(s,x,420000,cx,'SUMMARY · KEY TAKEAWAYS',size=12,color=CY,font=HF,bold=True,ls=0.9,cy=260000)
tb(s,x,740000,cx,'Right-size the model,\nkeep the control',size=36,color=INK,font=HF,bold=True,cy=1200000)
tk=[
    '1   Route sub-tasks by capability — no single model wins all.',
    '2   Stop paying 100× for simple work — & keep prefix caches warm.',
    '3   Adopt Copilot Auto, Copilot Fusion & Foundry Router first.',
    '4   Use Microsoft-Decision-1.1 for fast routing, priority & safety gates.',
]
tb(s,x,2100000,cx,None,paras=[{'text':t,'spaceAfterPt':10} for t in tk],size=14.2,color=INK,cy=2380000)
tb(s,x,4660000,cx,None,paras=[
    {'text':'aka.ms/decision-1.1  ·  blog.genisisiq.com','spaceAfterPt':7},
    {'text':'github.com/microsoftconnect/Decision-Benchmarks'},
],size=12.5,color=CY,font=MF,cy=720000)
tb(s,x,5540000,cx,'Thank you  ·  Q&A',size=24,color=INK,font=HF,bold=True,cy=480000)
footer(s,'',25)
note(s,'回到我们一开场提的问题：模型这么多、变化这么快，大家带回团队到底该怎么动手？其实抓住四件事就够了。\n别再试图找一个包打天下的模型从头绑到尾，按子任务的能力要求去拆解分工；算成本账的时候一定要把等待时间和前缀缓存算进去，守住首轮和独立子任务这些自然边界，千万别在对话半路乱切模型把十分之一价格的热缓存打碎；现成的平台能力优先用起来，日常办公打开 Copilot Auto，研发写代码用好 Copilot Fusion，调云端推理接口直接挂上 Foundry Model Router；而当你在自己的业务代码里需要做精准分流、排优先级或者加出站合规护栏时，试试把百毫秒级、概率校准过的 Microsoft-Decision-1.1 当成标准控制组件嵌进去。今天的内容就分享到这里，谢谢大家，看看大家有什么问题！')

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
footer(s,'',26)
note(s,'最后这一页把今天聊到的所有公开评测报告、产品机制文档、HyDRA 架构论文以及 Decision-1.1 的接入教程和开源基准库都汇总在了一起，在 PPT 和网页里都可以直接点开，方便大家回去对照查阅。')


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
                if nlines(txt,o.get('sizePt',29.5),o['cx'],HF,True)>1:
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
