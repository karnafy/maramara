# Visual References

## Design philosophy

**Liquid Glass UI** meets Stitch "The Empathetic Observer".

- Frosted glass panels with soft ambient lighting
- Purple → teal → pink gradient glows floating in the background
- No hard 1px borders — depth comes from translucent layering
- Pill-shaped buttons, generous corner radii
- Breathing animations for discretion (instead of loud "REC" indicators)

## Inspiration images (`V2/VISUAL FERERANCES/`)

| File | Theme |
|------|-------|
| `dce4f06ab46a682631c80f304c401b83.jpg` | **Primary inspiration** — Liquid Glass UI Kit: purple/teal frosted components |
| `08a15bf578480201647bb7f93efcf9c9.jpg` | Glass accents |
| `a21c69679022979cf3bd81f535932c58.jpg` | Soft lighting reference |
| `a5da0219b4c7261da759d9cc3d7c12e1.jpg` | Pill layouts |
| `bd8f4ea7370c071f1fcca93ae4c8905b.jpg` | Layered glass |
| `f41f011aba4b2157cffda8749c6c6804.jpg` | Gradient backgrounds |

## Stitch project

**Maramara Therapeutic Speech Intelligence**
`https://stitch.withgoogle.com/projects/820755570011171849`

Status: public. Access via Stitch MCP: `projects/820755570011171849`.

### Key design decisions from Stitch

- **Fonts:** Plus Jakarta Sans (body), Manrope (display), Inter (labels)
- **Primary:** `#104356` (midnight teal)
- **Secondary:** `#4659A5` (indigo, adapted to `#6b5ce7` for liquid purple)
- **Background:** `#f8fafb` (sanctuary calm)
- **Rule:** No 1px borders for sectioning — use tonal layering
- **Radii:** xs=4px, DEFAULT radii via Stitch "ROUND_FOUR" scale
- **Elevation:** Ambient glow (40px blur, 6% opacity) instead of drop shadows
- **Breathing animation** for recording state (not flashing REC light)
- **Glassmorphism container** for floating recording indicator

## CSS implementation

Token definitions → `api/static/css/tokens.css`
Base + layout → `api/static/css/base.css`
Components → `api/static/css/components.css`

Reusable utility classes:
- `.glass` / `.glass-panel` — frosted panel
- `.glass-panel--elevated` — higher-opacity variant
- `.btn--primary` — gradient pill button (purple → teal)
- `.status-ring--active` — breathing recording indicator

## Accessibility

- Respects `prefers-reduced-motion` (animations disabled for users who opt out)
- Minimum contrast: body text `#1a1826` on light glass, `#f1eef7` on dark glass
- Focus states use 3px purple ring inset rather than outlines
