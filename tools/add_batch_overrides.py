"""把一批扩展市场（自定义配置）文案合并进 assets/overrides.json。

这些字符串来自 Antigravity 的插件/扩展目录，属于界面文案（不是用户对话），
按整句精确匹配加入 overrides 后，DOM 引擎会直接命中。
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVR = ROOT / "assets" / "overrides.json"

BATCH = {
    # 分类名
    "Scientific Literature": "科学文献",
    "Structural Biology": "结构生物学",
    "Mass Spectrometry": "质谱分析",
    # Google Workspace 套件
    "Connect to Google Workspace, including Docs, Sheets, Slides, Drive, Calendar, and Gmail.":
        "连接 Google Workspace，包括文档、表格、幻灯片、云端硬盘、日历和 Gmail。",
    "Search, read, draft, and send emails in Gmail.": "在 Gmail 中搜索、阅读、起草和发送邮件。",
    # 常见第三方集成
    "Connect Antigravity to your ClickUp workspace — manage tasks, track time, and collaborate with your team without switching context.":
        "把 Antigravity 连接到你的 ClickUp 工作区——无需切换上下文即可管理任务、记录工时并与团队协作。",
    "The AI notepad for meetings. Connect to your meeting history and use your conversation context to get things done.":
        "面向会议的 AI 记事本。连接你的会议历史，利用对话上下文把事情办完。",
    "Build, deploy and manage apps on Cloudflare Workers, storage and AI, with platform skills and the Cloudflare API through one MCP server.":
        "在 Cloudflare Workers、存储与 AI 上构建、部署和管理应用，通过一个 MCP 服务器提供平台技能与 Cloudflare API。",
    "Manage Any.do personal tasks, workspace boards and sections, subtasks, reminders, and connected calendar events from your agent.":
        "在智能体中管理 Any.do 的个人任务、工作区看板与分区、子任务、提醒以及已连接的日历事件。",
    "Query Arize AX projects, traces, datasets, and experiments from Antigravity, with skills for tracing, evals, and prompt optimization.":
        "在 Antigravity 中查询 Arize AX 的项目、追踪、数据集与实验，并提供追踪、评测与提示词优化技能。",
    "Salaries, jobs & career advice. Levels.fyi is your career companion to ensure you get paid fairly and find jobs you'll love.":
        "薪资、职位与职业建议。Levels.fyi 是你的职业伙伴，帮你拿到公平报酬、找到心仪的工作。",
    # 科学类插件
    "Antigravity for science highlights, and an overview of the main science plugins.":
        "Antigravity 科学版亮点，以及主要科学类插件概览。",
    "Search scientific papers, clinical trials, FDA records, and historical texts.":
        "检索科学论文、临床试验、FDA 记录与历史文献。",
    "Agent skills, databases, and interactive viewers for scientific research.":
        "面向科学研究的智能体技能、数据库与交互式查看器。",
    "Search European procurement data and manage your tender pipeline.":
        "检索欧洲采购数据并管理你的招标流程。",
    "RDKit cheminformatics, reaction and property tools, plus ChEMBL and PubChem, to work with molecules, their properties, and bioactivity data.":
        "RDKit 化学信息学、反应与性质工具，配合 ChEMBL 与 PubChem，用于处理分子结构、性质与生物活性数据。",
    "AlphaFold, 3D visualization tools, and protein databases to explore protein structures, sequences, pathways, and drug interactions.":
        "AlphaFold、3D 可视化工具与蛋白质数据库，用于探索蛋白质结构、序列、通路与药物相互作用。",
    "AlphaGenome and major genetics databases to analyze DNA variants, gene regulation, and links between genes and disease.":
        "AlphaGenome 与主流遗传学数据库，用于分析 DNA 变异、基因调控以及基因与疾病的关联。",
    # 第二批：更多插件市场描述（2.35.2 新收集）
    "Build applications and shell workflows with the Gemini Interactions API, Decisions API, Live API, Genie 4 interactive worlds, and Gemini API CLI, including text, image, video, speech, and music generation, managed agents, and real-time multimodal streaming.":
        "使用 Gemini Interactions API、Decisions API、Live API、Genie 4 交互世界和 Gemini API CLI 构建应用与 shell 工作流，涵盖文本、图像、视频、语音与音乐生成，以及托管智能体和实时多模态流式输出。",
    "Robotics skills for any robot: 3D perception, collision-free motion planning, visual servoing, robot bring-up, sim2real, agent iteration, MuJoCo simulation, SimReady 3D asset authoring and physics auditing, and a live MuJoCo Studio 3D web sidecar.":
        "面向各类机器人的机器人技能：3D 感知、无碰撞运动规划、视觉伺服、机器人调试启动、sim2real、智能体迭代、MuJoCo 仿真、SimReady 3D 资产制作与物理校验，以及实时 MuJoCo Studio 3D Web 边车。",
    "Collection of tools for tandem mass spectrometry (MS/MS) analysis, including spectrum preprocessing, GNPS and MoNA spectral library search, SIRIUS formula prediction, and MetFrag and MAGMa fragment annotation.":
        "用于串联质谱（MS/MS）分析的工具集，包括谱图预处理、GNPS 与 MoNA 谱库检索、SIRIUS 分子式预测，以及 MetFrag 与 MAGMa 碎片注释。",
    "Up-to-date documentation lookup. Pull version-specific documentation and code examples directly from source repositories into your coding agent's context.":
        "获取最新文档。把特定版本的文档与代码示例从源码仓库直接拉取到你的编码智能体上下文中。",
    "Add authentication and user management with Clerk. Skills for setup, frameworks, organizations, billing, webhooks, and testing, plus the Clerk MCP server.":
        "使用 Clerk 添加身份认证与用户管理。提供配置、框架、组织、计费、Webhook 与测试相关技能，以及 Clerk MCP 服务器。",
    "Research U.S. case law, statutes, regulations, and court rules. Find authorities, check quotations against opinions, and see how later courts cite a case.":
        "检索美国判例法、法规、行政规章与法院规则。查找权威依据、核对引文与判决是否一致，并查看后续法院如何援引某个案例。",
    "Investigate incidents, check who's on call, and query logs, metrics, traces, errors and RUM in Better Stack. Build dashboards and manage uptime monitors.":
        "在 Better Stack 中排查故障、查看值班人员，并查询日志、指标、追踪、错误与 RUM 数据。构建仪表盘并管理可用性监控。",
    "Turn an idea into a website, dashboard, report, or small web tool you can share. Build it in chat or bring your own work, and publish it with Spacefast.":
        "把一个想法变成可分享的网站、仪表盘、报告或小型 Web 工具。在对话中构建或带入你自己的成果，用 Spacefast 一键发布。",
    "Build, test, and debug Docusign integrations with developer skills for authentication, template-based signing, envelope status, and troubleshooting.":
        "使用开发者技能构建、测试并调试 Docusign 集成，涵盖身份认证、模板化签署、信封状态与故障排查。",
    "Read-only marketing analytics: report spend, conversions, CPA and ROAS across ad platforms, GA4 and Search Console. It never changes your accounts.":
        "只读营销分析：跨广告平台、GA4 与 Search Console 报告花费、转化、CPA 与 ROAS，绝不改动你的账号。",
    "Build, test, and manage n8n workflows and Agents through your instance MCP server. Use official skills for node setup, credentials, and debugging.":
        "通过你的实例 MCP 服务器构建、测试和管理 n8n 工作流与智能体。使用官方技能完成节点配置、凭据与调试。",
}

data = json.loads(OVR.read_text(encoding="utf-8"))
before = len(data)

# 校验：每条原文都应能在收集文件里找到（防止手抄错字导致永远匹配不上）
import os
missing_file = Path(os.environ.get("APPDATA", "")) / "Antigravity" / "agy-zh" / "missing.jsonl"
collected = set()
if missing_file.exists():
    for line in missing_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line:
            try:
                collected.add(json.loads(line).get("t", "").strip())
            except Exception:
                pass
if collected:
    unknown = [k for k in BATCH if k not in collected and k not in data]
    for k in unknown:
        print(f"[warn] 收集文件里没有这条原文，可能抄错：{k[:60]}…")

data.update(BATCH)
OVR.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"overrides: {before} -> {len(data)} (+{len(data) - before})")
