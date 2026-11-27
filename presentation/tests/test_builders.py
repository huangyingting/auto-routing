import base64
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Pt

from presentation.src import build_html as H, build_pptx as D


class BuilderTests(unittest.TestCase):
    def test_html_and_pptx_share_card_and_font_styles(self):
        card = {
            'op': 'add_shape',
            'slide': 0,
            'preset': 'rect',
            'x': 100000,
            'y': 100000,
            'cx': 1800000,
            'cy': 900000,
            'fill': D.CARD,
            'line': D.EDGE,
            'lineWidth': 12700,
        }
        title = {
            'op': 'add_text_box',
            'slide': 0,
            'x': 200000,
            'y': 200000,
            'cx': 1500000,
            'cy': 400000,
            'text': '统一风格',
            'sizePt': 24,
            'bold': True,
            'color': D.INK,
            'fontFamily': D.HF,
            'align': 'left',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(D, 'slides', {0: [card, title]}), patch.object(D, 'notes', {0: '备注'}):
                H.build(str(root / 'index.zh.html'), str(root), 1600, lang='zh')
                D.build(str(root / 'deck.zh.pptx'), str(root), lang='zh')
            doc = (root / 'index.zh.html').read_text(encoding='utf-8')
            self.assertIn('border-radius:14px;', doc)
            self.assertIn('&quot;Microsoft YaHei UI&quot;', doc)
            self.assertNotIn('fonts.googleapis.com', doc)
            prs = Presentation(root / 'deck.zh.pptx')
            shape = prs.slides[0].shapes[0]
            self.assertEqual(shape.auto_shape_type, MSO_SHAPE.ROUNDED_RECTANGLE)
            run = prs.slides[0].shapes[1].text_frame.paragraphs[0].runs[0]
            self.assertEqual(run.font.name, 'Microsoft YaHei UI')

    def test_notes_share_content_and_cannot_terminate_the_script(self):
        zh_note = '\u8bb2\u8005\u5907\u6ce8\n</script><script>alert("zh")</script>'
        en_note = 'Speaker note\n</script><script>alert("en")</script>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(D, 'slides', {0: []}), patch.object(D, 'notes', {0: zh_note}), patch.object(D, 'EN_NOTES', {0: en_note}):
                H.build(str(root / 'index.html'), str(root), 1600, lang='en', alt_href='index.zh.html')
                H.build(str(root / 'index.zh.html'), str(root), 1600, lang='zh', alt_href='index.html')
                D.build(str(root / 'deck.pptx'), str(root), lang='en')
                D.build(str(root / 'deck.zh.pptx'), str(root), lang='zh')
            doc_en = (root / 'index.html').read_text(encoding='utf-8')
            doc_zh = (root / 'index.zh.html').read_text(encoding='utf-8')
            self.assertEqual(json.loads(re.search(r'window\.SLIDE_NOTES=(.*?);</script>', doc_en).group(1)), {'0': en_note})
            self.assertEqual(json.loads(re.search(r'window\.SLIDE_NOTES=(.*?);</script>', doc_zh).group(1)), {'0': zh_note})
            self.assertNotIn(en_note, doc_en)
            self.assertNotIn(zh_note, doc_zh)
            self.assertIn('data-base-href="index.zh.html"', doc_en)
            self.assertIn('data-base-href="index.html"', doc_zh)
            self.assertEqual(Presentation(root / 'deck.pptx').slides[0].notes_slide.notes_text_frame.text, en_note)
            self.assertEqual(Presentation(root / 'deck.zh.pptx').slides[0].notes_slide.notes_text_frame.text, zh_note)

    def test_bilingual_slides_and_notes_both_validate_cleanly(self):
        en_slides = D.get_localized_slides('en')
        zh_slides = D.get_localized_slides('zh')
        D.validate_layout(en_slides)
        D.validate_layout(zh_slides)
        self.assertEqual(len(D.get_localized_notes('en')), len(en_slides))
        self.assertEqual(len(D.get_localized_notes('zh')), len(zh_slides))
        for k in en_slides:
            self.assertTrue(any('a' <= ch.lower() <= 'z' for ch in D.get_localized_notes('en')[k]))
            self.assertTrue(any(ord(ch) > 0x4E00 for ch in D.get_localized_notes('zh')[k]))
        zh_text = '\n'.join(
            op.get('text', '') or '\n'.join(p.get('text', '') for p in op.get('paragraphs', []))
            for ops in zh_slides.values()
            for op in ops
            if op.get('op') == 'add_text_box'
        )
        zh_notes = '\n'.join(D.get_localized_notes('zh').values())
        self.assertIn('在对话中途为了省一点费用切到另一个模型', zh_text)
        self.assertIn('在对话中途为了省一点费用切到另一个模型', zh_notes)
        self.assertNotIn('第五轮', zh_text + zh_notes)
        self.assertNotIn('第 5 轮', zh_text + zh_notes)

    def test_slide_seven_chinese_tags_fit_on_one_line(self):
        labels = {'办公场景', '编程协作', '云端接口', '业务判断'}
        operations = [
            op
            for op in D.get_localized_slides('zh')[6]
            if op.get('op') == 'add_shape' and op.get('text') in labels
        ]
        self.assertEqual({op['text'] for op in operations}, labels)
        for op in operations:
            self.assertEqual(
                D.nlines(op['text'], op['sizePt'], op['cx'], op['fontFamily'], op['bold']),
                1,
                op['text'],
            )

    def test_decision_demo_code_stays_between_header_and_command_card(self):
        slide_ops = D.slides[21]
        def op_text(op):
            return op.get('text', '') or '\n'.join(p.get('text', '') for p in op.get('paragraphs', []))

        header = next(op for op in slide_ops if op_text(op).startswith('decision-controller.ts'))
        code = next(op for op in slide_ops if op_text(op).startswith('const photo = { type: "image"'))
        command = next(op for op in slide_ops if op_text(op).startswith('PS> npm --prefix demo run demo:decision:live'))
        self.assertGreaterEqual(code['y'] - (header['y'] + header['cy']), 150000)
        self.assertGreaterEqual(command['y'] - (code['y'] + code['cy']), 300000)

    def test_demo_launchers_only_appear_on_matching_slides(self):
        expected = {
            10: 'fusion',
            12: 'foundry',
            18: 'decision',
            19: 'fusion',
            20: 'foundry',
            21: 'decision',
        }
        self.assertEqual({k: v[0] for k, v in H.DEMO_LAUNCHERS.items()}, expected)
        self.assertEqual({k: v[0] for k, v in H.ZH_DEMO_LAUNCHERS.items()}, expected)
        self.assertEqual(sorted(D.slides), list(range(24)))
        for slide_index in range(24):
            en_markup = H.slide_html(slide_index, [], '.', 1600, lang='en')
            zh_markup = H.slide_html(slide_index, [], '.', 1600, lang='zh')
            should_have_launcher = slide_index in expected
            self.assertEqual('class="live-demo-trigger"' in en_markup, should_have_launcher)
            self.assertEqual('class="live-demo-trigger"' in zh_markup, should_have_launcher)
        deck_text = '\n'.join(
            op.get('text', '') or '\n'.join(p.get('text', '') for p in op.get('paragraphs', []))
            for slide_ops in D.slides.values()
            for op in slide_ops
        )
        self.assertNotIn('Sales agent case', deck_text)
        self.assertNotIn('CAC = $1.81', deck_text)
        self.assertNotIn('three-layer routing stack', deck_text)

    def test_chinese_demo_studio_localizes_controls_and_explanations(self):
        self.assertNotIn('Source', H.ZH_DEMO_TEXT_MAP)
        self.assertNotIn('Error', H.ZH_DEMO_TEXT_MAP)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(D, 'slides', {20: []}), patch.object(D, 'notes', {20: '中文备注'}):
                H.build(str(root / 'index.html'), str(root), 1600, lang='en')
                H.build(str(root / 'index.zh.html'), str(root), 1600, lang='zh')
            doc_en = (root / 'index.html').read_text(encoding='utf-8')
            doc = (root / 'index.zh.html').read_text(encoding='utf-8')
            for en_marker in ('id="studio-ledger"', 'id="btn-view-visual"', 'id="live-visual-stage"', 'CUMULATIVE LEDGER', 'CODE DIFF &amp; REVIEW'):
                self.assertIn(en_marker, doc_en)
            for expected in (
                '演示 1 · 编程 Agent',
                '运行步骤 1',
                '自动播放',
                '✦ 可视化',
                '累计成本与耗时',
                '代码修改与评审',
                '与固定使用大模型相比',
                '所有消息都交给大模型',
                '{ } 原始日志',
                '业务代码只调用一个 /chat/completions 接口',
                '简单任务只用一个模型',
                '4 条客户消息，3 条不需要调用大模型',
                '任务难度不高，使用轻量模型一次完成',
            ):
                self.assertIn(expected, doc)
            for forbidden in (
                'Auto Fast Path: 1-Line Config Lookup',
                'Demo 1 · Coding Agent',
                'Payoff vs. Naive Baseline',
                'All-Frontier Inbox',
                'Reviewing every AI draft manually kills ROI',
                'Fusion 高',
                '条件筛选与跨厂商参数转换',
                '路由选型与多轮缓存保持',
                '原生 Cascade',
                '受伤投诉分流与人工升级',
                '缺少上下文检查',
                'Bounded task complexity',
                'Within 1–2% of #1',
                'Event来源',
                'live来源',
                'new 错误',
            ):
                self.assertNotIn(forbidden, doc)
            for required_runtime_identifier in ('EventSource', 'liveSource', 'new Error'):
                self.assertIn(required_runtime_identifier, doc)
            if shutil.which('node'):
                scripts = re.findall(r'<script>(.*?)</script>', doc, flags=re.S)
                self.assertGreaterEqual(len(scripts), 2)
                for idx, script_body in enumerate(scripts):
                    js_path = root / f'zh_script_{idx}.js'
                    js_path.write_text(script_body, encoding='utf-8')
                    subprocess.run(['node', '--check', str(js_path)], check=True)

    def test_paragraph_spacing_and_links_survive_both_renderers(self):
        with patch.object(D, 'slides', {}):
            D.tb(0, 0, 0, 3000000, paras=[
                {'text': 'Reference', 'href': 'https://example.com/?a=1&b=2', 'spaceAfterPt': 9},
                {'text': 'Explanation'},
            ], space_after=4)
            operation = D.slides[0][0]
            markup = H.text_html(operation)
            self.assertIn('margin-bottom:12.0px;', markup)
            self.assertIn('href="https://example.com/?a=1&amp;b=2"', markup)
            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            frame = slide.shapes.add_textbox(0, 0, Emu(3000000), Emu(2000000)).text_frame
            D.write_text(frame, operation)
            self.assertEqual(frame.paragraphs[0].space_after, Pt(9))
            self.assertEqual(frame.paragraphs[0].runs[0].hyperlink.address, 'https://example.com/?a=1&b=2')
            D.tb(1, 0, 0, 3000000, paras=[{'text': 'Reference', 'href': 'https://example.com'}])
            self.assertIn('href="https://example.com"', H.text_html(D.slides[1][0]))

    def test_multiline_code_preserves_indentation(self):
        code = '{\n  "nested": {\n    "enabled": true\n  }\n}'
        with patch.object(D, 'slides', {}):
            D.tb(0, 0, 0, 3000000, code, font=D.MF)
            operation = D.slides[0][0]
            markup = H.text_html(operation)
            self.assertIn('white-space:pre-wrap;', markup)
            self.assertIn('    &quot;enabled&quot;: true', markup)
            presentation = Presentation()
            slide = presentation.slides.add_slide(presentation.slide_layouts[6])
            frame = slide.shapes.add_textbox(0, 0, Emu(3000000), Emu(2000000)).text_frame
            D.write_text(frame, operation)
            self.assertEqual(frame.text.replace('\v', '\n'), code)

    def test_image_cache_respects_requested_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'wide.png'
            Image.new('RGB', (400, 200)).save(path)
            cache = {}
            for maxw in (100, 200):
                uri = H.data_uri(str(path), maxw, cache)
                image = Image.open(io.BytesIO(base64.b64decode(uri.split(',', 1)[1])))
                self.assertEqual(image.size, (maxw, maxw // 2))

    def test_svg_remains_vector_in_html_and_is_contained_in_pptx(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"/>'
            (root / 'wide.svg').write_bytes(svg)
            Image.new('RGB', (400, 200)).save(root / 'wide.png')
            uri = H.data_uri(str(root / 'wide.svg'), 1600, {})
            self.assertEqual(base64.b64decode(uri.split(',', 1)[1]), svg)
            with patch.object(D, 'slides', {}):
                D.img(0, 'wide.svg', 0, 0, 2000000, 2000000, 'Chart', fit='contain')
                operation = D.slides[0][0]
                self.assertIn('contain-img', H.slide_html(0, [operation], str(root), 1600))
                presentation = Presentation()
                slide = presentation.slides.add_slide(presentation.slide_layouts[6])
                D.add_picture(slide, operation, str(root))
                picture = slide.shapes[0]
                self.assertEqual((picture.left, picture.top, picture.width, picture.height), (0, 500000, 2000000, 1000000))
                self.assertEqual((picture.crop_top, picture.crop_bottom), (0, 0))

    def test_layout_rejects_overlap_and_out_of_bounds(self):
        with patch.object(D, 'slides', {}):
            D.tb(0, 0, 0, 3000000, 'First', cy=500000)
            D.tb(0, 0, 200000, 3000000, 'Second', cy=500000)
            with self.assertRaisesRegex(ValueError, 'textbox overlap'):
                D.validate_layout()
        with patch.object(D, 'slides', {}):
            D.rect(0, D.W - 100000, 0, 200000, 500000)
            with self.assertRaisesRegex(ValueError, 'invalid bounds'):
                D.validate_layout()

    def test_cover_omits_duration_footer_and_renders_pages_qr_code(self):
        cover_texts = [op.get('text', '') for op in D.slides[0] if op['op'] == 'add_text_box']
        self.assertFalse(any('November 2026' in t or '45 minutes' in t for t in cover_texts))
        self.assertIn('Yingting Huang - Microsoft', cover_texts)
        self.assertTrue(all(op.get('name') != 'footer_src' for ops in D.slides.values() for op in ops))
        zh_slides = D.get_localized_slides('zh')
        zh_text = '\n'.join(
            op.get('text', '') or '\n'.join(p.get('text', '') for p in op.get('paragraphs', []))
            for slide_ops in zh_slides.values()
            for op in slide_ops
        )
        zh_notes = '\n'.join(D.get_localized_notes('zh').values())
        self.assertIn('内容安排', zh_text)
        self.assertIn('自动路由在微软产品中的实现', zh_text + zh_notes)
        self.assertNotIn('今天主要讲七件事', zh_text + zh_notes)
        self.assertNotIn('微软产品方案', zh_text + zh_notes)
        for slide_idx, ops in D.slides.items():
            nums = [op for op in ops if op.get('name') == 'footer_num']
            self.assertEqual(len(nums), 1, f'Slide {slide_idx + 1} missing footer_num')
            self.assertEqual((nums[0]['x'], nums[0]['y']), (D.W - 940000, D.H - 430000))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            url = 'https://huangyingting.github.io/auto-routing/'
            with patch.object(D, 'slides', {0: [], 1: []}), patch.object(D, 'notes', {}):
                H.build(str(root / 'index.html'), str(root), 1600, pages_url=url)
                D.build(str(root / 'deck.pptx'), str(root), pages_url=url)
            doc = (root / 'index.html').read_text(encoding='utf-8')
            self.assertEqual(doc.count('class="a pages-qr-card"'), 1)
            self.assertIn('href="https://huangyingting.github.io/auto-routing/"', doc)
            self.assertIn('huangyingting.github.io/auto-routing', doc)
            self.assertIn('<svg class="pages-qr-svg"', doc)
            self.assertIn('.pages-qr-svg{width:176px;height:176px;', doc)
            prs = Presentation(str(root / 'deck.pptx'))
            self.assertGreaterEqual(len(prs.slides[0].shapes), 5)

    def test_public_pages_build_omits_notes_studio_hud_but_keeps_demo_buttons(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            url = 'https://huangyingting.github.io/auto-routing/'
            with patch.object(D, 'slides', {0: [], 20: []}), patch.object(D, 'notes', {0: 'secret note'}), patch.object(D, 'EN_NOTES', {0: 'secret note'}):
                H.build(str(root / 'local.html'), str(root), 1600, pages_url=url, presenter_tools=True)
                H.build(str(root / 'pages.html'), str(root), 1600, pages_url=url, presenter_tools=False)
            local_doc = (root / 'local.html').read_text(encoding='utf-8')
            pages_doc = (root / 'pages.html').read_text(encoding='utf-8')
            for marker in ('id="deck-hud"', 'id="hud-notes-btn"', 'id="hud-demo-btn"', 'id="notes-drawer"', 'window.SLIDE_NOTES', 'secret note', 'toggleNotes'):
                self.assertIn(marker, local_doc)
                self.assertNotIn(marker, pages_doc)
            for kept in ('class="live-demo-trigger"', 'id="live-demo"', 'window.RECORDED_DEMO'):
                self.assertIn(kept, local_doc)
                self.assertIn(kept, pages_doc)
            self.assertIn('isLocalOrigin', local_doc)

    def test_recorded_demos_have_only_real_cloud_and_cli_steps(self):
        rec_path = Path(__file__).resolve().parents[1] / 'assets' / 'demo-recordings.json'
        rec = json.loads(rec_path.read_text(encoding='utf-8'))
        self.assertEqual(sorted(rec['steps']['fusion'].keys()), ['1', '2', '3', '4'])
        self.assertEqual(sorted(rec['steps']['foundry'].keys()), ['1', '2', '3', '4'])
        self.assertEqual(sorted(rec['steps']['decision'].keys()), ['1', '2', '3', '4'])
        self.assertEqual(
            {demo: len(steps) for demo, steps in rec['steps'].items()},
            D.DEMO_STEP_COUNTS,
        )
        self.assertNotIn('Local HTTP Failover Harness', json.dumps(rec))
        self.assertNotIn('5x consistency probe', json.dumps(rec))
        self.assertNotIn('Five live /providers/microsoft/v1/systemone', json.dumps(rec))
        self.assertNotIn('5× Live Repeat Probe', H.STUDIO_JS)

        raw_by_demo = {}
        for demo in ('fusion', 'foundry', 'decision'):
            raw_by_demo[demo] = [
                item['event']['text']
                for step_items in rec['steps'][demo].values()
                for item in step_items
                if item['event']['kind'] == 'raw'
            ]
        self.assertEqual(len(raw_by_demo['fusion']), D.DEMO_CALL_COUNTS['fusion'])
        self.assertTrue(all('Single native' in text for text in raw_by_demo['fusion']))
        self.assertEqual(
            sum(item['event']['kind'] == 'raw' for item in rec['steps']['fusion']['4']),
            2,
        )
        self.assertTrue(
            any(
                item['event']['kind'] == 'output'
                and item['event']['text'].startswith('[SETUP] Real warm-up call')
                for item in rec['steps']['fusion']['4']
            )
        )
        self.assertEqual(
            '\n'.join(raw_by_demo['foundry']).count('# HTTP 200 Response JSON'),
            D.DEMO_CALL_COUNTS['foundry'],
        )
        self.assertEqual(
            '\n'.join(raw_by_demo['decision']).count('# HTTP 200 Response JSON'),
            D.DEMO_CALL_COUNTS['decision'],
        )
        image_raw = '\n'.join(
            item['event']['text']
            for item in rec['steps']['decision']['4']
            if item['event']['kind'] == 'raw'
        )
        self.assertIn('image:cargo-damage.jpg', image_raw)
        self.assertIn('<base64 omitted:', image_raw)
        self.assertNotIn('"data_base64": "/9j/', image_raw)
        self.assertTrue(
            any(
                item['event']['kind'] == 'artifact'
                and item['event'].get('imageName') == 'cargo-damage.jpg'
                for item in rec['steps']['decision']['4']
            )
        )

        def visible_text(slide_ops):
            return '\n'.join(
                op.get('text', '') or '\n'.join(p.get('text', '') for p in op.get('paragraphs', []))
                for op in slide_ops
                if op.get('op') in {'add_text_box', 'add_shape'}
            )

        zh_slides = D.get_localized_slides('zh')
        self.assertIn('4 个场景 · 5 次真实 CLI 调用', visible_text(zh_slides[19]))
        self.assertIn('4 个场景 · 6 次真实 Foundry 请求', visible_text(zh_slides[20]))
        self.assertIn('4 个场景 · 7 次真实 /v1/systemone 请求', visible_text(zh_slides[21]))

        foundry_slide = visible_text(zh_slides[20])
        for step in range(1, 5):
            self.assertIn(f'场景 {step} ·', foundry_slide)
        self.assertNotIn('步骤 2–3', foundry_slide)

        decision_slide = visible_text(zh_slides[21])
        for step in range(1, 5):
            self.assertIn(f'场景 {step} ·', decision_slide)
        self.assertNotIn('场景 5 ·', decision_slide)
        self.assertNotIn('步骤 1–2', decision_slide)
        self.assertNotIn('步骤 4–5', decision_slide)

        natural_copy = '\n'.join(visible_text(zh_slides[index]) for index in (19, 20, 21))
        for expected in (
            '常规修改，一个模型就够了',
            '只提取两个字段，用 Flash 就够了',
            '只把难题交给大模型',
            '检查运输中的货物破损',
        ):
            self.assertIn(expected, natural_copy)
        for forbidden in (
            '简单提取直接使用 Flash',
            'Rust 任务变难后自动升级，追问继续沿用',
            '一次请求同时返回负责团队、紧急程度和重复投诉',
            '请求补充附件 0.99994',
        ):
            self.assertNotIn(forbidden, natural_copy)

    @unittest.skipUnless(shutil.which('node'), 'node is required to syntax-check embedded JS')
    def test_embedded_javascript_has_valid_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            for name, src in (('deck_only.js', H.DECK_JS), ('public.js', H.PUBLIC_JS), ('deck.js', H.JS)):
                js_path = Path(directory) / name
                js_path.write_text(src, encoding='utf-8')
                subprocess.run(['node', '--check', str(js_path)], check=True)

    def test_raw_log_is_scoped_to_current_step_or_probe(self):
        self.assertIn("}else if(data.kind==='step-start'){\n  stepRunning=true;", H.STUDIO_JS)
        self.assertIn("curKind=data.demo;curStep=Number(data.step);", H.STUDIO_JS)
        self.assertIn("currentExecutionMode=data.executionMode", H.STUDIO_JS)
        self.assertIn("currentExecutionMode=data.executionMode||(replayMode?'replay':'live');\n  rawLog='';", H.STUDIO_JS)
        self.assertIn("function runCustomProbe(cmd){\n if(!cmd||stepRunning)return;\n stopAutoPlay();\n rawLog='';", H.STUDIO_JS)
        self.assertIn("setupCustomSelect('cs-step',function(val){", H.STUDIO_JS)
        self.assertIn("activeProbeVisual=null;\n rawLog='';\n renderVisualStep", H.STUDIO_JS)
        self.assertIn("var rawParts=[];", H.STUDIO_JS)
        self.assertIn("rawParts.join('\\n\\n')", H.STUDIO_JS)

    def test_execution_status_preserves_live_or_replay_mode(self):
        server_source = (
            Path(__file__).resolve().parents[2] / 'demo' / 'src' / 'web-demo-server.mjs'
        ).read_text(encoding='utf-8')
        self.assertIn('executionMode: "live"', server_source)
        self.assertIn('executionMode: "replay"', server_source)
        self.assertIn("currentExecutionMode=data.executionMode", H.STUDIO_JS)
        self.assertIn("'Live · Running Step '", H.STUDIO_JS)
        self.assertIn("'Replay · Running Step '", H.STUDIO_JS)
        self.assertIn("'Live · Step '", H.STUDIO_JS)
        self.assertIn("'Replay · Step '", H.STUDIO_JS)
        self.assertIn("currentExecutionMode==='live'", H.STUDIO_JS)
        self.assertIn("'Live Backend · Running Step '", H.STUDIO_JS)
        self.assertIn("'Recorded Replay · Running Step '", H.STUDIO_JS)

    def test_fusion_studio_has_four_distinct_scenarios(self):
        self.assertNotIn('Auto Fast Path: 1-Line Config Lookup', H.STUDIO_JS)
        self.assertIn('Copilot Fusion &amp; Cache · 4 scenarios / 5 calls', H.LIVE_DEMO)
        for title in (
            'Fusion High: Picks pattern="single" on Routine Patch',
            'Fusion High: Native pattern="cascade" (Solver + Judge)',
            'Fusion High: Native pattern="critique" (Draft → Critic → Revise)',
            'Prefix-Cache Guard: 99% Cache Hit via --resume',
        ):
            self.assertIn(title, H.STUDIO_JS)

    def test_decision_studio_has_real_image_scenario(self):
        self.assertIn('Microsoft-Decision-1.1 · 4 scenarios / 7 calls', H.LIVE_DEMO)
        self.assertIn('Check 4 (image + noul): Live Cargo Damage Inspection', H.STUDIO_JS)
        self.assertIn('image:cargo-damage.jpg', H.STUDIO_JS)
        self.assertIn('vs-image-preview', H.STUDIO_JS)
        cargo_path = Path(__file__).resolve().parents[1] / 'assets' / 'images' / 'cargo-damage.jpg'
        self.assertTrue(cargo_path.is_file())
        with Image.open(cargo_path) as cargo_image:
            self.assertEqual(cargo_image.size, (960, 720))
        asset_readme = (cargo_path.parent.parent / 'README.md').read_text(encoding='utf-8')
        self.assertIn('Astrid Groeneveld', asset_readme)
        self.assertIn('CC BY-SA 3.0', asset_readme)
        self.assertIn('https://commons.wikimedia.org/wiki/File:Cargo_damage.JPG', asset_readme)
        runner_source = (
            Path(__file__).resolve().parents[2] / 'demo' / 'src' / 'live-runners.mjs'
        ).read_text(encoding='utf-8')
        for expected in (
            'data_base64: imageBytes.toString("base64")',
            'type: "image"',
            'format: "jpeg"',
            'cargo_damage_visible',
            '<base64 omitted:',
        ):
            self.assertIn(expected, runner_source)
        self.assertNotIn('request_missing_exhibit', runner_source)
        self.assertNotIn('Missing Document Caught', H.STUDIO_JS)

    def test_foundry_step_three_requests_match_visual_and_summary(self):
        turn1 = (
            'Design a lock-free MPMC ring buffer in Rust and state the exact '
            'Acquire/Release memory-ordering and ABA epoch-reclamation invariants '
            'in 5 concise lines.'
        )
        turn2 = 'Now add 1 sentence on how wrap-around index overflow is prevented.'
        runner_source = (
            Path(__file__).resolve().parents[2] / 'demo' / 'src' / 'live-runners.mjs'
        ).read_text(encoding='utf-8')
        recordings = json.loads(
            (Path(__file__).resolve().parents[1] / 'assets' / 'demo-recordings.json')
            .read_text(encoding='utf-8')
        )
        replay_output = '\n'.join(
            item['event'].get('text', '')
            for item in recordings['steps']['foundry']['3']
            if item['event']['kind'] == 'output'
        )
        replay_raw = next(
            item['event']['text']
            for item in recordings['steps']['foundry']['3']
            if item['event']['kind'] == 'raw'
        )

        for expected in (turn1, turn2):
            self.assertIn(expected, runner_source)
            self.assertIn(expected, H.STUDIO_JS)
            self.assertIn(expected, replay_output)
            self.assertIn(expected, replay_raw)
        self.assertIn(
            'Turn 1 asks for a five-line Rust MPMC design',
            H.STUDIO_JS,
        )
        self.assertNotIn('Add a 3-bullet check', H.STUDIO_JS)
        self.assertNotIn('head - tail == capacity', H.STUDIO_JS)


if __name__ == '__main__':
    unittest.main()
