# Inno's Skills Pack

个人 AI Coding Agent 技能包，支持 **Claude Code**、**Codex**、**Hermes**。

> **Claude Code 用户建议优先从官方源安装**（`npx skills add -g <name>`），版本更新更及时。
> 此包主要用于：Hermes / Codex 安装、团队统一技能集、离线环境。

## 技能清单（23 个）

| 分类 | 技能 | 来源 |
|------|------|------|
| Browser | browser-use, remote-browser, cloud, x402, open-source | [browser-use/browser-use](https://github.com/browser-use/browser-use) |
| PaperSpine | paper-spine + 11 个子模块 | [WUBING2023/PaperSpine](https://github.com/WUBING2023/PaperSpine) |
| Research | academic-search, academic-paper-review | [ustc-ai4science](https://github.com/ustc-ai4science/academic-search) · [bytedance/deer-flow](https://github.com/bytedance/deer-flow/tree/main/skills/public/academic-paper-review) |
| Tools | skill-creator | [clawhub.ai](https://clawhub.ai) |
| — | cleanup, find-skills, grill-me | — |

## 快速安装

```bash
git clone https://github.com/Innoksadk223/skills-repo.git ~/inno-skills
cd ~/inno-skills
bash setup.sh
```

`setup.sh` 会：
- 自动检测你装了哪些 agent（支持多选 / 全选）
- Hermes 直接从 skills/ 构建分类目录（不依赖中间 symlink）
- 已有技能自动跳过，只装新增的
- 以后 `git pull && bash setup.sh` 即可同步增删

### Claude Code 推荐方式

```bash
npx skills add -g browser-use    # browser-use 全系列
npx skills add -g academic-search
# paper-spine 需手动从 GitHub 安装:
# git clone https://github.com/WUBING2023/PaperSpine.git
```

---

## 安装完成后

安装命令执行完毕后，**你的 AI 会自动读取下方速查表并逐一介绍每个技能的用途**。不需要你主动问。

---

## 技能速查

| 技能 | 用途 |
|------|------|
| browser-use | 浏览器自动化：网页测试、表单填充、截图、数据提取 |
| remote-browser | 从远端沙箱控制本地浏览器 |
| cloud | Browser Use Cloud API / 云端浏览器 |
| x402 | Cloud 支付集成（USDC 钱包，无需 API key） |
| open-source | browser-use Python SDK 开发文档 |
| paper-spine | 学术论文写作流水线总调度 |
| paper-spine-audit | 审计输出完整性 |
| paper-spine-build | 从素材构建论文 |
| paper-spine-citation | 引用文库构建与验证 |
| paper-spine-humanize | 降低 AI 检测率，提升人味 |
| paper-spine-intake | 交互式工作流配置采集 |
| paper-spine-latex | LaTeX 项目组装与排版 |
| paper-spine-research | 期刊/会议要求研究 |
| paper-spine-rewrite | 已有稿件深度改写 |
| paper-spine-translate | 中英学术翻译 |
| paper-spine-ui | PaperSpine 终端配置界面 |
| paper-spine-update | PaperSpine 版本检查与更新 |
| academic-search | 学术搜索、引用分析、OA PDF 判定 |
| academic-paper-review | 论文审阅、方法论评估、同行评审 |
| skill-creator | 创建新的 AI 技能 |
| cleanup | 任务完成后清理临时文件 |
| find-skills | 发现和安装社区技能 |
| grill-me | 深度质询你的方案/设计决策 |

## 目录结构

```
skills-repo/
├── skills/              ← 扁平结构（Claude Code / Codex）
├── skills-hermes/       ← 分类结构（Hermes，symlink → skills/）
│   ├── browser-use/     ← 5 个技能
│   ├── paperspine/      ← 12 个技能
│   └── ...
└── setup.sh
```
