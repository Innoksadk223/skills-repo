---
name: wiki-to-okf
description: Convert karpathy-wiki pages (human-readable argumentation graph) into OKF (Open Knowledge Format) — an AI-consumable knowledge bundle of Markdown files with structured YAML frontmatter. Use when building AI-readable knowledge format from existing wiki, when adding an OKF output layer to social-science-km projects, or when converting any karpathy-wiki claims/concepts/entities/comparisons/synthesis/debates into machine-actionable concept files.
---

# Wiki → OKF Converter

将 karpathy-wiki 的人读论证图谱转化为 OKF bundle：目录 + Markdown + YAML frontmatter。AI agent 可直接消费——导航、查询、工具调用。

OKF 核心原则来自 Google Cloud 的 Open Knowledge Format v0.1：**格式，不是平台**。没有 SDK，没有 runtime，没有私有账号。一个目录就是完整知识包。

## 工作流

| 步 | 做什么 | 产物 |
|----|--------|------|
| 1. SCAN | 扫描 `wiki/` 下 claims/concepts/entities/comparisons/synthesis/debates 的所有 .md 页面 | 文件清单 |
| 2. CONVERT | 逐个页面：规则提取 metadata → LLM 压缩 body → 提取交叉链接 | `okf/<type>/<page>.md` |
| 3. ASSEMBLE | 生成 `okf/index.md` + `okf/log.md` | 索引 + 变更日志 |
| 4. VALIDATE | 所有页面含有效 YAML frontmatter，交叉链接可解析 | pass / 错误清单 |

输出位置：`<知识库>/okf/`，作为 `wiki/` 的兄弟目录。

## 前置条件

- 已有 karpathy-wiki 产物在 `wiki/` 下
- `wiki/claims/`, `wiki/concepts/`, `wiki/entities/`, `wiki/comparisons/` 至少一个目录存在
- 有 LLM 可调用（本 skill 不绑定特定 LLM，agent 用当前可用模型）
- Python 3 环境含 PyYAML（`pip install pyyaml`，Step 4 验证脚本需要）

## Step 1: SCAN

```bash
find wiki/claims wiki/concepts wiki/entities wiki/comparisons wiki/synthesis wiki/debates -name "*.md" -not -name "index.md" 2>/dev/null | sort
```

同时读取 `wiki/SCHEMA.md` 获取类型定义和 wiki 约定。
同时读取 `wiki/log.md` 获取最近变更（用于 OKF log.md 起始点）。

输出文件清单，按类型分组。

## Step 2: CONVERT

对每个页面执行三步转换：

### 2a. 规则提取 Metadata

从 karpathy-wiki 页面提取结构化字段，写入 OKF YAML frontmatter。映射规则详见 `references/okf-spec.md`。

核心映射：

| Wiki 来源 | OKF 字段 | 提取方式 |
|-----------|---------|---------|
| 页面所在目录 | `type` | `claims/`→`claim`, `concepts/`→`concept`, `entities/`→`entity`, `comparisons/`→`comparison`, `synthesis/`→`synthesis`, `debates/`→`debate` |
| 页面 YAML `title` 或首个 `# heading` | `title` | 规则：优先 YAML frontmatter 的 `title` 字段，否则取 `# heading` |
| 页面首段（≤160 chars） | `description` | 规则：截取 `# heading` 后第一个非空段落的前 160 字符 |
| 页面 YAML `tags` | `tags` | 规则：直接映射 wiki YAML tags；若无则见 `references/okf-spec.md` 扩展规则 |
| Wiki 页面路径 | `source` | 规则：相对于 `wiki/` 的路径 |
| Wiki 页面 mtime 或 `wiki/log.md` 中最近变更时间 | `timestamp` | 规则：`stat` 文件 mtime，ISO 8601 |

### 2b. LLM 压缩 Body

将 wiki 页面正文（去掉 YAML frontmatter 后的 Markdown）喂给 LLM，按 `references/transform-prompt.md` 中的 prompt 模板压缩为 AI 可消费格式。

约束：
- 保留所有论证关系的核心逻辑（support/oppose/limit/depend）
- 保留原始引文锚点（`wiki/raw/` 路径引用）
- 去掉叙事性段落，保留可操作的结构化信息
- 标记不确定性（如 "来源未验证"、"解释存在争议"）

### 2c. 提取交叉链接

从压缩后的 body 和原始 wiki 的交叉链接中提取 `relates_to` 字段——指向 `okf/` 下其他页面的相对路径列表。解析规则见 `references/okf-spec.md`。

### 批量处理

对于大量页面，按类型分组并行转换。每个子 agent 处理一个类型目录（如 `wiki/claims/`），但只写 `okf/claims/` 下的文件，不碰 `okf/index.md` 或 `okf/log.md`。

### 2d. 解析 UNRESOLVED 链接

LLM 输出中若含 `UNRESOLVED:` 块（无法确定目标页面所属类型目录的交叉引用），agent 需利用 Step 1 的文件清单查找概念名对应目录，将解析后的路径补充到该页面的 `relates_to`。无法解析的保留在 body 的 UNRESOLVED 块中，作为后续人工审核线索。

## Step 3: ASSEMBLE

在所有页面转换完成后执行。

### 生成 `okf/index.md`

按 `references/index-template.md` 结构生成导航枢纽。每个类型目录下生成 `index.md`（列出该类型所有页面 + 一句话 description），顶层 `okf/index.md` 列出所有类型目录 + 统计摘要。

### 生成 `okf/log.md`

从 `wiki/log.md` 提取当次转换相关的条目，记录：
- 转换时间
- 源 wiki 状态（commit hash 或 log 起始点）
- 转换统计（各类型页面数）

## Step 4: VALIDATE

### 4a. Frontmatter 完整性

```bash
python3 -c "
import os, yaml, re, sys

okf_dir = 'okf'
errors = []
for root, dirs, files in os.walk(okf_dir):
    for f in files:
        if f in ('index.md', 'log.md') or not f.endswith('.md'):
            continue
        path = os.path.join(root, f)
        with open(path) as fh:
            content = fh.read()
        if not content.startswith('---'):
            errors.append(f'{path}: MISSING_FRONTMATTER')
            continue
        parts = re.split(r'^---$', content, maxsplit=2, flags=re.MULTILINE)
        if len(parts) < 3:
            errors.append(f'{path}: MALFORMED_FRONTMATTER (unclosed ---)')
            continue
        fm = yaml.safe_load(parts[1])
        if not isinstance(fm, dict):
            errors.append(f'{path}: FRONTMATTER_NOT_DICT')
            continue
        for field in ['type', 'title', 'description']:
            if field not in fm:
                errors.append(f'{path}: MISSING_FIELD {field}')
        valid_types = {'claim','concept','entity','comparison','synthesis','debate','index','log'}
        if 'type' in fm and fm['type'] not in valid_types:
            errors.append(f'{path}: INVALID_TYPE {fm[\"type\"]} (allowed: {sorted(valid_types)})')

if errors:
    print('VALIDATION FAILED:')
    for e in errors:
        print(f'  - {e}')
    sys.exit(1)
else:
    print('Frontmatter validation: PASS')
"
```

Frontmatter 解析使用 `re.split(r'^---$', ..., flags=re.MULTILINE)` 而非 `content.split('---', 2)`——避免 body 中的 `---`（horizontal rule）被误判为 frontmatter 边界。

### 4b. 交叉链接可解析

```bash
python3 -c "
import os, yaml, re, sys

okf_dir = 'okf'
missing_links = []
for root, dirs, files in os.walk(okf_dir):
    for f in files:
        if f in ('index.md', 'log.md') or not f.endswith('.md'):
            continue
        path = os.path.join(root, f)
        with open(path) as fh:
            content = fh.read()
        parts = re.split(r'^---$', content, maxsplit=2, flags=re.MULTILINE)
        if len(parts) < 3:
            continue
        fm = yaml.safe_load(parts[1])
        if not isinstance(fm, dict) or 'relates_to' not in fm:
            continue
        for link_path in fm['relates_to']:
            target = os.path.join(okf_dir, link_path)
            if not os.path.exists(target):
                missing_links.append(f'{path} → {link_path} (NOT FOUND)')

if missing_links:
    print('CROSS-LINK VALIDATION FAILED:')
    for m in missing_links:
        print(f'  - {m}')
    sys.exit(1)
else:
    print('Cross-link validation: PASS')
"
```

验证标准：
- 所有概念页面有完整的 YAML frontmatter（type, title, description），使用 `re.MULTILINE` 健壮解析
- `relates_to` 中所有路径指向 `okf/` 下存在的文件（`os.path.exists` 逐条验证）
- `type` 值在允许的枚举范围内

## 与 social-science-km 的集成

`wiki-to-okf` 是独立 skill，不修改 social-science-km workflow。在 social-science-km 的 Step 3（karpathy-wiki 编译）完成后，可选执行：

```
social-science-km Step 3 完成 → wiki/ 就绪
  ↓ (可选)
wiki-to-okf → okf/ 生成
  ↓
okf/ 可直接喂给 AI agent 作为上下文、挂载到文件系统、或打包分发
```

## 注意事项

- 目录结构保留 karpathy-wiki 的树形组织（claims/concepts/entities/…），不重新分类
- LLM body 压缩可能丢失细微论证关系；重要节点应在 `description` 中标注不确定性
- 首次转换后，后续增量更新只需重新处理 `wiki/log.md` 中标记为变更的页面
- `okf/` 目录可作为独立包分发（tarball / git repo），不依赖任何平台
