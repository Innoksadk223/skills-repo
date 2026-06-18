# M4 Positioning Audit

## 状态检查

检查 `state/M4_positioning_audit.json` 是否存在。
- 存在 -> 读取并跳过本模块
- 不存在 -> 执行以下逻辑

## 输入

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `review_brief` | JSON | `state/M1_review_brief.json` | 领域和审阅限制 |
| `claim_map` | JSON | `state/M2_claim_map.json` | 贡献声明 |
| `method_audit` | JSON | `state/M3_method_audit.json` | 方法可信度 |
| `literature_discussion` | text | 用户材料/必要检索 | 文献综述、讨论、参考文献 |

## 执行

1. 判断文献综述是否服务于研究问题，而不是堆引用。
2. 检查引用是否有作者自己的解释：每个关键引用应说明“它证明了什么、与本文问题有什么关系、作者如何继承或反驳它”。
3. 识别堆砌式引用：连续罗列作者或括号引用，但没有解释、比较、综合或转化为本文论点。
4. 检查作者是否准确说明“已有研究知道什么、尚未知道什么、本文补什么”。
5. 评估理论贡献：新概念、新机制、新边界条件、新证据、反常案例，还是只是换场景复述旧结论。
6. 检查关键文献遗漏：经典文献、近五年核心研究、相邻领域、相反发现。
7. 检查讨论部分是否承认证据边界：样本、场景、时间、制度环境、群体差异。
8. 检查伦理和社会影响：隐私、匿名化、污名化、偏见、政策误用、弱势群体风险。
9. 给出贡献等级和定位修法：重写引言、收窄主张、补文献、重构理论框架等。

## 输出

- **文件**: `state/M4_positioning_audit.json`
- **格式**: JSON
- **结构**:
```json
{
  "literature_fit": "strong|adequate|weak",
  "citation_interpretation": {
    "author_voice": "strong|adequate|weak|missing",
    "citation_piling_issues": ["..."],
    "rewrite_needed": ["..."]
  },
  "contribution_level": "strong|solid|incremental|unclear|below_threshold",
  "missing_or_misused_literature": ["..."],
  "boundary_conditions": ["..."],
  "ethics_and_social_risk": ["..."],
  "positioning_revisions": ["..."]
}
```

## 回滚

如果本模块失败：
- 删除 `state/M4_positioning_audit.json`
- 重新运行本模块即可
