# 中文字体排版适配规则

> 当目标 PPT 内容以中文为主时，必须在风格选择后应用以下字体栈覆盖。默认 26 风格的字体定义是拉丁优先的，不改会导致中文显示为fallback字体、段落可读性差、serif italic 对中文无效等问题。

## 核心原则

| 原则 | 说明 |
|------|------|
| **标题 serif，正文 sans** | 中文正文用 sans-serif 可读性远优于 serif（中文笔画复杂，小字号 serif 会糊） |
| **中文无 true italic** | 中文字体没有真正的 italic，浏览器只能做 oblique（机械倾斜，丑）。强调中文词用颜色/字重替代 italic |
| **英文关键词保留 italic** | 用 `<em>` 或 `.em` 包裹英文术语，设置 `font-family: var(--font-display); font-style: italic` |
| **数字用 tabular-nums** | 所有数据数字必须等宽 |

## 字体栈三层降级（中文版）

| 角色 | Google Fonts | 系统字体（macOS/Win） |
|------|-------------|---------------------|
| 中文 serif | Noto Serif SC | STSong, SimSun, serif |
| 中文 sans | — | PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif |
| 英文 display | Playfair Display | Georgia, serif |
| 英文 body | Inter, Source Serif 4 | -apple-system, sans-serif |
| 等宽/mono | JetBrains Mono | SF Mono, Courier New, monospace |

## 实战 CSS 变量覆盖

选定风格后覆盖 typography 字段：

```json
{
  "typography": {
    "display_font": "'Playfair Display', 'Noto Serif SC', 'STSong', Georgia, serif",
    "body_font": "'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif",
    "serif_italic_font": "'Playfair Display', Georgia, serif",
    "mono_font": "'JetBrains Mono', 'SF Mono', 'Courier New', monospace"
  }
}
```

> `body_font` 去掉拉丁 serif（如 Source Serif 4），改用中文 sans-serif 优先。

## HTML 中的特殊处理

1. **英文关键词 italic**：只对英文词用 `<span class="em">`，不对中文用 `<em>`
2. **中文强调**：用 `color: var(--accent-1); font-weight: 600;` 不用 italic
3. **中英混排**：关键位置手动加半角空格

## 风格选择优先级（中文内容）

| 原始风格 | 中文适配 | 备注 |
|---------|---------|------|
| `minimal_gray` | ✅ 最推荐 | 学术气质强，中文可读性好 |
| `mocha_editorial` | ✅ 推荐 | 温暖学术风 |
| `blue_white` | ⚠️ 可 | 商务风，正文已 sans |
| `dark_tech` | ⚠️ 需调 | 暗底中文小字，body_size → 15px |
| `bauhaus_block` | ❌ 不推荐 | 依赖拉丁几何字形 |
