"""打包安装包并发布 GitHub Release。

用法:
    python tools/publish_release.py --version 2.35.1          # 打包 + 建 tag/release + 上传资产
    python tools/publish_release.py --version 2.35.1 --zip-only

需要本机已有 token: %LOCALAPPDATA%\\agy-zh\\.github-token（install 脚本创建 token 时写入）。
"""
import argparse
import json
import os
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SLUG = "13083940714lx-lgtm/antigravity-zhcn"
TOKEN_FILE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "agy-zh" / ".github-token"

INCLUDE = [
    "install.py",
    "install.bat",
    "restore.bat",
    "一键汉化.bat",
    "还原英文.bat",
    "README.md",
    "README_EN.md",
    "LICENSE",
    "assets",
    "vendor",
    "tools",
]
SKIP_PARTS = {".git", "dist", "build", "__pycache__", "docs"}


def build_zip(out: Path, version: str) -> Path:
    root_name = f"antigravity-zhcn-{version}"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDE:
            path = ROOT / item
            if path.is_file():
                zf.write(path, f"{root_name}/{item}")
            elif path.is_dir():
                for f in sorted(path.rglob("*")):
                    if not f.is_file():
                        continue
                    if SKIP_PARTS & set(f.parts) or "__pycache__" in f.parts:
                        continue
                    zf.write(f, f"{root_name}/{f.relative_to(ROOT).as_posix()}")
    return out


def notes(version: str) -> str:
    return f"""## Antigravity 中文汉化 v{version}

适配 **Antigravity {version}（Windows x64）**，词库 **8158 条**，界面级 DOM 热翻译。

### 安装（三选一）

1. **双击**：解压 `agy-zh-installer-{version}.zip`，双击 `一键汉化.bat`
2. **命令行**：`python install.py install --close`
3. **交给 Agent**：把 README「方式一」的提示词整段丢给你电脑上的 AI Agent

### 本版内容

- 三份社区词库去重合并扩到 **8158 条**
- 新增动态文案规则：版本号、删除项目确认（含对话数）、活跃对话数、发送反馈邮箱
- 漏翻自动收集：`%APPDATA%\\Antigravity\\agy-zh\\missing.jsonl` + `tools/report_missing.py`
- 设置页更新卡片指向本仓库；「一键更新」改为打开发布页下载（避免下错包覆盖）
- 官方升级后自动归档旧备份，并按新客户端版本重新打补丁（防版本错配）
- 修正项目设置页「3 active conversations」残留英文

### 已验证

- 客户端：Antigravity 2.35.1 / Electron 44.9.1 / Windows 11 x64
- 覆盖：菜单栏、全部设置分页、快捷键页、模型与用量、项目设置、输入框
- 代码块、编辑器、输入框内容不做翻译

### 还原英文

`python install.py restore --close`

### 鸣谢（词库与引擎来自这些 MIT 项目）

- [ruxiayu/antigravity-zh-cn](https://github.com/ruxiayu/antigravity-zh-cn)
- [yuexps/Antigravity-Hans](https://github.com/yuexps/Antigravity-Hans)
- [nkjDSLcvanv/antigravity-codex-theme](https://github.com/nkjDSLcvanv/antigravity-codex-theme)
"""


def api(method: str, url: str, payload=None, raw: bytes | None = None, ctype: str | None = None):
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    data = raw if raw is not None else (json.dumps(payload).encode("utf-8") if payload is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("User-Agent", "agy-zh-release")
    req.add_header("Accept", "application/vnd.github+json")
    if data is not None:
        req.add_header("Content-Type", ctype or "application/json; charset=utf-8")
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = resp.read().decode("utf-8", "replace")
        return resp.status, (json.loads(body) if body.strip().startswith(("{", "[")) else body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--zip-only", action="store_true")
    parser.add_argument("--update-notes", action="store_true", help="只刷新已有 Release 的说明正文")
    args = parser.parse_args()

    tag = f"v{args.version}"
    if args.update_notes:
        status, rel = api(
            "PATCH",
            f"https://api.github.com/repos/{SLUG}/releases/tags/{tag}",
            {"body": notes(args.version)},
        )
        print("notes updated:", status, rel.get("html_url"))
        return 0

    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    zip_path = build_zip(dist / f"agy-zh-installer-{args.version}.zip", args.version)
    size_mb = round(zip_path.stat().st_size / 1024 / 1024, 2)
    print(f"zip built: {zip_path} ({size_mb} MB)")
    if args.zip_only:
        return 0

    try:
        status, release = api(
            "POST",
            f"https://api.github.com/repos/{SLUG}/releases",
            {
                "tag_name": tag,
                "name": f"v{args.version} · Antigravity 中文汉化",
                "body": notes(args.version),
                "draft": False,
                "prerelease": False,
            },
        )
        print("release created:", status, release.get("html_url"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        if exc.code == 422 and "already_exists" in detail:
            _, release = api("GET", f"https://api.github.com/repos/{SLUG}/releases/tags/{tag}")
            print("release exists:", release.get("html_url"))
        else:
            raise SystemExit(f"create release failed: {exc.code} {detail}")

    upload_url = release["upload_url"].split("{")[0]
    try:
        status, asset = api(
            "POST",
            f"{upload_url}?name={zip_path.name}",
            raw=zip_path.read_bytes(),
            ctype="application/zip",
        )
        print("asset uploaded:", status, asset.get("name"), asset.get("browser_download_url"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        if exc.code == 422 and "already_exists" in detail:
            print("asset already exists, skipped")
        else:
            raise SystemExit(f"upload asset failed: {exc.code} {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
