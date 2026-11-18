# Brand profile (`brand.json`)

The brand profile is what makes each brand's ads look like that brand. Fill it from the website (or brand guidelines), then reference it from the spec with `"brand": "brand.json"`.

## Reading a website's style

### With a browser tool (best, works on JavaScript sites)

Open the site, then run this in the page and read the result:

```js
const cs = e => getComputedStyle(e);
const pick = sel => { const e = document.querySelector(sel); if (!e) return null; const s = cs(e);
  return { text: (e.innerText || '').slice(0, 80), font: s.fontFamily, size: s.fontSize, weight: s.fontWeight,
           tracking: s.letterSpacing, color: s.color, bg: s.backgroundColor, radius: s.borderRadius, border: s.border }; };
const vars = {}; for (const sh of document.styleSheets) { try { for (const r of sh.cssRules)
  if (r.selectorText === ':root') for (const p of r.style) if (p.startsWith('--')) vars[p] = r.style.getPropertyValue(p).trim(); } catch (e) {} }
const grads = [...new Set([...document.querySelectorAll('*')].map(e => cs(e).backgroundImage)
  .filter(b => b && b.includes('gradient')))].slice(0, 12);
const buttons = [...document.querySelectorAll('a,button')].filter(e => e.offsetWidth > 60 && cs(e).backgroundColor !== 'rgba(0, 0, 0, 0)')
  .slice(0, 4).map(e => ({ text: e.innerText.trim().slice(0, 30), bg: cs(e).backgroundColor, color: cs(e).color,
  radius: cs(e).borderRadius, border: cs(e).border, image: cs(e).backgroundImage.slice(0, 120) }));
JSON.stringify({ title: document.title, vars, fonts: [...new Set([...document.fonts].map(f => f.family))],
  fontLinks: [...document.querySelectorAll('link[href*="font"]')].map(l => l.href),
  body: pick('body'), h1: pick('h1'), h2: pick('h2'), p: pick('main p, p'), buttons, grads }, null, 1);
```

Also take a screenshot of the top of the page. Use it to:
- judge which colors dominate
- see whether headline words are gradient-filled
- spot tag pills, dots and other motifs
- find a background grid or soft glows

### With web fetch
Fetch the page and its linked CSS. Look for `:root` variables, `font-family`, Google Fonts links, `linear-gradient`, `border-radius` and button classes.

### Without either
Ask the user for a homepage screenshot or their brand guidelines.

## Turning findings into fields

| Field | What to put | Example (marianajohnels.com) |
|---|---|---|
| `name` | Brand or person name (shown as a wordmark) | `"Mariana Johnels"` |
| `domain` | Shown small in the footer | `"marianajohnels.com"` |
| `colors.background` / `background_2` | Page background, top and bottom of a soft vertical fade | `"#FFFFFF"` / `"#FBFCFF"` |
| `colors.text` / `muted` | Headline color and secondary text | `"#0A0A0A"` / `"#525252"` |
| `colors.primary` / `on_primary` | Main button fill and its text | `"#0A0A0A"` / `"#FFFFFF"` |
| `colors.accent` | Second brand color | `"#7C3AED"` |
| `colors.border` | Light outline color for pills | `"#E5E7EB"` |
| `colors.scrim` | Dark color behind text on photos | `"#0A0A0A"` |
| `colors.band` | Solid band color for the `band` layout (defaults to primary) | `"#0A0A0A"` |
| `gradient` | 2–3 stops of the brand gradient, left to right | `["#0284C7", "#7C3AED", "#F59E0B"]` |
| `glows` | Soft radial blobs on the background: `color`, `x`, `y` (0–1), `r` (radius, fraction of the short side), `strength` (0–1) | `[{"color":"#DBEAFE","x":0.2,"y":0.1,"r":0.55}]` |
| `grid` | Background grid lines: `color`, `opacity`, `size` (px at 1080) | `{"color":"#0EA5E9","opacity":0.08,"size":64}` |
| `fonts.heading` / `body` / `label` | Font file path, or `{"path": ..., "variation": "Bold"}` for variable fonts. `label` is used for buttons, tags and the wordmark | `"fonts/SpaceGrotesk_wght.ttf"` |
| `headline_tracking` | Letter spacing in em (negative = tighter) | `-0.025` |
| `headline_leading` | Line height as a multiple of font size | `1.08` |
| `headline_case` | `"none"` or `"upper"` | `"none"` |
| `button.style` | `"solid"` (primary color), `"gradient"` (brand gradient) | `"solid"` |
| `button.radius` | `"pill"` or a number of px | `"pill"` |
| `motifs` | Any of `gradient_text` (key words in the gradient), `gradient_underline`, `eyebrow_pill` (small tag above the headline), `dots` (row of brand-color dots) | `["gradient_text","eyebrow_pill","dots"]` |
| `eyebrow` | Short tag text, 2–4 words | `"Product design · UX · Systems"` |
| `logo` / `logo_on_dark` | Logo PNGs with transparency. Without one, `name` is set as a wordmark | `"logo.png"` |

Paths are relative to the `brand.json` file.

## Tips
- Choose motifs the site actually uses. A gradient headline on a brand that never uses gradients looks off-brand.
- `gradient_text` colors the words in the variant's `emphasis` (or the last word if none is given). Pick words that carry the message: "together", "the numbers".
- Gradient buttons often fail contrast. The script warns you; switch to `solid` if it does.
- Keep `glows` subtle (`strength` around 0.6–0.9 with pale colors).

## Example: marianajohnels.com

```json
{
  "name": "Mariana Johnels",
  "domain": "marianajohnels.com",
  "colors": {"background": "#FFFFFF", "background_2": "#FBFCFF", "text": "#0A0A0A", "muted": "#525252",
             "primary": "#0A0A0A", "on_primary": "#FFFFFF", "accent": "#7C3AED", "border": "#E5E7EB", "scrim": "#0A0A0A"},
  "gradient": ["#0284C7", "#7C3AED", "#F59E0B"],
  "glows": [{"color": "#DBEAFE", "x": 0.2, "y": 0.1, "r": 0.55}, {"color": "#EDE9FE", "x": 0.8, "y": 0.05, "r": 0.55}],
  "grid": {"color": "#0EA5E9", "opacity": 0.08, "size": 64},
  "headline_tracking": -0.025,
  "button": {"style": "solid", "radius": "pill"},
  "motifs": ["gradient_text", "eyebrow_pill", "dots"],
  "eyebrow": "Product design · UX · Systems"
}
```

The site uses the system font (SF Pro on Apple devices), so the bundled Inter is the closest match.
