# Chinese Academic Presentation Patterns

## When to Use

Chinese thesis proposals (开题报告), defense presentations (答辩), and academic conference talks.

## Color Palette

**Vintage & Academic (#4)** is the go-to palette for Chinese humanities/social-science academic presentations:

| Key | Value | Usage |
|-----|-------|-------|
| primary | `003049` | Deep navy — titles, body text |
| secondary | `780000` | Burgundy — section divider backgrounds, accent callouts |
| accent | `669bbc` | Steel blue — decorative, badges, secondary elements |
| light | `fdf0d5` | Cream — content slide backgrounds |
| bg | `c1121f` | Bright red — alternate section divider backgrounds |

## Section Divider Convention

Chinese academic PPTs conventionally use numbered sections with Chinese numerals (壹、贰、叁). Alternate section divider background colors for visual variety:

- First section → `theme.primary` background
- Second section → `theme.bg` background
- Third section → `theme.secondary` background

Each divider should show: large numeral + section title + 2-3 subtopic labels.

## Slide Type Mapping

| Thesis Section | Slide Type | Layout Pattern |
|---------------|------------|----------------|
| 选题来源 | Content (Text) | Two-column: classical vs modern, or problem vs solution |
| 研究意义 | Content (Comparison) | 3-column cards: 理论/现实/教育 |
| 国内文献综述 | Content (Timeline) | Flow diagram (e.g. 天→性→情→道→孝→仁) + scholar cards |
| 国外文献综述 | Content (Comparison) | Left-right theorists + bottom comparison table |
| 研究方法 | Content (Grid) | 2×3 icon-card grid for 5-6 methods |
| 创新之处 | Content (Comparison) | Side-by-side: 传统进路 vs 本文创新 + flow diagram |
| 已有成绩 | Content (Mixed) | Left accomplishments + right limitations box |
| 预期结果 | Content (Cards) | 3 vertical outcome cards with big numbers |

## Direct Authoring vs Subagents

For content-precise Chinese academic slides:
- **Direct authoring is preferred** — subagents can garble specialized academic terminology
- Write all slide JS files yourself, then compile once
- Subagents are OK for English/generic business slides

## Flow Diagrams

Chinese academic PPTs often include conceptual flow diagrams. Use `ROUNDED_RECTANGLE` blocks connected by text arrows (`→`). Example pattern:

```javascript
const stages = [
  { label: "依恋情感", sub: "生物本能", color: theme.accent },
  { label: "亲亲互动", sub: "家庭教化", color: theme.accent },
  { label: "孝之德性", sub: "道德自觉", color: theme.secondary },
  { label: "仁之完成", sub: "推及社会", color: theme.primary }
];
// Render as horizontal row with "→" between blocks
```
