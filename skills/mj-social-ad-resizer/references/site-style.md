# Website-style option (`site`)

This option is not a template. It copies the structure of the brand's own homepage hero, so the ad looks like the site, not like one of the shared layouts. You write it per brand as one HTML file, `site_layout.html`, set `"site_layout": "site_layout.html"` in the spec, and the renderer builds every size from it with the same checks as the templates.

Always include it in the snapshot. Skip it only when the site has no clear hero (then say so).

## 1. Study the hero

With a browser tool, open the homepage and measure the hero section (the first full-width block):

```js
const cs = e => getComputedStyle(e);
const h1 = document.querySelector('h1') || document.querySelector('h2');
let hero = h1; for (let i = 0; i < 8 && hero; i++) { if (hero.offsetHeight > 300) break; hero = hero.parentElement; }
const layers = [];
for (const k of [hero, ...hero.querySelectorAll('*')]) for (const pe of [null, '::before', '::after']) {
  const s = cs(k, pe);
  if (s.backgroundImage !== 'none' || (pe && s.content !== 'none' && s.backgroundColor !== 'rgba(0, 0, 0, 0)'))
    layers.push({el: k.tagName + '.' + String(k.className).slice(0, 40), pe, img: s.backgroundImage.slice(0, 160),
                 bg: s.backgroundColor, op: s.opacity, blend: s.mixBlendMode, clip: s.clipPath.slice(0, 100)});
}
const btn = [...hero.querySelectorAll('a,button')].find(a => a.offsetWidth > 80);
JSON.stringify({heroBg: cs(hero).backgroundColor, heroH: hero.offsetHeight, layers,
  imgs: [...hero.querySelectorAll('img')].map(i => [i.currentSrc.split('?')[0].slice(-80), i.naturalWidth, cs(i).mixBlendMode, cs(i).borderRadius, cs(i).objectFit]),
  h1: {font: cs(h1).fontFamily, size: cs(h1).fontSize, weight: cs(h1).fontWeight, color: cs(h1).color, align: cs(h1).textAlign, shadow: cs(h1).textShadow},
  btn: btn && {bg: cs(btn).backgroundColor, color: cs(btn).color, radius: cs(btn).borderRadius, border: cs(btn).border, text: btn.innerText.trim()}}, null, 1)
```

Also take a screenshot of the hero. Write down, in plain words:
- **Background:** solid color, photo, tinted photo, texture or pattern image (and its blend mode), gradient, overlays.
- **Composition:** where the text sits (left, centered, in a panel), where the photo sits (full bleed, side, rounded card), diagonal or curved edges, decorative shapes.
- **Type:** headline weight, size relative to the frame, case, tracking; eyebrow or tag style; subhead.
- **Button:** fill or outline, radius (including odd shapes like one square corner), arrow or chevron.

## 2. Save the hero's visual assets

Background photos, textures and pattern images become files next to the spec (e.g. `photos/hero.jpg`, `photos/texture.png`). Use `fetch_site_images.py`, or open the image URL in the browser, make it fill the window, and save a screenshot (see SKILL.md Step 3). Only the brand's own site. Never stretch an image; use `background-size: cover` with a position.

## 3. Write `site_layout.html`

An HTML fragment (a `<style>` block plus markup). Relative paths resolve from the spec's folder. The renderer injects:

**CSS variables**
- Brand tokens: `--ink`, `--ink-alt`, `--primary`, `--on-primary`, `--text-accent`, `--text-accent-dark`, `--surface`, `--tint`, `--dark`, `--shape2`, `--shape3`, `--cream`, `--grey`, `--grad-a`, `--grad-b`, `--grad-text`, `--radius`
- Fonts: `--font-head`, `--font-body`, `--font-label` (family names) and `--w-head`, `--w-body`, `--w-label` (weights). Companion families `CompanionSerif` (italic and regular) and `CompanionCondensed` are also loaded.
- Size: `--w`, `--h`, `--s` (scale: 1 at 1080 wide; height-based on wide sizes; boosted on Stories and pins), `--fit` (shrinks to 0.7 when content collides), `--pt`, `--pb` (Stories safe zones in px; 0 elsewhere)
- Minimum font sizes: `--min-h`, `--min-b`, `--min-c`, `--min-l`, `--min-u`

**Body class** for the frame shape: `r-sq`, `r-portrait` (4:5), `r-tall` (2:3), `r-story` (9:16), `r-wide` (1.91:1, 16:9).

**Placeholders:** `{{headline}}` (with `<span class="emph">` around starred words), `{{headline_plain}}`, `{{subhead}}`, `{{eyebrow}}`, `{{cta}}`, `{{fine}}`, `{{url}}`, `{{bullets}}` (`<li>` items), `{{logo}}` (for light backgrounds), `{{logo_on_dark}}`, `{{photo}}` / `{{photo_wide}}` / `{{photo_half}}` (a CSS background value for the spec's photos, cropped around the focus for a full, half-height or half-width frame).

**Rules**
- Size everything with `calc(var(--s) * Npx)` (N = the size at 1080 wide). Font sizes: `font-size: max(var(--min-b), calc(var(--s) * var(--fit) * 34px))`, using the matching minimum (`--min-h` headline, `--min-b` body, `--min-c` CTA, `--min-l` tags and fine print, `--min-u` URL).
- Keep text out of the Stories safe zones: offset top content by `var(--pt)` and bottom content by `var(--pb)`. Backgrounds still bleed to the edges.
- Mark every text element with `data-check`: `h` headline, `b` body, `c` CTA, `l` tag/label/fine print, `u` URL. Mark leaveable text with `data-optional="eyebrow"`, `"subhead"` or `"url"`.
- Logos come only from `{{logo}}` / `{{logo_on_dark}}` (they're sized to a third of the width and checked).
- Add `body.r-wide` rules (usually text left, image right) and check `r-story` spacing.
- Emphasis color: style `.emph` (e.g. `h1 .emph { color: var(--text-accent-dark); }`).

## Example: insperatio.com

Hero: indigo-tinted office photo with a line grid, centered heavy white DM Sans headline, outline button with a chevron, centered logo.

```html
<style>
  body { background: #3B3FA8 url('photos/ins-hero.jpg') 62% 50% / cover; font-family: var(--font-head); }
  .shade { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(31,33,120,.55) 0%, rgba(31,33,120,.25) 45%, rgba(25,27,100,.7) 100%); }
  .top { position: absolute; left: 0; right: 0; top: calc(var(--pt) + var(--s) * 64px); display: flex; justify-content: center; }
  .mid { position: absolute; left: calc(var(--s) * 70px); right: calc(var(--s) * 70px); top: calc(var(--pt) + var(--s) * 200px);
         bottom: calc(var(--pb) + var(--s) * 130px); display: flex; flex-direction: column; align-items: center; justify-content: center;
         text-align: center; gap: calc(var(--s) * 30px); }
  .pill { color: #fff; border: calc(var(--s) * 2px) solid rgba(255,255,255,.8); border-radius: 999px; padding: calc(var(--s) * 10px) calc(var(--s) * 26px);
          font-family: var(--font-label); font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
          font-size: max(var(--min-l), calc(var(--s) * var(--fit) * 28px)); }
  h1 { color: #fff; font-weight: 900; line-height: 1.06; letter-spacing: -.02em; font-size: max(var(--min-h), calc(var(--s) * var(--fit) * 96px)); }
  p { color: #fff; font-family: var(--font-body); font-weight: 700; line-height: 1.35; max-width: calc(var(--s) * 860px);
      font-size: max(var(--min-b), calc(var(--s) * var(--fit) * 34px)); }
  .btn { border: calc(var(--s) * 2px) solid #fff; border-radius: calc(var(--s) * 6px); padding: calc(var(--s) * 20px) calc(var(--s) * 40px); }
  .btn span { color: #fff; font-weight: 700; font-size: max(var(--min-c), calc(var(--s) * var(--fit) * 32px)); }
  .url { position: absolute; left: 0; right: 0; bottom: calc(var(--pb) + var(--s) * 50px); text-align: center; color: #fff; font-weight: 700;
         letter-spacing: .04em; font-size: max(var(--min-u), calc(var(--s) * 28px)); }
  body.r-wide .top { justify-content: flex-start; left: calc(var(--s) * 60px); top: calc(var(--s) * 50px); }
  body.r-wide .mid { align-items: flex-start; text-align: left; left: calc(var(--s) * 60px); right: 38%; top: calc(var(--s) * 150px); bottom: calc(var(--s) * 60px); }
  body.r-wide .url { left: auto; right: calc(var(--s) * 60px); text-align: right; }
  body.r-wide .shade { background: linear-gradient(90deg, rgba(25,27,100,.8) 0%, rgba(31,33,120,.35) 70%, rgba(31,33,120,.2) 100%); }
</style>
<div class="shade"></div>
<div class="top">{{logo_on_dark}}</div>
<div class="mid">
  <div class="pill" data-check="l" data-optional="eyebrow">{{eyebrow}}</div>
  <h1 data-check="h">{{headline}}</h1>
  <p data-check="b" data-optional="subhead">{{subhead}}</p>
  <div class="btn"><span data-check="c">{{cta}} &nbsp;›</span></div>
</div>
<div class="url" data-check="u" data-optional="url">{{url}}</div>
```

## Other hero patterns and how to rebuild them

| Hero pattern (example) | How to build it |
|---|---|
| Solid brand color with a texture image in a blend mode (skills.snhu.edu: Ink Blue + triangle texture in `color-burn`) | `body { background: var(--dark); }` plus an absolutely positioned div with the texture as `background: url(...) center/cover; mix-blend-mode: color-burn;` Copy left, rounded photo card right (`border-radius` from the site); on tall sizes the photo moves under the copy. |
| Lifestyle photo with a diagonal split and a navy panel (ucbi.com) | Photo block on top using `{{photo}}` or the hero file; a panel with `clip-path: polygon(0 calc(var(--s)*160px), 100% 0, 100% 100%, 0 100%)` holding the copy; the site's leaf-shaped button (`border-radius: 32px 0 32px 32px`, scaled). |
| Centered type over a video still or gradient | Hero frame as the background, the site's exact headline weight and case, the button copied from the site. |

If a fix is needed after the snapshot ("make the logo bigger", "use the second photo"), edit `site_layout.html` and re-run.
