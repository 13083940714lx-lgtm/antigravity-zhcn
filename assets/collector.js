/* ===== Antigravity 汉化 · 漏翻文案收集器（渲染进程侧） =====
 * 在 DOM 翻译引擎之后注入。为避免把"引擎还没轮到翻译"的文案误报成漏翻，
 * 这里采用二次确认：同一段英文连续两轮扫描仍然存在才上报。
 *
 * 上报路径：preload -> IPC 'agy-zh:missing' -> 主进程 agy-zh-main.js
 *          -> %APPDATA%\Antigravity\agy-zh\missing.jsonl
 * 只读 DOM + 本地写文件，不联网。
 */
(function () {
  'use strict';
  if (typeof window === 'undefined' || typeof document === 'undefined') return;
  if (window.__agyZhCollectorInstalled) return;

  var send = null;
  try {
    var electron = require('electron');
    if (electron && electron.ipcRenderer && typeof electron.ipcRenderer.send === 'function') {
      send = electron.ipcRenderer.send.bind(electron.ipcRenderer);
    }
  } catch (_e) {
    send = null;
  }
  if (!send) return;
  window.__agyZhCollectorInstalled = true;

  var SKIP_TAGS = {
    SCRIPT: 1, STYLE: 1, CODE: 1, PRE: 1, KBD: 1, SAMP: 1,
    TEXTAREA: 1, INPUT: 1, SVG: 1, CANVAS: 1, OPTION: 1, SELECT: 1
  };
  var SKIP_SELECTOR = '[contenteditable="true"],[contenteditable=""],[contenteditable="plaintext-only"],' +
    '.monaco-editor,.monaco-diff-editor,.cm-editor,.cm-content,[data-agy-zh-ignore],' +
    '[translate="no"],.notranslate';
  var CJK = /[\u3400-\u9fff\uf900-\ufaff]/;
  var LETTERS = /[A-Za-z]{2}/;

  var pending = new Map();   // text -> 连续命中轮次
  var reported = new Set();  // 已上报
  var timer = null;

  function shouldSkip(el) {
    if (!el || !el.tagName) return true;
    if (SKIP_TAGS[el.tagName]) return true;
    if (el.isContentEditable) return true;
    try {
      if (el.closest(SKIP_SELECTOR)) return true;
    } catch (_e) { /* ignore */ }
    return false;
  }

  function collectCurrent() {
    var current = new Set();
    var body = document.body;
    if (!body) return current;
    var walker;
    try {
      walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, null);
    } catch (_e) {
      return current;
    }
    var node;
    var guard = 0;
    while ((node = walker.nextNode()) && guard < 60000) {
      guard++;
      var text = (node.nodeValue || '').trim();
      if (text.length < 2 || text.length > 300) continue;
      if (!LETTERS.test(text)) continue;
      if (CJK.test(text)) continue;
      if (shouldSkip(node.parentElement)) continue;
      current.add(text);
    }
    return current;
  }

  function flush(list) {
    if (!list.length) return;
    try { send('agy-zh:missing', list); } catch (_e) { /* main may be gone */ }
  }

  function scan() {
    timer = null;
    var current = collectCurrent();
    var confirmed = [];

    current.forEach(function (text) {
      if (reported.has(text)) return;
      var hits = (pending.get(text) || 0) + 1;
      pending.set(text, hits);
      if (hits >= 2) {
        reported.add(text);
        confirmed.push(text);
      }
    });

    // 已经不在 DOM 里的（多半已被翻译或切走了）清掉，避免内存增长
    pending.forEach(function (_v, text) {
      if (!current.has(text)) pending.delete(text);
    });

    if (confirmed.length) flush(confirmed.slice(0, 200));
  }

  function schedule() {
    if (timer) return;
    timer = setTimeout(scan, 2500);
  }

  function start() {
    schedule();
    try {
      var obs = new MutationObserver(schedule);
      obs.observe(document.documentElement, { childList: true, subtree: true, characterData: true });
      window.__agyZhCollectorObserver = obs;
    } catch (_e) { /* ignore */ }
    [5000, 12000, 25000, 45000].forEach(function (ms) { setTimeout(schedule, ms); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
