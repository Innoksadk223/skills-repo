# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes**。

> 新手先看 [GUIDE.md](GUIDE.md) — 不用懂技术，会说人话就行。
>
> **Claude Code 用户建议优先从官方源安装**（`npx skills add -g <name>`），版本更新更及时。
> 此包主要用于：Hermes / Codex 安装、团队统一技能集、离线环境。

## AI 使用流程

收到安装请求后，AI 应按以下步骤：

1. **先介绍** — 按分组介绍技能（如下方速查表），每组一句话概括
2. **再确认** — 问用户要装到哪个 agent
3. **再安装** — `bash setup.sh`

介绍示例：
> 「这个包有 27 个技能，分 5 组：
>  🌐 浏览器自动化 — browser-use 等 5 个：网页操控、远端沙箱、Cloud API、支付、SDK
>  📝 论文写作 — PaperSpine 12 个：从研究到 LaTeX 排版的完整流水线
>  📄 文档生成 — Minimax 4 个：DOCX/PDF/XLSX/PPTX 专业文档
>  🔬 学术研究 — 2 个：学术搜索 + 论文审阅
>  🛠 开发工具 — 4 个：技能创建、清理、发现、质询」

## 技能速查（27 个）

| 分组 | 技能 | 一句话 |
|------|------|--------|
| 🌐 浏览器 | browser-use / remote-browser / cloud / x402 / open-source (5) | 网页自动化、远端沙箱、Cloud API、支付、SDK |
| 📝 PaperSpine | paper-spine + 11 子模块 (12) | 学术论文全流程：研究→引用→改写→LaTeX→翻译→审校 |
| 📄 Minimax | minimax-docx / minimax-pdf / minimax-xlsx / pptx-generator (4) | DOCX/PDF/XLSX/PPTX 专业文档生成 |
| 🔬 学术 | academic-search / academic-paper-review (2) | 学术搜索与引用分析 + 论文审阅 |
| 🛠 工具 | skill-creator / cleanup / find-skills / grill-me (4) | 技能创建、清理、发现、质询 |

### 详细

| 技能 | 用途 | 来源 |
|------|------|------|
| browser-use | 浏览器自动化：网页测试、表单填充、截图、数据提取 | [browser-use](https://github.com/browser-use/browser-use) |
| remote-browser | 从远端沙箱控制本地浏览器 | ↑ |
| cloud | Browser Use Cloud API / 云端浏览器 | ↑ |
| x402 | Cloud 支付集成（USDC 钱包，无需 API key） | ↑ |
| open-source | browser-use Python SDK 开发文档 | ↑ |
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
| pptx-generator | PowerPoint 演示文稿生成与编辑 | ↑ |
| academic-search | 学术搜索、引用分析、OA PDF 判定 | [ustc-ai4science](https://github.com/ustc-ai4science/academic-search) |
| academic-paper-review | 论文审阅、方法论评估、同行评审 | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) |
| skill-creator | 创建新的 AI 技能 | [clawhub.ai](https://clawhub.ai) |
| cleanup | 任务完成后清理临时文件 | — |
| find-skills | 发现和安装社区技能 | — |
| grill-me | 深度质询你的方案/设计决策 | — |

## 安装

```bash
git clone https://github.com/Innoksadk223/skills-repo.git ~/inno-skills
cd ~/inno-skills
bash setup.sh
```

`setup.sh` 会：
- 自动检测你装了哪些 agent（支持多选 / 全选）
- **可选分组安装** — 默认全装，也可只选 browser / paperspine / minimax 等
- 直接将技能文件复制到 agent 目录（非 symlink，独立可迁移）
- Hermes 自动构建分类目录（browser-use/, paperspine/, minimax/）
- 已有技能自动跳过
- 更新: `git pull && bash setup.sh`（覆盖已有技能）

### Claude Code 官方安装（推荐）

```bash
npx skills add -g browser-use    # browser-use 全系列
# paper-spine 需手动: git clone https://github.com/WUBING2023/PaperSpine.git
```

## 目录结构

```
skills-repo/
├── skills/              ← 扁平结构（Claude Code / Codex）
├── skills-hermes/       ← 分类结构（Hermes，symlink → skills/）
│   ├── browser-use/     ← 5 个技能
│   ├── paperspine/      ← 12 个技能
│   ├── minimax/         ← 4 个技能
│   └── ...
└── setup.sh
```
