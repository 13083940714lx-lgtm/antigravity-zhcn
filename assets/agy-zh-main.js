'use strict';
/*
 * Antigravity 汉化 · 主进程模块（未翻译文案落盘 + 词库状态查询）
 *
 * 由 dist/main.js 顶部 require('./agy-zh-main.js') 载入。
 * - 渲染进程（preload 里的收集器）通过 IPC 'agy-zh:missing' 上报未命中的英文文案
 * - 这里按去重、限时限量写入 %APPDATA%\Antigravity\agy-zh\missing.jsonl
 * - 只做本地文件写入，不发起任何网络请求
 */
const { app, ipcMain } = require('electron');
const fs = require('fs');
const path = require('path');

const STATE_DIR = path.join(app.getPath('userData'), 'agy-zh');
const OUT_FILE = path.join(STATE_DIR, 'missing.jsonl');
const MAX_BYTES = 4 * 1024 * 1024;
const MAX_ENTRIES = 20000;

const seen = new Set();
let pending = [];
let timer = null;
let total = 0;
let written = 0;

function flushNow() {
  timer = null;
  if (!pending.length) return;
  const payload = pending.join('\n') + '\n';
  pending = [];
  try {
    fs.mkdirSync(STATE_DIR, { recursive: true });
    try {
      const st = fs.statSync(OUT_FILE);
      if (st.size > MAX_BYTES) fs.renameSync(OUT_FILE, OUT_FILE + '.1');
    } catch (_e) { /* first write */ }
    fs.appendFileSync(OUT_FILE, payload, 'utf8');
    written += 1;
  } catch (_e) { /* disk full / permission: silently drop */ }
}

function queue(text) {
  const t = String(text == null ? '' : text).replace(/\s+/g, ' ').trim();
  if (t.length < 2 || t.length > 300) return;
  if (!/[A-Za-z]{2}/.test(t)) return;
  if (/[\u3400-\u9fff\uf900-\ufaff]/.test(t)) return;
  if (seen.has(t)) return;
  seen.add(t);
  if (total >= MAX_ENTRIES) return;
  total += 1;
  pending.push(JSON.stringify({ t: t, at: Date.now() }));
  if (!timer) timer = setTimeout(flushNow, 1500);
}

ipcMain.on('agy-zh:missing', (_event, list) => {
  if (!Array.isArray(list)) return;
  for (const item of list) queue(item);
});

ipcMain.handle('agy-zh:state', () => ({
  missingFile: OUT_FILE,
  collected: total,
  flushed: written,
}));

app.on('will-quit', () => {
  try {
    if (timer) clearTimeout(timer);
    flushNow();
  } catch (_e) { /* ignore */ }
});

module.exports = { STATE_DIR, OUT_FILE };
