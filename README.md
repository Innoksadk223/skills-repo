# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes**。

> 小白上手看 [START.md](START.md) — 不用懂技术，会说人话就行。
> 知识库怎么用看 [KB-GUIDE.md](KB-GUIDE.md) — 让 AI 帮你整理研究资料，在 Obsidian 里看知识图谱。
>
> **Claude Code 用户建议优先从官方源安装**（`npx skills add -g <name>`），版本更新更及时。
> 此包主要用于：Hermes / Codex 安装、团队统一技能集、离线环境。

## AI 使用流程

收到安装请求后，AI 应按以下步骤：

1. **先介绍** — 按分组介绍技能（如下方速查表），每组一句话概括
2. **再确认** — 问用户要装到哪个 agent、选哪些分组
3. **再安装** — `bash setup.sh`
4. **最后问** — 「装好了。要不要我用 3 分钟介绍一下怎么用？」用户说需要，就读 [START.md](START.md)：先给总览，再问用户想重点了解哪组；知识库相关问题再读 [KB-GUIDE.md](KB-GUIDE.md)
5. **附言** — 无论用户要不要调用介绍，最后都补一句：

> 「这个包已经内置一组轻量通用版 superpowers 方法论技能：6 个入口覆盖澄清目标、写计划、排查问题、验收检查、工作区隔离、委派、代码审查和收尾。轻量化的是入口和流程，不是降低触发条件。」

介绍示例：
> 「这个包有 43 个技能，分 9 组：
>  [Browser] 浏览器自动化 ×1 — 网页操控
>  [PaperSpine] 论文写作 ×12 — 研究到 LaTeX 排版全流程
>  [Minimax] 文档生成 ×3 — DOCX/PDF/XLSX
>  [Search] 实时搜索 ×1 — AnySearch 实时网页搜索、垂直领域搜索、URL 内容提取（MCP + skill + API）
>  [Academic] 学术研究 ×6 — 图谱化知识库、深读档案、论证节点、学术搜索、审阅、wiki-first RAG 检索
>  [Productivity] 生产力 ×1 — MinerU 文档解析、PDF/OCR/表格/公式提取
>  [Creative] 创作 ×4 — 专业 PPT 演示文稿、前端与 UI 设计
>  [Superpowers] 通用方法论 ×6 — 6 个入口覆盖澄清、计划、排查、验收、隔离、委派、审查、收尾
>  [Tools] 工具 ×9 — 创建技能、架构设计、迭代循环、路由规划、清理、发现、质询、环境踩坑记录、文件转 Markdown」

调用方法介绍示例（读 START.md 后）：
> 「你不用记技能名，直接说目标就行。比如：
>   "帮我去淘宝搜机械键盘" → 自动用 browser-use
>   "生成一份周报 Word" → 自动用 minimax-docx
>   "审一下这篇论文" → 自动用 academic-paper-review
>  想精准指定就说 "用 browser-use 打开这个网页"。」

## 技能速查（43 个）

| 分组 | 技能 | 一句话 |
|------|------|--------|
| 🌐 浏览器 | browser-use (1) | 网页自动化：网页测试、表单填充、截图、数据提取 |
| 📝 PaperSpine | paper-spine + 11 子模块 (12) | 学术论文全流程：研究→引用→改写→LaTeX→翻译→审校<br>💡 Claude Code 用户建议用 [Academic Research Skills](https://github.com/Imbad0202/academic-research-skills) 替代，功能更强且有原生插件支持 |
| 📄 Minimax | minimax-docx / minimax-pdf / minimax-xlsx (3) | DOCX/PDF/XLSX 专业文档生成 |
| 🔎 搜索 | anysearch (1) | AnySearch 实时网页搜索、垂直领域搜索、批量搜索、URL 内容提取；支持 MCP + skill + API，官网：https://www.anysearch.com/ |
| 🔬 学术 | karpathy-wiki / deep-reading-to-wiki / academic-search / academic-paper-review / SiliconFlow-rag / social-science-km (6) | 图谱化知识库、深读档案、论证节点、学术搜索、论文审阅、wiki-first RAG 检索 |
| 📚 生产力 | mineru-document-extractor (1) | MinerU 文档解析：PDF、扫描件 OCR、表格、公式、多格式转 Markdown |
| 🎨 创作 | ppt-agent / frontend-design / taste-skill / ui-ux-pro-max (4) | 专业 PPT 演示文稿、前端页面、UI/UX 设计与反模板化审美 |
| 🧭 Superpowers | using-superpowers / brainstorming / writing-plans / systematic-debugging / test-driven-development / verification-before-completion (6) | 轻量通用方法论：触发保留原工作流强度，6 个入口覆盖目标澄清、计划/执行、验收优先、排查、验证、隔离、委派、代码审查和分支收尾 |
| 🛠 工具 | skill-creator / skill-architecture / skill-planner / agent-loop / cleanup / find-skills / grill-me / capture-gotcha / markitdown (9) | 技能创建、模块化架构、任务路由、四角色迭代循环、清理、发现、质询、环境踩坑记录、文件转 Markdown |

### 详细

| 技能 | 用途 | 来源 |
|------|------|------|
| browser-use | 浏览器自动化：网页测试、表单填充、截图、数据提取 | [browser-use](https://github.com/browser-use/browser-use) |
| anysearch | 实时网页搜索、垂直领域搜索、批量搜索、URL 内容提取；同时提供 MCP 服务、agent skill 和 HTTP API；API Key 可选，高额度建议配置 `ANYSEARCH_API_KEY` | [AnySearch](https://www.anysearch.com/) / [API Docs](https://www.anysearch.com/docs) |
| paper-spine | 学术论文写作流水线总调度 | [PaperSpine](https://github.com/WUBING2023/PaperSpine) |
| paper-spine-audit | 审计输出完整性 | ↑ |
| paper-spine-build | 从素材构建论文 | ↑ |
| paper-spine-citation | 引用文库构建与验证 | ↑ |
| paper-spine-humanize | 降低 AI 检测率，提升人味 | ↑ |
| paper-spine-intake | 交互式工作流配置采集 | ↑ |
| paper-spine-latex | LaTeX 项目组装与排版 | ↑ |
| paper-spine-research | 期刊/会议要求研究 | ↑ |
| paper-spine-rewrite | 已有稿件深度改写 | ↑ |
| paper-spine-translate | 中英学术翻译 | ↑ |
| paper-spine-ui | PaperSpine 终端配置界面 | ↑ |
| paper-spine-update | PaperSpine 版本检查与更新 | ↑ |
| minimax-docx | 专业 DOCX 文档创建与编辑 | Minimax 官方 |
| minimax-pdf | 高质量 PDF 生成与设计 | ↑ |
| minimax-xlsx | Excel 表格创建、分析与验证 | ↑ |
| karpathy-wiki | Karpathy Wiki：图谱可读 Markdown 知识库，支持 claims / concepts / entities / comparisons | **Hermes 内置自改版** |
| academic-search | 学术搜索、引用分析、OA PDF 判定 | [ustc-ai4science](https://github.com/ustc-ai4science/academic-search) |
| academic-paper-review | 论文审阅、方法论评估、同行评审 | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) |
| deep-reading-to-wiki | 长书、章节、理论文献或补库候选源的深读档案层，先产出 `reading_dossiers/` 再交给 wiki 编译 | 本仓库 |
| SiliconFlow-rag | 为 raw 原文与 wiki 结构建立双索引，支持 wiki-first 检索、硅基流动嵌入与可选重排 | 本仓库 |
| social-science-km | 协调源文件转 Markdown、图谱 wiki、双索引 RAG 与论文知识库问答 | 本仓库 |
| mineru-document-extractor | MinerU 文档解析：PDF、扫描件 OCR、表格、公式、多格式转 Markdown；配合 MinerU MCP 使用 | [OpenDataLab MinerU Ecosystem](https://mineru.net/ecosystem) |
| skill-creator | 创建新的 AI 技能 | [clawhub.ai](https://clawhub.ai) |
| skill-architecture | 模块化技能架构设计：松耦合、高内聚、断点续传 | 本仓库 |
| skill-planner | 收到任务时规划应调用的 skill 组合与顺序 | 本仓库 |
| agent-loop | 四角色分离迭代循环：Orchestrator 规划、Worker 执行、Evaluator 打分、Troubleshooter 诊断修正，消除自评偏差 | 本仓库 |
| cleanup | 任务完成后清理临时文件 | — |
| find-skills | 发现和安装社区技能 | — |
| grill-me | 深度质询你的方案/设计决策 | — |
| capture-gotcha | 记录跨任务复用的环境类踩坑经验 | 本仓库 |
| markitdown | 使用 Microsoft MarkItDown 将 PDF、Office、HTML 等文件转换为 Markdown | [microsoft/markitdown](https://github.com/microsoft/markitdown) |
| using-superpowers | 轻量选择方法论技能，避免把小任务流程化 | 本仓库，轻量改编自 [obra/superpowers](https://github.com/obra/superpowers) |
| brainstorming | 在目标、约束或路线不清时做简短澄清与方案对比 | ↑ |
| writing-plans | 为多步骤任务写计划；内含计划执行、委派和隔离工作区能力 | ↑ |
| systematic-debugging | 对失败、异常行为或反复尝试无效的问题做根因排查 | ↑ |
| test-driven-development | 先定义验收条件，再行动；代码场景可用红绿重构 | ↑ |
| verification-before-completion | 完成前核验证据；内含代码审查、反馈处理和分支收尾能力 | ↑ |
| ppt-agent | 专业 PPT 演示文稿全流程生成，输出 HTML/预览/PPTX 管线 | 本仓库 |
| frontend-design | 创建高质量前端页面、组件和 Web App | 本仓库 |
| taste-skill | 反模板化前端设计审美与落地检查 | 本仓库 |
| ui-ux-pro-max | UI/UX 设计、配色、字体、布局与多技术栈界面实现参考 | 本仓库 |

## 知识库构建（六技能联合）

把一堆论文变成可搜索、可对话、可可视化的知识库，由六个技能接力完成：

| 步骤 | 技能 | 做什么 |
|------|------|--------|
| 1 | **mineru-document-extractor** | PDF 优先入口；扫描件、古籍影印本、复杂表格/公式 → 高保真 Markdown |
| 1b | **markitdown** | 非 PDF 文档的轻量转换；失败、空输出或乱码时交给 MinerU 兜底 |
| 2 | **deep-reading-to-wiki** | 长书、理论文献、补库候选源 → `reading_dossiers/` 深读档案，避免浅层总结直接入库 |
| 3 | **karpathy-wiki** | raw + 深读档案 → claims 论证节点 + concepts/entities/comparisons 图谱页面 + 轻量 synthesis |
| 4 | **SiliconFlow-rag** | raw 原文 + wiki 结构 → 双向量索引，查询默认 wiki-first |
| 协调 | **social-science-km** | 调度以上步骤，一步到位；补库时先找 raw 证据，再深读，再入图谱 |

> MinerU 需要 **skill + MCP** 两部分：`mineru-document-extractor` skill 已在本仓库；MinerU MCP 需要按 https://mineru.net/ecosystem 的说明安装/配置。

**直接说「帮我把这个文件夹里的论文建个知识库」就行**，AI 会自动调用这些技能。建完后在 Obsidian 里打开文件夹，按 `Ctrl/Cmd + G` 即可看到彩色知识图谱。

> 📖 详细用法见 [KB-GUIDE.md](KB-GUIDE.md)

## 安装

新手直接运行：

```bash
git clone https://github.com/Innoksadk223/skills-repo.git ~/inno-skills
cd ~/inno-skills
bash setup.sh
```

脚本会进入菜单，默认选择**推荐安装**：只装常用核心技能，避免第一次就装一大堆。

常用高级命令：

```bash
bash setup.sh --dry-run                         # 先预览，不写文件
bash setup.sh --preset all                      # 安装全部技能
bash setup.sh --target codex --groups tools,search
bash setup.sh --target codex --skills agent-loop,anysearch
bash setup.sh --update-only                     # 只更新已有技能，不新增
bash setup.sh --help                            # 查看完整选项
```

`setup.sh` 会：
- 自动检测你装了哪些 agent（支持多选 / 全选）
- **小白模式** — 默认推荐安装，也可预览后再安装
- **自由选择** — 可按预设、分组或单个 skill 安装
- 直接将技能文件复制到 agent 目录（非 symlink，独立可迁移）
- Hermes 自动构建分类目录（browser-use/, paperspine/, minimax/, research/, creative/ 等）
- 已有技能自动比较更新（`diff -rq`），不一致则覆盖
- 不删除不在本仓库里的技能

## 给 Agent 的安装/更新指令

当用户要求在另一台电脑安装本技能库时，直接执行：

```bash
git clone https://github.com/Innoksadk223/skills-repo.git ~/inno-skills
cd ~/inno-skills
bash setup.sh
```

如果用户要求“先看看会安装什么”，执行：

```bash
bash setup.sh --dry-run
```

当用户要求更新本技能库时：

1. 先找安装路径：检查 `~/.{agent}/skills/.skills-repo-path` 获取 repo 位置
2. 然后执行：
```bash
cd $(cat ~/.claude/skills/.skills-repo-path)
git pull
bash setup.sh --update-only
```

执行规则：
- 已有技能 → 自动 `diff` 比较，不一致则覆盖更新，无需手动干预
- 新增技能 → 列出清单询问用户是否安装
- 不在本仓库的技能 → 不删除、不覆盖

### Claude Code 官方安装（推荐）

```bash
npx skills add -g browser-use    # browser-use 全系列
# paper-spine 需手动: git clone https://github.com/WUBING2023/PaperSpine.git
```

## 目录结构

```
skills-repo/
├── skills/              ← 扁平结构（Claude Code / Codex）
├── skills-hermes/       ← 分类结构（Hermes；按用途分组）
|   ├── browser-use/     ← 浏览器自动化
|   ├── paperspine/      ← 12 个技能
│   ├── minimax/         ← 3 个技能
|   ├── research/        ← 4 个知识库/RAG/深读技能
|   ├── productivity/    ← MinerU 文档解析
│   ├── creative/        ← PPT Agent
│   ├── superpowers/     ← 6 个轻量通用方法论技能入口
│   ├── anysearch         ← 实时搜索（solo symlink）
│   └── agent-loop        ← 四角色迭代循环（solo symlink）
└── setup.sh
```
