# -*- coding: utf-8 -*-
"""
generate_map.py —— 《铭刻录》全大陆程序化地图生成器（v1）

输出（data/content/）:
- provinces.png   省份色块图（每地块唯一平色、无抗锯齿，分辨率 1920x1200）
- base-map.png    装饰底图（地形色 + 海洋渐变 + 岸线描边，供 branding.mapSources）
- map-pack.json   完整 MapPack（质心/面积/邻接全部由图自动推导）

确定性：全部随机走种子 RNG（默认 seed=488，呼应纪元年份）。改布局/改地形直接改
TILES 清单与布局参数，重跑即可；同一 seed 输出逐字节可复现。
"""
import json
import math
import io
import random
from collections import deque

import numpy as np
from PIL import Image, ImageFilter

SEED = 488
W, H = 1920, 1200
KM_PER_PX = 1.6
CONTENT_HASH = 'mingke-map-v1-488'

rng = random.Random(SEED)
np_rng = np.random.RandomState(SEED)

# ── 地形词汇（与 travelRules.terrainFactor 一一对应）──
TERRAINS = ['平原', '农田', '丘陵', '山脉', '高原', '森林', '针叶林', '湿地', '草原',
            '苔原', '冰原', '峡谷', '海岸', '近海', '远洋', '荒地']
TERRAIN_FACTOR = {'平原': 1, '农田': 1, '丘陵': 1.4, '山脉': 2.4, '高原': 1.6, '森林': 1.5,
                  '针叶林': 1.6, '湿地': 1.8, '草原': 1.1, '苔原': 1.5, '冰原': 2.2,
                  '峡谷': 2, '海岸': 1.2, '近海': 1, '远洋': 1, '荒地': 1.9}

COUNTRIES = [
    {'id': 'country_empire', 'name': '奥古斯提姆帝国', 'color': [176, 60, 50], 'anchorTileId': 2},
    {'id': 'country_valentia', 'name': '瓦伦蒂亚公国', 'color': [58, 110, 176], 'anchorTileId': 13},
    {'id': 'country_wild', 'name': '无主之地', 'color': [128, 122, 112], 'unclaimed': True, 'anchorTileId': 26},
]
MIDTIERS = [
    {'id': 'mid_jingji', 'name': '冕京京畿', 'countryId': 'country_empire', 'climateId': 'climate_temperate', 'anchorTileId': 2},
    {'id': 'mid_dongjing', 'name': '东境', 'countryId': 'country_empire', 'climateId': 'climate_temperate', 'anchorTileId': 3},
    {'id': 'mid_nanjing', 'name': '南境', 'countryId': 'country_empire', 'climateId': 'climate_coastal', 'anchorTileId': 5},
    {'id': 'mid_xinong', 'name': '西畿农带', 'countryId': 'country_empire', 'climateId': 'climate_temperate', 'anchorTileId': 6},
    {'id': 'mid_val_core', 'name': '公国本部', 'countryId': 'country_valentia', 'climateId': 'climate_temperate', 'anchorTileId': 13},
    {'id': 'mid_val_north', 'name': '公国北境', 'countryId': 'country_valentia', 'climateId': 'climate_cold', 'anchorTileId': 15},
    {'id': 'mid_wuminglu', 'name': '无名录', 'countryId': 'country_wild', 'climateId': 'climate_harsh', 'anchorTileId': 26},
    {'id': 'mid_liesi', 'name': '底石裂隙', 'countryId': 'country_wild', 'climateId': 'climate_harsh', 'anchorTileId': 28},
    {'id': 'mid_sea', 'name': '环陆海域', 'countryId': 'country_wild', 'climateId': 'climate_coastal', 'anchorTileId': 33},
]

CLIMATES = {
    'climate_temperate': {'name': '温带内陆', 'table': {
        '春季': [['晴', 4], ['多云', 3], ['阴', 2], ['小雨', 3], ['雾', 1]],
        '夏季': [['晴', 5], ['多云', 3], ['大雨', 2], ['雷暴', 2]],
        '秋季': [['晴', 3], ['多云', 3], ['阴', 3], ['小雨', 2], ['雾', 2]],
        '冬季': [['阴', 3], ['多云', 2], ['小雪', 3], ['雾', 2], ['晴', 2]]}},
    'climate_coastal': {'name': '沿海润风', 'table': {
        '春季': [['多云', 4], ['小雨', 3], ['阴', 2], ['晴', 2], ['雾', 2]],
        '夏季': [['晴', 4], ['多云', 3], ['雷暴', 3], ['大雨', 2]],
        '秋季': [['多云', 4], ['阴', 3], ['小雨', 2], ['晴', 2]],
        '冬季': [['阴', 4], ['小雨', 2], ['雾', 3], ['多云', 2]]}},
    'climate_cold': {'name': '北地寒温', 'table': {
        '春季': [['阴', 3], ['小雪', 3], ['多云', 3], ['雾', 2]],
        '夏季': [['多云', 4], ['晴', 3], ['小雨', 2], ['雾', 2]],
        '秋季': [['阴', 4], ['小雪', 2], ['雾', 3], ['多云', 2]],
        '冬季': [['小雪', 4], ['大雪', 3], ['冰雾', 2], ['阴', 3]]}},
    'climate_harsh': {'name': '铭异荒地', 'table': {
        '春季': [['阴', 4], ['雾', 3], ['黑风', 2], ['晴', 1]],
        '夏季': [['雾', 3], ['阴', 3], ['黑风', 3], ['晴', 2]],
        '秋季': [['雾', 4], ['黑风', 3], ['阴', 3]],
        '冬季': [['黑风', 3], ['雪雾', 3], ['阴', 4]]}},
}

DEV_LEVELS = ['废墟', '荒野', '营地', '聚落', '村庄', '乡镇', '城镇', '城市', '大城', '都会']
MAIN_BUILDINGS = ['断墙残垣', '界石营地', '驿站', '村祠', '仓储院', '会馆', '督府', '总督署', '行宫', '帝都·冕京']

# ── 地块清单（manifest）：
# (name, terrain, water, impassable, countryId, midTierId, seedX, seedY, dev, mainBuilding)
# 坐标为 0-1 归一化（x 向东，y 向南），生成器缩放到画布。
T = lambda **k: k
TILES = [
    # ── 帝国·京畿 ──
    T(name='帝都·冕京', terrain='平原', water=None, imp=False, c='country_empire', m='mid_jingji', x=0.62, y=0.30, dev=10, main='帝都·冕京'),
    T(name='冕京近畿', terrain='农田', water=None, imp=False, c='country_empire', m='mid_jingji', x=0.58, y=0.34, dev=8),
    T(name='京畿林地', terrain='森林', water=None, imp=False, c='country_empire', m='mid_jingji', x=0.66, y=0.26, dev=3),
    # ── 帝国·东境（艾瑟嘉德所在）──
    T(name='艾瑟嘉德', terrain='草原', water=None, imp=False, c='country_empire', m='mid_dongjing', x=0.78, y=0.22, dev=7, main='冒险者公会总会'),
    T(name='东境丘陵', terrain='丘陵', water=None, imp=False, c='country_empire', m='mid_dongjing', x=0.83, y=0.28, dev=3),
    T(name='东境哨堡', terrain='草原', water=None, imp=False, c='country_empire', m='mid_dongjing', x=0.89, y=0.15, dev=4),
    # ── 帝国·农带与南境 ──
    T(name='麦乡平原', terrain='农田', water=None, imp=False, c='country_empire', m='mid_xinong', x=0.54, y=0.40, dev=6),
    T(name='西部农业带', terrain='农田', water=None, imp=False, c='country_empire', m='mid_xinong', x=0.48, y=0.38, dev=6),
    T(name='帝国牧场', terrain='草原', water=None, imp=False, c='country_empire', m='mid_xinong', x=0.50, y=0.46, dev=4),
    T(name='南粮仓', terrain='农田', water=None, imp=False, c='country_empire', m='mid_nanjing', x=0.60, y=0.50, dev=6),
    T(name='帝国南港', terrain='海岸', water=None, imp=False, c='country_empire', m='mid_nanjing', x=0.66, y=0.54, dev=7),
    T(name='南部渔村', terrain='海岸', water=None, imp=False, c='country_empire', m='mid_nanjing', x=0.57, y=0.56, dev=3),
    # ── 瓦伦蒂亚公国 ──
    T(name='诺瓦·瓦伦蒂亚城', terrain='平原', water=None, imp=False, c='country_valentia', m='mid_val_core', x=0.30, y=0.38, dev=8, main='女大公府'),
    T(name='卡匠工坊区', terrain='平原', water=None, imp=False, c='country_valentia', m='mid_val_core', x=0.34, y=0.42, dev=6),
    T(name='公国农田', terrain='农田', water=None, imp=False, c='country_valentia', m='mid_val_core', x=0.27, y=0.44, dev=5),
    T(name='灰笺老街', terrain='城镇', water=None, imp=False, c='country_valentia', m='mid_val_north', x=0.30, y=0.24, dev=5),
    T(name='灰笺矿区', terrain='山脉', water=None, imp=False, c='country_valentia', m='mid_val_north', x=0.27, y=0.18, dev=6),
    T(name='菌孢林', terrain='森林', water=None, imp=False, c='country_valentia', m='mid_val_north', x=0.22, y=0.28, dev=2),
    T(name='西部海岸', terrain='海岸', water=None, imp=False, c='country_valentia', m='mid_val_core', x=0.22, y=0.42, dev=4),
    T(name='北境山口', terrain='峡谷', water=None, imp=False, c='country_valentia', m='mid_val_north', x=0.24, y=0.12, dev=2),
    # ── 特殊/无主 ──
    T(name='无名录边缘', terrain='荒地', water=None, imp=False, c='country_wild', m='mid_wuminglu', x=0.84, y=0.40, dev=1),
    T(name='无名录腹地', terrain='荒地', water=None, imp=True, c='country_wild', m='mid_wuminglu', x=0.90, y=0.44, dev=1),
    T(name='底石裂隙', terrain='峡谷', water=None, imp=True, c='country_wild', m='mid_liesi', x=0.12, y=0.08, dev=1),
    T(name='霜颸北境', terrain='苔原', water=None, imp=False, c='country_wild', m='mid_liesi', x=0.18, y=0.04, dev=1),
    T(name='野铭者谷地', terrain='峡谷', water=None, imp=False, c='country_wild', m='mid_liesi', x=0.16, y=0.14, dev=2),
    # ── 海域 ──
    T(name='南部近海', terrain='近海', water='sea', imp=False, c='country_wild', m='mid_sea', x=0.60, y=0.72, dev=None),
    T(name='东南近海', terrain='近海', water='sea', imp=False, c='country_wild', m='mid_sea', x=0.86, y=0.66, dev=None),
    T(name='西部近海', terrain='近海', water='sea', imp=False, c='country_wild', m='mid_sea', x=0.10, y=0.52, dev=None),
    T(name='北部近海', terrain='近海', water='sea', imp=False, c='country_wild', m='mid_sea', x=0.55, y=0.03, dev=None),
    T(name='裂隙外海', terrain='近海', water='sea', imp=False, c='country_wild', m='mid_sea', x=0.06, y=0.20, dev=None),
    T(name='南方远洋', terrain='远洋', water='sea', imp=False, c='country_wild', m='mid_sea', x=0.42, y=0.88, dev=None),
    T(name='东南远洋', terrain='远洋', water='sea', imp=False, c='country_wild', m='mid_sea', x=0.78, y=0.90, dev=None),
    T(name='西方远洋', terrain='远洋', water='sea', imp=False, c='country_wild', m='mid_sea', x=0.03, y=0.80, dev=None),
]

PLACE_BINDINGS = {
    '艾瑟嘉德': 4, '帝都·冕京': 1, '诺瓦·瓦伦蒂亚城': 13, '灰笺矿脉': 16,
    '灰笺老街': 17, '无名录': 26, '底石裂隙': 28, '命运祭坛': 4,
}

# ═══════════════ 生成 ═══════════════

def smooth_noise(w, h, scale, seed_offset):
    """双线性插值的平滑值噪声（0-1），seed_offset 控制不同图层。"""
    small_w, small_h = max(2, w // scale), max(2, h // scale)
    base = np_rng.random_sample((small_h, small_w)) + seed_offset * 0.37
    img = Image.fromarray((base * 255).astype('uint8'), 'L').resize((w, h), Image.BICUBIC)
    return np.asarray(img, dtype=np.float64) / 255.0


def build_land_mask(w, h):
    """大陆掩码：噪声 + 北重心衰减（大陆居北，南部留给海洋）。"""
    ny, nx = np.mgrid[0:h, 0:w]
    nxn, nyn = nx / w, ny / h
    noise = (smooth_noise(w, h, 160, 1) * 0.55
             + smooth_noise(w, h, 80, 2) * 0.28
             + smooth_noise(w, h, 36, 3) * 0.17)
    # 大陆重心在 (0.48, 0.30)，半径覆盖到 ~0.55 宽
    dist = np.sqrt(((nxn - 0.48) * 1.05) ** 2 + (nyn - 0.30) ** 2)
    falloff = np.clip(1.0 - (dist - 0.18) * 2.6, -0.4, 1.0)
    return (noise * 0.62 + falloff * 0.55) > 0.52


def region_colors(n):
    """黄金比例色相环生成 n 个互异 RGB（避开近白/近黑）。"""
    colors, used = [], set()
    golden = 0.618033988749895
    hue = rng.random()
    while len(colors) < n:
        hue = (hue + golden) % 1.0
        sat = 0.45 + rng.random() * 0.4
        val = 0.45 + rng.random() * 0.4
        # HSV→RGB
        i = int(hue * 6) % 6
        f = hue * 6 - int(hue * 6)
        p, q, t = val * (1 - sat), val * (1 - f * sat), val * (1 - (1 - f) * sat)
        rgb = [(val, t, p), (q, val, p), (p, val, t), (p, q, val), (t, p, val), (val, p, q)][i]
        rgb = tuple(int(v * 255) for v in rgb)
        if rgb in used:
            continue
        used.add(rgb)
        colors.append(list(rgb))
    return colors


def main():
    land_mask = build_land_mask(W, H)
    water_mask = ~land_mask

    # 多源 BFS 区域扩张（4 邻接，种子顺序由洗牌后的 rng 决定 → 有机边界）
    tile_id = np.zeros((H, W), dtype=np.int32)  # 0 = 未分配
    queues = deque()
    id_by_index = {}
    land_seeds = [(t, i) for i, t in enumerate(TILES) if not t['water']]
    water_seeds = [(t, i) for i, t in enumerate(TILES) if t['water']]

    def seed_pixel(t):
        return max(1, min(W - 2, int(t['x'] * W))), max(1, min(H - 2, int(t['y'] * H)))

    order = list(range(len(land_seeds)))
    rng.shuffle(order)
    for k in order:
        t, i = land_seeds[k]
        x, y = seed_pixel(t)
        if not land_mask[y, x]:  # 种子落在海里 → 找最近的陆像素
            found = False
            for r in range(1, 400):
                y0, y1 = max(0, y - r), min(H, y + r + 1)
                x0, x1 = max(0, x - r), min(W, x + r + 1)
                yy, xx = np.mgrid[y0:y1, x0:x1]
                sub_mask = land_mask[y0:y1, x0:x1]
                if sub_mask.any():
                    d = (yy - y) ** 2 + (xx - x) ** 2
                    d = np.where(sub_mask, d, d.max() + 1)
                    cy, cx = np.unravel_index(d.argmin(), d.shape)
                    y, x = int(yy[cy, cx]), int(xx[cy, cx])
                    found = True
                    break

            if not found:
                continue
        if tile_id[y, x] == 0:
            tile_id[y, x] = i + 1
            id_by_index[i + 1] = t
            queues.append((i + 1, x, y))

    for k in range(len(water_seeds)):
        t, i = water_seeds[k]
        x, y = seed_pixel(t)
        for r in range(0, 500):
            y0, y1 = max(0, y - r), min(H, y + r + 1)
            x0, x1 = max(0, x - r), min(W, x + r + 1)
            yy, xx = np.mgrid[y0:y1, x0:x1]
            sub_mask = water_mask[y0:y1, x0:x1]
            if sub_mask.any():
                d = (yy - y) ** 2 + (xx - x) ** 2
                d = np.where(sub_mask, d, d.max() + 1)
                cy, cx = np.unravel_index(d.argmin(), d.shape)
                y, x = int(yy[cy, cx]), int(xx[cy, cx])
                break
        if water_mask[y, x] and tile_id[y, x] == 0:
            tile_id[y, x] = i + 1
            id_by_index[i + 1] = t
            queues.append((i + 1, x, y))

    while queues:
        tid, x, y = queues.popleft()
        is_water = id_by_index[tid]['water'] is not None
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx_, ny_ = x + dx, y + dy
            if 0 <= nx_ < W and 0 <= ny_ < H and tile_id[ny_, nx_] == 0:
                if is_water and not water_mask[ny_, nx_]:
                    continue
                if not is_water and not land_mask[ny_, nx_]:
                    continue
                tile_id[ny_, nx_] = tid
                queues.append((tid, nx_, ny_))

    # 未分配像素收敛（两段式，避免全分辨率下数千趟膨胀）：
    # ① 4x 降采样网格上快速膨胀至无零；② 全分辨率边界精修（上限 60 趟）。
    def dilate_once(grid):
        grew = False
        h, w = grid.shape
        for axis in (0, 1):
            a = np.take(grid, range(0, h - 1), axis=axis)
            b = np.take(grid, range(1, h), axis=axis)
            for src, dst in ((a, b), (b, a)):
                hole = (dst == 0) & (src > 0)
                if hole.any():
                    dst[hole] = src[hole]
                    grew = True
        return grew

    # ① 降采样（步长 4，取块内首个非零 id）
    small = tile_id[::4, ::4].copy()
    for _ in range(2000):
        if not (small == 0).any() or not dilate_once(small):
            break
    # 上采样回写仍为零的像素
    up = np.repeat(np.repeat(small, 4, axis=0), 4, axis=1)[:H, :W]
    tile_id[tile_id == 0] = up[tile_id == 0]

    # ② 全分辨率边界精修（上限 60 趟；剩余极零散像素按行内近邻兜底）
    for _ in range(60):
        if not (tile_id == 0).any() or not dilate_once(tile_id):
            break
    if (tile_id == 0).any():
        idx = np.where(tile_id.ravel() == 0)[0]
        for flat in idx:
            y0, x0 = divmod(flat, W)
            best, btid = 1 << 30, 1
            for dy in (-8, -4, 0, 4, 8):
                for dx in (-8, -4, 0, 4, 8):
                    yy, xx = y0 + dy, x0 + dx
                    if 0 <= yy < H and 0 <= xx < W and tile_id[yy, xx] > 0:
                        d2 = dy * dy + dx * dx
                        if d2 < best:
                            best, btid = d2, int(tile_id[yy, xx])
            tile_id[y0, x0] = btid

    # ═══ provinces.png（平色）═══
    colors = region_colors(len(TILES))
    pal = np.zeros((len(TILES) + 1, 3), dtype=np.uint8)
    for i, t in enumerate(TILES):
        pal[i + 1] = colors[i]
    img = pal[tile_id]
    Image.fromarray(img, 'RGB').save('data/content/provinces.png', optimize=True)

    # ═══ 质心 / 面积 / 邻接 ═══
    tiles_out, adjacency_set = [], set()
    for i, t in enumerate(TILES):
        tid = i + 1
        mask = tile_id == tid
        area = int(mask.sum())
        if area == 0:
            raise SystemExit(f'地块 {t["name"]} 面积为 0——种子被挤出，请调整布局参数')
        ys, xs = np.nonzero(mask)
        tiles_out.append({
            'id': tid, 'name': t['name'], 'terrain': t['terrain'],
            'water': t['water'], 'impassable': t['imp'],
            'countryId': t['c'], 'midTierId': t['m'],
            'color': colors[i],
            'centroid': [round(float(xs.mean()), 1), round(float(ys.mean()), 1)],
            'areaPx': area,
            **({'development': t['dev']} if t.get('dev') else {}),
            **({'mainBuilding': t['main']} if t.get('main') else {}),
        })
    # 邻接：横向/纵向相邻像素对不同 id
    for axis in (0, 1):
        a = np.take(tile_id, range(0, (H if axis == 0 else W) - 1), axis=axis)
        b = np.take(tile_id, range(1, H if axis == 0 else W), axis=axis)
        pairs = np.unique(np.stack([a.ravel(), b.ravel()], axis=1), axis=0)
        for pa, pb in pairs:
            if pa != pb and pa > 0 and pb > 0:
                adjacency_set.add((min(int(pa), int(pb)), max(int(pa), int(pb))))
    adjacency = [[a, b, 40] for a, b in sorted(adjacency_set)]

    # ═══ map-pack.json ═══
    pack = {
        'version': 'mingke-1.0.0',
        'contentHash': CONTENT_HASH,
        'resolution': {'w': W, 'h': H},
        'kmPerPx': KM_PER_PX,
        'terrains': TERRAINS,
        'developmentLevels': DEV_LEVELS,
        'mainBuildingNames': MAIN_BUILDINGS,
        'travelRules': {
            'rates': {'land': 30, 'nearSea': 60, 'farSea': 90},
            'embarkCost': 40,
            'terrainFactor': TERRAIN_FACTOR,
            'modes': [
                {'key': 'foot', 'name': '步行', 'rateMult': 1},
                {'key': 'cart', 'name': '骡车', 'rateMult': 1.2, 'note': '官道专用'},
                {'key': 'ship', 'name': '海船', 'rateMult': 2, 'note': '仅海域'},
            ],
        },
        'countries': COUNTRIES,
        'midTiers': MIDTIERS,
        'climates': CLIMATES,
        'tiles': tiles_out,
        'adjacency': adjacency,
        'straits': [],
        'placeBindings': PLACE_BINDINGS,
    }
    wr = lambda path, o: io.open(path, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(o, ensure_ascii=False, indent=2) + '\n')
    wr('data/content/map-pack.json', pack)

    # ═══ 装饰底图（地形色 + 海洋渐变 + 国界柔光）═══
    TERRAIN_TINT = {
        '平原': (168, 196, 120), '农田': (208, 196, 110), '丘陵': (176, 168, 110),
        '山脉': (142, 134, 126), '森林': (110, 152, 96), '针叶林': (92, 128, 100),
        '峡谷': (120, 100, 88), '海岸': (196, 188, 150), '近海': (84, 130, 172),
        '远洋': (56, 96, 148), '苔原': (176, 186, 190), '冰原': (216, 226, 232),
        '荒地': (178, 160, 128), '草原': (180, 200, 120),
    }
    base = np.zeros((H, W, 3), dtype=np.uint8)
    for i, t in enumerate(TILES):
        tint = TERRAIN_TINT.get(t['terrain'], (150, 150, 150))
        if t.get('water'):
            tint = (84, 130, 172) if t['terrain'] == '近海' else (56, 96, 148)
        base[tile_id == i + 1] = tint
    # 轻噪声肌理 + 柔化
    base = (base.astype(np.int16) + ((np_rng.random_sample((H, W, 3)) - 0.5) * 14).astype(np.int16)).clip(0, 255).astype(np.uint8)
    bimg = Image.fromarray(base, 'RGB').filter(ImageFilter.GaussianBlur(1.2))
    bimg.save('data/content/base-map.png', optimize=True)

    # ═══ 自检报告 ═══
    land_ids = {i + 1 for i, t in enumerate(TILES) if not t['water']}
    adj_ids = set()
    for a, b_, _ in adjacency:
        adj_ids.add(a)
        adj_ids.add(b_)
    orphan = [TILES[i - 1]['name'] for i in land_ids if i not in adj_ids]
    print(f'[generate_map] tiles={len(tiles_out)} land={len(land_ids)} sea={len(TILES) - len(land_ids)}')
    print(f'[generate_map] adjacency pairs={len(adjacency)} | 无邻接孤岛: {orphan or "无"}')
    areas = {t["name"]: t["areaPx"] for t in tiles_out}
    tiny = [n for n, a in areas.items() if a < 4000]
    print(f'[generate_map] 过小地块(<4000px): {tiny or "无"}')
    # 连通性：艾瑟嘉德(4) → 诺瓦(13) BFS
    adj_map = {}
    for a, b_, _ in adjacency:
        adj_map.setdefault(a, set()).add(b_)
        adj_map.setdefault(b_, set()).add(a)
    seen, stack = {4}, [4]
    while stack:
        for nb in adj_map.get(stack.pop(), ()):
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    print(f'[generate_map] 艾瑟嘉德↔诺瓦连通: {13 in seen}')


if __name__ == '__main__':
    main()
