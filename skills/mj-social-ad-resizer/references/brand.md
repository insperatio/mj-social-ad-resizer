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

Also take a screenshot of the top of the page, and scroll to see the main content blocks. Use them to:
- judge which colors dominate
- see whether headline words are gradient-filled
- spot tag pills, dots and other motifs
- find a background grid or soft glows
- read the **layout DNA**: alignment, image shapes, frames, dividers, label style, button style (see `layouts.md`)
- list the page's images (`[...document.images].map(i => [i.currentSrc, i.naturalWidth, i.naturalHeight])`) in case the user has no photo

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
| `button.style` | `"solid"` (primary color), `"gradient"` (brand gradient), `"outline"`, `"link"` (underlined uppercase text link) | `"solid"` |
| `button.radius` | `"pill"` or a number of px | `"pill"` |
| `motifs` | Any of `gradient_text` (key words in the gradient), `gradient_underline`, `eyebrow_pill` / `eyebrow_caps` (shortcuts for `style.eyebrow`), `gradient_divider`, `dots` (row of brand-color dots) | `["gradient_text","eyebrow_pill","dots"]` |
| `eyebrow` | Short tag text, 2–4 words | `"Product design · UX · Systems"` |
| `logo` / `logo_on_dark` | Logo PNGs with transparency, for light and dark backgrounds. Make them with `scripts/prepare_logo.py`. Without a logo, `name` is set as a text wordmark | `"logo/logo.png"` |
| `logo_min_width` | Smallest logo width as a share of the ad's width (default 1/3). The logo only gets smaller where it physically can't fit, with a warning | `0.4` |
| `colors.on_dark` | Text color on photos and dark backgrounds (e.g. cream instead of pure white) | `"#F6F0E2"` |
| `colors.surface` / `surface_text` | Card color and its text, for the `card` layout | `"#F6F0E2"` / `"#1C1712"` |
| `colors.link` | Color of link-style CTAs | `"#8B2E2E"` |
| `colors.value` | Color of fact values and emphasis words (numbers, grams, minutes) | `"#3E6B3A"` |
| `colors.value_on_dark` / `link_on_dark` | Optional replacements on dark backgrounds. By default the brand color is used as-is on dark backgrounds and only adjusted if it fails contrast | `"#FFD166"` |
| `colors.value_on_light` / `link_on_light` | Optional replacements for `value` / `link` on light backgrounds, for brand colors that fail contrast on white (e.g. a bright yellow). Without them, the script darkens the color automatically | `"#8A6100"` |
| `fonts.accent` | Italic or display font for taglines (used when `style.subhead_italic` is true) | `{"path": "fonts/Vollkorn-Italic_wght.ttf", "variation": "Italic"}` |
| `fonts.wordmark` | Font for the brand name when there is no logo (defaults to `label`) | `{"path": "fonts/Vollkorn_wght.ttf", "variation": "SemiBold"}` |
| `tiles` | Colors for `stats` tiles: list of `{bg, fg}` | `[{"bg":"#EFF6FF","fg":"#0369A1"}]` |
| `style` | The **layout DNA**: `align`, `photo_shape`, `radius`, `frame`, `divider`, `eyebrow`, `shadow`, `dark_background`, `subhead_italic`. See `layouts.md` for how to read these from a site | `{"align": "center", "frame": "double"}` |

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
  "tiles": [{"bg": "#EFF6FF", "fg": "#0369A1"}, {"bg": "#ECFDF5", "fg": "#047857"},
            {"bg": "#F5F3FF", "fg": "#6D28D9"}, {"bg": "#FFFBEB", "fg": "#B45309"}],
  "motifs": ["gradient_text", "eyebrow_pill", "dots"],
  "eyebrow": "Product design · UX · Systems",
  "style": {"align": "left", "photo_shape": "rounded", "radius": 28}
}
```

The site uses the system font (SF Pro on Apple devices), so the bundled Inter is the closest match.

## Example: glpkitchen.com (a very different brand)

Dark espresso and cream paper, serif headlines with italic taglines, uppercase tracked labels, a centered menu card with a double rule, an ornament divider, and red text-link CTAs.

```json
{
  "name": "GLPKitchen",
  "domain": "glpkitchen.com",
  "colors": {"background": "#F6F0E2", "background_2": "#EFE6D2", "text": "#1C1712", "muted": "#6B5D4F",
             "primary": "#1C1712", "on_primary": "#F6F0E2", "accent": "#8B2E2E", "border": "#CDBFA6",
             "scrim": "#1C1712", "on_dark": "#F6F0E2", "surface": "#F6F0E2", "surface_text": "#1C1712",
             "link": "#8B2E2E", "value": "#3E6B3A", "band": "#1C1712"},
  "fonts": {
    "heading":  {"path": "fonts/Vollkorn_wght.ttf", "variation": "SemiBold"},
    "accent":   {"path": "fonts/Vollkorn-Italic_wght.ttf", "variation": "Italic"},
    "wordmark": {"path": "fonts/Vollkorn_wght.ttf", "variation": "SemiBold"},
    "body":     {"path": "fonts/Jost_wght.ttf", "variation": "Regular"},
    "label":    {"path": "fonts/Jost_wght.ttf", "variation": "Medium"}
  },
  "headline_tracking": 0, "headline_leading": 1.12,
  "button": {"style": "link"},
  "eyebrow": "Real food for GLP-1",
  "style": {"align": "center", "photo_shape": "rounded", "radius": 6, "frame": "double", "divider": "ornament",
            "eyebrow": "caps", "shadow": true, "subhead_italic": true, "dark_background": "#1C1712"}
}
```

Fonts were fetched with `python3 scripts/fetch_font.py Vollkorn fonts` and `... Jost fonts`.

## Contrast

Brand colors are checked where they land, not in isolation. A bright yellow can pass on navy and fail on white. The renderer measures each line of text against the pixels behind it and adjusts failing colors (see `spec.md`, "Contrast report"). Record the brand's own accessible alternatives in `value_on_light` / `link_on_light` when the guidelines provide them.

