#!/usr/bin/env python3
"""check-lore.py — 世界书验收门（v2：v1.4 写作正典执法版，2026-09-19）

用法: python tools/check-lore.py [worldbooks/ 下的文件名，缺省检查全部]

真源: docs/canon.md「七、写作正典」（主人提供全文）——本文件是它的机器执法副本，
改禁则/限频须两处同步。

验收门:
  ① 禁词/禁句式 grep 零命中（含空洞形容词四禁）
  ② 长度：**上限硬拦**，下限只提示不阻塞（v1.4「字数宁可低于下限」——
     颗粒度区间是扩写目标，不是灌水指标）
  ③ 术语对照（暂缓：词表文件立起后启用）
  ④ 触发键覆盖（暂缓：批 3 起对照引擎素材表/中层名）
  ⑤ 每条有 name（comment 标题）
  ⑥ 非常驻条目必须含 EJS 自门控
  ⑦ 句式限频（写作正典「句式限频」节的机器执法）
  ⑧ 凑字数检测（同段车轱辘话复读 + 空洞形容词硬四禁同源）
退出码 1 = 有未过门条目（CI 可用）。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

WB = Path(__file__).resolve().parent.parent / 'worldbooks'

# ── ① 文风禁则（真源 = canon.md 写作正典；此处是机器可读副本，改禁则两处同步）──
BANNED_WORDS = ['一丝', '不容置疑', '不易察觉', '几不可察']
# 空洞形容词四禁（写作正典 §核心生成原则 1）——按⑧与①双记
HOLLOW_WORDS = ['强大', '神秘', '古老', '极其危险']
BANNED_PATTERNS = [
    r'他没有[^。]{0,30}，而是',
    r'不是[^。]{0,30}，而是',
    r'与其说[^。]{0,30}，不如说',
]
# ── ⑦ 句式限频（写作正典「句式限频」节）──
# 每条：(标签, 正则, 上限)
PER_ENTRY_LIMITS = [
    ('⑦ 破折号', r'——', 2),
    ('⑦ 行话', r'行话说|行话叫|行话是|行里叫|行里称', 1),
    ('⑦ 规矩腔', r'的说法|的规矩|的原则', 1),
    ('⑦ 排比框架', r'先[^。]{1,18}(再|后|最后)', 1),
    ('⑦ 导演腔', r'写[^。，；]{0,12}时写', 1),
]
# 每册：平衡腔
PER_BOOK_LIMITS = [
    ('⑦ 平衡腔', r'两派|各有各的说法|两种说法', 2),
]
# ── ② 长度：上限硬拦；下限提示（advisory）──
LENGTH_BANDS = {
    '文风校准': (250, 400),
    'DEFAULT': (220, 420),
}
BOOK_BANDS = {
    'adventure_area.json': (380, 660),
    'material_lore.json': (200, 340),
    'monster_ecology.json': (250, 420),
    'organization.json': (200, 460),
    'faction.json': (140, 460),
    'variable.json': (150, 420),
    'extra_setting.json': (140, 420),
    'character.json': (150, 420),
    'race.json': (150, 480),
    'event.json': (140, 420),
    'industry.json': (140, 420),
    'dlc.json': (150, 520),
    # 天赋词：条目=描述原文+机制口径，描述长短随目录，下限放宽
    'talent_glossary.json': (80, 560),
}
# ⑥ 自门控要求
GATED_BOOKS = {
    'adventure_area.json',
    'world_setting.json',
    'material_lore.json',
    'monster_ecology.json',
    'organization.json',
    'faction.json',
    'variable.json',
    'character.json',
    'race.json',
    'event.json',
    'industry.json',
    'dlc.json',
    'talent_glossary.json',
}
# 二/三批待扩写书（显式挂账：全量跑不计入失败，逐条列出提醒）
PENDING_BOOKS = {
    'cot.json', 'quick_feature.json', 'extra_setting.json',
}

# 剔除 EJS 门控与标签后的正文体（长度/句式/复读统计共用）
def body_of(content):
    c = re.sub(r'<%[^%]*%>', '', content)  # 剥 EJS 门控行
    c = re.sub(r'</?[^>]+>', '', c)        # 剥 <条目名> 标签
    return c


def check_book(path):
    problems = []
    book = json.loads(path.read_text(encoding='utf-8'))
    book_balance = 0
    for e in book.get('entries', []):
        tag = f"{path.name}#{e.get('uid')}({e.get('name', '?')})"
        content = e.get('content', '')
        if not e.get('name'):
            problems.append(f'⑤ 标题缺失 {tag}')
        if path.name in GATED_BOOKS and not e.get('constant') and '<%' not in content:
            problems.append(f'⑥ 非常驻条目缺 EJS 自门控 {tag}')
        is_charter = e.get('name') == '文风校准'
        banned_w = [] if is_charter else BANNED_WORDS
        banned_p = [] if is_charter else BANNED_PATTERNS
        for w in banned_w:
            if w in content:
                problems.append(f'① 禁词「{w}」 {tag}')
        for w in HOLLOW_WORDS:
            if w in content and not is_charter:
                problems.append(f'①⑧ 空洞形容词「{w}」（canon 写作正典 §1；上下文合理可申诉） {tag}')
        for pat in banned_p:
            m = re.search(pat, content)
            if m:
                problems.append(f'① 禁句式「{m.group(0)}」 {tag}')
        body = body_of(content)
        # ② 长度：上限硬拦；下限提示不阻塞
        band = LENGTH_BANDS.get(e.get('name', ''))
        if band is None:
            band = BOOK_BANDS.get(path.name, LENGTH_BANDS['DEFAULT'])
        lo, hi = band
        if len(body) > hi:
            problems.append(f'② 长度 {len(body)} 超上限 {hi} {tag}')
        elif len(body) < lo:
            print(f'  [提示] {len(body)} < {lo}（若已无具体细节可写，合规） {tag}')
        # ⑦ 句式限频（对正文统计）
        for label, pat, cap in PER_ENTRY_LIMITS:
            n = len(re.findall(pat, body))
            if n > cap:
                problems.append(f'{label} {n}/{cap} {tag}')
        for label, pat, cap in PER_BOOK_LIMITS:
            book_balance += len(re.findall(pat, body))
        # ⑧ 凑字数：8 字以上片段重复出现（车轱辘话）
        frag = Counter(m.group(0) for m in re.finditer(r'[\u4e00-\u9fff]{8,}', body))
        dup = [f for f, n in frag.items() if n >= 2]
        if dup:
            problems.append(f'⑧ 车轱辘话复读 {dup[:2]} {tag}')
    for label, pat, cap in PER_BOOK_LIMITS:
        if book_balance > cap:
            problems.append(f'{label} 全册 {book_balance}/{cap} {path.name}')
    return problems


# ⑨ 起始地点对表（2026-09-19）：catalog.json 起始地树叶子的路径末段必须是
#    map-pack.json 里真实存在的地块名——防「御道枢纽」式过时项（内容改了地图，
#    起始地树忘了跟）。
def check_start_locations() -> list:
    problems = []
    cat_path = WB.parent / 'data' / 'content' / 'catalog.json'
    map_path = WB.parent / 'data' / 'content' / 'map-pack.json'
    if not cat_path.exists() or not map_path.exists():
        return problems
    cat = json.loads(cat_path.read_text(encoding='utf-8'))
    mp = json.loads(map_path.read_text(encoding='utf-8'))
    tile_names = {t.get('name') for t in mp.get('tiles', [])}
    forbidden_zones = {
        t.get('name') for t in mp.get('tiles', []) if t.get('impassable')
    }
    def leaves(nodes):
        out = []
        for n in nodes:
            if n.get('children'):
                out += leaves(n['children'])
            else:
                out.append(n)
        return out
    for leaf_node in leaves(cat.get('startLocations', [])):
        value = str(leaf_node.get('value', ''))
        last = value.split('-')[-1]
        if last not in tile_names:
            problems.append(f'⑨ 起始地点「{leaf_node.get("label")}」末段「{last}」不是地图地块名')
        elif last in forbidden_zones:
            problems.append(f'⑨ 起始地点「{leaf_node.get("label")}」落在不可通行地块上')
    return problems


def main() -> int:
    targets = [WB / n for n in sys.argv[1:]] if len(sys.argv) > 1 else sorted(WB.glob('*.json'))
    all_problems = []
    pending_problems = []
    for t in targets:
        problems = check_book(t)
        if t.name in PENDING_BOOKS:
            pending_problems += problems
        else:
            all_problems += problems
    all_problems += check_start_locations()
    if pending_problems:
        print(f'（挂账：二/三批待扩写书 {len(pending_problems)} 项，不阻塞门禁）')
    if all_problems:
        print(f'未过门 {len(all_problems)} 项:')
        for p in all_problems:
            print(' -', p)
        return 1
    print('验收门全过（①禁词句式 ②长度上限 ⑤标题 ⑥自门控 ⑦句式限频 ⑧凑字数 ⑨起始地对表；③④随批次启用）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
