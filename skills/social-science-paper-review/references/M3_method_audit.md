# M3 Method Audit

## 状态检查

检查 `state/M3_method_audit.json` 是否存在。
- 存在 -> 读取并跳过本模块
- 不存在 -> 执行以下逻辑

## 输入

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `review_brief` | JSON | `state/M1_review_brief.json` | 论文类型 |
| `claim_map` | JSON | `state/M2_claim_map.json` | 需要验证的主张和证据 |
| `methods_results` | text | 用户材料 | 方法、数据、结果、附录、表图 |

## 执行

1. 判断研究设计是否能回答研究问题：描述、解释、因果识别、机制解释、理论建构或诠释。
2. 审查方法论理由：作者为什么选择这种方法，它与研究问题、理论立场、知识主张和材料性质是否匹配；不要只检查技术步骤。
3. 按论文类型审查：
   - 定量：样本、测量、变量操作化、模型设定、识别策略、稳健性、缺失值、效应量、统计不确定性。
   - 定性：案例选择、进入田野/材料来源、编码或解释过程、证据透明度、反例、饱和度、研究者位置。
   - 混合方法：两类证据是否回答同一问题，是否只是并列摆放，是否互相校验或解释。
   - 综述/理论：检索范围、纳入排除标准、分类框架、概念推演、替代解释。
4. 检查因果语言：没有识别设计时，不允许把关联、叙述或解释写成因果证明。
5. 检查证据充分性：关键表图、访谈引文、档案材料、案例细节是否足以支撑中心结论。
6. 检查可复核性：数据、代码、访谈协议、附录、编码规则、检索式是否足够透明。
7. 识别致命方法问题、大修问题、小修问题，并说明对论文结论的影响。
8. 给每个重大方法问题写一条作者可执行修法。

## 输出

- **文件**: `state/M3_method_audit.json`
- **格式**: JSON
- **结构**:
```json
{
  "design_fit": "strong|adequate|weak|fatal",
  "methodological_rationale": {
    "fit_to_question": "strong|adequate|weak|missing",
    "fit_to_theory_or_epistemology": "strong|adequate|weak|missing",
    "notes": "..."
  },
  "major_method_findings": [
    {
      "issue": "...",
      "severity": "fatal|major|minor",
      "impact": "...",
      "revision_path": "..."
    }
  ],
  "credibility_checks": {
    "measurement_or_materials": "...",
    "identification_or_interpretation": "...",
    "robustness_or_triangulation": "...",
    "transparency": "..."
  }
}
```

## 回滚

如果本模块失败：
- 删除 `state/M3_method_audit.json`
- 重新运行本模块即可
