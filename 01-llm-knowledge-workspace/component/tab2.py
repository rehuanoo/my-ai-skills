# -*- coding: utf-8 -*-
"""
Tab 2：论文生成
==============
三步交互流程（使用商汤 SenseNova 付费模型，复用 tab1 中的 llm 配置）：
    ① 输入论文标题 → 调用付费 API 生成论文大纲，每个标题带索引编号（1.、2.、3.…）
    ② 输入想生成的章节索引（如 1,3,5）→ 逐章调用付费 API 生成，
       已生成章节按索引顺序累加到论文预览区，可分多次把整篇论文写完。
    ③ 阅读文献：从 07-langchain-rag/arxiv_papers 选一篇 PDF，付费模型自动阅读
       并提取论点（核心论点/支撑论据/局限），作为章节写作的参考。
    ④ 自动文献研究（三步）：
       ④-1 论文题目 → 付费模型提取 3~5 个英文关键词（可手动修改）
       ④-2 关键词 → arXiv 检索并下载文献到 arxiv_papers/lit_题目/（目标 ≥5 篇）
       ④-3 付费模型通读全部文献提取论点，逐条按论文题目判断相关性，
            无关论点舍弃，最终给出可引用论点清单（要求可引用文献 ≥5 篇）

大纲与已生成章节保存在模块级 _STATE 中（本地单用户应用，重启服务后清空）。
后续扩展（如导出 Word/保存文件）只需在 generate_sections 末尾追加。
"""

import os
import re
import time

import arxiv
import gradio as gr
import requests

from component.tab1 import llm   # 复用商汤 SenseNova 付费模型

# 检索/PDF 直连共用的请求头（OpenAlex 建议带 mailto 走礼貌池）
_HTTP_HDR = {'User-Agent': 'Mozilla/5.0 (research-course-demo; mailto:course-demo@example.com)'}

# ============================================================
# 会话状态：最近一次生成的大纲与已生成章节
# ============================================================
_STATE = {
    'title': None,           # 论文标题（① 大纲所属）
    'sections': {},          # {索引 int: 章节标题 str}
    'generated': {},         # {索引 int: 已生成的本章 Markdown}
    'research_title': None,  # ④ 研究题目（关键词提取与论点筛选依据）
    'lit_folder': None,      # ④ 本轮文献下载目录
    'lit_papers': [],        # ④ [(arxiv_id, 文献标题, 本地路径)]
}

OUTLINE_PROMPT = '''你是论文写作助手。请为论文《{title}》拟定一份中文学术论文大纲。

要求：
1. 只输出大纲本身，不要任何解释、寒暄，也不要用代码块包裹。
2. 共 8~10 个一级章节，每行一个，格式严格为"数字. 标题"，例如：1. 引言
3. 章节顺序符合学术论文惯例（引言→相关工作→方法→实验→结论等），标题要紧扣论文主题。
4. 不要输出二级标题或要点列表。
'''

SECTION_PROMPT = '''你是论文写作助手。论文题目：《{title}》。
整篇论文的大纲如下：
{outline}

请只撰写其中第 {idx} 章「{section}」的内容。

要求：
1. 直接输出 Markdown 正文，以"## {idx}. {section}"作为本章开头标题。
2. 正文 500~800 字，学术风格，逻辑连贯，可适当使用列表；不要撰写其他章节。
3. 不要寒暄、不要重复大纲、不要用代码块包裹全文。
'''

# 按钮③：待阅读文献所在目录（上一阶段下载的 5 篇 arXiv 论文 PDF）
PAPERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'sample_docs', 'papers')   # 放你自己的论文 PDF

POINT_PROMPT = '''你是论文阅读助手。请仔细阅读以下论文文本（可能因篇幅被截断），为学生提取论点。

论文标题：{title}
论文正文：
{text}

要求：直接输出 Markdown，不要寒暄、不要复述原文，包含以下三部分：
## 核心论点
提炼 1~3 条最主要的论点，每条一句话，标注序号。
## 支撑论据
2~4 条：说明论文用什么方法/数据/实验结果支撑上述论点，每条一两句话。
## 局限与讨论
1~2 条：论文自己承认或明显可见的局限性、未来研究方向。
'''

# ④-1：从论文题目提取 arXiv 检索关键词
KEYWORDS_PROMPT = '''你是学术检索助手。论文题目：《{title}》。
请提炼 3~5 个适合在 arXiv（英文文献库）检索的英文关键词。

要求：只输出关键词本身，用英文逗号分隔；不要编号、不要解释、不要输出其他任何文字。
'''

# ④-3：通读单篇文献，提取论点并按我们的论文题目筛选
READ_FILTER_PROMPT = '''你是论文研究助手。我们正在撰写论文《{our_title}》，现在阅读参考文献《{ref_title}》。

文献正文（可能因篇幅截断）：
{text}

任务：从该文献中提取论点（核心观点/研究发现/结论），并逐条判断该论点是否与
论文《{our_title}》的写作主题相关：相关则保留，无关则舍弃。

直接输出 Markdown，格式如下（不要寒暄、不要复述文献内容、每条论点单独一行）：
## 保留论点
- 论点内容（每条一两句话）
## 舍弃论点
- 论点内容（原因：与论文主题《{our_title}》无关）

若没有可保留的论点，"保留论点"下方写"无"；若全部相关，"舍弃论点"下方写"无"。
'''


# ============================================================
# 付费模型调用（失败/响应过短自动重试）
# ============================================================
def _invoke_with_retry(prompt, min_len=100, attempts=3):
    '''调用付费模型；返回正文文本，全部失败返回 None'''
    for attempt in range(attempts):
        try:
            resp = llm.invoke([{'role': 'user', 'content': prompt}])
            text = resp.content.strip()
            if len(text) >= min_len:
                return text
            print(f'[论文生成] 第{attempt+1}次响应过短({len(text)}字)，重试')
        except Exception as e:
            print(f'[论文生成] 第{attempt+1}次调用失败: {type(e).__name__}: {e}')
        time.sleep(2)
    return None


def _render_paper():
    '''把已生成章节按索引顺序拼成完整论文 Markdown'''
    if not _STATE['generated']:
        return '> 📄 生成的论文将显示在这里……（先 ① 生成大纲，再 ② 按索引生成章节）'
    parts = [f'# {_STATE["title"]}\n']
    for idx in sorted(_STATE['generated']):
        parts.append(_STATE['generated'][idx])
    return '\n\n'.join(parts)


# ============================================================
# 按钮①：根据标题生成大纲（每个标题带索引编号）
# ============================================================
def generate_outline(title):
    title = (title or '').strip()
    if not title:
        return '⚠️ 请先在上方输入论文标题', '⚠️ 请先输入论文标题'

    outline_text = _invoke_with_retry(OUTLINE_PROMPT.format(title=title), min_len=40)
    if outline_text is None:
        return ('⚠️ 大纲生成失败：付费 API 多次调用未成功，请检查网络后重试',
                '❌ 大纲生成失败')

    # 解析"数字. 标题"格式的行 → {索引: 章节标题}（兼容 **加粗** 与 、)．等分隔符）
    sections = {}
    for ln in outline_text.splitlines():
        m = re.match(r'\s*\*{0,2}(\d+)[.、)．]\s*(.+?)\*{0,2}\s*$', ln.strip())
        if m:
            sections[int(m.group(1))] = m.group(2).strip().strip('*').strip()

    if len(sections) < 3:
        # 模型没按约定输出编号大纲：展示原文并提示重新生成
        _STATE.update(title=None, sections={}, generated={})
        return (outline_text, '⚠️ 大纲未按"数字. 标题"格式返回，请点击①重新生成')

    _STATE['title'] = title
    _STATE['sections'] = sections
    _STATE['generated'] = {}   # 换了新大纲，清空旧章节

    lines = [f'{i}. {sections[i]}' for i in sorted(sections)]
    display = (
        f'**《{title}》论文大纲**（共 {len(sections)} 章，每个标题带索引编号）：\n\n'
        + '\n'.join(lines)
        + '\n\n👇 在下方输入索引（如 `1,3,5`）并点击 ②，即可只生成选中的章节。'
    )
    status = f'✅ 已生成大纲（{len(sections)} 章）。请输入章节索引并点击②生成所选章节'
    return display, status


# ============================================================
# 按钮②：按索引生成所选章节，累加进论文预览
# ============================================================
def generate_sections(indices_text):
    if not _STATE['title'] or not _STATE['sections']:
        return _render_paper(), '⚠️ 请先输入论文标题并点击①生成大纲'

    # 从"1,3,5"这类输入中提取有效索引
    picked = []
    for n in re.findall(r'\d+', indices_text or ''):
        n = int(n)
        if n in _STATE['sections'] and n not in picked:
            picked.append(n)
    if not picked:
        valid = '、'.join(str(i) for i in sorted(_STATE['sections']))
        return (_render_paper(),
                f'⚠️ 未识别到有效索引，请输入大纲中的编号（可选：{valid}）')

    outline_lines = '\n'.join(f'{i}. {_STATE["sections"][i]}'
                              for i in sorted(_STATE['sections']))

    ok, fail = [], []
    for idx in picked:
        prompt = SECTION_PROMPT.format(
            title=_STATE['title'], outline=outline_lines,
            idx=idx, section=_STATE['sections'][idx])
        body = _invoke_with_retry(prompt, min_len=150)
        if body is None:
            fail.append(str(idx))
            continue
        # 去掉模型偶尔重复输出的一级标题（# 开头行，二级标题 ## 保留）
        body = '\n'.join(ln for ln in body.splitlines()
                         if not ln.lstrip().startswith('# ')).strip()
        # 保证本章以标准二级标题开头
        header = f'## {idx}. {_STATE["sections"][idx]}'
        if not body.startswith('##'):
            body = header + '\n\n' + body
        _STATE['generated'][idx] = body
        ok.append(f'第{idx}章「{_STATE["sections"][idx]}」')

    paper = _render_paper()
    if ok and not fail:
        status = (f'🎉 已生成 {"、".join(ok)}；论文累计 '
                  f'{len(_STATE["generated"])}/{len(_STATE["sections"])} 章，'
                  f'可继续输入其他索引生成剩余章节')
    elif ok:
        status = (f'⚠️ {"、".join(ok)} 已生成；第 {"、".join(fail)} 章生成失败，'
                  f'可单独输入该索引重试')
    else:
        status = '❌ 所选章节全部生成失败：付费 API 多次调用未成功，请检查网络后重试'
    return paper, status


# ============================================================
# 按钮③：阅读文献（PDF）并提取论点
# ============================================================
def _pdf_text(path, max_chars=12000):
    '''用 pypdf 提取 PDF 文本，凑够 max_chars 即停（长文截断省 token）'''
    from pypdf import PdfReader
    reader = PdfReader(path)
    parts, total = [], 0
    for page in reader.pages:
        t = page.extract_text() or ''
        parts.append(t)
        total += len(t)
        if total >= max_chars:
            break
    return ' '.join(' '.join(parts).split())


def list_papers():
    '''列出 arxiv_papers 目录下全部 PDF 文件名（供下拉框选择）'''
    if not os.path.isdir(PAPERS_DIR):
        return []
    return sorted(f for f in os.listdir(PAPERS_DIR) if f.lower().endswith('.pdf'))


def extract_points(pdf_name):
    '''按钮③：付费模型阅读选定 PDF，提取核心论点/支撑论据/局限'''
    if not pdf_name:
        return '⚠️ 请先选择一篇论文 PDF', '⚠️ 请先选择论文 PDF'
    path = os.path.join(PAPERS_DIR, pdf_name)
    title = re.sub(r'^\d+_', '', os.path.splitext(pdf_name)[0]).replace('-', ' ')

    # 1) 提取 PDF 文本（扫描件会提取不到足够文字）
    try:
        text = _pdf_text(path)
    except Exception as e:
        return (f'⚠️ PDF 文本提取失败：{type(e).__name__}: {str(e)[:80]}',
                f'❌ 无法读取「{pdf_name}」')
    if len(text) < 200:
        return ('⚠️ 该 PDF 提取到的文本过少（可能是扫描/图片版论文），无法阅读',
                '⚠️ 文本提取量不足')
    fed = text[:10000]   # 控制输入长度，适配付费模型上下文窗口

    # 2) 调付费模型提取论点（失败自动重试）
    body = _invoke_with_retry(POINT_PROMPT.format(title=title, text=fed), min_len=80)
    if body is None:
        return ('❌ 论点提取失败：付费 API 多次调用未成功，请检查网络或 Key 后重试',
                '❌ 论点提取失败')
    status = (f'✅ 已阅读「{title[:36]}…」（正文前 {len(fed)} 字），'
              f'论点提取完成，可作为 ② 生成章节时的写作参考')
    return body, status


# ============================================================
# 按钮④-1：论文题目 → 付费模型提取 arXiv 检索关键词
# ============================================================
def _parse_keywords(text):
    '''把模型输出解析成关键词列表（去编号/符号，最多 5 个，去重）'''
    kws, seen = [], set()
    for tok in re.split(r'[,，;；、\n]+', (text or '').strip()):
        tok = re.sub(r'^\s*\d+[.、)]\s*', '', tok.strip()).strip('`* .')
        if tok and 1 < len(tok) <= 60 and tok.lower() not in seen:
            seen.add(tok.lower())
            kws.append(tok)
    return kws[:5]


def extract_keywords(research_title):
    '''按钮④-1：付费模型从论文题目提取 3~5 个英文检索关键词'''
    title = (research_title or '').strip() or (_STATE['title'] or '')
    if not title:
        return '', '⚠️ 请先输入论文题目（可与①相同），或先执行①生成大纲'
    _STATE['research_title'] = title

    out = _invoke_with_retry(KEYWORDS_PROMPT.format(title=title), min_len=5)
    if out is None:
        return '', '❌ 关键词提取失败：付费 API 多次调用未成功，请检查网络后重试'
    kws = _parse_keywords(out)
    if not kws:
        return out, '⚠️ 模型输出未能解析出关键词，请在下方手动填写英文关键词'
    return (', '.join(kws),
            f'✅ 已从题目提取 {len(kws)} 个关键词。可手动修改后点击④-2下载文献')


# ============================================================
# 按钮④-2：关键词 → arXiv 检索并下载文献（目标 ≥5 篇）
# ============================================================
def _safe_name(s):
    '''去掉 Windows 文件名非法字符并截断（防长标题撑坏组件/路径）'''
    return re.sub(r'[\\/:*?"<>|]+', '', (s or '')).strip()[:60]


def _render_lit():
    '''渲染已下载文献清单（Markdown，长标题自动换行不撑坏布局）'''
    papers = _STATE['lit_papers']
    if not papers:
        return '> 🗂️ 下载的文献清单将显示在这里……（先④-1提取关键词，再④-2下载）'
    lines = [f'**本轮已下载 {len(papers)} 篇**（目录：`{_STATE["lit_folder"]}`）：\n']
    for i, (aid, title, path) in enumerate(papers, 1):
        size_kb = os.path.getsize(path) / 1024
        lines.append(f'{i}. {title[:70]}（`{aid}`，{size_kb:.0f} KB）')
    return '\n'.join(lines)


def _http_get(url, params=None, timeout=60, attempts=3, gap=20):
    '''带长间隔重试的 GET（应对限流与网络抖动）；全部失败返回 None'''
    last = None
    for k in range(attempts):
        if k:
            time.sleep(gap)
        try:
            r = requests.get(url, params=params, headers=_HTTP_HDR, timeout=timeout)
            if r.status_code == 200:
                return r
            last = f'HTTP {r.status_code}'
        except Exception as e:
            last = f'{type(e).__name__}: {str(e)[:60]}'
        print(f'[文献检索] 第{k+1}次请求: {last}')
    return None


def _aid_key(aid):
    '''arXiv 编号去版本号（2401.12345v1 → 2401.12345），用于去重'''
    return re.sub(r'v\d+$', '', aid)


def download_literature(keywords_text):
    '''按钮④-2：按关键词检索并下载文献（目标 ≥5 篇，最多 6 篇）
    双通道：arXiv 官方 API →（限流时）OpenAlex 检索 + arXiv PDF 直连'''
    kws = _parse_keywords(keywords_text)
    if not kws:
        return _render_lit(), '⚠️ 请先执行④-1提取关键词，或在关键词框手动填写英文关键词'

    our_title = _STATE.get('research_title') or '文献'
    folder = os.path.join(PAPERS_DIR, 'lit_' + _safe_name(our_title)[:24])
    os.makedirs(folder, exist_ok=True)

    papers, failed = [], 0
    channel = 'arXiv 官方接口'

    # ---- 通道 1：arXiv 官方 API ----
    try:
        query = ' OR '.join(f'all:"{k}"' for k in kws)
        search = arxiv.Search(query=query, max_results=7,
                              sort_by=arxiv.SortCriterion.Relevance)
        client = arxiv.Client(page_size=7, delay_seconds=4, num_retries=4)
        for cand in client.results(search):
            if len(papers) >= 6:
                break
            try:
                fn = f'{len(papers) + 1}_{_safe_name(cand.title)[:50]}.pdf'
                path = cand.download_pdf(dirpath=folder, filename=fn)
                papers.append((cand.get_short_id(), ' '.join(cand.title.split()), path))
                print(f'[文献下载|arXiv] ✅ {cand.title[:44]}')
            except Exception as e:
                failed += 1
                print(f'[文献下载|arXiv] ⚠️ 单篇失败: {type(e).__name__}: {str(e)[:60]}')
            time.sleep(2)
    except Exception as e:
        print(f'[文献下载|arXiv] 检索失败: {type(e).__name__}: {str(e)[:70]}')

    # ---- 通道 2：OpenAlex 元数据检索 + arXiv PDF 直连（篇数不足 5 时启用） ----
    if len(papers) < 5:
        print('[文献下载] arXiv 接口限流或篇数不足，切换 OpenAlex 备用通道…')
        channel = 'OpenAlex 备用通道'
        have = {_aid_key(p[0]) for p in papers}
        r = _http_get('https://api.openalex.org/works',
                      params={'search': ' '.join(kws),
                              'filter': 'locations.source.id:S4306400194',  # arXiv 来源
                              'per-page': 12, 'select': 'title,locations'})
        if r is None:
            return (_render_lit(),
                    '❌ arXiv 官方接口被限流，OpenAlex 备用通道也不可用。'
                    '请稍后重试或更换 VPN 节点。')
        cands = []
        for w in r.json().get('results', []):
            title = ' '.join((w.get('title') or '').split())
            for loc in w.get('locations', []):
                m = re.match(r'https?://arxiv\.org/abs/(.+?)(?:[?#].*)?$',
                             loc.get('landing_page_url') or '')
                if m and _aid_key(m.group(1)) not in have:
                    have.add(_aid_key(m.group(1)))
                    cands.append((m.group(1), title))
                    break
        for aid, title in cands:
            if len(papers) >= 6:
                break
            dest = os.path.join(folder, f'{len(papers) + 1}_{_safe_name(title)[:50]}.pdf')
            got = False
            for base in ('https://arxiv.org/pdf/', 'https://export.arxiv.org/pdf/'):
                pr = _http_get(base + aid, timeout=120, attempts=2, gap=15)
                if pr is not None and 'pdf' in pr.headers.get('content-type', ''):
                    with open(dest, 'wb') as f:
                        f.write(pr.content)
                    papers.append((aid, title, dest))
                    print(f'[文献下载|OpenAlex] ✅ {title[:44]}')
                    got = True
                    break
                if pr is not None:
                    print(f'[文献下载|OpenAlex] {base} -> HTTP {pr.status_code}')
            if not got:
                failed += 1
            time.sleep(5)

    _STATE['lit_folder'] = folder
    _STATE['lit_papers'] = papers

    if not papers:
        return (_render_lit(),
                '❌ 两条检索通道都未能下载到文献（arXiv 接口限流中）。'
                '请稍后重试、更换 VPN 节点，或调整关键词。')
    status = (f'🎉 经{channel}下载 {len(papers)} 篇文献到 {folder}'
              + (f'（{failed} 篇失败）' if failed else ''))
    if len(papers) < 5:
        status += f'\n⚠️ 仅 {len(papers)} 篇，不足 5 篇引用要求，建议稍后重试或调整关键词'
    return _render_lit(), status


# ============================================================
# 按钮④-3：通读全部文献 → 提取论点 → 按论文题目筛选
# ============================================================
def _split_points(md):
    '''把模型输出拆成（保留论点列表, 舍弃论点列表）'''
    m1 = re.search(r'##\s*保留论点(.*?)(?=##|\Z)', md, re.S)
    m2 = re.search(r'##\s*舍弃论点(.*?)\Z', md, re.S)

    def bullets(seg):
        if not seg or seg.strip().lower() in ('无', 'none', ''):
            return []
        items = []
        for ln in seg.splitlines():
            ln = re.sub(r'^\s*[-*\d.、)]+\s*', '', ln).strip()
            if len(ln) > 4 and ln != '无':
                items.append(ln)
        return items

    if m1:
        kept = bullets(m1.group(1))
    elif not m2:
        kept = bullets(md)          # 模型没按格式输出：整段视为保留论点
    else:
        kept = []
    return kept, bullets(m2.group(1)) if m2 else []


def _render_points(kept_by_paper, dropped_all, our_title, used, total):
    '''渲染筛选后的可引用论点清单（长内容全部走 Markdown，防 label 崩坏）'''
    n_pts = sum(len(k) for _, _, _, k in kept_by_paper)
    if not any(k for _, _, _, k in kept_by_paper):
        return ('> 📌 未筛选出任何与题目相关的论点。'
                '建议更换关键词检索更贴近的文献，或放宽题目范围。')
    lines = [
        f'## 📌 与《{our_title}》相关的可引用论点',
        f'**统计**：通读 {total} 篇文献，保留 **{n_pts}** 条论点'
        f'（来自 **{used}** 篇文献），舍弃 {len(dropped_all)} 条。\n',
    ]
    for i, rtitle, aid, kept in kept_by_paper:
        if not kept:
            continue
        lines.append(f'### 📄 文献{i}：{rtitle[:64]}（`{aid}`）')
        for j, p in enumerate(kept, 1):
            lines.append(f'{j}. {p}')
        lines.append('')
    if dropped_all:
        lines.append(f'<details><summary>🗑️ 已舍弃论点（{len(dropped_all)} 条，'
                     f'点击展开）</summary>\n')
        for src, d in dropped_all:
            lines.append(f'- **[{src}]** {d[:80]}')
        lines.append('\n</details>')
    return '\n'.join(lines)


def read_filter_points():
    '''按钮④-3：逐篇通读文献，提取论点并按论文题目筛选，无关论点舍弃'''
    papers = _STATE['lit_papers']
    if not papers:
        return ('> 📌 筛选后的可引用论点将显示在这里……',
                '⚠️ 请先执行④-2下载文献')
    our_title = _STATE.get('research_title') or _STATE['title'] or ''
    if not our_title:
        return ('> 📌 筛选后的可引用论点将显示在这里……',
                '⚠️ 缺少论文题目，请先在④-1输入题目并提取关键词')

    kept_by_paper, dropped_all, skipped = [], [], []
    used = 0
    for i, (aid, rtitle, path) in enumerate(papers, 1):
        print(f'[文献通读] ({i}/{len(papers)}) {rtitle[:44]}')
        try:
            text = _pdf_text(path)
        except Exception as e:
            skipped.append(f'文献{i}（读取失败 {type(e).__name__}）')
            continue
        if len(text) < 200:
            skipped.append(f'文献{i}（扫描件/文本过少）')
            continue

        out = _invoke_with_retry(
            READ_FILTER_PROMPT.format(our_title=our_title, ref_title=rtitle,
                                      text=text[:10000]),
            min_len=30, attempts=2)
        if out is None:
            skipped.append(f'文献{i}（付费 API 调用失败）')
            continue
        kept, dropped = _split_points(out)
        if kept:
            used += 1
        kept_by_paper.append((i, rtitle, aid, kept))
        dropped_all.extend((f'文献{i}', d) for d in dropped)

    n_pts = sum(len(k) for _, _, _, k in kept_by_paper)
    points_md = _render_points(kept_by_paper, dropped_all, our_title, used, len(papers))

    if used >= 5:
        verdict = '满足"至少引用 5 篇文献"的要求 ✅'
    else:
        verdict = (f'⚠️ 可引用文献 {used} 篇（少于 5 篇），'
                   f'建议更换关键词重新执行④-2，或更换题目')
    extra = f'；另有 {len(skipped)} 篇无法处理：{"、".join(skipped)}' if skipped else ''
    status = (f'🎉 已通读 {len(papers)} 篇文献：保留 {n_pts} 条论点'
              f'（{used} 篇可引用），舍弃 {len(dropped_all)} 条；{verdict}{extra}')
    return points_md, status


# ============================================================
# 标签页 UI（由 server.py 在 gr.Tabs() 上下文中调用）
# ============================================================
def create_tab():
    '''构建「论文生成」标签页，返回 gr.Tab 对象'''
    with gr.Tab('📝 论文生成') as tab:
        gr.Markdown(
            '## 📝 论文生成\n'
            '流程：**① 输入标题生成大纲（每个标题带索引编号）→ ② 输入索引生成所选章节**，'
            '已生成章节按顺序累加到论文预览中；**③ 阅读文献提取论点**（手动单篇精读）；'
            '**④ 自动文献研究**（关键词 → 下载 ≥5 篇 → 通读筛选论点）。'
            '使用商汤 SenseNova 付费模型。'
        )

        with gr.Row():
            title_box = gr.Textbox(
                label='论文标题',
                placeholder='例如：基于深度学习的医学影像分割方法研究',
                lines=1, scale=5,
            )
            btn_outline = gr.Button('① 生成大纲', variant='secondary', scale=1)

        outline_view = gr.Markdown(
            value='> 🗂️ 论文大纲将显示在这里（每个标题带索引编号）……')

        with gr.Row():
            idx_box = gr.Textbox(
                label='要生成的章节索引（如 1,3,5）',
                placeholder='输入大纲中的索引编号，多个用逗号分隔，如：1,3,5',
                lines=1, scale=3,
            )
            btn_section = gr.Button('② 生成所选章节', variant='primary', scale=1)

        status_box = gr.Textbox(label='运行状态', interactive=False, lines=2)
        paper_view = gr.Markdown(
            value='> 📄 生成的论文将显示在这里……（先 ① 生成大纲，再 ② 按索引生成章节）')

        # ---- ③ 文献论点提取（付费模型阅读 arxiv_papers 下的 PDF）----
        gr.Markdown(
            '---\n'
            '### 📖 文献论点提取\n'
            '从 `07-langchain-rag/arxiv_papers` 选择一篇论文 PDF，付费模型自动阅读，'
            '提取核心论点 / 支撑论据 / 局限，作为 ② 生成章节时的写作参考。'
        )
        with gr.Row():
            pdf_box = gr.Dropdown(
                choices=list_papers(),
                value=list_papers()[0] if list_papers() else None,
                label='选择要阅读的论文 PDF',
                scale=5,
            )
            btn_points = gr.Button('③ 阅读文献，提取论点', variant='secondary', scale=1)
        lit_status = gr.Textbox(label='文献阅读状态', interactive=False, lines=2)
        points_view = gr.Markdown(
            value='> 💡 选择论文并点击 ③，提取出的论点将显示在这里……')

        # ---- ④ 自动文献研究：关键词 → 下载 ≥5 篇 → 通读筛选论点 ----
        gr.Markdown(
            '---\n'
            '### 🔬 自动文献研究（最少引用 5 篇文献）\n'
            '**④-1 提取关键词 → ④-2 检索下载文献 → ④-3 通读并按题目筛选论点。** '
            '关键词可手动修改后再下载；无关论点自动舍弃，只保留可引用内容。'
        )
        with gr.Row():
            research_title = gr.Textbox(
                label='④-0 论文题目（关键词与论点筛选的依据）',
                placeholder='与①相同，或填写一个新的研究题目',
                lines=1, scale=5,
            )
            btn_keywords = gr.Button('④-1 提取关键词', variant='secondary', scale=1)
        kw_box = gr.Textbox(
            label='arXiv 检索关键词（英文，逗号分隔，可手动修改）',
            placeholder='点击④-1自动提取，或直接手动填写，如：mental health, large language models',
            lines=2, interactive=True,
        )
        btn_download = gr.Button('④-2 检索并下载文献（目标 ≥5 篇）', variant='secondary')
        lit_view = gr.Markdown(
            value='> 🗂️ 下载的文献清单将显示在这里……')
        btn_points_all = gr.Button('④-3 通读文献 · 提取论点 · 按题目筛选', variant='primary')
        lit4_status = gr.Textbox(label='④ 文献研究状态', interactive=False, lines=3)
        points4_view = gr.Markdown(
            value='> 📌 筛选后的可引用论点将显示在这里……')

        # ---- 事件绑定 ----
        btn_outline.click(generate_outline,
                          inputs=[title_box],
                          outputs=[outline_view, status_box])
        btn_section.click(generate_sections,
                          inputs=[idx_box],
                          outputs=[paper_view, status_box])
        btn_points.click(extract_points,
                         inputs=[pdf_box],
                         outputs=[points_view, lit_status])
        btn_keywords.click(extract_keywords,
                           inputs=[research_title],
                           outputs=[kw_box, lit4_status])
        btn_download.click(download_literature,
                           inputs=[kw_box],
                           outputs=[lit_view, lit4_status])
        btn_points_all.click(read_filter_points,
                             outputs=[points4_view, lit4_status])

    return tab
