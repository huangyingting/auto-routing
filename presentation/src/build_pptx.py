#!/usr/bin/env python3
"""
build_pptx.py - builds "Auto-routing LLMs" (26 slides, 16:9,
hand-drawn illustrations + product screenshots/charts, Chinese speaker notes)
as a standalone .pptx with build-time layout & overlap verification.

Usage:   pip install python-pptx pillow
         python -m presentation.src.build_pptx [--out "dist/pptx/Auto-routing LLMs.pptx"]
"""
import argparse, copy, os
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from PIL import Image
try:
    from .i18n import EN_NOTES, ZH_TEXT_MAP, ZH_DEMO_LAUNCHERS
except ImportError:
    from i18n import EN_NOTES, ZH_TEXT_MAP, ZH_DEMO_LAUNCHERS

# ===================== THEME & LAYOUT =====================
W,H=12192000,6858000; M=457200; CW=W-2*M
BG='F3EEE4'; CARD='E9E2D4'; CARD2='FAF7F1'; EDGE='C9C0AE'; INK='2B2B2B'; MUTED='57534C'; FOOT='6E685F'
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
WF={'Inter Tight':0.50,'Segoe UI Variable Display':0.51,'Segoe UI Variable Text':0.50,'Calibri':0.50,'Microsoft YaHei UI':0.50,'Consolas':0.55,'Inconsolata':0.50,'Plus Jakarta Sans':0.55,'Newsreader':0.58,'JetBrains Mono':0.62,'Aptos Display':0.56,'Aptos':0.53,'Cascadia Code':0.62,'Georgia':0.6,'Arial':0.56,'Courier New':0.62}
def _disp_units(s):
    return sum(1.85 if ord(ch) > 0x2E80 else 1.0 for ch in s)
def nlines(text,size,cx,font,bold):
    f=WF[font]*(1.08 if bold else 1)
    cpl=max(1,int((cx-240000)/(size*12700*f)))
    n=0
    for para in text.split('\n'):
        has_cjk=any(ord(ch)>0x2E80 for ch in para)
        if has_cjk:
            u=_disp_units(para)
            n+=max(1,int((u+cpl-1)//cpl)) if u>0 else 1
        else:
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
    tb(s,W-940000,H-430000,700000,f'{num:02d}',size=11.5,color=FOOT,font=MF,bold=True,align='right',cy=290000,name='footer_num')
def note(s,t): notes[s]=t

def card_box(s,x,y,cx,cy,paras,fill=CARD,line=EDGE,lw=12700,pad_x=240000,pad_y=120000,font=BF,space_after=6.5,align='left'):
    rect(s,x,y,cx,cy,fill=fill,line=line,lw=lw if line else None)
    tb(s,x+pad_x,y+pad_y,cx-2*pad_x,None,paras=paras,font=font,align=align,cy=cy-2*pad_y,space_after=space_after)

def banner_box(s,x,y,cx,cy,text,accent=CY,fill=CODEBG,color=INK,size=15.5,bold=True,align='left'):
    rect(s,x,y,cx,cy,fill=fill,line=EDGE,lw=12700)
    rect(s,x+95000,y+110000,46000,cy-220000,fill=accent,preset='roundRect')
    tb(s,x+240000,y,cx-480000,text,size=size,bold=bold,color=color,align=align,cy=cy)

def medallion(s,cx_mid,cy_mid,diam=360000,glyph='→',fill=CY,color=BG,size=14):
    r=diam//2
    rect(s,cx_mid-r,cy_mid-r,diam,diam,fill=fill,preset='ellipse',text=glyph,size=size,bold=True,color=color,font=MF)

# ===================== SLIDES ====================
# ---------- 0 COVER
s=0
img(s,'hd-fork.jpg',W-M-5100000,1580000,5100000,3400000,'Hand-drawn illustration: robot dispatcher at a fork choosing between a fast courier bike and a heavy cargo van')
x=M+80000; cx=5800000
rect(s,x,480000,560000,40000,fill=CY,preset='roundRect')
tb(s,x,590000,cx,'INTELLIGENT MODEL SELECTION & DECISION SYSTEMS',size=12,color=CY,font=HF,bold=True,ls=0.9,cy=260000)
tb(s,x,920000,cx,'Auto-routing\nLLMs',size=44,color=INK,font=HF,bold=True,cy=1380000)
tb(s,x,2400000,cx,'Routing every task to the right model for quality, cost and speed — from Microsoft Copilot and Foundry to Microsoft-Decision-1.1.',size=16,color=MUTED,cy=1100000)
tb(s,x,3620000,cx,'Yingting Huang  |  Sr. Cloud Solution Architect, Microsoft',size=15.2,color=INK,bold=True,cy=350000)
footer(s,'',1)
note(s,'大家好，欢迎来到今天的分享。现在做 AI 应用，几乎每个团队都会碰到一个现实问题：模型越出越多、换代越来越快，怎么在不掉效果的前提下，把调用成本和等待时间压下来？答案就是自动路由。\n接下来这 45 分钟，我会结合微软自己的落地经验，先带大家看 Microsoft Copilot、GitHub Copilot Fusion 和 Foundry Model Router 在后台是怎么选模型的，再重点聊聊微软专门为程序控制打造的决策模型 Decision-1.1，最后现场跑三组真实 Demo，看看怎么把这套机制接进你自己的系统里。')

# ---------- 1 AGENDA
s=1
header(s,'AGENDA','Our journey today')
items=[
    ('01','Capability gap','No single model wins all'),
    ('02','Cost & cache','163× gap & prefix cache'),
    ('03','MS products','Copilot, Fusion & Foundry'),
    ('04','Under the hood','Industry vs. MS HyDRA'),
    ('05','Decision-1.1','Fast, calibrated control'),
    ('06','Live demos','Fusion, Foundry & Decision'),
    ('07','Takeaways','Ship your own router'),
]
gap_a=115000; cw7=(CW-6*gap_a)/7; y0_a=1960000; ch_a=3260000
rect(s,M+200000,1680000,CW-400000,26000,fill=EDGE,preset='roundRect')
for i,(n,t,d) in enumerate(items):
    cx0=M+i*(cw7+gap_a)
    rect(s,cx0+cw7/2-70000,1623000,140000,140000,fill=CY,preset='ellipse')
    rect(s,cx0,y0_a,cw7,ch_a,fill=CARD,line=EDGE,lw=12700)
    pad_a=135000
    rect(s,cx0+pad_a,y0_a+210000,660000,300000,fill=CODEBG,line=EDGE,lw=12700,preset='roundRect',text=n,size=12,bold=True,color=CY,font=MF)
    tb(s,cx0+pad_a,y0_a+660000,cw7-2*pad_a,t,size=16,color=INK,bold=True,cy=780000)
    rect(s,cx0+pad_a,y0_a+1520000,cw7-2*pad_a,14000,fill=EDGE)
    tb(s,cx0+pad_a,y0_a+1640000,cw7-2*pad_a,d,size=13.2,color=MUTED,cy=1240000)
footer(s,'',2)
note(s,'今天的内容分这几块。我们先说清楚为什么要做自动路由：一来没有哪个模型样样都强，二来不同模型干同一件活，成本能差出一百多倍；这里面还藏着一条很容易踩坑的前缀缓存规律。\n接着看微软几款核心产品在生产环境里是怎么调度的，再往下挖一层，对比业内常见的路由方案和微软 HyDRA 架构的区别。后半场我们重点看 Decision-1.1 的三个控制原语，并在现场把三组真实链路跑通。')

# ---------- 2 PART 1: NO SINGLE BEST MODEL (CHARLES LAMANNA)
s=2
header(s,'01 · CAPABILITY SPECIALIZATION','No single model is best at everything')
cw_=5180000; cyy=1540000; ch=3680000
for idx_m,(xx,badge,title_m,sub_m,bullets,is_auto) in enumerate([
    (M,'PINNED MODEL','Static single-model mindset','One model forced onto every turn',[
        '• Biggest model always → pay 2.5×–5× more & wait longer',
        '• Small model always → fail when reasoning gets hard',
        '• Users switch for one hard bug & forget to switch back',
        '• Text-only models cannot generate diagrams or visuals',
    ],False),
    (W-M-cw_,'DYNAMIC ROUTING','Task-routed multi-model Auto','>90% of Microsoft Copilot queries today',[
        '• Enforces tenant admin rules, subprocessors & geography',
        '• Classifier matches sub-tasks via live eval scorecards',
        '• Adopts newly shipped frontier models automatically',
        '• Combines SLMs, reasoning LLMs & image models in one job',
    ],True),
]):
    rect(s,xx,cyy,cw_,ch,fill=CARD2 if is_auto else CARD,line=CY if is_auto else EDGE,lw=19050 if is_auto else 12700)
    pad=240000
    rect(s,xx+pad,cyy+210000,1920000,280000,fill=CY if is_auto else CODEBG,line=None if is_auto else EDGE,lw=12700,preset='roundRect',text=badge,size=10,bold=True,color=BG if is_auto else MUTED,font=MF)
    tb(s,xx+pad,cyy+590000,cw_-2*pad,title_m,size=21,bold=True,color=INK if is_auto else MUTED,font=HF,cy=420000)
    tb(s,xx+pad,cyy+1030000,cw_-2*pad,sub_m,size=13.8,bold=True,color=CY,cy=320000)
    rect(s,xx+pad,cyy+1420000,cw_-2*pad,14000,fill=EDGE)
    tb(s,xx+pad,cyy+1540000,cw_-2*pad,None,paras=[{'text':b,'spaceAfterPt':7.5} for b in bullets],size=13.8,color=INK if is_auto else MUTED,cy=1980000)
medallion(s,W//2,cyy+ch//2,diam=460000,glyph='→',fill=CY,size=18)
banner_box(s,M,5420000,CW,600000,'Shift from “which model is #1 overall?” to “which model fits this sub-task right now?”',size=16.5)
footer(s,'',3)
note(s,'先问大家一个问题：你们团队现在调大模型，是不是先挑一个综合表现最好的型号，然后所有请求从头绑到尾？全程绑死最贵的旗舰模型，账单翻几倍不说，连提个摘要都得等半天；可要是全换成小模型，稍微绕一点的逻辑又顶不住。更常见的是，工程师为了查个疑难杂症手动切到大模型，修完就忘了切回来，后面一礼拜干杂活全在烧最贵的算力。\n微软 Copilot 负责人 Charles Lamanna 说得很实在：今天已经没有哪个模型能在所有任务上都拿第一了——有的擅长深度推理和算账，有的专门做图，而翻邮件、提字段用小模型又快又省。所以现在 Microsoft Copilot 里超过九成的请求都走了 Auto，在企业合规边界之内，按每一步子任务自动挑最合适的模型。')

# ---------- 3 ONE PROMPT -> FOUR SPECIALIZED JOBS (LAMANNA WHITEBOARD)
s=3
header(s,'01 · CAPABILITY SPECIALIZATION','One prompt, four specialized jobs')
card_box(s,M,1520000,CW,920000,[
    {'text':'PROMPT  ·  “Customer renewal Thursday — expand, hold, or discount, and build a deck to make the case?”','sizePt':14.5,'bold':True,'color':CODE,'spaceAfterPt':6},
    {'text':'Guardrail gate first: filters tenant-allowed model providers, data residency, and live endpoint health.','sizePt':13,'color':MUTED},
],fill=CODEBG,line=EDGE,lw=12700,pad_x=240000,pad_y=100000)
gap=160000; cw4=(CW-3*gap)/4; y0=2620000; ch=3380000
jobs=[
    ('JOB 01 · RETRIEVE','Small Language Model','Scans M365 emails, Teams chats, meeting notes & prior contracts fast and cheaply.','SLM · Fast & cheap'),
    ('JOB 02 · REASON','Claude Opus 5.5','Main agentic loop evaluates expand / hold / discount economics; caches full context.','Main loop · Cached'),
    ('JOB 03 · VISUALIZE','GPT Image 2.5','Generates custom proposal graphics and infographics that text LLMs cannot render.','Image specialist'),
    ('JOB 04 · ASSEMBLE','Claude Opus 5.5','Reuses warm context cache to build the finished PowerPoint proposal without re-reading.','Deck synthesis'),
]
for i,(kicker,model,desc,badge) in enumerate(jobs):
    x=M+i*(cw4+gap)
    rect(s,x,y0,cw4,ch,fill=CARD,line=EDGE,lw=12700)
    rect(s,x+180000,y0+180000,cw4-360000,270000,fill=CODEBG,line=EDGE,lw=12700,preset='roundRect',text=kicker,size=10,bold=True,color=CY,font=MF)
    tb(s,x+180000,y0+560000,cw4-360000,model,size=18.2,bold=True,color=INK,cy=520000)
    rect(s,x+180000,y0+1140000,cw4-360000,14000,fill=EDGE)
    tb(s,x+180000,y0+1240000,cw4-360000,desc,size=13.4,color=MUTED,cy=1440000)
    rect(s,x+200000,y0+ch-560000,cw4-400000,360000,fill=CODEBG,line=EDGE,lw=12700,preset='roundRect',text=badge,size=11.5,bold=True,color=CY,font=MF)
footer(s,'',4)
note(s,'我们拿一个真实的办公场景看看什么叫按子任务分工。假设周二下午你跟 Copilot 说：“周四要谈客户续约了，帮我算算该推增购、保原价还是给折扣，再做一份汇报 PPT。”\n这句话进了 Auto 之后，先过一道企业合规筛子，确保供应商和数据驻留都符合要求，接着拆成四步接力：第一步派小模型去邮件、聊天记录和老合同里快速捞背景；第二步把烧脑的续约经济账交给擅长深度推理的 Opus 5.5，顺便把整套上下文缓存在那儿；第三步需要配插图了，文字模型画不了图，就自动切给 GPT Image 2.5；最后汇总生成整套幻灯片，再回到缓存还热着的 Opus 5.5 一气呵成，不用把几万字资料重读一遍。')

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
    ('Hard problems → escalate selectively','Save heavy reasoning models (Opus 5.5, Sonnet 5.5, GPT-6 Sol) for complex specs where small models stall in retry loops.',CY),
]
for i,(head_t,desc,col_) in enumerate(stats):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1360000,[
        {'text':head_t,'sizePt':16.2,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':desc,'sizePt':13.1,'color':MUTED},
    ],fill=CARD,pad_x=220000,pad_y=115000)
footer(s,'',5)
note(s,'除了模型各有所长，更大的动力来自成本差距。左边这张评测拿 28 个主流模型跑了 8 类多模态工程任务，一共测了 224 轮。\n结果非常有意思：排名前 14 的模型，综合质量分全挤在 86 到 90 这四分多一点的区间里，平时用起来体感差别并不大；但跑完同样这批任务的开销，从自动路由的 9 美分、Haiku 5.5 的 23 美分，一直拉到 Opus 5 的 14.75 美元，足足差了 163 倍。也就是说，日常大部分编码和结构化任务，轻量模型完全够用，Haiku 5.5 在做数据看板上甚至拿了全场第一；只有碰到逻辑特别绕、小模型容易死循环重试的复杂架构题，才真有必要把重型推理模型请出来。\n\n参考来源：GenisisIQ 28 模型多模态工程基准评测（blog.genisisiq.com）。')

# ---------- 5 PREFIX CACHE LAW
s=5
header(s,'02 · COST & LATENCY ECONOMICS','Don’t break a warm prefix cache')
img(s,'hd-tradeoff.jpg',M,1540000,5040000,3360000,'Hand-drawn robot balancing stopwatch, coin, and quality checkmark')
banner_box(s,M,5060000,5040000,860000,'Rule of thumb: switch models only at Turn 1, after compaction, or on isolated sub-agents.',size=13)
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
    ],fill=CARD,line=EDGE,lw=12700,pad_x=240000,pad_y=120000)
footer(s,'',6)
note(s,'一听说成本差出一百多倍，很多人的第一反应是：那我干脆每轮对话都算一下难度，哪句简单就立马切去便宜模型，岂不是最省钱？千万别这么干——这是做自动路由最容易踩的坑，叫打碎前缀缓存。\n现在的 Agent 第一轮启动时，往往已经把几万字的合同、代码文件和七八十个工具定义喂给了主模型。只要后面继续用这个模型，命中缓存的读取单价大概只有原价的十分之一，速度也快得多。要是第五轮为了省一句简单追问的钱，半路切去别家的便宜模型，缓存当场作废，新模型得按全价把几万个 Token 从头再读一遍，算下来反而更慢、更贵。所以成熟的路由器都守着一条规矩：只在对话第一轮、上下文压缩之后、派独立子 Agent，或者任务难度突然大跳水这些自然边界上才换模型。\n\n参考来源：Charles Lamanna（M365 Copilot Auto）与 Joe Binder（GitHub Blog 前缀缓存感知路由技术解析）。')

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
    rect(s,x,y0,cw4,ch,fill=CARD,line=EDGE,lw=12700)
    rect(s,x+200000,y0+230000,620000,300000,fill=CODEBG,line=EDGE,lw=12700,preset='roundRect',text=f'0{i+1}',size=11.5,bold=True,color=CY,font=MF)
    rect(s,x+890000,y0+230000,cw4-1090000,300000,fill=CODEBG,line=EDGE,lw=12700,preset='roundRect',text=tag_,size=10.5,bold=True,color=INK,font=MF)
    tb(s,x+200000,y0+700000,cw4-400000,prod,size=18.5,bold=True,color=INK,cy=680000)
    rect(s,x+200000,y0+1480000,cw4-400000,14000,fill=EDGE)
    tb(s,x+200000,y0+1620000,cw4-400000,desc,size=13.8,color=MUTED,cy=2480000)
footer(s,'',7)
note(s,'带着按需分工和保护缓存这两条原则，我们来看微软自己的产品线。虽然前台看起来都叫 Auto，但针对四类不同场景，后台其实做了四套各有侧重的调度系统。\n日常办公用的 M365 Copilot 和 Cowork，管的是什么时候从普通问答转进多步长任务，以及怎么在合规范围内跨厂商挑模型；写代码用的 GitHub Copilot Fusion，不光挑模型，还会按题目深浅自动切换单跑、级联和互审三种协作方式；面向云端 API 开发者的 Foundry Model Router，能在 45 个模型里做 20 毫秒级的极速排序，顺带优先消耗买好的 PTU 配额并自动兜底限流；最右边的 Decision-1.1，则是把这套做分流、做风控的决策能力直接开放成 API，让你嵌进自己的业务代码里。')

# ---------- 7 MICROSOFT COPILOT HOME SCREENSHOT
s=7
header(s,'03 · MICROSOFT PRODUCTS · MICROSOFT COPILOT','Microsoft Copilot Home: unified Auto')
ix=M; iy=1540000; icw=6400000; ich=3600000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'m365-copilot-home.png',ix+50000,iy+50000,icw-100000,ich-100000,'Official Microsoft screenshot: Microsoft Copilot Home composer unifying Chat and Cowork with Auto',fit='contain')
banner_box(s,ix,5260000,icw,700000,'One unified prompt box: Auto answers quick questions in Chat or hands off multi-step work to Cowork.',size=12.8)
rx=ix+icw+280000; rw=W-M-rx
m365_pts=[
    ('1 · Chat → Cowork handoff','Decision-1.1 detects when a prompt needs multi-step execution and suggests Cowork (2.2× faster, 4.4× cheaper).',CY),
    ('2 · Multi-provider within IT rules','Routes across OpenAI, Anthropic Claude & xAI Grok while enforcing EU Data Boundary & tenant admin switches.',CY),
    ('3 · Scoped context & local offload','Pulls only relevant M365 emails, chats & files via Work IQ — and offloads light tasks to local Windows PC models.',CY),
]
for i,(t,d,col_) in enumerate(m365_pts):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'',8)
note(s,'先看办公侧的 Microsoft Copilot 主界面。以前大家经常纠结一件事该在聊天框里直接问，还是去开个长任务工作区；现在一个 Auto 输入框全接住了。\n你发出一句话，后台在一百多毫秒里就做完了三件事：先用 Decision-1.1 判断这是快问快答，还是需要拆步骤跑的长任务——如果是后者，就主动提示转去 Cowork，比用通用大模型做判断快了两倍多，成本省掉四分之三；接着严格按企业管理员开的模型白名单和欧盟数据边界挑模型；同时靠 Work IQ 只捞最相关的企业邮件和文档，在支持的 Windows 电脑上甚至能把轻活直接交给本机小模型跑。')

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
    ('Predictable spend guardrails','Agent 365 Cost Management tracks work completed and enforces team spending limits so frontier runs never surprise IT.',CY),
]
for i,(t,d,col_) in enumerate(cw_pts):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.8,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'',9)
note(s,'一旦转进多步执行的 Copilot Cowork，它的策略就是典型的“锁模型、调力度”。系统先看你第一句话是要写封快信、排个会，还是要跨好几张财务表做测算，然后从企业开通的 GPT 6.1 Sol、Opus 5.5、Grok 4.7 等模型里挑一个最趁手的主模型，后面整场对话就一直跟着它走，避免换模型把热缓存废掉；每条回复旁边也会标清楚当前是哪个模型在干活。\n那锁死主模型以后，怎么兼顾快慢呢？靠的是每轮用 Decision-1.1 动态调推理档位，从最快的 Light 一路调到深度思考的 Max：简单步骤秒回，啃硬骨头时再给足思考预算，最外层还有 Agent 365 帮 IT 管住团队预算上限。')

# ---------- 9 GITHUB COPILOT FUSION COMPOSER SCREENSHOT
s=9
header(s,'03 · MICROSOFT PRODUCTS · GITHUB COPILOT FUSION','Copilot Fusion: pick effort, not models')
ix=M; iy=1540000; icw=6200000; ich=3592000
rect(s,ix,iy,icw,ich,fill='11161D',line=EDGE,lw=12700)
img(s,'fusion-picker.png',ix+40000,iy+40000,icw-80000,ich-80000,'Official GitHub screenshot: Copilot Fusion composer menu showing Standard, High, and Max effort levels',fit='contain')
banner_box(s,ix,5260000,icw,700000,'Pick Standard, High, or Max effort — hover the badge on any reply to see which models ran.',size=12.8)
rx=ix+icw+280000; rw=W-M-rx
fus_cards=[
    ('Standard · High · Max (+ Fast)','Standard routes 1 model per task (including local MAI Code 1.1 Flash / Qwen3.8 Flash); High & Max unlock orchestration.',CY),
    ('Frontier quality at ~50% cost','On AA Coding Agent Index, Fusion Max scores 60 (within 2 pts of Opus 5.5 Max) at ~50% lower API cost & ~40% less time.',CY),
    ('Fixes “forgot to switch back” waste','AT&T found developers picked a heavy model for one hard bug and left it on; Fusion right-sizes every turn automatically.',CY),
]
for i,(t,d,col_) in enumerate(fus_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.8,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'',10)
note(s,'再看程序员每天用的 GitHub Copilot Fusion。以前点开模型下拉框，面对一长串不断更新的模型名字很容易挑花眼；Fusion 直接改成了选投入档位：Standard、High 和 Max。\n实测效果非常能打：在 Artificial Analysis 的编程 Agent 榜单上，Fusion Max 拿到 60 分，几乎追平全程死磕最贵 Opus 5.5 Max 的水平，但平均每单省了一半接口费，耗时也缩短了四成。之前 AT&T 研发团队就反馈过，工程师为了查一个难缠的 Bug 切到大模型，之后写普通代码就再也没切回来过；换成 Fusion 自动伸缩后，简单任务甚至能直接落到本机的轻量模型上秒回。')

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
    ('3 · Critique  (Draft → Critics → Revise)','Primary drafts while read-only Critics review in parallel (cannot edit files, avoiding conflicts); Primary revises.',CY),
]
for i,(t,d,col_) in enumerate(pat_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':16.5,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13.4,'color':MUTED},
    ],fill=CARD,pad_x=220000,pad_y=110000)
footer(s,'',11)
note(s,'Fusion 为什么能做到效果不降、费用减半？因为它不光挑模型，还会按题目深浅自动换协作方式。\n日常查个配置、改个小函数，它直接走 Single 单模型，一步到位，不花一分钱额外评审费。碰到容易出并发隐患或逻辑漏洞的修改，它走 Cascade 级联：先让高性价比模型把代码改出来，再请裁判模型复核——没问题就直接放行，真抓出毛病才升级请重型模型返工。而遇上高风险的复杂架构设计，它会切到 Critique 互审：主模型先起草方案，再拉起跨厂商的只读评审模型挑刺，因为只有只读权限所以不会把文件改乱，最后交回主模型吸收意见改定稿。')

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
    ('Adaptive Cache Affinity','Tracks sessions via ID, previous_response_id or message fingerprint — keeping the prior model while warm & in-band.',CY),
]
for i,(t,d,col_) in enumerate(fo_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.2,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=105000)
footer(s,'',12)
note(s,'如果你们不是直接用现成的 Copilot，而是自己调云端 API 做应用，最顺手的就是 Foundry 里的 Model Router——在请求里直接传 model 等于 auto，调的也是同一套服务。\n很多人担心加一层路由会不会变慢。其实它本身并不是大语言模型，而是在海量问答、编程和工具调用记录上训练出来的专用机器学习排序器，把提示词、上下文和工具定义全扫一遍只要 20 毫秒左右，而且不留存客户数据。挑模型的逻辑也很清晰：默认的 Balanced 模式会在紧贴第一名 1% 到 2% 分差的第一梯队里挑最便宜的；Cost 模式把容忍带放宽到 5% 到 6%。到了多轮对话，它还会靠会话 ID 或消息指纹跟踪状态——只要前文缓存还热着，而且上一个模型没掉出当前质量带，就继续用它，把缓存折扣吃满。')

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
    ('3 · PTU Priority & Auto-Failover','Uses your pre-paid PTU first ($0 extra model fee) → PAYG → Managed, then fails over to #2 inside your allow-list.',CY),
]
for i,(t,d,col_) in enumerate(f_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.2,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=105000)
footer(s,'',13)
note(s,'自己接过多家模型接口的同学肯定有体会：打分选型只是第一步，真正折腾人的是参数兼容和线上限流。Foundry Model Router 把这些脏活全包了。\n排序之前先过资格门槛：按数据驻留区域、企业模型白名单，以及这次请求带没带工具调用、JSON Schema 或图片，把不支持的模型提前筛掉。选好模型往后转发时，它还会自动洗参数——比如推理模型不认 temperature，非推理模型不认 reasoning_effort，系统角色有的叫 developer 有的叫 system，路由器都会自动转换或剔除，不再莫名其妙报 400 错误。最后是消化配额和容灾：优先用你自己买好的零额外模型费 PTU，不够再走按量部署和微软托管容量池；哪怕线上突发高峰撞上 429 限流，也会在白名单里自动切去第二顺位模型，业务代码连重试逻辑都不用写。')

# ---------- 13 PART 4: INDUSTRY ROUTING ARCHITECTURES (GENERAL APPROACHES)
s=13
header(s,'04 · MODEL-LEVEL IMPLEMENTATION','Four general routing architectures')
c1=M; w1=2650000; c2=c1+w1+110000; w2=1650000; c3=c2+w2+110000; w3=3300000; c4=c3+w3+110000; w4=W-M-c4
hy=1460000
rect(s,M,hy,CW,400000,fill=CODEBG,line=EDGE,lw=12700)
for xx,ww,tt in [(c1,w1,'ARCHITECTURE'),(c2,w2,'OVERHEAD'),(c3,w3,'HOW IT WORKS'),(c4,w4,'KEY LIMITATION')]:
    tb(s,xx+150000,hy,ww-160000,tt,size=10.8,color=CY,font=MF,bold=True,ls=0.8,cy=400000)
approaches=[
    ('1 · Heuristic & Semantic','2 – 15 ms','Regex, token count, or embedding k-NN (e.g., Aurelio Semantic Router) against anchor prompts.','Surface topics ≠ reasoning difficulty; misses subtle traps.',CY),
    ('2 · Binary Preference','20 – 90 ms','Matrix factorization / BERT classifier (e.g., RouteLLM) predicting P(Strong beats Weak).','Coupled to fixed model IDs — must retrain when catalog changes!',CY),
    ('3 · Cascade (FrugalGPT)','+1× draft','Run cheap model first; a verifier scores the draft and escalates to strong if low.','Pays double latency on hard tasks; correlated judge blind spots.',CY),
    ('4 · Generative LLM Router','400 – 2000 ms','Prompt a general LLM to pick a tool/model and explain its reasoning in JSON/text.','Slow, expensive, and overconfident — RLHF hurts calibration!',AMB),
]
y=1960000; rh=940000
for a,lat,how,lim,col_ in approaches:
    rect(s,M,y,CW,rh,fill=CARD,line=EDGE,lw=12700)
    tb(s,c1+160000,y+80000,w1-180000,a,size=15,bold=True,color=col_,cy=rh-160000)
    rect(s,c2+120000,y+rh//2-170000,w2-200000,340000,fill=CODEBG,line=EDGE,lw=12700,preset='roundRect',text=lat,size=12.5,bold=True,color=INK,font=MF)
    tb(s,c3+150000,y+80000,w3-180000,how,size=13.2,color=INK,cy=rh-160000)
    tb(s,c4+150000,y+80000,w4-180000,lim,size=13.2,color=AMB if col_==AMB else MUTED,cy=rh-160000)
    y+=rh+90000
footer(s,'',14)
note(s,'看完产品，我们往底层退一步，看看业界做模型路由常见的四条路线，以及它们各自的短板。\n最早大家爱写正则或者做向量相似度匹配，几毫秒就出结果，但它只认字面主题，分不清“写个冒泡排序”和“写个无锁并发队列”难度差了十万八千里。后来像开源的 RouteLLM，改用分类器预测强模型赢过弱模型的概率，准度上去了，但把具体模型名字焊死在了权重里——现在模型几乎月月上新，池子一换就得重采数据重训。第三种 FrugalGPT 式的串行级联，每次先让小模型试写，一碰到难题就得白搭进去一轮等待时间。至于直接写提示词让通用大模型当路由，不仅慢、贵，而且经过人类偏好微调的模型天生爱装自信，输出的概率根本没法拿来卡工程阈值。')

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
    ('Multilingual Across 19 Languages','Trained on full multi-turn coding sessions (including Chinese, Japanese & Korean) within 4 pts of English accuracy.',CY),
]
for i,(t,d,col_) in enumerate(hy_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.8,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
footer(s,'',15)
note(s,'那怎么解决“模型月月换、路由器总不能月月重训”的问题？GitHub Copilot 底层的 HyDRA 论文给出了一个很巧的思路：把“这道题需要什么能力”和“手头有哪些模型”彻底解耦。\n它用了一个很轻的 ModernBERT 编码器，上面挂四个预测头，普通 CPU 上跑一次中位耗时只要 86 毫秒。关键在于，它输出的不是模型名字，而是这道题在推理、写代码、调试和调工具四个维度上的需求分。而每个候选模型擅长什么、单价多少，全写在一张静态配置表里；运行时只要比对一下谁能覆盖这四项需求，挑最便宜、最健康的那个就行。哪怕明天新上了 GPT-6，改一行配置就能接进来，完全不用重训分类器。在 SWE-Bench 实测里，它在同等解决率下省了 54.1% 的成本，省钱幅度是传统二分类路由的六倍。\n\n参考来源：Garg et al., HyDRA 论文（arXiv:2605.17106）。')

# ---------- 15 MICROSOFT'S THREE-LAYER ROUTING STACK
s=15
header(s,'04 · MICROSOFT’S ARCHITECTURE · BLUEPRINT','Microsoft’s three-layer routing stack')
img(s,'hd-sorter.jpg',M,1520000,4980000,3320000,'Hand-drawn robot sorting incoming tasks into three policy-governed trays')
banner_box(s,M,5020000,4980000,980000,'Models score bounded options; deterministic code enforces policy gates, thresholds & fallbacks.',size=13)
rx=M+4980000+320000; rw=W-M-rx
layers=[
    ('Layer 1 · Deterministic Policy & Cache Gate','Hard code filters tenant-allowed providers, data zones, required tool/schema capabilities, and warm prefix-cache state.',CY),
    ('Layer 2 · Fast Scorer / Decision Model (<180 ms)','Purpose-built encoder (HyDRA / Foundry ML ranker) or Microsoft-Decision-1.1 produces calibrated scores over allowed options.',CY),
    ('Layer 3 · Workflow Pattern & Output Verifier','Executes Single, Cascade or Critique, then runs deterministic schema, citation or policy safety checks before acting.',CY),
]
ch_=1300000; gap_=290000; y0_=1520000
for i,(t,d,col_) in enumerate(layers):
    yy=y0_+i*(ch_+gap_)
    card_box(s,rx,yy,rw,ch_,[
        {'text':t,'sizePt':16.2,'bold':True,'color':col_,'spaceAfterPt':6},
        {'text':d,'sizePt':13.1,'color':MUTED},
    ],fill=CARD,line=EDGE,lw=12700,pad_x=220000,pad_y=95000)
    if i<2:
        medallion(s,rx+rw//2,yy+ch_+gap_//2,diam=230000,glyph='↓',fill=CY,size=11)
footer(s,'',16)
note(s,'把前面聊的产品和算法放到一张图里，微软做路由的工程套路其实特别统一，就是明确的三层分工。\n第一层永远是确定性的硬代码，管租户白名单、数据驻留、接口能力过滤和前缀缓存状态，合规红线绝不交给模型去猜；第二层是百毫秒以内的专用打分器，只管在合规候选集里算出客观分数；第三层再按分数走单模型、级联或互审，并在输出前做好格式与安全校验。\n听到这儿大家肯定会问：微软内部有 HyDRA 和专用排序器，那我们自己开发业务 Agent 时，上哪儿找中间这一层又快、又便宜、概率还准的决策组件呢？')

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
],fill=CARD2,line=CY,lw=19050,pad_x=240000,pad_y=130000)
gap4=160000; tw4=(CW-3*gap4)/4; ty=4560000; th4=1400000
facts=[
    ('$0.042 / 1M','Input tokens (Global Std); output tokens FREE!',CY),
    ('~123 ms','Median decision latency (2.2× faster than v1.0)',CY),
    ('35×–100×','Faster than frontier LLMs on routing & QC',CY),
    ('3 Clouds','Microsoft Foundry, OpenRouter & Vercel',CY),
]
for i,(v,l,col_) in enumerate(facts):
    xx=M+i*(tw4+gap4)
    card_box(s,xx,ty,tw4,th4,[
        {'text':v,'sizePt':23,'bold':True,'color':col_,'spaceAfterPt':6},
        {'text':l,'sizePt':12.8,'color':INK},
    ],fill=CODEBG,line=EDGE,lw=12700,pad_x=180000,pad_y=120000)
footer(s,'',17)
note(s,'这正是微软推出 Microsoft-Decision-1.1 的原因。平时我们用的生成式大模型，训练目标是把话写得漂亮、完整；哪怕你只让它做个二选一的路由判断，它也得一个字一个字吐解释，动辄大几百毫秒，碰到缺信息时还特别容易硬猜。\n刚刚正式发布的 Decision-1.1 彻底换了条路子：它基于混合专家架构，每次推理只激活 4B 参数，单次前向计算直接输出校准过的概率，一句废话都不生成，还能同时读文本、JSON 和图片。价格更是便宜到几乎可以忽略——每百万输入 Token 只要 4.2 美分，输出完全免费，中位延迟只有 123 毫秒左右；哪怕把选项顺序打乱，判断波动也不到 1.3%，非常稳。')

# ---------- 17 DECISION-1.1 THREE TYPED PRIMITIVES
s=17
header(s,'05 · MICROSOFT DECISION-1.1 · API PRIMITIVES','Three primitives: choice, noul, score')
gap=180000; cw3=(CW-2*gap)/3; y0=1540000; ch=2360000
prims=[
    ('01 · choice  (Pick one)','“Which option fits best?”','Picks one label and returns calibrated probabilities per candidate.\nUse: model routing, ticket triage, tool pick.',CY),
    ('02 · noul  (Yes / No gate)','“Is this condition true?”','Returns a single [0, 1] probability for any true/false check.\nUse: safety gates, refund/rival checks, photo damage.',CY),
    ('03 · score  (0–N scale)','“How urgent or strong?”','Computes a probability-weighted score across ordered levels.\nUse: P0–P3 incident priority, output grading.',CY),
]
for i,(k,sub,desc,col_) in enumerate(prims):
    x=M+i*(cw3+gap)
    card_box(s,x,y0,cw3,ch,[
        {'text':k,'sizePt':18,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':sub,'sizePt':13.5,'bold':True,'color':INK,'spaceAfterPt':8},
        {'text':desc,'sizePt':12.8,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=110000)
rect(s,M,4060000,CW,1920000,fill=CODEBG,line=EDGE,lw=12700)
tb(s,M+220000,4140000,CW-440000,'POST <foundry-endpoint>/providers/microsoft/v1/systemone   ·   Ask all 3 in ONE call',size=11,color=FOOT,font=MF,cy=260000)
rect(s,M+220000,4430000,CW-440000,14000,fill=EDGE)
api_code=(
    '{ "model": "microsoft-decision-1.1", "state": {"msg": "Checkout is down in EU (3rd ping).", "contacts": 3},\n'
    '  "questions": {\n'
    '    "route":    {"type": "choice", "instructions": "Pick tier", "criteria": {"slm":"FAQ","sol":"Incident"}},\n'
    '    "severity": {"type": "score",  "instructions": "Severity",  "criteria": ["Cosmetic","Minor","Major","Critical"]},\n'
    '    "escalate": {"type": "noul",   "instructions": "Needs immediate human on-call?"} } }'
)
tb(s,M+220000,4460000,CW-440000,api_code,size=11.5,color=CODE,font=MF,cy=1420000)
footer(s,'',18)
note(s,'它在代码里用起来也非常直观。接口叫 systemone，意思就是替系统做毫秒级的直觉快判断。你把当前上下文放进 state，一次请求可以同时问好几个问题，一共就三种基础题型：\n多选一用 choice，比如决定派给哪个模型或哪个客服组，它会返回每个选项的概率——如果最高概率还不到 0.75，代码就可以停下来先找用户问清楚，不瞎猜；是非判断用 noul，比如查草稿有没有违规提竞品、买家拍的快递盒破没破，直接拿回 0 到 1 的概率；排高低轻重用 score，比如给工单定 P0 到 P3 紧急度，它会算出概率加权的期望分。最方便的是，这三种题型可以塞进同一个请求里一次拿齐。')

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
note(s,'靠这三个简单原语，平时写 Agent 最烦人的外围控制逻辑就都好办了。比如自己搭个路由器，用 choice 列好轻快提取、常规编码、深度互审和“信息不全先追问”四个出口，缺材料时第一时间拦住，不白烧大模型的钱。\n再比如做客服入口，一次请求同时跑 choice 分组和 score 定级：一看到客户说“床架塌了伤到腰”，严重度直接飙到 2.94，系统马上跳过机器人自动回复，直接呼人工安全专员。做电商售后，把退货照片放进 assets 跑个 noul，破损概率过八成就自动换货，拿不准再转人工。甚至在大模型拟好回复、发给客户之前，还能并排设几道 noul 安检门——一旦发现草稿里居然推荐了竞品或者私自承诺打折，概率过半就当场扣下。')

# ---------- 19 DECISION-1.1 BENCHMARKS & INTERNAL WINS
s=19
header(s,'05 · MICROSOFT DECISION-1.1 · BENCHMARKS','#1 across 102 decision benchmarks')
ix=M; iy=1540000; icw=6150000; ich=4460000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'decision-102-benchmarks.svg',ix+40000,iy+40000,icw-80000,ich-80000,'Vector SVG chart: Microsoft Decision benchmark report (Nov 14, 2026) — Microsoft-Decision-1.1 ranks #1 overall (78.8%) across 102 blind benchmarks (385,246 questions) and leads 7 of 9 capability categories',fit='contain')
rx=ix+icw+240000; rw=W-M-rx
card_box(s,rx,1540000,rw,1240000,[
    {'text':'#1 Overall Across 102 Blind Benchmarks','sizePt':15.2,'bold':True,'color':CY,'spaceAfterPt':7},
    {'text':'78.8% mean accuracy over 385,246 zero-overlap questions — ahead of Jev 1.14 (78.1), Gemini Decision 1 (77.7) & GPT-6 Luna (73.4).','sizePt':12.4,'color':MUTED},
],fill=CARD,pad_x=200000,pad_y=95000)
card_box(s,rx,2900000,rw,1240000,[
    {'text':'Leads 7 of 9 Capabilities  ·  2.2× Faster','sizePt':15.2,'bold':True,'color':CY,'spaceAfterPt':7},
    {'text':'#1 in routing, tools, safety, rules, reasoning, judging & consistency — plus Score 68 (+6 pts, 123 ms) on AA Decision Index v2.1.','sizePt':12.4,'color':MUTED},
],fill=CARD,pad_x=200000,pad_y=95000)
card_box(s,rx,4260000,rw,1740000,[
    {'text':'Powering Microsoft & 4,000+ Customers','sizePt':15.2,'bold':True,'color':CY,'spaceAfterPt':7},
    {'text':'• Copilot Chat→Cowork: 2.2× faster, 4.4× cheaper','sizePt':12.2,'color':INK,'spaceAfterPt':5},
    {'text':'• Cowork Auto effort + Foundry Evaluation judge','sizePt':12.2,'color':INK,'spaceAfterPt':5},
    {'text':'• Xbox Research: 14× faster, 200× cheaper than GPT-6 Sol','sizePt':12.2,'color':INK,'spaceAfterPt':5},
    {'text':'• Adopted by Epic, Equinor, Atos & Raiffeisen Bank','sizePt':12.2,'color':INK},
],fill=CARD,pad_x=200000,pad_y=90000)
footer(s,'',20)
note(s,'看到它每次只激活 4B 参数、价格又这么便宜，大家难免会问：它判得准吗？为了防止在少数公开题库上刷分过拟合，微软直接拉了训练集之外的 102 项基准、一共 38.5 万道题，对八款主流模型做了盲测。\n左边这张成绩单非常硬气：Decision-1.1 以 78.8% 的平均准确率排在总榜第一，九大能力维度里拿下了七个第一，尤其是路由分流、工具选择、安全风控和前后一致性全在榜首；在第三方 Artificial Analysis 决策指数上也涨到 68 分，速度快了 2.2 倍。它发布才五周就已经有四千多家企业用上了，微软自家的 Copilot 分流、Cowork 力度调节、Foundry 评测裁判，还有比旗舰模型快 14 倍、省 200 倍的 Xbox 分析管线，背后跑的全是它。\n\n参考来源：Microsoft Command Line — Microsoft-Decision-1.1 GA（2026 年 11 月 17 日，附 Microsoft Decision benchmark report 2026-11-14）。')

# ---------- 20 CONTOSO 7.2X CAC CASE STUDY VECTOR SVG
s=20
header(s,'05 · MICROSOFT DECISION-1.1 · IMPACT','Sales agent case: 7.2× lower CAC',cx=CW-2300000)
ix=M; iy=1540000; icw=6100000; ich=4400000
rect(s,ix,iy,icw,ich,fill='FFFFFF',line=EDGE,lw=12700)
img(s,'decision-cac-waterfall.svg',ix+50000,iy+50000,icw-100000,ich-100000,'Vector SVG chart: Contoso $10,000/mo sales agent Cost-per-Lead waterfall and 32-reply 100% accuracy router benchmark',fit='contain')
rx=ix+icw+260000; rw=W-M-rx
steps_cac=[
    ('1 · Baseline: Frontier LLM + 100% review','$0.31 per lead  ·  CAC = $13.00','Every email calls a $0.15 frontier LLM plus $0.24 human review — capping $10k/mo at 764 customers.',AMB),
    ('2 · Add choice router + score priority','$0.07 per lead  ·  CAC = $2.63','100% routing accuracy (vs. 88% regex): 57% of simple replies skip the LLM; only P1–P3 go to humans.',CY),
    ('3 · Add noul outbound safety gate','$0.05 per lead  ·  CAC = $1.81 (7.2× lower)','All 3 Decision-1.1 checks cost $0.00019/email total — cutting human review 100% → 8% (5,511 customers).',CY),
]
for i,(t,sub,desc,col_) in enumerate(steps_cac):
    yy=1540000+i*1510000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':14.6,'bold':True,'color':INK if col_==MUTED else col_,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':12.2,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.1,'color':MUTED},
    ],fill=CARD,pad_x=200000,pad_y=95000)
footer(s,'',21)
note(s,'准度有了、成本也低，放到真实业务里到底能省多少钱？我们看这个月预算一万美元的销售跟进案例。以前的做法很粗放：每封客户回信都扔给昂贵的旗舰大模型写草稿，又因为怕它乱说话，每一封还得安排销售人工复核。算下来处理一条线索要 3 毛 1，签下一单的获客成本高达 13 美元。\n加上 Decision-1.1 之后，先在入口用 choice 分流——32 类真实客户回信它做到了 100% 分对，把将近六成像“谢谢”、“退订”这种简单邮件直接交给规则或小模型处理，根本不惊动旗舰模型；接着用 score 给高意向客户排优先级，最后在出口用 noul 拦住乱提竞品的草稿。三道检查加起来，每封信只多花不到万分之二美元，却把人工复核率从 100% 压到了 8%。同样一万美元月预算，签单客户数翻了七倍多，获客成本直接降到 1.81 美元。\n\n参考来源：Microsoft Command Line 博客（$10k/月销售收件箱架构测算案例）。')

# ---------- 21 LIVE DEMO 1: GITHUB COPILOT AUTO & FUSION
s=21
header(s,'06 · LIVE DEMO 1','Copilot CLI Auto & Fusion live',cx=CW-3400000)
cx_=5550000; cy0=1540000; chh=4420000
rect(s,M,cy0,cx_,chh,fill=CODEBG,line=EDGE,lw=12700)
tb(s,M+220000,cy0+130000,cx_-440000,'copilot --model fusion --fusion-tier high  ·  1-call JSONL',size=11,color=FOOT,font=MF,cy=280000)
rect(s,M+220000,cy0+440000,cx_-440000,14000,fill=EDGE)
d1_code=(
    '$ copilot --model fusion --fusion-tier high \\\n'
    '    -p "..." --output-format json --usage-output-file u.json\n\n'
    '// Server-resolved pattern per single CLI command:\n'
    '-> Routine fix  : pattern="single"   (gpt-6.1-terra, 0 review)\n'
    '-> Lock bug     : pattern="cascade"  (sol -> luna Judge 5/5)\n'
    '-> 50k RPS RFC  : pattern="critique" (opus -> luna -> revise)\n'
    '-> --resume <id>: 99% cacheReadTokens hit (5,655 / 5,733 tok)'
)
tb(s,M+220000,cy0+480000,cx_-440000,d1_code,size=11.1,color=CODE,font=MF,cy=2600000)
card_box(s,M+220000,cy0+3260000,cx_-440000,960000,[
    {'text':'PS> npm --prefix demo run demo:fusion:live','sizePt':11.5,'bold':True,'color':INK,'spaceAfterPt':7},
    {'text':'Auto → Single → Native Cascade → Native Critique → 99% Cache','sizePt':10.6,'color':CY},
],fill=CARD,line=EDGE,lw=12700,pad_x=180000,pad_y=90000,font=MF)
rx=M+cx_+320000; rw=W-M-rx
d1_cards=[
    ('✓  Auto & Fusion Single fast path','categoryScores ≤ 0.10 & pattern="single"','Even on Fusion High, simple lookups & routine patches run 1 solver with zero review calls (3/3 node --test).',CY),
    ('↗  1-command native Cascade','gpt-6.1-sol → gpt-6-luna Judge → Opus skipped','One CLI call fixes ABBA lock order; native Judge scores 5/5 (accept) & skips conditional Opus 5.5 repair.',CY),
    ('⇄  1-command Critique + 99% Cache','Opus draft → Luna Critic → Opus revise','Native Critic flags Active-Active zero-RPO gap for Opus to revise; --resume hits 99% cacheReadTokens.',AMB),
]
for idx,(t,sub,desc,col_) in enumerate(d1_cards):
    yy=1540000+idx*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':INK,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':11.8,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,line=EDGE,lw=12700,pad_x=200000,pad_y=95000)
footer(s,'',22)
note(s,'账算完了，接下来我们点开右上角进入 Demo Studio，用三组真枪实弹的实验看看运行时到底发生了什么。第一个 Demo 跑的是 GitHub Copilot CLI，一共五步，每一步都只敲一条原生命令。\n第一步用 auto 模式去读配置文件里的默认端口。因为任务很简单，后台打出的四项能力需求分全在 0.1 以下，直接走单模型快车道分给 GPT-6 Luna，花 0.055 个额度就把 8787 端口读出来了，顺便把会话缓存预热好。\n接下来第二、三、四步最有看头——我们故意保持完全一样的 Fusion High 命令参数，只换题目，看服务端怎么自动变阵：第二步只是修个空白符裁剪的小问题，哪怕开了 High 档位，服务端一看难度不高，照样选 Single 单模型让 Terra 一次改完跑通单测，绝不乱花评审费。第三步换成修隐蔽的双锁并发死锁，同一条命令在服务端自动切成了 Cascade 级联：先由 Sol 把加锁顺序修好，再由 Luna 当裁判检查代码并打出 5 分满分放行，原本备着的 Opus 返工阶段直接省掉跳过，五百次并发压测一次通过。第四步让它写一份五万并发支付网关的容灾方案，服务端又自动切到 Critique 互审跑满三棒：Opus 先起草，跨厂商的 Luna 立刻挑出漏洞——指出初稿把“单写者租约”错当成了“跨机房零数据丢失”，随后交回 Opus 补齐复制机制完成定稿。\n第五步我们用 resume 接着第一步的会话追问两行监控指标，模型稳稳留在刚才预热好的 Luna 上，九成九的输入 Token 直接命中缓存，只花了 0.024 个额度。演示时点一下终端右上角的 Raw Log，每一步原始的事件流、裁判评语和账单都能看得一清二楚。')

# ---------- 22 LIVE DEMO 2: MICROSOFT FOUNDRY MODEL ROUTER
s=22
header(s,'06 · LIVE DEMO 2','Foundry Model Router live',cx=CW-3400000)
cx_=5550000; cy0=1540000; chh=4420000
rect(s,M,cy0,cx_,chh,fill=CODEBG,line=EDGE,lw=12700)
tb(s,M+220000,cy0+130000,cx_-440000,'foundry-v1preview.http  ·  ModelRouterControls=V1Preview',size=11,color=FOOT,font=MF,cy=280000)
rect(s,M+220000,cy0+440000,cx_-440000,14000,fill=EDGE)
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
    {'text':'4 live Foundry V1Preview cloud traces (0 local mocks)','sizePt':11,'color':CY},
],fill=CARD,line=EDGE,lw=12700,pad_x=180000,pad_y=90000,font=MF)
rx=M+cx_+320000; rw=W-M-rx
d2_cards=[
    ('✓  Pre-rank gate & param normalization','developer role + json_object → gpt-5.6-luna','One V1Preview endpoint normalizes cross-provider params and serves valid JSON in 30 ms router overhead.',CY),
    ('⚡  27–30 ms ML routing & retain affinity','DeepSeek-V4.1-Flash (JSON) vs. gpt-6-luna (Rust)','Routes simple JSON to Flash (0 reason tok) and escalates Rust proofs to Luna with retain affinity on Turn 2.',CY),
    ('⇄  Two-stage cost → quality routing','grok-4-1-fast (cost) → gpt-5.6-terra (quality)','Splits renewal analysis into two live calls: cheap extraction in cost mode followed by strategy in quality mode.',CY),
]
for idx,(t,sub,desc,col_) in enumerate(d2_cards):
    yy=1540000+idx*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':INK,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':11.8,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.6,'color':MUTED},
    ],fill=CARD,line=EDGE,lw=12700,pad_x=200000,pad_y=95000)
footer(s,'',23)
note(s,'第二个 Demo 看云端 API 层的 Foundry Model Router。这四步全程调的都是同一个 chat/completions 接口、传 model 等于 auto，看云端那颗二十多毫秒的机器学习排序器怎么帮我们省心又省钱。\n第一步测参数兼容和资格过滤。请求里同时塞了 developer 角色、temperature 和 JSON 模式——平时自己接多家模型最怕这种组合报 400 参数错误，这里 Foundry 先自动筛掉不支持 JSON 的模型、把参数洗干净，30 毫秒就路由给 gpt-5.6-luna 拿回合法 JSON。\n第二步和第三步，接口和 balanced 配置一个字都不改，连发两道难度悬殊的题做对比：第二步只从发票文本里提编号和币种，路由器 27 毫秒就挑中了又快又便宜的 DeepSeek-V4.1-Flash，推理 Token 为零，一点不浪费算力；第三步换成设计 Rust 无锁队列并做形式化内存序证明，小模型兜不住了，路由器 30 毫秒自动升级到强推理模型 gpt-6-luna；紧接着第二轮简短追问一句溢出怎么防，路由器靠消息指纹识别出是同一通对话，返回 retain 稳稳留住 gpt-6-luna，不会因为追问简单就乱切回小模型把缓存废掉。\n第四步演示怎么把长工作流拆成两棒调同一个接口：第一棒传 cost 模式，让便宜快速的 grok-4-1-fast 先从原始材料里提取两条关键续约数字；第二棒只喂这两条摘要并切成 quality 模式，交给旗舰 gpt-5.6-terra 推演博弈策略，真正做到粗活便宜做、细活精做。点右上角 Raw Log 同样能直接看云端返回的路由耗时和轨迹详情。')

# ---------- 23 LIVE DEMO 3: MICROSOFT-DECISION-1.1 CONTROLLER
s=23
header(s,'06 · LIVE DEMO 3','Decision-1.1 agent controller',cx=CW-3400000)
cx_=5550000; cy0=1540000; chh=4420000
rect(s,M,cy0,cx_,chh,fill=CODEBG,line=EDGE,lw=12700)
rect(s,M+cx_-1480000,cy0+120000,1240000,300000,fill=CY,preset='roundRect',text='GA · Nov 2026',size=10.5,bold=True,color=BG,font=MF)
tb(s,M+220000,cy0+120000,cx_-1800000,'decision-controller.ts  ·  /v1/systemone',size=11,color=FOOT,font=MF,cy=300000)
rect(s,M+220000,cy0+450000,cx_-440000,14000,fill=EDGE)
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
],fill=CARD,line=EDGE,lw=12700,pad_x=180000,pad_y=90000,font=MF)
rx=M+cx_+320000; rw=W-M-rx
d3_cards=[
    ('✓  Zero-spread routing (choice & noul)','5/5 identical 0.9835 · 4/4 inbox p=1.00','5 consecutive live calls return 0.00 pt spread; 3 of 4 routine inbox messages skip the frontier LLM.',CY),
    ('!  3-in-1 safety triage (choice+score+noul)','safety_support (0.998) + score 1.97 + repeat 1.00','One 348 ms call classifies injury risk, scores urgency & flags 3rd repeat contact — blocking bot reply.',AMB),
    ('✕  Outbound guardrail & missing-doc abstain','Rival promo noul=0.970 & missing Exhibit B p=0.9999','Holds a draft recommending rival Fabrikam (0.970) and stops to ask when Exhibit B is missing from state.',AMB),
]
for idx,(t,sub,desc,col_) in enumerate(d3_cards):
    yy=1540000+idx*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':15.5,'bold':True,'color':INK,'spaceAfterPt':6.5},
        {'text':sub,'sizePt':11.8,'bold':True,'color':col_,'spaceAfterPt':6.5},
        {'text':desc,'sizePt':12.4,'color':MUTED},
    ],fill=CARD,line=EDGE,lw=12700,pad_x=200000,pad_y=95000)
footer(s,'',24)
note(s,'第三个 Demo 看应用控制层的 Decision-1.1，全程直连云端 systemone 接口，分五步看它怎么替掉又慢又飘的提示词裁判。\n第一步测稳定性：拿同一封打听沙发折扣、说亲戚20号要来的询价信连调五次 noul，五次一分不差全返回 0.9835，极差是零，中位耗时三百多毫秒，完全没有生成式模型每次跑结果都乱飘的毛病。\n第二步测前置分流：用 choice 配好免回复、规则模板、轻量小模型和旗舰模型四条道，把“谢谢点赞”、“退订 STOP”、“促销咨询”和“跨系列质保对比”四条消息送进去，四条全以接近满分的把握各走各道，直接帮旗舰大模型省掉四分之三的调用。\n第三步测一石三鸟：客户投诉床架半夜塌了伤到人，而且是第三次来信。我们在一次请求里同时问归属团队、紧急度打分和是否重复投诉三个问题，三百多毫秒一次拿回安全团队、1.97 高危分和重复投诉确认，代码当场拦住自动回复机器人，直接转人工安全专员。\n第四步测出口护栏：大模型草稿里居然写着“竞品 Fabrikam 有同款只要 749 美元”，发出去之前过一道 noul 安检，测出推荐竞品概率高达 0.97，当场扣下，帮业务把人工抽检比例压到个位数。\n第五步测缺件拒答：用户让对比合同 A 和附件 B 的解约期，但上下文里根本没挂附件 B。它没有跟着瞎编，而是以 0.9999 的概率选了“先找用户要附件 B”。另外工作台最下面还留了个输入框，现场观众想测什么句子随时敲进去就能试；点 Raw Log 也能看每次返回的完整概率分布。')

# ---------- 24 CLOSER: KEY TAKEAWAYS
s=24
img(s,'hd-review.jpg',W-M-5040000,1620000,5040000,3360000,'Hand-drawn illustration: two friendly robots reviewing and approving a routed workflow together')
x=M+80000; cx=5850000
rect(s,x,330000,520000,38000,fill=CY,preset='roundRect')
tb(s,x,420000,cx,'SUMMARY · KEY TAKEAWAYS',size=12,color=CY,font=HF,bold=True,ls=0.9,cy=260000)
tb(s,x,740000,cx,'Right-size the model,\nkeep the control',size=36,color=INK,font=HF,bold=True,cy=1200000)
tk=[
    '1   Route sub-tasks by capability — no single model wins all.',
    '2   Stop paying 100× for simple work — & keep prefix caches warm.',
    '3   Adopt Copilot Auto, Copilot Fusion & Foundry Router first.',
    '4   Use Microsoft-Decision-1.1 for fast routing, priority & safety gates.',
]
tb(s,x,2080000,cx,None,paras=[{'text':t,'spaceAfterPt':10} for t in tk],size=14.4,color=INK,cy=2320000)
card_box(s,x,4560000,cx,820000,[
    {'text':'aka.ms/decision-1.1  ·  blog.genisisiq.com','sizePt':12.5,'bold':True,'color':CY,'spaceAfterPt':5},
    {'text':'github.com/microsoftconnect/Decision-Benchmarks','sizePt':12.5,'bold':True,'color':CY},
],fill=CODEBG,line=EDGE,lw=12700,pad_x=200000,pad_y=90000,font=MF)
tb(s,x,5540000,cx,'Thank you  ·  Q&A',size=24,color=INK,font=HF,bold=True,cy=480000)
footer(s,'',25)
note(s,'最后用四句话把今天的内容收个尾，方便大家带回团队直接落地：\n第一，别再找一个全能模型从头绑到尾了，按子任务拆开分工；第二，算成本账一定要盯紧前缀缓存，只在首轮或独立子任务这些自然边界换模型，别在对话半路瞎切换；第三，现成轮子优先用，办公开 Copilot Auto，写代码用 Copilot Fusion，调云端接口直接挂 Foundry Model Router；第四，轮到你自己写业务分流、排工单优先级或者加出口合规护栏时，把百毫秒级、概率准又几乎不花钱的 Decision-1.1 当成标准零件用起来。今天的内容就到这里，谢谢大家，看看各位有什么问题！')

# ---------- 25 APPENDIX: PUBLIC REFERENCES
s=25
header(s,'APPENDIX · OFFICIAL SOURCES & BENCHMARKS','Public field guide')
gap=240000; colw=(CW-gap)/2; cy0=1540000; ch=4420000
app_cols=[
    ('Benchmarks & Product Routing','Capability specialization, 163× cost benchmarks, Microsoft Copilot Auto & GitHub Copilot Fusion.',REFS_LEFT,CY),
    ('Routing Architecture & Decision-1.1','HyDRA multi-head routing paper, Foundry Model Router internals, Decision-1.1 API & open benchmarks.',REFS_RIGHT,CY),
]
for i,(t,sub,links,col_) in enumerate(app_cols):
    xx=M+i*(colw+gap)
    rect(s,xx,cy0,colw,ch,fill=CARD,line=EDGE,lw=12700)
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
note(s,'最后一页把今天提到的评测报告、官方文档、HyDRA 论文以及 Decision-1.1 的接入指南和开源题库都整理好了，PPT 和网页上都能直接点开，方便大家回去查阅。')


# ===================== LOCALIZATION & LAYOUT VALIDATOR =====================
def get_localized_slides(lang='en'):
    if lang == 'en':
        return slides
    if lang != 'zh':
        raise ValueError(f'Unsupported language: {lang}')
    out = {}
    for k, ops in slides.items():
        new_ops = []
        for o in ops:
            no = copy.deepcopy(o)
            if 'text' in no and no['text'] in ZH_TEXT_MAP:
                no['text'] = ZH_TEXT_MAP[no['text']]
            if 'paragraphs' in no:
                for p in no['paragraphs']:
                    if p.get('text') in ZH_TEXT_MAP:
                        p['text'] = ZH_TEXT_MAP[p['text']]
            new_ops.append(no)
        out[k] = new_ops
    return out

def get_localized_notes(lang='en'):
    if lang == 'zh':
        return notes
    if lang == 'en':
        return {k: EN_NOTES.get(k, v) for k, v in notes.items()}
    raise ValueError(f'Unsupported language: {lang}')

def validate_layout(slide_map=None):
    target = slides if slide_map is None else slide_map
    errors=[]
    for k in sorted(target):
        ops=target[k]
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

def write_text(tf,o,lang='en'):
    tf.word_wrap=True; tf.vertical_anchor=MSO_ANCHOR.MIDDLE
    tf.margin_left=Emu(76200); tf.margin_right=Emu(76200)
    tf.margin_top=Emu(57150); tf.margin_bottom=Emu(57150)
    paras=o.get('paragraphs') or [{'text':o['text']}]
    raw_font=o.get('fontFamily',BF)
    eff_font='Microsoft YaHei UI' if (lang=='zh' and raw_font!=MF) else raw_font
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
            f.name=eff_font; f.size=Pt(sz)
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

def add_pages_qr(sl, pages_url, lang='en'):
    clean = (pages_url or '').strip()
    if not clean:
        return
    import io, re, qrcode
    display = re.sub(r'^https?://', '', clean).rstrip('/')
    kicker = ZH_TEXT_MAP.get('SCAN FOR LIVE SLIDES & DEMO', 'SCAN FOR LIVE SLIDES & DEMO') if lang == 'zh' else 'SCAN FOR LIVE SLIDES & DEMO'
    card = sl.shapes.add_shape(PRESETS['roundRect'], Emu(740000), Emu(4190000), Emu(4720000), Emu(1930000))
    card.shadow.inherit = False
    card.fill.solid(); card.fill.fore_color.rgb = rgb(CODEBG)
    card.line.color.rgb = rgb(EDGE); card.line.width = Emu(12700)
    pad = sl.shapes.add_shape(PRESETS['roundRect'], Emu(860000), Emu(4310000), Emu(1690000), Emu(1690000))
    pad.shadow.inherit = False
    pad.fill.solid(); pad.fill.fore_color.rgb = rgb('FFFFFF')
    pad.line.color.rgb = rgb(EDGE); pad.line.width = Emu(9525)
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=12, border=2)
    qr.add_data(clean); qr.make(fit=True)
    img_buf = io.BytesIO()
    qr.make_image(fill_color='#' + INK, back_color='#FFFFFF').save(img_buf, format='PNG')
    img_buf.seek(0)
    sl.shapes.add_picture(img_buf, Emu(875000), Emu(4325000), Emu(1660000), Emu(1660000))
    cap = sl.shapes.add_textbox(Emu(2710000), Emu(4780000), Emu(2640000), Emu(280000))
    write_text(cap.text_frame, {'text': kicker, 'sizePt': 8.5, 'bold': True, 'color': CY, 'fontFamily': BF}, lang=lang)
    url_tb = sl.shapes.add_textbox(Emu(2710000), Emu(5060000), Emu(2640000), Emu(380000))
    write_text(url_tb.text_frame, {'text': display, 'sizePt': 11, 'bold': True, 'color': INK, 'fontFamily': MF}, lang=lang)
    url_tb.text_frame.paragraphs[0].runs[0].hyperlink.address = clean

def build(out,img_dir,pages_url=None,lang='en'):
    loc_slides = get_localized_slides(lang)
    loc_notes = get_localized_notes(lang)
    validate_layout(loc_slides)
    out_dir=os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir,exist_ok=True)
    prs=Presentation(); prs.slide_width,prs.slide_height=Emu(W),Emu(H)
    blank=prs.slide_layouts[6]
    for k in sorted(loc_slides):
        sl=prs.slides.add_slide(blank)
        sl.background.fill.solid(); sl.background.fill.fore_color.rgb=rgb(BG)
        rendered=[]
        for o in loc_slides[k]:
            op=o['op']
            if op=='add_image': add_picture(sl,o,img_dir)
            elif op=='add_text_box':
                sh=sl.shapes.add_textbox(Emu(o['x']),Emu(o['y']),Emu(o['cx']),Emu(o['cy'])); write_text(sh.text_frame,o,lang=lang)
                rendered.append(sh)
            elif op=='add_shape':
                sh=sl.shapes.add_shape(PRESETS[o['preset']],Emu(o['x']),Emu(o['y']),Emu(o['cx']),Emu(o['cy']))
                sh.shadow.inherit=False
                sh.fill.solid(); sh.fill.fore_color.rgb=rgb(o['fill'])
                if o.get('line'): sh.line.color.rgb=rgb(o['line']); sh.line.width=Emu(o.get('lineWidth',12700))
                else: sh.line.fill.background()
                if o.get('rot'): sh.rotation=o['rot']/60000
                if 'text' in o: write_text(sh.text_frame,o,lang=lang)
                rendered.append(sh)
        if k==0 and pages_url:
            add_pages_qr(sl, pages_url, lang=lang)
        if k==3:
            add_appear_animation(sl,[rendered[start:start+6] for start in (4,10,16,22)])
        elif k==6:
            add_appear_animation(sl,[rendered[start:start+6] for start in (2,8,14,20)])
        if k in loc_notes: sl.notes_slide.notes_text_frame.text=loc_notes[k]
    prs.save(out); print(f'Saved {out}  ({len(prs.slides)} slides, lang={lang})')

if __name__=='__main__':
    here=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root=os.path.dirname(here)
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',default=os.path.join(root,'dist','pptx','Auto-routing LLMs.pptx'))
    ap.add_argument('--images',default=os.path.join(here,'assets','images'))
    ap.add_argument('--pages-url',default=os.environ.get('PAGES_URL'))
    ap.add_argument('--lang',choices=('en','zh'),default='en')
    a=ap.parse_args(); build(a.out,a.images,pages_url=a.pages_url,lang=a.lang)
