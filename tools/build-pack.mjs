#!/usr/bin/env node
/**
 * build-pack.mjs —— 《铭刻录》内容树 → 单 JSON 内容包
 *
 * 用法: node tools/build-pack.mjs [--version 2.8.0] [--out dist]
 *
 * 纪律:
 * - 内容树即真相：收集不加工（唯一允许的变换是剥 $comment 注释键）
 * - 黑名单硬拦（退出码 1）：占位 uid 段(900001+)、占位字样、非 builtIn 世界书、
 *   creative_workshop 分区、缺失必填字段
 * - sectionHashes 仅作升级 diff 展示（D18：冲突判定一律由引擎从 payload 现算）
 */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(fileURLToPath(import.meta.url)) + '/..';
const args = process.argv.slice(2);
function argOf(name, dflt) {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : dflt;
}
const VERSION = argOf('--version', '2.9.0');
const OUT_DIR = join(ROOT, argOf('--out', 'dist'));

/** 收集时剥掉所有 $comment 注释键（递归） */
function stripComments(v) {
  if (Array.isArray(v)) return v.map(stripComments);
  if (v && typeof v === 'object') {
    const out = {};
    for (const [k, val] of Object.entries(v)) {
      if (k === '$comment') continue;
      out[k] = stripComments(val);
    }
    return out;
  }
  return v;
}

const errors = [];
function fail(msg) {
  errors.push(msg);
}

function readJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

// ═══ 1. worldbooks/ → worldBooks ═══
const WB_DIR = join(ROOT, 'worldbooks');
const worldBooks = [];
if (existsSync(WB_DIR)) {
  for (const f of readdirSync(WB_DIR).filter((x) => x.endsWith('.json')).sort()) {
    const book = stripComments(readJson(join(WB_DIR, f)));
    if (book.builtIn !== true) fail(`[blacklist] ${f}: builtIn !== true`);
    if (book.partition === 'creative_workshop') fail(`[blacklist] ${f}: creative_workshop 分区`);
    for (const e of book.entries ?? []) {
      if (typeof e.uid !== 'number') fail(`[blacklist] ${f}#${e.uid}: uid 非数字`);
      else if (e.uid >= 900001) fail(`[blacklist] ${f}: uid ${e.uid} 落在占位保留段(900001+)`);
      if (typeof e.content === 'string' && /(占位|placeholder|演示用)/i.test(e.content)) {
        fail(`[blacklist] ${f}#${e.uid}: 内容含占位字样`);
      }
    }
    worldBooks.push(book);
  }
} else {
  fail('worldbooks/ 目录不存在');
}

// ═══ 2. data/content/ → 各注册表面 ═══
const contentDir = join(ROOT, 'data', 'content');
const pack = {
  formatVersion: 1,
  packId: 'narrative-official',
  packVersion: VERSION,
  name: '《铭刻录》正式内容包',
  description: '铭刻纪元的世界真源：14 本世界书、目录池、事件委托、agent 默认层与品牌面。',
  exportedAt: new Date().toISOString(),
  worldBooks,
};

function has(name) {
  return existsSync(join(contentDir, `${name}.json`));
}
if (has('catalog')) pack.catalog = { data: stripComments(readJson(join(contentDir, 'catalog.json'))) };
if (has('bloodlines')) pack.bloodlines = { bloodlines: stripComments(readJson(join(contentDir, 'bloodlines.json'))) };
if (has('name-pools')) pack.namePools = { data: stripComments(readJson(join(contentDir, 'name-pools.json'))) };
if (has('random-events')) pack.randomEvents = stripComments(readJson(join(contentDir, 'random-events.json')));
if (has('commissions')) pack.commissions = { defs: stripComments(readJson(join(contentDir, 'commissions.json')).defs ?? []) };
if (has('branding')) pack.branding = stripComments(readJson(join(contentDir, 'branding.json')));
if (has('map-pack')) pack.mapPack = stripComments(readJson(join(contentDir, 'map-pack.json')));
if (has('remote-assets')) pack.remoteAssets = stripComments(readJson(join(contentDir, 'remote-assets.json')));

// ═══ 3. data/defaults/agent-config.json → agentDefaults ═══
const agentCfgPath = join(ROOT, 'data', 'defaults', 'agent-config.json');
if (existsSync(agentCfgPath)) {
  const cfg = stripComments(readJson(agentCfgPath));
  pack.agentDefaults = {
    version: typeof cfg.version === 'number' ? cfg.version : 1,
    agents: cfg.agents ?? {},
  };
} else {
  fail('data/defaults/agent-config.json 不存在（agentDefaults 是契约测试的必测分节）');
}

// ═══ 4. 黑名单全仓文本扫描（世界书之外的分节也扫）═══
const blob = JSON.stringify(pack);
if (/(占位内容|演示用|placeholder-hashes)/i.test(blob)) {
  fail('[blacklist] 包体含占位字样');
}

// ═══ 5. sectionHashes（稳定序列化 sha256；仅展示用）═══
function stable(v) {
  if (Array.isArray(v)) return `[${v.map(stable).join(',')}]`;
  if (v && typeof v === 'object') {
    const ks = Object.keys(v).sort();
    return `{${ks.map((k) => `${JSON.stringify(k)}:${stable(v[k])}`).join(',')}}`;
  }
  return JSON.stringify(v) ?? 'null';
}
const sectionHashes = {};
for (const [k, v] of Object.entries(pack)) {
  if (k === 'sectionHashes') continue;
  sectionHashes[k] = createHash('sha256').update(stable(v)).digest('hex');
}
pack.sectionHashes = sectionHashes;

// ═══ 6. 输出 ═══
if (errors.length > 0) {
  console.error(`[build-pack] 黑名单拦截 ${errors.length} 项，构建终止：`);
  for (const e of errors) console.error('  -', e);
  process.exit(1);
}
mkdirSync(OUT_DIR, { recursive: true });
const outFile = join(OUT_DIR, `narrative-pack-${VERSION}.json`);
writeFileSync(outFile, JSON.stringify(pack, null, 2) + '\n', 'utf8');
const kb = (Buffer.byteLength(JSON.stringify(pack)) / 1024).toFixed(1);
const counts = [];
counts.push(`worldBooks=${worldBooks.length}(${worldBooks.reduce((n, b) => n + (b.entries?.length ?? 0), 0)} 条)`);
for (const k of ['catalog', 'bloodlines', 'namePools', 'randomEvents', 'commissions', 'branding', 'agentDefaults']) {
  if (pack[k]) counts.push(k);
}
console.log(`[build-pack] ${outFile}`);
console.log(`[build-pack] ${kb} KB | ${counts.join(' | ')}`);
