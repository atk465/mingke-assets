# -*- coding: utf-8 -*-
"""build-org-lore.py — 批5：机构/势力门控化+扩写+新增（一次性脚本）"""
import json

def gate(name, gates, content):
    cond = ' || '.join(f"chat.match('{g}')" for g in gates)
    return "<% if (" + cond + ") { %>\n" + content.strip() + "\n<% } %>"

def expand(name, add, close_marker):
    """在条目正文结尾（</名> 前）追加一段"""
    e = E[name]
    c = e['content']
    idx = c.rfind(close_marker)
    assert idx > 0, name
    e['content'] = c[:idx].rstrip() + '\n' + add + '\n' + c[idx:]

# ═══ organization.json ═══
p = 'worldbooks/organization.json'
book = json.load(open(p, encoding='utf-8'))
E = {e['name']: e for e in book['entries']}

# 门控化 + 加厚
GATES_O = {
    '铭法院': ['铭法院', '法院', '书记'],
    '冒险者公会': ['公会', '冒险者', '委托', '委托板'],
    '禁录库': ['禁录库', '禁录', '收容'],
}
for name, gates in GATES_O.items():
    e = E[name]
    assert '<%' not in e['content'], name
    e['content'] = gate(name, gates, e['content'])

expand('铭法院', '法院的灰袍自备，洗得越旧越体面——新袍意味着你还没抄坏过一支笔。', '\n</铭法院>')
expand('冒险者公会', '公会的账目明到骨头里：佣金一成，写进章程第一行；改章程要全体在册冒险者表决——上一次表决是九十年前，议题是佣金改成九成五，没通过。', '\n</冒险者公会>')

# 新增两条
def entry(uid, name, gates, body, order):
    return {'uid': uid, 'name': name, 'content': gate(name, gates, body), 'enabled': True,
            'constant': False, 'key': gates, 'keysecondary': [],
            'selectiveLogic': 0, 'order': order, 'position': 0}

book['entries'].append(entry(12, '卡匠行会', ['卡匠行会', '行会', '制卡师行会', '火印'], """
大陆制卡业的自律组织，本座在公国诺瓦的卡匠工坊区，各省设分册。行会管三件事：发照（制卡师的执业铭籍）、验印（每一张正规卡都要盖火印）、记账（行会的火印册页记录着每一张在册卡的出身——连「晨露」这样一张传讯卡的来历都能翻到页）。
行会最忙的是每年一度的修复季：一批损坏的旧卡排队等裱匠与铭匠上手，按修复质量分级付酬。修复师的地位在行会里高于铸造师，理由写在老会员的口头禅里：「铸造靠天赋，修复靠良心。」
写行会时写它的规矩与体面：火印的油墨味、册页的翻动声、以及验印时那把谁也不许碰的放大晶。
""", 13))
book['entries'].append(entry(13, '守誓人', ['守誓人', '祭坛', '守誓'], """
看护命运祭坛的人，散居诸野，编制没有，俸禄没有，职责却清清楚楚：守「问过之后不得反悔」这条老规，替坛清洁，替问路人见证。守誓人多独身，带一个学徒，学徒的第一课是背熟守则第一页——「坛不说谎，人不说真话。」
守誓人认卡不认人：双月夜的坛前，一张像样的供卡比任何介绍信都好使。命运祭坛的供卡换季时，守誓人会通过公会贴出征集单，指名的行属从不解释——坛要什么，守誓人只负责转达。
写守誓人时写他们的安静与固执：矮坛、旧袍、擦了又擦的验卡晶，以及一句被问急了才说的实话：「我们不守坛，我们守的是你们问完之后的那点体面。」
""", 14))
book['description'] = '结社条目：提到机构名才注入（chat.match 门控）。职能/运作/与冒险者的关系+风味。'
json.dump(book, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('organization:', len(book['entries']), '条')

# ═══ faction.json ═══
p = 'worldbooks/faction.json'
book = json.load(open(p, encoding='utf-8'))
E = {e['name']: e for e in book['entries']}
GATES_F = {
    '奥古斯提姆帝国': ['帝国', '奥古斯提姆'],
    '瓦伦蒂亚公国': ['瓦伦蒂亚', '公国', '诺瓦'],
    '野铭者': ['野铭者', '逃铭', '私铭'],
}
for name, gates in GATES_F.items():
    e = E[name]
    assert '<%' not in e['content'], name
    e['content'] = gate(name, gates, e['content'])

expand('奥古斯提姆帝国', '帝国的节庆多到官僚抱怨：女帝生辰、交锋约缔结日、灭铭之战休战日——最后这一条的官方名称是「收手节」，民间的叫法更直接：补觉节。', '\n</奥古斯提姆帝国>')
expand('瓦伦蒂亚公国', '公国的钱庄可以拿卡抵押：品级越高押得越多，赎回期限越短，行话说「好卡睡当铺」。婚俗里也讲究卡——定亲要互赠一张亲手制的卡，手艺不论，诚意验收；验收人是双方家里最不会说谎的老人。', '\n</瓦伦蒂亚公国>')
book['description'] = '势力条目：提到势力名才注入（chat.match 门控）。'
json.dump(book, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('faction:', len(book['entries']), '条')

# ═══ variable.json 禁句式修复 ═══
p = 'worldbooks/variable.json'
book = json.load(open(p, encoding='utf-8'))
for e in book['entries']:
    if e['name'] == '交锋赌注惯例':
        bad = '不是「赌一百金冕」，而是「赌『欠款一笔销』这条铭」。街头野交锋才直接赌币。'
        good = '要赌就赌「铭写内容」——「赌『欠款一笔销』这条铭」是正写；直接赌币的只有街头野交锋。'
        assert bad in e['content']
        e['content'] = e['content'].replace(bad, good)
        # 门控化
        assert '<%' not in e['content']
        e['content'] = gate(e['name'], e['key'], e['content'])
json.dump(book, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('variable 禁句式已修并门控')
