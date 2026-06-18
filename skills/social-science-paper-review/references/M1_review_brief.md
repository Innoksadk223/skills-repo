# M1 Review Brief

## 状态检查

检查 `state/M1_review_brief.json` 是否存在。
- 存在 -> 读取并跳过本模块
- 不存在 -> 执行以下逻辑

## 输入

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `user_goal` | string | 用户输入 | 用户想要严格审稿、修改指导、投稿前自查或期刊审稿意见 |
| `paper_material` | text/file/url | 用户输入 | 论文全文、摘要、片段、PDF、链接或粘贴文本 |
| `target_context` | string | 用户输入/推断 | 期刊投稿、课程论文、学位论文、工作论文、匿名评审等 |

## 执行

1. 判断材料完整度：全文、摘要、片段、结果表、方法部分或仅题目。
2. 识别论文类型：定量、定性、混合方法、理论、综述、政策评估、方法论文。
3. 识别社科子领域和目标读者：学术期刊、导师、会议、政策读者或课程评分者。
4. 提取作者显性目标：研究问题、理论对象、经验对象、贡献声明。
5. 确认审阅口径：默认输出“严格审稿 + 修改指导”；如果用户只要摘要，降级为简版。
6. 记录审阅限制：缺全文、缺附录、缺数据、缺访谈材料、缺文献表等。
7. 如果缺口会改变判断，先问一个效果题；否则带着限制继续。

## 输出

- **文件**: `state/M1_review_brief.json`
- **格式**: JSON
- **结构**:
```json
{
  "material_completeness": "full_text|partial|abstract_only",
  "paper_type": "quantitative|qualitative|mixed_methods|theory|review|policy_evaluation|methods|unknown",
  "field": "sociology|political_science|education|communication|management|public_policy|psychology|anthropology|other",
  "review_mode": "strict_peer_review_plus_revision_guidance",
  "target_context": "journal|thesis|course|working_paper|unknown",
  "limits": ["missing appendix"],
  "confidence": "high|medium|low"
}
```

## 回滚

如果本模块失败：
- 删除 `state/M1_review_brief.json`
- 重新运行本模块即可
