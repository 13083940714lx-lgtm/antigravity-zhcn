"""列出漏翻收集文件里真正需要翻译的条目（自动过滤品牌名 / 标识符 / 快捷键 / 邮箱）。

用法:  python tools/report_missing.py [missing.jsonl 路径]
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DICT = ROOT / "assets" / "dict.json"
OVR = ROOT / "assets" / "overrides.json"


def state_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return base / "Antigravity" / "agy-zh"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Antigravity" / "agy-zh"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "Antigravity" / "agy-zh"


SKIP_WORDS = {
    "ctrl", "alt", "shift", "enter", "tab", "esc", "escape", "space", "backspace", "delete",
    "home", "end", "pageup", "pagedown", "cmd", "meta", "cmd+enter", "ctrl+enter", "ctrl+shift",
    "ctrl+shift+p", "ctrl+,", "ctrl+/", "ctrl+l", "ctrl+k", "ctrl+c", "ctrl+v", "ctrl+s",
    "antigravity", "google", "gemini", "claude", "gpt", "chrome", "google chrome",
    "google ai pro", "google ai ultra", "google sans", "inter", "jetbrains mono",
}
ID_LIKE = re.compile(r"^[a-z0-9_.\-/]+$")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
UNIT = re.compile(r"^[0-9.,]+\s*(px|%|s|ms|h|d|m|kb|mb|gb|k|M)?$")
HTML_LIKE = re.compile(r"^[<>{}\[\]#*|=+_\-–—·•…\s]+$")


def reason_skip(text: str):
    s = text.strip()
    low = s.lower()
    if not s:
        return "empty"
    if re.search(r"[\u3400-\u9fff]", s):
        return "has-cjk"
    if UNIT.match(s) or HTML_LIKE.match(s):
        return "unit/symbol"
    if EMAIL.search(s) and len(s.split()) <= 3:
        return "email"
    if low in SKIP_WORDS:
        return "brand/key"
    if ID_LIKE.match(s) and ("_" in s or "/" in s or "." in s):
        return "identifier"
    if ID_LIKE.match(s) and len(s) <= 12:
        return "lower-word"
    return None


def main():
    missing = Path(sys.argv[1]) if len(sys.argv) > 1 else state_dir() / "missing.jsonl"
    if not missing.exists():
        print(f"no missing file: {missing}")
        print("先正常使用 Antigravity 把各页面点一遍，收集器会自动生成该文件。")
        return

    dictionary = json.loads(DICT.read_text(encoding="utf-8"))
    if OVR.exists():
        dictionary.update(json.loads(OVR.read_text(encoding="utf-8")))
    keys = {str(k).strip() for k in dictionary}
    lower_keys = {k.lower() for k in keys}

    seen, got = [], set()
    for line in missing.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            t = json.loads(line).get("t", "")
        except Exception:
            continue
        if t and t not in got:
            got.add(t)
            seen.append(t)

    untranslated, skipped = [], []
    for t in seen:
        s = t.strip()
        if s in keys or s.lower() in lower_keys:
            skipped.append(("dict-hit", s))
            continue
        reason = reason_skip(s)
        (skipped.append((reason, s)) if reason else untranslated.append(s))

    print(f"collected: {len(seen)}   needs translation: {len(untranslated)}")
    for t in sorted(untranslated, key=len, reverse=True):
        print("  T:", t)
    if skipped:
        print("\nskipped:")
        for reason, s in skipped[:40]:
            print(f"  [{reason}] {s}")


if __name__ == "__main__":
    main()
