# DELIVER 阶段手册

Orchestrator 在 VERIFY 判定 PASS（或触发终止条件）后，交付最终成果时加载。

## 交付内容

交付物 = **worktree 中的全部产出物** + 验收记录。不交付 PLAN、不交付中间分析。

### 标准交付格式

```markdown
## 交付

### 产出物清单
- `state/step1_output.json` — [步骤 1 产出描述]
- `state/step2_output.json` — [步骤 2 产出描述]
- `state/article.md` — 最终文章（2350 字）

### 验收结果
- [x] 标准 1 — PASS（证据：...）
- [x] 标准 2 — PASS（证据：...）
- [x] 标准 3 — PASS（证据：...）
结果：3/3 PASS

### 修正历史
- 第 1 次修正轮：补充生态数据（Feedbacker 诊断：缺少量化指标）
- 第 2 次修正轮：无需修正（Feedbacker 判定 proceed_to_verify）

### 预算使用
- 迭代：1 次
- 修正轮：2 次
- Worker：2 个
```

## 未达标交付

触发终止条件但 checklist 未全部通过时：

```markdown
## 交付（未达标）

### 未达标项
- [ ] 标准 3 — 生态分析缺少企业采用案例（状态：STAGNATE，连续 2 次修正轮无实质进展）

### 当前最佳版本
[产出物清单，与标准交付格式相同]

### 终止原因
连续 2 次修正轮提升 <10%（STAGNATE）
```

## 预算耗尽交付

```markdown
## 交付（预算耗尽）

### 消耗
- token：21,340 / 预算 20,000
- 时间：48 分钟 / 预算 45 分钟
- 修正轮：2 次

### 未达标项
[列出]

### 当前最佳版本
[产出物清单]
```

## Orchestrator 自检清单

交付前确认：

- [ ] worktree 文件全部可读且内容非空
- [ ] 验收记录每项有 PASS/FAIL 判定和证据
- [ ] 修正历史与 worktree 中 feedback 文件一致
- [ ] 终止原因明确标注（PASS / 硬上限 / STAGNATE / BUDGET_STOP）
- [ ] 未达标项（如有）已列出
