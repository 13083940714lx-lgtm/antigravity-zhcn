import json
import os
import urllib.request
from pathlib import Path

TOKEN_FILE = Path(os.environ["LOCALAPPDATA"]) / "agy-zh" / ".github-token"
TOKEN = TOKEN_FILE.read_text(encoding="utf-8").strip()
SLUG = "13083940714lx-lgtm/antigravity-zhcn"

DESC = "Google Antigravity 桌面版简体中文汉化：合并社区词库 8158 条 · DOM 热翻译引擎 · 漏翻自动收集 · 一键安装与无损还原"
TOPICS = ["antigravity", "localization", "chinese", "zh-cn", "i18n", "electron", "dom-translation"]


def call(method, url, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {TOKEN}")
    req.add_header("User-Agent", "agy-zh-meta")
    req.add_header("Accept", "application/vnd.github+json")
    if data:
        req.add_header("Content-Type", "application/json; charset=utf-8")
    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.status, resp.read().decode("utf-8", "replace")


status, body = call(
    "PATCH",
    f"https://api.github.com/repos/{SLUG}",
    {"description": DESC, "homepage": f"https://github.com/{SLUG}"},
)
info = json.loads(body)
print("repo patched:", status, "|", info.get("description"))

status, body = call(
    "PUT",
    f"https://api.github.com/repos/{SLUG}/topics",
    {"names": TOPICS},
)
print("topics set:", status, "|", json.loads(body).get("names"))
