# Frontend Slides → PPTX 主题映射

将 [frontend-slides](../../creative/frontend-slides/SKILL.md) 的 12 个视觉风格翻译为 pptx-generator 可用的 theme 对象。

> **翻译原则**：pptx-generator 不支持渐变、动画、Google Fonts。颜色取 CSS 变量中的主色/辅色/强调色映射到 theme 五色；字体选最接近的系统字体；Style Recipe 根据风格氛围匹配。

---

## 1. Bold Signal

**氛围**：自信、高冲击、现代

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `1a1a1a` | bg-primary |
| secondary | `2d2d2d` | gradient 深色 |
| accent | `FF5722` | card-bg 橙色卡片 |
| light | `ffffff` | text-primary |
| bg | `1a1a1a` | 主背景深黑 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Archivo Black | Arial Black |
| 正文 | Space Grotesk | Calibri |

**Style Recipe**：Sharp & Compact（匹配高冲击几何感）

---

## 2. Electric Studio

**氛围**：干净、专业、高对比

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `0a0a0a` | bg-dark |
| secondary | `4361ee` | accent-blue |
| accent | `4361ee` | accent-blue |
| light | `ffffff` | bg-white |
| bg | `ffffff` | 白底为主 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Manrope 800 | Calibri（加粗） |
| 正文 | Manrope 400 | Calibri |

**Style Recipe**：Soft & Balanced

---

## 3. Creative Voltage

**氛围**：大胆、创意、能量感

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `1a1a2e` | bg-dark |
| secondary | `0066ff` | bg-primary 电蓝 |
| accent | `d4ff00` | accent-neon 霓虹黄 |
| light | `ffffff` | text-light |
| bg | `0066ff` | 电蓝主色 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Syne 700 | Trebuchet MS |
| 正文 | Space Mono | Consolas |

**Style Recipe**：Pill & Airy（匹配大胆创意的开放感）

---

## 4. Dark Botanical

**氛围**：优雅、精致、艺术感

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `0f0f0f` | bg-primary |
| secondary | `9a9590` | text-secondary |
| accent | `d4a574` | accent-warm 暖金 |
| light | `e8b4b8` | accent-pink 柔和粉 |
| bg | `0f0f0f` | 深色底 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Cormorant | Georgia |
| 正文 | IBM Plex Sans | Calibri |

**Style Recipe**：Rounded & Spacious（匹配优雅从容的呼吸感）

---

## 5. Notebook Tabs

**氛围**：编辑风、有条理、触感

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `2d2d2d` | bg-outer |
| secondary | `1a1a1a` | text-primary |
| accent | `98d4bb` | tab-1 薄荷绿 |
| light | `f8f6f1` | bg-page 纸张色 |
| bg | `f8f6f1` | 米白纸底 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Bodoni Moda | Georgia |
| 正文 | DM Sans | Calibri |

**Style Recipe**：Soft & Balanced（匹配编辑风的舒适间距）

---

## 6. Pastel Geometry

**氛围**：友好、现代、亲和

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `7c6aad` | pill-violet（最深 pill 色） |
| secondary | `5a7c6a` | pill-sage |
| accent | `f0b4d4` | pill-pink 主打粉 |
| light | `c8d9e6` | bg-primary 淡蓝底 |
| bg | `faf9f7` | card-bg 白卡片 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Plus Jakarta Sans 700 | Calibri（加粗） |
| 正文 | Plus Jakarta Sans 400 | Calibri |

**Style Recipe**：Rounded & Spacious（匹配柔和友好的圆角感）

---

## 7. Split Pastel

**氛围**：俏皮、现代、创意

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `1a1a1a` | text-dark |
| secondary | `e4dff0` | bg-lavender |
| accent | `f5e6dc` | bg-peach 蜜桃色 |
| light | `c8f0d8` | badge-mint |
| bg | `f5e6dc` | 蜜桃底为主 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Outfit 700 | Calibri（加粗） |
| 正文 | Outfit 400 | Calibri |

**Style Recipe**：Rounded & Spacious

---

## 8. Vintage Editorial

**氛围**：机智、个性、编辑风

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `1a1a1a` | text-primary |
| secondary | `555555` | text-secondary |
| accent | `e8d4c0` | accent-warm 暖驼色 |
| light | `f5f3ee` | bg-cream |
| bg | `f5f3ee` | 奶油纸底 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Fraunces 700 | Georgia |
| 正文 | Work Sans | Calibri |

**Style Recipe**：Soft & Balanced

---

## 9. Neon Cyber

**氛围**：未来感、科技、赛博

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `0a0f1c` | deep navy |
| secondary | `ff00aa` | magenta |
| accent | `00ffcc` | cyan 霓虹青 |
| light | `0a0f1c` | 深色底 |
| bg | `0a0f1c` | 深海军蓝底 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Clash Display | Impact |
| 正文 | Satoshi | Calibri |

**Style Recipe**：Sharp & Compact（匹配科技锋利感）

---

## 10. Terminal Green

**氛围**：开发者、黑客美学

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `0d1117` | GitHub dark |
| secondary | `39d353` | terminal green |
| accent | `39d353` | terminal green |
| light | `0d1117` | 深色底 |
| bg | `0d1117` | 终端黑底 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | JetBrains Mono | Consolas |
| 正文 | JetBrains Mono | Consolas |

**Style Recipe**：Sharp & Compact（匹配终端极简感）

---

## 11. Swiss Modern

**氛围**：极简、包豪斯、几何

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `000000` | pure black |
| secondary | `ffffff` | pure white |
| accent | `ff3300` | red accent |
| light | `ffffff` | 纯白 |
| bg | `ffffff` | 纯白底 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Archivo 800 | Arial Black |
| 正文 | Nunito 400 | Calibri |

**Style Recipe**：Sharp & Compact（匹配包豪斯几何精确感）

---

## 12. Paper & Ink

**氛围**：文学、编辑、思辨

| theme key | 值 | 来源 |
|-----------|-----|------|
| primary | `1a1a1a` | charcoal |
| secondary | `c41e3a` | crimson |
| accent | `c41e3a` | crimson 朱红强调 |
| light | `faf9f7` | warm cream |
| bg | `faf9f7` | 暖奶油纸底 |

| 字体 | 原字体 | 替换 |
|------|--------|------|
| 标题 | Cormorant Garamond | Georgia |
| 正文 | Source Serif 4 | Cambria |

**Style Recipe**：Soft & Balanced（匹配文学编辑的经典间距）

---

## 使用方式

在 pptx-generator 的 compile.js 中替换 theme 对象即可：

```javascript
// 例如使用 Bold Signal
const theme = {
  primary: "1a1a1a",
  secondary: "2d2d2d",
  accent: "FF5722",
  light: "ffffff",
  bg: "1a1a1a"
};
```

字体设置在各 slide-XX.js 中按上表替换 `fontFace`。

---

## 限制说明

以下 frontend-slides 的视觉效果在 PPTX 中**无法实现**：

- **渐变背景**（如 Bold Signal 的 `linear-gradient`）→ 取主色作为纯色底
- **CSS 动画**（如 staggered reveal）→ PPTX 静态，无动画
- **粒子/纹理背景**（如 Neon Cyber 粒子、Terminal 扫描线）→ 纯色替代
- **Google Fonts**（如 Archivo Black、Syne、Clash Display）→ 最接近的系统字体
- **半透明叠加**（如 Dark Botanical 的模糊渐变圆）→ 用纯色形状替代，效果打折
