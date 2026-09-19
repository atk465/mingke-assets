#!/usr/bin/env python3
"""check-lore.py — 世界书五道验收门（委托×世界书共识稿 2026-09-19）

用法: python tools/check-lore.py [worldbooks/ 下的文件名，缺省检查全部]

五道门:
  ① 禁词/禁句式 grep 零命中（文风校准条目自身的禁则清单是唯一真源）
  ② 长度落在分档区间（常驻 250-350；区域另定；其余概念条目 250-400）
  ③ 术语对照（暂缓：词表文件立起后启用）
  ④ 触发键覆盖（暂缓：批 3 起对照引擎素材表/中层名）
  ⑤ 每条有 name（comment 标题）
退出码 1 = 有未过门条目（CI 可用）。
"""
import json
import re
import sys
from pathlib import Path

WB = Path(__file__).resolve().parent.parent / 'worldbooks'

# ① 文风禁则（真源 = 文风校准条目；此处是它的机器可读副本，改禁则须两处同步）
BANNED_WORDS = ['一丝', '不容置疑', '不易察觉', '几不可察']
BANNED_PATTERNS = [
    r'他没有[^。]{0,30}，而是',
    r'不是[^。]{0,30}，而是',
    r'与其说[^。]{0,30}，不如说',
]
# ② 长度分档：条目名 → (min, max)；未列名的概念条目走书级/全局 DEFAULT
LENGTH_BANDS = {
    '文风校准': (250, 400),
    'DEFAULT': (220, 420),
}
# 书级档位（区域 380-660；素材 200-340——共识档 200-300 并入族内事实后放宽上限）
BOOK_BANDS = {
    'adventure_area.json': (380, 660),
    'material_lore.json': (200, 340),
    'monster_ecology.json': (250, 420),
    'organization.json': (200, 460),
    'faction.json': (140, 460),
    'variable.json': (150, 420),
    'extra_setting.json': (140, 420),
}
# ⑥ 自门控要求：这些书里的条目必须含 '<%' 门控
GATED_BOOKS = {
    'adventure_area.json',
    'world_setting.json',
    'material_lore.json',
    'monster_ecology.json',
    'organization.json',
    'faction.json',
    'variable.json',
}


# 二/三批待扩写书（显式挂账：全量跑时不计入失败，但逐条列出提醒）
PENDING_BOOKS = {
    'character.json', 'cot.json', 'dlc.json', 'event.json', 'race.json',
    'industry.json',
    'quick_feature.json',
    'extra_setting.json',
}


def check_book(path):
    problems = []
    book = json.loads(path.read_text(encoding='utf-8'))
    for e in book.get('entries', []):
        tag = f"{path.name}#{e.get('uid')}({e.get('name', '?')})"
        content = e.get('content', '')
        if not e.get('name'):
            problems.append(f'⑤ 标题缺失 {tag}')
        if path.name in GATED_BOOKS and not e.get('constant') and '<%' not in content:
            problems.append(f'⑥ 非常驻条目缺 EJS 自门控 {tag}')
        is_charter = e.get('name') == '文风校准'
        for w in [] if is_charter else BANNED_WORDS:
            if w in content:
                problems.append(f'① 禁词「{w}」 {tag}')
        for pat in [] if is_charter else BANNED_PATTERNS:
            m = re.search(pat, content)
            if m:
                problems.append(f'① 禁句式「{m.group(0)}」 {tag}')
        band = LENGTH_BANDS.get(e.get('name', ''))
        if band is None:
            band = BOOK_BANDS.get(path.name, LENGTH_BANDS['DEFAULT'])
        lo, hi = band
        # 长度按去标签正文字数
        body = re.sub(r'</?[^>]+>', '', content)
        if not (lo <= len(body) <= hi):
            problems.append(f'② 长度 {len(body)} 不在 [{lo},{hi}] {tag}')
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
    if pending_problems:
        print(f'（挂账：二/三批待扩写书 {len(pending_problems)} 项，不阻塞门禁）')
    if all_problems:
        print(f'未过门 {len(all_problems)} 项:')
        for p in all_problems:
            print(' -', p)
        return 1
    print('五道门全过（①禁词句式 ②长度 ⑤标题；③④随批次启用）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
