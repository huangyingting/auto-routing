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
footer(s,'',1)
note(s,'大家好，欢迎参加今天的分享。现在做 AI 应用，很多团队都会遇到同一个问题：市面上的模型越来越多、更新也很快，怎么在不牺牲效果的前提下，把调用费用和响应时间降下来？这就是今天要讲的自动路由。\n接下来这 45 分钟，我会结合微软在几个产品里的实际做法，先看看 Microsoft Copilot、GitHub Copilot Fusion 和 Foundry Model Router 是怎么自动选模型的，再介绍专门用于程序判断的决策模型 Decision-1.1，最后通过三组演示，看看怎么把这些能力用到自己的项目里。')

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
note(s,'今天的内容分这几个部分。我们先说说为什么要做自动路由：一方面没有哪个模型在所有任务上都是最好的，另一方面不同模型完成同样任务的费用可以相差上百倍；这里面还有一个关于前缀缓存的关键注意事项。\n接着我们看微软几款产品是怎么实现调度的，再对比一下业内常见的路由方案和微软 HyDRA 架构的区别。后半部分重点介绍 Decision-1.1 的三种用法，并在现场跑完三组演示。')

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
note(s,'先看一个很常见的现象：不少团队在接入大模型时，习惯先挑一个综合表现最好的型号，然后所有请求都固定发给它。如果全程只用最贵的大模型，费用高出好几倍，连简单的文字摘要也要多等一会儿；如果全部换成小模型，遇到稍微复杂的推理又容易出错。日常使用中还常出现一种情况：为了查一个疑难问题手动切到大模型，解决之后忘了改回来，后面好几天普通问答也一直在用最贵的模型。\n微软 Copilot 负责人 Charles Lamanna 提到过一个实际情况：现在没有哪一个模型能在所有任务上都排第一——有的擅长复杂推理和数据分析，有的专门用来生成图片，而检索邮件、提取字段用小模型就既快又便宜。所以目前 Microsoft Copilot 里超过 90% 的请求都由后台的 Auto 自动分配，在企业后台允许的模型和数据区域范围内，为每一步任务挑选合适的模型。')

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
note(s,'我们看一个实际的办公例子。假设周二下午你对 Copilot 说：“周四要谈客户续约了，帮我算一下应该推增购、维持原价还是给折扣，再做一份汇报用的 PPT。”\n请求进入 Auto 后，系统会先检查企业允许使用哪些模型提供商、数据保存在哪个区域，然后把任务拆成四个步骤：第一步用响应很快的小模型，从邮件、聊天记录和历史合同里找出相关背景资料；第二步把需要计算的续约方案交给推理能力强的 Opus 5.5，同时把整理好的上下文缓存下来；第三步需要给 PPT 配插图，文本模型做不了图，就切换到图像模型 GPT Image 2.5；第四步汇总生成整套幻灯片时，再回到第二步已经建好缓存的 Opus 5.5，不需要把几万字材料重新读一遍。')

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
note(s,'除了不同模型各有侧重，成本差异也是做自动路由的重要原因。左边这项评测用 28 个主流模型跑了 8 类多模态工程任务，总共测试了 224 轮。\n可以看到，排名前 14 的模型综合得分都在 86.2 到 90.4 之间，分差只有 4.2 分，日常任务里的体验很接近；但跑完同样这组任务的费用，从自动路由的 0.09 美元、Haiku 5.5 的 0.23 美元，一直到 Opus 5 的 14.75 美元，相差了 163 倍。也就是说，大部分常规编码和结构化处理用轻量模型就够了，比如 Haiku 5.5 在生成数据看板这项任务上还排到了第一；只有遇到需求复杂、小模型容易反复出错的任务，才需要调用高成本的推理模型。\n\n参考来源：GenisisIQ 28 模型多模态工程基准评测（blog.genisisiq.com）。')

# ---------- 5 PREFIX CACHE LAW
s=5
header(s,'02 · COST & LATENCY ECONOMICS','Don’t break a warm prefix cache')
img(s,'hd-tradeoff.jpg',M,1540000,5040000,3360000,'Hand-drawn robot balancing stopwatch, coin, and quality checkmark')
banner_box(s,M,5060000,5040000,860000,'Rule of thumb: switch models only at Turn 1, after compaction, or on isolated sub-agents.',size=13)
rx=M+5040000+340000; rw=W-M-rx
cache_cards=[
    ('Warm prefix cache = 10×–20× cheaper','Once a main model caches contracts, emails, repo files and 80+ tool schemas, follow-up turns pay ~10% cache-read rates.',CY),
    ('Mid-session downgrades can cost MORE','Switching to a “cheaper” model mid-session invalidates the prefix cache and forces re-prefilling 50k+ tokens from scratch.',AMB),
    ('Route at natural cache boundaries','Pick on Turn 1, after context compaction, on isolated sub-agents, or only when task complexity shifts dramatically.',CY),
]
for i,(t,d,col_) in enumerate(cache_cards):
    yy=1540000+i*1520000
    card_box(s,rx,yy,rw,1380000,[
        {'text':t,'sizePt':17,'bold':True,'color':col_,'spaceAfterPt':7},
        {'text':d,'sizePt':13.6,'color':MUTED},
    ],fill=CARD,line=EDGE,lw=12700,pad_x=240000,pad_y=120000)
footer(s,'',6)
note(s,'看到模型之间有这么大的价差，很容易想到一个做法：干脆每一轮对话都重新算一次难度，遇到简单的追问就马上切到便宜的小模型。实际上这样做往往适得其反，因为会让前缀缓存失效。\n现在的 Agent 在第一轮对话时，通常会放入大量合同文本、代码文件和几十个工具定义。只要后续轮次继续用同一个模型，读取已缓存内容的单价一般只有原价的十分之一左右，响应也更快。如果在对话中途为了省一点费用切到另一个模型，原来的缓存就用不上了，新模型必须按全价把前面几万个 Token 重新处理一遍，结果反而更慢、更贵。因此更合理的做法是：只在会话刚开始、上下文压缩重置之后、独立的子任务，或者任务难度明显变化时才切换模型。\n\n参考来源：Charles Lamanna（M365 Copilot Auto）与 Joe Binder（GitHub Blog 前缀缓存感知路由技术解析）。')

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
note(s,'结合按任务选型和保持缓存这两点，我们来看看微软自己的四类产品方案。虽然界面上大多都叫 Auto，但针对不同使用场景，底层的处理方式各有侧重。\n面向日常办公的 M365 Copilot 和 Cowork，主要处理什么时候从普通问答转入多步任务，以及在企业允许的范围内跨厂商选模型；面向开发者的 GitHub Copilot Fusion，除了选模型，还会根据问题难度在单次执行、级联评审和多模型审校之间切换；面向云端 API 开发的 Foundry Model Router，用约 20 毫秒在 45 个模型里完成排序，并优先使用企业已购买的 PTU 配额；最右边的 Decision-1.1，则是把用于分类、打分和内容检查的决策模型直接做成 API，方便业务系统自己调用。')

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
note(s,'先看办公场景下的 Microsoft Copilot 主界面。以前用户常常拿不准一个问题该在普通聊天框里问，还是单独开一个多步任务；现在统一成了一个 Auto 输入框。\n用户发出提问后，后台在百毫秒左右完成三步处理：先用 Decision-1.1 判断这是普通问答，还是需要分步执行的复杂任务——如果是后者，就提示转到 Cowork 处理，比用通用大模型做判断快 2.2 倍，费用省掉四分之三以上；接着按照企业管理员开启的模型范围和欧盟数据边界要求筛选可用模型；同时通过 Work IQ 只提取相关的企业邮件和文档，在支持的 Windows 电脑上还可以把简单任务交给本地小模型。')

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
note(s,'进入多步执行的 Copilot Cowork 后，它的设计思路是先固定主模型、再按步调整推理强度。系统根据第一条提问的内容——比如是写封短邮件、安排会议，还是跨多张表格做财务测算——从企业启用的 GPT 6.1 Sol、Opus 5.5、Grok 4.7 等模型里选出一个主模型，后续步骤保持不变，这样就能持续复用前缀缓存；每条回复旁边也会显示当前使用的模型名称。\n主模型固定之后，再通过 Decision-1.1 在每一步动态调整推理档位，从轻量的 Light 到深度推理的 Max：简单步骤快速返回，复杂步骤分配更多思考计算量，同时配合 Agent 365 控制团队的整体用量预算。')

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
note(s,'再看开发场景里的 GitHub Copilot Fusion。过去开发者点开模型菜单，需要在不断增加的模型型号里手动挑选；Fusion 改成了直接选择投入档位：Standard、High 和 Max。\n从评测数据看，在 Artificial Analysis 编程评测里，Fusion Max 拿到 60 分，与全程固定使用 Opus 5.5 Max 非常接近，但平均每次任务的 API 费用降低了约一半，耗时也减少了约 40%。之前 AT&T 的工程团队提到，开发者常为了排查一个复杂 Bug 切到大模型，之后写常规代码也一直没切回来；交给 Fusion 自动调整后，简单修改可以直接交给本地或云端的轻量模型快速完成。')

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
note(s,'Fusion 之所以能在保持质量的同时省下一半费用，是因为它除了选模型，还会根据问题难度切换三种执行模式。\n日常查配置、改简单函数时，使用 Single 单模型模式，由一个合适的模型直接完成，不产生额外的评审开销。遇到容易出并发或边界问题的代码修改，会使用 Cascade 级联模式：先用高性价比模型写出修改，再由 Judge 模型检查——没问题就直接通过，发现缺陷时才升级交给更强的模型重新修复。如果遇到复杂的架构方案设计，则切换到 Critique 审校模式：主模型起草初稿，同时调用其他厂商的只读模型审阅挑错（因为设为只读权限，不会互相覆盖文件），最后由主模型综合修改意见生成终稿。')

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
note(s,'如果团队是自己调用云端 API 开发应用，可以使用 Microsoft Foundry 里的 Model Router——在请求参数里直接把 model 设为 auto，调用的也是这套机制。\n不少人会关心加一层路由会不会拖慢响应。其实这个路由器本身不是大语言模型，而是基于大量问答、编程和工具调用记录训练的轻量机器学习排序模型，读完系统提示词、历史对话和工具定义大约只需 20 毫秒，也不会存储用户的提示词内容。选模型的规则也很直观：默认的 Balanced 模式会在与最高分差距 1% 到 2% 的候选模型里选价格最低的；Cost 模式把这个范围放宽到 5% 到 6%。在多轮对话中，它会根据会话 ID 或历史消息指纹判断上下文是否连续——只要缓存还没过期，且上一轮模型仍在当前质量区间内，就继续沿用原模型。')

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
note(s,'实际接入多家模型接口时，除了选型，参数差异和限流处理也很花精力，Foundry Model Router 把这些步骤做进了统一流程里。\n首先在打分前先做条件筛选：根据区域设置、允许使用的模型列表，以及当前请求是否包含工具定义、JSON Schema 或图片输入，提前筛掉不支持的模型。选定目标模型后，路由器会自动转换不兼容的参数——例如推理模型不支持 temperature，普通模型不支持 reasoning_effort，系统角色有的叫 developer 有的叫 system，转发时都会自动处理，避免触发 400 参数报错。最后在资源调度上，会优先使用企业已购买的 PTU 部署，不产生额外模型费，不足时再使用按量部署和微软托管资源池；如果遇到突发流量触发 429 限流，会自动切换到候选列表里的下一个模型。')

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
note(s,'了解完产品方案，我们再来看看底层实现。目前业界常见的模型路由主要有四类做法，各自都有比较明显的局限。\n第一类是正则规则或向量相似度匹配，几毫秒就能算完，但表面话题相似不代表推理难度一样，比如“写一个简单排序”和“实现无锁并发队列”在字面上都是数据结构问题，实际难度却相差很多。第二类是像 RouteLLM 这样的二分类偏好路由，预测强模型表现优于弱模型的概率，准确率更高，但分类器权重和具体模型型号绑在一起——每当候选模型更新，就需要重新收集数据训练。第三类是 FrugalGPT 式的串行级联，先让小模型试跑，遇到难题时白白多花了一轮等待时间。第四类是直接写提示词让通用大模型做路由判断，不仅耗时长、费用高，而且通用模型容易盲目自信，输出的概率很难直接拿来做阈值判断。')

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
note(s,'那么怎么解决候选模型频繁更新、不想反复重训路由器的问题？GitHub Copilot 采用的 HyDRA 架构给出了一个做法：把“评估任务需要什么能力”和“当前有哪些可用模型”分开处理。\n它底层使用一个轻量的 ModernBERT 编码器，带有四个输出头，在普通 CPU 上运行的中位耗时只有 86 毫秒。它预测的不是某个模型的名字，而是当前请求在推理、代码生成、调试和工具调用四个维度上的需求分值。同时，每个候选模型的四项能力指标和单价单独写在配置文件里；运行时只要对比哪些模型能满足这四项需求，从中选出可用且成本最低的一个即可。后续上线新模型时，只需要更新配置文件，不需要重新训练分类器。在 SWE-Bench 测试中，这套方法在保持同等解决率的前提下节省了 54.1% 的成本。\n\n参考来源：Garg et al., HyDRA 论文（arXiv:2605.17106）。')

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
note(s,'把前面这些产品和算法放在一起看，其实可以归纳成三层。\n第一层是普通代码，负责检查企业允许使用哪些模型、数据可以在哪些区域处理、目标模型是否支持工具或结构化输出，以及当前缓存还能不能继续用。这些明确的规则不应该交给模型猜。第二层用一个速度很快的专用模型，在允许的选项里判断哪个更合适。第三层再按判断结果执行：简单任务只用一个模型，难题增加检查，最后由普通代码核对格式和必要字段。\n如果我们在自己的业务系统里也需要这样一个速度快、成本低的判断组件，可以用什么？下一页就是答案。')

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
note(s,'Microsoft-Decision-1.1 就是为这种程序判断准备的。常见的生成式大模型主要擅长写完整回答；即使只让它做一次分类，也会逐字生成解释，额外增加几百毫秒到两秒，而且缺少信息时仍可能给出看似确定的答案。\nDecision-1.1 的做法不同。它基于混合专家架构，每次只激活 4B 参数，通过一次前向计算直接返回各个选项的概率，不生成多余文字；输入既可以是文本和 JSON，也可以是图片。每百万输入 Token 的价格是 0.042 美元，输出 Token 免费，典型响应时间约 123 毫秒。把选项顺序打乱后，结果变化也小于 1.3%，因此程序可以更放心地按阈值处理。')

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
note(s,'它的接口调用方式很简洁，路径是 systemone。调用时把当前业务上下文放在 state 里，针对同一份上下文可以一次提交多个问题，主要包含三种类型：\n第一种是 choice，用于多项选一，比如决定调用哪个模型或分给哪个客服组，它会同时返回每个选项的概率——如果最高概率低于设定的阈值（例如 0.75），程序就可以先停下来让用户补充信息；第二种是 noul，用于是非判断，比如检查回复草稿里有没有提及竞品、退货照片里的包装是否破损，返回一个 0 到 1 的概率；第三种是 score，用于按等级打分，比如评估工单是 P0 到 P3 哪一档紧急程度，返回加权后的分值。这三种问题可以在同一次请求里一起返回。')

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
note(s,'通过这三种基本类型，可以很方便地实现常见的流程控制。比如自己搭一个模型路由，用 choice 设置轻量提取、常规编码、多模型审校和“缺少信息需追问”四个选项，遇到附件缺失或描述不清时先提示用户补充，避免直接调用高成本模型。\n再比如客服工单入口，在一次调用里同时使用 choice 分组和 score 定级：看到用户反馈“床架塌了伤到腰”，紧急度打到 2.94 分，系统就直接跳过机器人回复，转给人工客服跟进。在电商售后场景里，把退货照片放进 assets 做 noul 判断，破损概率超过 0.8 自动换货，介于中间区间的再转人工处理。另外在大模型生成完回复草稿、正式发给用户之前，也可以用几个 noul 检查是否提到竞品或擅自承诺折扣，超过阈值就暂停发送。')

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
note(s,'由于每次推理只激活 4B 参数、价格也很低，大家自然会关心它的准确率够不够高。为了避免在单一测试集上过拟合，评测团队选取了训练集以外的 102 项基准测试（包含 41 项公开测试和 61 项企业场景测试，共 38.5 万道题），对 8 款决策模型做了对比。\n左侧图表展示了测试结果：Decision-1.1 平均准确率为 78.8%，排在综合第一，并在 9 个细分能力维度中拿到了 7 项第一，包括路由分流、工具选择、安全检查和结果一致性；在第三方 Artificial Analysis 决策指数上得分为 68 分，速度提升了 2.2 倍。目前它除了用于微软内部的 Copilot 分流、Cowork 强度调节、Foundry 自动评测和 Xbox 数据分析流程外，也已经有四千多家企业接入使用。\n\n参考来源：Microsoft Command Line — Microsoft-Decision-1.1 GA（2026 年 11 月 17 日，附 Microsoft Decision benchmark report 2026-11-14）。')

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
note(s,'再看一个具体的成本测算案例，场景是每月预算 1 万美元的销售邮件跟进。最初的做法是每收到一封客户回信，都直接调用 0.15 美元一次的大模型起草回复，再为了稳妥起见安排人工逐封审核，每封人工成本 0.24 美元。算下来处理一条线索需要 0.31 美元，平均签下一位客户的获客成本是 13 美元。\n引入 Decision-1.1 后做了三处改动：先在入口用 choice 做邮件分流，在 32 类真实客户回信测试中准确率达到 100%（原本的正则规则是 88%），把 57% 像“谢谢”或“退订”这类简单回信直接用规则处理，不再调用大模型；接着用 score 给高意向客户排优先级；最后在发送前用 noul 检查草稿内容。三项检查加在一起，每封邮件只花 0.00019 美元，但把需要人工审核的比例从 100% 降到了 8%。同样每月 1 万美元预算，转化的客户数量增加到原来的 7.2 倍，获客成本降到了 1.81 美元。\n\n参考来源：Microsoft Command Line 博客（$10k/月销售收件箱架构测算案例）。')

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
note(s,'下面进入第一组演示。它调用本机 GitHub Copilot CLI，一共五步；每一步只发起一条 copilot 命令，模型选择和多模型协作都由服务端完成。\n第一步让 Auto 读取配置文件里的默认端口。这个任务很简单，四项能力需求分都低于 0.1，因此系统直接选择 GPT-6 Luna，一次返回 8787，同时建立当前会话的缓存，消耗 0.055 AIU。\n第二到第四步的命令参数完全相同，都是 Fusion High；我们只改变任务本身。第二步修复字符串首尾空白，系统判断一个模型就够了，所以使用 Single，由 Terra 一次改完并通过 3 项单元测试，没有额外评审。第三步处理两把锁顺序相反造成的死锁，系统改用 Cascade：Sol 先修正加锁顺序，Luna 再检查代码并给出 5 分通过；既然评审通过，就不再调用 Opus 重做，最后 500 次并发测试全部通过。第四步要求设计五万并发的多区域支付网关，系统改用 Critique：Opus 先写初稿，Luna 指出“防止重复写入”并不能保证跨区域数据零丢失，Opus 再补上三区域同步多数派提交方案。\n第五步通过 --resume 在第一步的会话里继续生成监控指标。模型仍是 Luna，5,655 个输入 Token 直接从缓存读取，缓存命中率 99%，本轮只消耗 0.024 AIU。演示时可以随时切到“原始日志”，核对完整 JSONL 和 usage.json。')

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
note(s,'第二组演示使用 Foundry Model Router。四个步骤都调用同一个 /chat/completions 接口，model 始终设为 auto；业务代码不改，只看请求内容变化后，云端会选择什么模型。\n第一步把 developer 角色、temperature 和 JSON 输出格式放在同一个请求里。自己对接多家模型时，这些参数经常因为支持方式不同而报 400；Foundry 会先排除不兼容的模型，再做参数转换，30 毫秒完成路由，最终由 gpt-5.6-luna 返回正确 JSON。\n第二步从发票文本中提取编号和币种。任务很简单，Balanced 模式在 27 毫秒内选择 DeepSeek-V4.1-Flash，推理 Token 为 0。第三步接口和配置都不变，只把任务换成 Rust 无锁队列和内存序推导；轻量模型不再满足要求，系统在 30 毫秒内升级到 gpt-6-luna。紧接着第二轮追问下标回绕问题时，系统识别出这是同一段对话，返回 retain，继续使用原模型和原有缓存。\n第四步把续约分析拆成两个明确阶段：先用 cost 模式，让 grok-4-1-fast 从原始材料里整理关键数字；再把精简后的结果交给 quality 模式，由 gpt-5.6-terra 制定续约报价和谈判方案。这样高价模型只处理真正需要深度分析的部分。切到“原始日志”可以核对每次请求的 routing_trace。')

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
note(s,'第三组演示调用 /v1/systemone，重点不是生成回答，而是让业务代码快速做出可解释的判断。\n第一步把同一条购买咨询连续提交 5 次。五次 noul 结果都是 0.9835，没有波动，中位耗时约 354 毫秒，而且不收输出 Token 费用。\n第二步先给客服收件箱分流。我们准备了四条消息：“谢谢”、“退订 STOP”、“促销规则咨询”和“跨产品质保对比”。系统分别选择无需回复、业务代码、小模型和大模型；前三条都不用调用高成本大模型。\n第三步处理一条受伤投诉。客户说床架坍塌伤到家人，而且已经第三次联系。一次请求同时返回负责团队、紧急程度和是否重复投诉：团队为 safety_support，紧急程度 1.97，重复投诉概率接近 1。业务代码立即停用自动回复并通知人工专员。\n第四步检查待发送草稿。草稿中出现“Fabrikam 有类似沙发，只要 749 美元”，提及竞品的概率为 0.970，超过 0.50 阈值，因此在发送前暂停并转人工审核。\n第五步检查资料是否齐全。用户要求对比合同 A 和附件 B，但当前只上传了合同 A。系统以 0.9999 的概率选择“请用户补充附件”，没有把不完整的材料交给大模型猜测。底部输入框还可以现场输入任意句子；“原始日志”里可以核对完整请求和返回 JSON。')

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
note(s,'最后简单总结四条落地建议：\n第一，不要把所有请求都固定绑在同一个模型上，可以根据子任务的特点分别选择合适的模型；第二，控制成本时要注意前缀缓存，尽量在对话开始或独立子任务时选定模型，避免中途频繁切换；第三，优先利用平台已有的能力，日常办公开启 Copilot Auto，写代码使用 Copilot Fusion，调用云端接口可以直接接入 Foundry Model Router；第四，如果业务代码里需要做请求分流、优先级评估或发送前的内容检查，可以尝试接入低延迟、低成本的 Decision-1.1。今天的内容就分享到这里，谢谢大家，欢迎提问交流。')

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
note(s,'最后一页整理了今天提到的评测报告、产品文档、HyDRA 论文以及 Decision-1.1 的使用指南和开源测试集链接，在 PPT 和网页版里都可以直接点击打开，方便会后查阅。')


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
