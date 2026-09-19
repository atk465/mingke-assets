# fated_poem_independent_assets ——《铭刻录》正式内容仓

> 来源声明：本项目世界观改编自《命定之诗》并遵循其内容二创授权协议标明来源；
> 去关联工程（世界观众名词替换）已立项，见 docs/canon.md v1.3+ 备注。

《铭刻录》（引擎仓 `IndependentFront-for-destined-journey`）的**正式内容包真源**。
产出单 JSON 内容包 `narrative-pack-<semver>.json`（packId `narrative-official`），经引擎设置页导入安装。

> 🔴 packId 已于 2026-09-20 随引擎仓"去 fated-poem 化"改名（`fated-poem-official` → `narrative-official`）。
> 引擎侧对装着旧 id 官方包的存档做了读取迁移与备份依赖映射，见引擎仓 `types-content.ts` 的
> `LEGACY_PACK_ID_MAP` 与 `docs/planning/2026-09-20-universal-frontend-rename-map.md`（改名映射表）。

## 目录形状（= 引擎 URL 约定，D14/D15）

```
worldbooks/        14 本内置世界书（world_setting / race / faction / character / event /
                   adventure_area / monster_ecology / industry / organization / variable /
                   quick_feature / extra_setting / cot / dlc）
data/content/      注册表内容面：catalog / locations / bloodlines / name-pools /
                   random-events / commissions / branding / map-pack / remote-assets
data/defaults/     引擎默认层：agent-config / story-preset / beautifier-rules
tools/             构建器 build-pack.mjs（内容树 → 单 JSON 包）
docs/              世界观内核（canon.md）与构建参考
```

## 开发调试

引擎 dev server 设 `POEM_CONTENT_DIR` 指向本仓根目录，`/data/*` 即服务本树（读+写回），
改内容刷新即见；`build-pack.mjs` 从同一棵树收集打包——**树即真相，构建不加工**。

## 世界观公理（详见 docs/canon.md）

1. 卡牌战斗是世界核心：纷争以「交锋」解决
2. 万物全雌：除玩家角色外一切角色皆为雌性/女性（铭灵皆以女性形貌显世）
3. 纪元名「铭刻」；IP 锚点：帝冕币、奥古斯提姆帝国、艾瑟嘉德、瓦伦蒂亚公国

## 版本纪律

- `packVersion` 走 semver，从 2.8.0 起步，单调不回退
- 世界书条目 uid 用真实段（每本独立从 1 递增）；**uid 永不回收**（D38），稳定性靠 git
- 占位 uid 段（900001+）与占位字样不得进包（构建器黑名单硬拦）
