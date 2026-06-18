# M2 Claim Map

## 状态检查

检查 `state/M2_claim_map.json` 是否存在。
- 存在 -> 读取并跳过本模块
- 不存在 -> 执行以下逻辑

## 输入

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `review_brief` | JSON | `state/M1_review_brief.json` | 论文类型、领域、审阅限制 |
| `paper_text` | text | 用户材料 | 摘要、引言、理论、方法、结果、讨论 |

## 执行

1. 提取中心研究问题，并判断它是否明确、重要、可回答。
2. 提取理论命题或机制链条：核心概念、变量/过程、预期关系、边界条件。
3. 提取作者声称的贡献：理论贡献、经验贡献、方法贡献、政策贡献。
4. 检查文章脉络：引言是否铺出问题，文献是否导向缺口，理论是否导向方法，结果是否回扣问题，讨论是否收束贡献。
5. 建立“研究问题 -> 理论/概念 -> 方法 -> 证据 -> 结论”论证链，标注每段链条是否断裂、跳跃或重复。
6. 建立“主张 -> 证据 -> 结论”映射，标注每个主张的支撑强度。
7. 标出概念漂移：同一概念是否在问题、理论、测量和结论中含义变化。
8. 标出越界结论：证据只能支持相关性，却写成因果；局部材料却写成普遍规律。
9. 生成需要 M3/M4/M5 重点核查的问题清单。

## 输出

- **文件**: `state/M2_claim_map.json`
- **格式**: JSON
- **结构**:
```json
{
  "research_question": "...",
  "theory_or_mechanism": ["..."],
  "argument_spine": {
    "main_thread": "...",
    "chain_breaks": ["..."],
    "section_flow_issues": ["..."]
  },
  "claimed_contributions": {
    "theoretical": ["..."],
    "empirical": ["..."],
    "methodological": ["..."],
    "practical_or_policy": ["..."]
  },
  "claim_evidence_map": [
    {
      "claim": "...",
      "evidence": "...",
      "support_strength": "strong|moderate|weak|unsupported",
      "risk": "overclaim|concept_drift|missing_evidence|none"
    }
  ],
  "priority_checks": ["..."]
}
```

## 回滚

如果本模块失败：
- 删除 `state/M2_claim_map.json`
- 重新运行本模块即可
