#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity 中文汉化安装器（Windows / macOS / Linux）

用法:
    python install.py status
    python install.py install [--close] [--app-dir DIR] [--asar FILE]
    python install.py build --out OUT.asar
    python install.py restore [--close]

特性:
    * 备份原始 app.asar（app.asar.original.bak），可一键无损还原
    * 词典 = 社区合并词库(8123) + 本仓库 overrides.json
    * DOM 翻译引擎（含 Shadow DOM / MutationObserver / 动态时间与配额文案）
    * 主进程菜单 / 托盘 / 更新器文本翻译
    * 漏翻文案自动收集：%APPDATA%\\Antigravity\\agy-zh\\missing.jsonl

词库版权: ruxiayu/antigravity-zh-cn (MIT)、yuexps/Antigravity-Hans (MIT)、
nkjDSLcvanv/antigravity-codex-theme (MIT) 的社区词条，本仓库做合并与增补。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# PyInstaller onefile 运行时资源被解到临时目录，用 _MEIPASS 定位
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", str(ROOT)))
ASSETS = BUNDLE_ROOT / "assets"
VENDOR = BUNDLE_ROOT / "vendor"
sys.path.insert(0, str(VENDOR))

from asar_codec import (  # noqa: E402
    collect_unpacked_paths,
    compute_integrity,
    extract_asar,
    pack_asar,
    read_header,
    read_text_entry,
)
from localize import (  # noqa: E402
    BACKUP_SUFFIX,
    discover_installation,
    is_asar_localized,
    read_asar_version,
    verify_js_syntax,
)
from patches_main import PRELOAD_MARKERS, apply_all_patches  # noqa: E402

UNPACK_DIRS = ("node_modules/chrome-devtools-mcp",)
MAIN_MODULE = "agy-zh-main.js"

# 设置页「中文汉化与更新」卡片、菜单里的检查更新都指向这个仓库
GITHUB_SLUG = "13083940714lx-lgtm/antigravity-zhcn"
GITHUB_REPO = f"https://github.com/{GITHUB_SLUG}"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_SLUG}"
GITHUB_API = f"{GITHUB_API_BASE}/releases/latest"

# 上游项目里硬编码的仓库地址，构建时统一重定向到 GITHUB_REPO
UPSTREAM_REPO = "https://github.com/ruxiayu/antigravity-zh-cn"
UPSTREAM_API = "https://api.github.com/repos/ruxiayu/antigravity-zh-cn"
ENGINE_ANCHOR = "if (!trimmed || !/[a-zA-Z]/.test(trimmed)) return str;"
ENGINE_EXTRA = """
    // ===== agy-zh 增强规则：动态版本号 =====
    const __agyVerHit = /^Version\\s+v?([0-9][0-9A-Za-z.\\-]*)$/.exec(trimmed);
    if (__agyVerHit) return replaceTrimmed(str, trimmed, '版本 ' + __agyVerHit[1]);

    // ===== agy-zh 增强规则：项目删除确认（含项目名与对话数） =====
    const __agyDelProj = /^Permanently deletes\\s+(.+?)\\s+including\\s+([0-9]+)\\s+active conversations?\\.?$/i.exec(trimmed);
    if (__agyDelProj) {
      return replaceTrimmed(str, trimmed, '永久删除 ' + __agyDelProj[1] + '，包括 ' + __agyDelProj[2] + ' 个活跃对话');
    }

    // ===== agy-zh 增强规则：N active conversations =====
    const __agyActiveConv = /^([0-9]+)\\s+active conversations?\\.?$/i.exec(trimmed);
    if (__agyActiveConv) return replaceTrimmed(str, trimmed, __agyActiveConv[1] + ' 个活跃对话');

    // ===== agy-zh 增强规则：发送反馈（含邮箱） =====
    const __agyFeedback = /^Send feedback as\\s+(\\S+@\\S+)$/i.exec(trimmed);
    if (__agyFeedback) return replaceTrimmed(str, trimmed, '以 ' + __agyFeedback[1] + ' 身份发送反馈');

    // ===== agy-zh 增强规则：扩展市场「See N more」 =====
    const __agySeeMore = /^See\\s+([0-9]+)\\s+more$/i.exec(trimmed);
    if (__agySeeMore) return replaceTrimmed(str, trimmed, '查看另外 ' + __agySeeMore[1] + ' 个');

    // ===== agy-zh 增强规则：模型提示「<描述>. Leaving on Nov 30.」 =====
    const __agyLeavingOn = /^([\\s\\S]+?)[.\\s]*Leaving on\\s+([A-Za-z]{3,9}\\.?\\s+[0-9]{1,2}(?:,?\\s*[0-9]{4})?)\\.?$/i.exec(trimmed);
    if (__agyLeavingOn) {
      const headRaw = __agyLeavingOn[1].trim().replace(/[.\\s]+$/, '');
      const headCn = exactMap.get(headRaw) || lowerMap.get(headRaw.toLowerCase()) || headRaw;
      const whenRaw = __agyLeavingOn[2].trim();
      const whenCn = String(formatEnDateStr(whenRaw) || whenRaw).replace(/\\s+/g, '');
      return replaceTrimmed(str, trimmed, headCn + ' 将于 ' + whenCn + ' 下线');
    }
"""


# ---------------------------------------------------------------- 词库

def load_dictionary() -> dict[str, str]:
    base_path = ASSETS / "dict.json"
    dict_data: dict[str, str] = json.loads(base_path.read_text(encoding="utf-8"))
    overrides_path = ASSETS / "overrides.json"
    if overrides_path.exists():
        overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
        dict_data.update({str(k).strip(): str(v) for k, v in overrides.items()})
    return dict_data


def load_engine_template() -> str:
    text = (ASSETS / "engine_preload.js").read_text(encoding="utf-8")
    if "agy-zh 增强规则" in text:
        return text
    if ENGINE_ANCHOR not in text:
        raise SystemExit("引擎模板结构变化：找不到插入锚点，请更新 assets/engine_preload.js")
    return text.replace(ENGINE_ANCHOR, ENGINE_ANCHOR + ENGINE_EXTRA, 1)


# ---------------------------------------------------------------- 补丁

def patch_collector(dist_dir: Path) -> None:
    """在 dist/preload.js 末尾追加漏翻收集器。"""
    collector = (ASSETS / "collector.js").read_text(encoding="utf-8")
    target = dist_dir / "preload.js"
    text = target.read_text(encoding="utf-8")
    marker = "Antigravity 汉化 · 漏翻文案收集器"
    idx = text.find(marker)
    if idx != -1:
        text = text[:idx].rstrip()
    target.write_text(text + "\n\n" + collector, encoding="utf-8")


def patch_main_module(dist_dir: Path) -> str:
    """把 agy-zh-main.js 放进 dist/ 并在 main.js 顶部 require 它。"""
    module_src = (ASSETS / MAIN_MODULE).read_text(encoding="utf-8")
    (dist_dir / MAIN_MODULE).write_text(module_src, encoding="utf-8")

    main_path = dist_dir / "main.js"
    text = main_path.read_text(encoding="utf-8")
    marker = "require('./agy-zh-main.js')"
    if marker in text:
        return MAIN_MODULE
    anchor = "'use strict';\n"
    if anchor not in text:
        anchor = '"use strict";\n'
    if anchor not in text:
        raise SystemExit("main.js 结构变化：找不到 'use strict' 锚点")
    inject = anchor + marker + ";\n"
    main_path.write_text(text.replace(anchor, inject, 1), encoding="utf-8")
    return MAIN_MODULE


def retarget_upstream_links(dist_dir: Path) -> list[str]:
    """把上游硬编码的仓库/API 地址重定向到本项目仓库（设置页更新卡片用）。"""
    touched: list[str] = []
    for path in sorted(dist_dir.rglob("*.js")):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if UPSTREAM_API not in text and UPSTREAM_REPO not in text:
            continue
        new_text = text.replace(UPSTREAM_API, GITHUB_API_BASE).replace(UPSTREAM_REPO, GITHUB_REPO)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            touched.append(str(path.relative_to(dist_dir)).replace("\\", "/"))
    return touched


def sync_patch_version(dist_dir: Path, app_ver: str) -> list[str]:
    """让补丁展示版本跟随实际上被汉化的客户端版本（上游常量里写死的是 2.34.0）。"""
    pat_meta = re.compile(r'("patchVersion"\s*:\s*")([^"]*)(")')
    pat_var = re.compile(r'(const __agyZhPatchVer = ")([^"]*)(")')
    touched: list[str] = []
    for path in sorted(dist_dir.rglob("*.js")):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new_text = pat_meta.sub(lambda m: m.group(1) + app_ver + m.group(3), text)
        new_text = pat_var.sub(lambda m: m.group(1) + app_ver + m.group(3), new_text)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            touched.append(str(path.relative_to(dist_dir)).replace("\\", "/"))
    return touched


def patch_all(
    extracted_dir: Path,
    engine_template: str,
    dictionary: dict[str, str],
    app_ver: str,
    block_auto_update: bool = False,
) -> list[str]:
    touched = apply_all_patches(
        extracted_dir,
        engine_template=engine_template,
        dictionary=dictionary,
        block_auto_update=block_auto_update,
        is_test_preview=False,
    )
    dist_dir = extracted_dir / "dist"
    patch_collector(dist_dir)
    main_module = patch_main_module(dist_dir)
    touched += retarget_upstream_links(dist_dir)
    touched += sync_patch_version(dist_dir, app_ver)
    return touched + [main_module]


# ---------------------------------------------------------------- 构建

def build_localized(
    source_asar: Path,
    out_asar: Path,
    workdir: Path | None = None,
    block_auto_update: bool = False,
) -> dict:
    dictionary = load_dictionary()
    engine_template = load_engine_template()
    header, _base, _unpacked = read_header(source_asar)
    unpacked_files = collect_unpacked_paths(header)
    app_ver = read_asar_version(source_asar)

    tmp_path = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="agy_zh_"))
    tmp_path.mkdir(parents=True, exist_ok=True)
    extracted = tmp_path / "extracted"
    packed = tmp_path / "app.asar"
    if extracted.exists():
        shutil.rmtree(extracted)
    if packed.exists():
        packed.unlink()
    if True:
        print(f"[1/5] 解包原版 asar (v{app_ver}, {len(unpacked_files)} 个 unpacked 文件)…")
        extract_asar(source_asar, extracted)

        print(f"[2/5] 打补丁（词典 {len(dictionary)} 条）…")
        touched = patch_all(extracted, engine_template, dictionary, app_ver, block_auto_update)

        print(f"[3/5] 校验 {len(touched)} 个 JS 模块语法…")
        if shutil.which("node"):
            verify_js_syntax(extracted, touched)
        else:
            print("      未找到 Node.js，跳过语法校验（不影响安装结果）")

        print("[4/5] 重新打包 asar…")
        pack_asar(extracted, packed, unpack_dirs=UNPACK_DIRS, unpack_files=unpacked_files)
        _h, _b, _count = read_header(packed)
        new_unpacked = collect_unpacked_paths(_h)
        if unpacked_files and new_unpacked != unpacked_files:
            only_old = sorted(unpacked_files - new_unpacked)
            only_new = sorted(new_unpacked - unpacked_files)
            print("  ! unpacked 集合差异：")
            for p in only_old[:10]:
                print(f"      仅原版: {p}")
            for p in only_new[:10]:
                print(f"      仅新版: {p}")
            raise SystemExit(
                f"unpacked 文件集合不一致: 原 {len(unpacked_files)} / 新 {len(new_unpacked)}"
            )

        out_asar.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(packed, out_asar)
        packed_unpacked = packed.with_name(packed.name + ".unpacked")
        if packed_unpacked.exists():
            shutil.copytree(
                packed_unpacked,
                out_asar.with_name(out_asar.name + ".unpacked"),
                symlinks=True,
                dirs_exist_ok=True,
            )

    print("[5/5] 完成")
    return {
        "version": app_ver,
        "dict_entries": len(dictionary),
        "md5": compute_integrity(out_asar)["hash"][:16],
        "path": str(out_asar),
    }


# ---------------------------------------------------------------- 进程

def antigravity_running() -> bool:
    try:
        if os.name == "nt":
            out = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Antigravity.exe", "/NH"],
                capture_output=True, text=True, errors="ignore", timeout=15,
            ).stdout
            return "Antigravity.exe" in out
        out = subprocess.run(["pgrep", "-f", "Antigravity"], capture_output=True, text=True, timeout=10).stdout
        return bool(out.strip())
    except Exception:
        return False


def close_antigravity() -> None:
    print("[关闭] 正在退出 Antigravity…")
    if os.name == "nt":
        subprocess.run(["taskkill", "/IM", "Antigravity.exe", "/F"], capture_output=True, timeout=30)
    else:
        subprocess.run(["pkill", "-f", "Antigravity"], capture_output=True, timeout=30)


# ---------------------------------------------------------------- 命令

def deploy(built_asar: Path, built_unpacked: Path | None, target_asar: Path) -> None:
    target_unpacked = target_asar.with_name(target_asar.name + ".unpacked")
    try:
        shutil.copy2(built_asar, target_asar)
    except PermissionError:
        raise SystemExit("写入 app.asar 失败：请完全退出 Antigravity 后重试（或加 --close）。")
    if built_unpacked and built_unpacked.exists():
        shutil.copytree(built_unpacked, target_unpacked, symlinks=True, dirs_exist_ok=True)


def cmd_install(args) -> int:
    target_asar, exe = discover_installation(args.app_dir, args.asar)
    print(f"安装目录: {target_asar.parent}")
    if antigravity_running():
        if args.close:
            close_antigravity()
        else:
            print("Antigravity 正在运行，请先完全退出（或加 --close 自动关闭）。")
            return 2

    backup = target_asar.with_name(target_asar.name + BACKUP_SUFFIX)
    target_ver = read_asar_version(target_asar)
    target_localized = is_asar_localized(target_asar)

    if not target_localized:
        # 官方更新会把 app.asar 换成新版本：旧备份不能再当补丁源，否则版本错配
        if backup.exists():
            backup_ver = read_asar_version(backup)
            if backup_ver != target_ver:
                archived = backup.with_name(f"{backup.name}.{backup_ver}")
                shutil.move(str(backup), str(archived))
                print(f"[备份] 客户端已从 v{backup_ver} 升级到 v{target_ver}，旧备份另存为 {archived.name}")
        if not backup.exists():
            print(f"[备份] 保存当前原版 asar -> {backup.name} (v{target_ver})")
            shutil.copy2(target_asar, backup)
        source = backup
        print(f"[源] 使用当前版本原始备份 {backup.name} (v{read_asar_version(backup)})")
    elif backup.exists() and not is_asar_localized(backup):
        if read_asar_version(backup) == target_ver:
            source = backup
            print(f"[源] 使用原始备份 {backup.name} (v{read_asar_version(backup)})")
        else:
            source = target_asar
            print("[源] 备份版本与当前客户端不一致，改为在已汉化文件上幂等重打补丁")
    else:
        source = target_asar
        print("[源] 目标已含汉化补丁，直接在其上重新打补丁（幂等）")

    out = Path(tempfile.gettempdir()) / "agy-zh-app.asar"
    info = build_localized(source, out, block_auto_update=getattr(args, "block_auto_update", False))
    deploy(out, out.with_name(out.name + ".unpacked"), target_asar)
    print(
        "\n汉化完成！\n"
        f"  版本      : {info['version']}\n"
        f"  词条      : {info['dict_entries']}\n"
        f"  词典指纹  : {info['md5']}\n"
        f"  可执行文件: {exe}\n"
        "  还原命令  : python install.py restore\n"
        "  漏翻清单  : %APPDATA%\\Antigravity\\agy-zh\\missing.jsonl"
    )
    return 0


def cmd_restore(args) -> int:
    target_asar, _exe = discover_installation(args.app_dir, args.asar)
    backup = target_asar.with_name(target_asar.name + BACKUP_SUFFIX)
    if not backup.exists():
        print("未找到原始备份，无法还原。")
        return 2
    if antigravity_running():
        if args.close:
            close_antigravity()
        else:
            print("Antigravity 正在运行，请先完全退出（或加 --close 自动关闭）。")
            return 2
    shutil.copy2(backup, target_asar)
    print(f"已还原官方原版: {target_asar}")
    return 0


def state_dir() -> Path:
    """漏翻收集文件的目录（与 Electron 的 app.getPath('userData') 对齐）。"""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return base / "Antigravity" / "agy-zh"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Antigravity" / "agy-zh"
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "Antigravity" / "agy-zh"


def cmd_status(args) -> int:
    target_asar, exe = discover_installation(args.app_dir, args.asar)
    backup = target_asar.with_name(target_asar.name + BACKUP_SUFFIX)
    dictionary = load_dictionary()
    missing_file = state_dir() / "missing.jsonl"
    print(f"安装 asar    : {target_asar}")
    print(f"可执行文件   : {exe}")
    print(f"应用版本     : {read_asar_version(target_asar)}")
    print(f"已汉化       : {'是' if is_asar_localized(target_asar) else '否（官方原版）'}")
    print(f"原始备份     : {'存在' if backup.exists() else '无'}")
    print(f"词典词条     : {len(dictionary)}")
    print(f"仓库链接     : {GITHUB_REPO}")
    print(f"进程运行中   : {'是' if antigravity_running() else '否'}")
    if missing_file.exists():
        n = sum(1 for _ in missing_file.open("r", encoding="utf-8", errors="ignore"))
        print(f"漏翻收集     : {missing_file} ({n} 行)")
    else:
        print(f"漏翻收集     : 尚未生成 ({missing_file})")
    return 0


def cmd_build(args) -> int:
    target_asar, _exe = discover_installation(args.app_dir, args.asar)
    backup = target_asar.with_name(target_asar.name + BACKUP_SUFFIX)
    source = backup if backup.exists() and not is_asar_localized(backup) else target_asar
    info = build_localized(source, Path(args.out), block_auto_update=getattr(args, "block_auto_update", False))
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


def ensure_node() -> None:
    """让脚本在没有配置 PATH 的机器上也能找到 node（校验 JS 语法用）。"""
    if shutil.which("node"):
        return
    candidates = [
        Path(os.environ.get("PROGRAMFILES", "")) / "nodejs" / "node.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "nodejs" / "node.exe",
    ]
    candidates.extend(sorted((Path.home() / ".dsh" / "dsh-runtimes").glob("*/dependencies/node/bin/node.exe")))
    for exe in candidates:
        if exe.is_file():
            os.environ["PATH"] = str(exe.parent) + os.pathsep + os.environ.get("PATH", "")
            return


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Antigravity 中文汉化安装器")
    parser.add_argument("--app-dir", default=None, help="Antigravity 安装目录")
    parser.add_argument("--asar", default=None, help="直接指定 app.asar 路径")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # 子命令也能直接带 --app-dir / --asar（应用内更新调用的是 `install --app-dir ...`）
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--app-dir", default=None, help="Antigravity 安装目录")
    common.add_argument("--asar", default=None, help="直接指定 app.asar 路径")

    p_install = sub.add_parser("install", parents=[common], help="安装/更新汉化")
    p_install.add_argument("--close", action="store_true", help="自动关闭正在运行的 Antigravity")
    p_install.add_argument("--block-auto-update", action="store_true", help="禁止后台静默下载官方更新")
    p_install.set_defaults(func=cmd_install)

    p_restore = sub.add_parser("restore", parents=[common], help="还原官方原版")
    p_restore.add_argument("--close", action="store_true")
    p_restore.set_defaults(func=cmd_restore)

    p_status = sub.add_parser("status", parents=[common], help="查看汉化状态")
    p_status.set_defaults(func=cmd_status)

    p_build = sub.add_parser("build", parents=[common], help="只构建，不安装")
    p_build.add_argument("--out", required=True, help="输出 asar 路径")
    p_build.add_argument("--block-auto-update", action="store_true")
    p_build.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    ensure_node()
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
