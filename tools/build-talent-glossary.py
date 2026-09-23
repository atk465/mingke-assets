# -*- coding: utf-8 -*-
"""build-talent-glossary.py — 《天赋词》：SSS/SS 天赋词条目组（2026-09-23 二批追加）

为什么只收 SSS/SS：全目录 697 天赋不可能逐条入书；SSS+SS（95 条）是最可能被
剧情、NPC、传闻提及的名目。玩家**持有**的天赋由 {{TALENT}} 块逐回合注入
（含描述与条目摘要），词表补的正是「不在玩家手里」的那一半。
自定义天赋（天赋制作器）是运行时数据，走 {{TALENT}} 块的动态词表段
（placeholder-registry.renderCustomTalentWords），不进静态书。

数据源：tools/talent-glossary-dump.json（引擎 TALENT_CATALOG 的 SSS/SS 投影）。
重导：引擎仓根目录 `npx tsx` 执行四行导出脚本（见提交说明），再跑本脚本。

文风（主人面谕：防不明所以/防文青）：条目 = 描述原文 + 机制口径白话行。
机制口径按 kind 对照表生成，不发明数值；叙事类 kind 明说「引擎不强制、
按描述演绎」。
"""
import json

# kind → 白话机制口径（数值类与引擎条目池同语义；叙事类明说交给演绎）
KIND_GLOSS = {
    '材料限定': '制卡选料宜用「{materialClass}」类素材（成功率+30%）',
    '成品限定': '效果只对「{productClass}」类成品生效',
    '成功率加成': '相关制卡判定成功率+{bonus}%',
    '品质锁定': '产出品质锁定为{tier}',
    '品质突破': '产出品质可越一级',
    '启封加值': '启封判定+{amount}',
    '行动值加成': '交锋行动值+{amount}',
    '防御加值': '交锋防御+{amount}',
    '配方解锁': '已解锁配方「{recipe}」——素材命中即按配方产出',
    '词条加权': '制卡时更容易出指定方向的词条',
    '叙事意图': '规则面交给叙事演绎，引擎不强制数值',
    '判定取优': '相关判定掷两次取高',
    '威压': '对敌时敌方属性按档位折减',
    '环境加成': '对应环境域生效时获得加成',
    '连战递增': '连续交锋每多一拍行动值递增',
    '终章': '交锋拖到终局拍数触发强制终结',
    '战技附加': '为卡牌附加战技',
    '越阶': '可以越阶挑战或越阶产出',
    '捕获': '可捕获对象入卡',
    '孕育': '含孕育/诞生类规则，按描述演绎',
    '吞噬': '含吞噬/吸收类规则，按描述演绎',
    '融合': '涉及卡牌或素材的融合规则',
    '拆解': '可拆解卡牌或素材取回价值',
    '剥离': '可剥离既有卡牌的部件或词条',
    '形态转化': '涉及形态转化规则，按描述演绎',
    '合同': '涉及契约文书类规则，按描述演绎',
    '结缘': '涉及结缘/羁绊类规则，按描述演绎',
    '熔炼': '涉及熔炼合成规则',
    '位份': '涉及位份/阶序类规则，按描述演绎',
    '自我进化': '卡牌或对象可自我进化，按描述演绎',
    '转化': '涉及素材转化规则',
    '情绪素材': '情绪可作为制卡素材',
    '改造': '涉及改造类规则',
    '深渊契约': '涉及深渊契约规则，按描述演绎',
    '烙印': '涉及烙印类规则，按描述演绎',
    '本名武器': '涉及本名武器/卡随名长规则',
    '克上': '以下克上类加成，按描述演绎',
    '同契': '涉及同契契约成长规则',
    '日掷': '每日一次的掷问/抽取类规则',
    '欲望主导': '涉及欲望主导类规则，按描述演绎',
}

def gloss_of(entry):
    g = KIND_GLOSS.get(entry['kind'])
    if g is None:
        return f"{entry['kind']}：按描述演绎"
    try:
        return g.format(**entry.get('params', {}))
    except (KeyError, IndexError):
        return g

def build():
    dump = json.load(open('tools/talent-glossary-dump.json', encoding='utf-8'))
    entries = []
    for i, t in enumerate(dump, start=1):
        name, grade, desc = t['name'], t['grade'], (t['description'] or '').strip()
        glosses = '；'.join(gloss_of(e) for e in t['entries'])
        body = f"{grade} 天赋。{desc}"
        if glosses:
            body += f"\n机制口径：{glosses}。"
        cond = ' || '.join(f"chat.match('{name}')")
        content = f"<% if ({cond}) {{ %>\n<{name}>\n{body}\n</{name}>\n<% }} %>"
        entries.append({
            'uid': i,
            'name': name,
            'content': content,
            'enabled': True,
            'constant': False,
            'key': [name],
            'keysecondary': [],
            'selectiveLogic': 0,
            'order': i,
            'position': 0,
        })
    book = {
        'id': 'talent_glossary',
        'name': '《天赋词》',
        'partition': 'talent_glossary',
        'description': 'SSS/SS 级天赋的词条目组：叙事中出现天赋名时按条内口径演绎。玩家持有的天赋另有 {{TALENT}} 块逐回合注入；自定义天赋（天赋制作器）走动态词表段，不入本册。',
        'builtIn': True,
        'entries': entries,
    }
    json.dump(book, open('worldbooks/talent_glossary.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f"worldbooks/talent_glossary.json: {len(entries)} 条")

if __name__ == '__main__':
    build()
