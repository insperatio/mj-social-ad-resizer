# Spec file reference

Ads (ad mode) are built with `scripts/html_ads.py` in two runs: a **snapshot** of every option at one size, then the **final** sizes for the options the user picked. Plain mode (photo resizing, no text) still uses `make_images.py` directly.

## Snapshot (ad mode)

```bash
python3 scripts/html_ads.py snapshot spec.json
```

```json
{
  "name": "Insperatio",
  "output_dir": "/Users/me/Downloads/insperatio-ads",
  "mode": "ad",
  "brand": "brand.json",
  "site_layout": "site_layout.html",
  "images": {
    "wide": {"path": "photos/team.jpg", "focus": {"x": 0.5, "y": 0.42}, "subject": {"x0": 0.06, "y0": 0.22, "x1": 0.98, "y1": 0.92}},
    "tall": {"path": "photos/meeting.jpg", "focus": {"x": 0.55, "y": 0.66}}
  },
  "snapshot_placement": "meta_portrait",
  "variants": [
    {"id": "A",
     "eyebrow": "Brand · Marketing · Operations",
     "headline": "Grow with clarity, *not chaos*",
     "subhead": "Strategy, design and systems for growing teams.",
     "cta": "Book a free consultation",
     "bullets": ["Brand & messaging that builds trust", "High-converting website design", "Marketing plans with measurable results"],
     "question": "Tired of marketing that feels *scattered?*",
     "answer": "Get strategy, design and systems that actually work.",
     "punchline": "You run the business.\nWe build the systems.",
     "emoji": "🚀",
     "poster": [["Your", 1], ["brand", 2], ["deserves", 1], ["better", 2]],
     "highlight": "not chaos",
     "fine": "Free discovery call"}
  ]
}
```

Writes `<Name>_snapshot.png` (every option, numbered) and `snapshot/options.json`, and prints each option's number, id, kind (`site`, `template`, `classic`) and any issues. Options are numbered in this order: the website style, the 11 templates (`references/templates.md`), then the classic layouts (`references/layouts.md`). An option is left out, with a warning, when its copy or photo is missing (e.g. no bullets for `headline_3_bullets`, no `facts` for `stats`).

Optional: `"templates": [...]` and `"classic": [...]` to limit what's shown (default: all), `"snapshot_placement"` (default `meta_portrait`).

## Final (ad mode)

Same file, plus the user's picks and the placements:

```json
{
  "picks": ["site", "headline_3_bullets", "split"],
  "placements": ["meta_square", "meta_portrait", "meta_story"],
  "format": "png"
}
```

```bash
python3 scripts/html_ads.py final spec.json
```

Each pick gets its own subfolder (`site/`, `headline_3_bullets/`, `split/`) with one file per placement and variant (`Insperatio_site_IG-4x5.png`), plus `<Name>_contact-sheet.png` and one `manifest.json` for everything. Classic picks are rendered by `make_images.py` with the same spec. `"only": ["site:meta_story"]` (or a pick id, or a placement) re-renders just those.

The final output prints `contrast_fixes` (from → to, ratio before/after, the text) and `warnings` (dropped copy, enlarged photos, photo swapped for a gradient, logo height-capped, contrast that couldn't be fixed). Report the ones that matter.

---

# Classic renderer (make_images.py)

Used directly for plain mode, and by `html_ads.py` for the classic layouts.

## Concepts stage (classic only)

```json
{
  "name": "Mariana Johnels",
  "output_dir": "/Users/me/Downloads/mj-ads",
  "mode": "ad",
  "stage": "concepts",
  "brand": "brand.json",
  "images": {
    "wide": {"path": "photo-wide.jpg", "focus": {"x": 0.45, "y": 0.4}},
    "tall": {"path": "photo-tall.jpg", "focus": {"x": 0.5, "y": 0.35}}
  },
  "concepts": ["editorial", "stats", "split", "full_bleed"],
  "concept_placement": "meta_portrait",
  "variants": [
    {"id": "A", "headline": "Let's work together", "emphasis": "together", "cta": "Book a call",
     "facts": [{"value": "$9.3M", "label": "Realized revenue impact"}, {"value": "+134%", "label": "Referral share rate lift"}]}
  ]
}
```

### Without a photo

```json
{
  "name": "GLPKitchen", "output_dir": "/Users/me/Downloads/glp-ads", "mode": "ad", "stage": "concepts",
  "brand": "glp_brand.json", "images": {},
  "concepts": ["card", "centered", "type_only", "stats"],
  "variants": [{"id": "A", "headline": "What to eat when you don't feel like eating.",
    "subhead": "And what to cook when you do again.",
    "facts": [{"label": "protein per 100 cal", "value": "11.6 g"}, {"label": "minutes, start to plate", "value": "15"}],
    "cta": "See the menu"}]
}
```

## Final stage

Same file, with:

```json
{
  "stage": "final",
  "layout": "full_bleed",
  "placements": ["meta_square", "meta_portrait", "meta_story"],
  "format": "png",
  "link": "https://marianajohnels.com",
  "variants": [
    {"id": "A", "headline": "Let's work together", "emphasis": "together", "cta": "Book a call"},
    {"id": "B", "headline": "Design that moves the numbers", "emphasis": "the numbers",
     "subhead": "Product experiences, systems and teams.", "cta": "Book a call"}
  ]
}
```

## Fields

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Used in file names (`Mariana_Johnels_IG-4x5_A.png`). |
| `output_dir` | yes | The connected export folder. Concepts go in a `concepts/` subfolder. |
| `images` | plain mode, photo layouts | One or more photos. The script picks the photo whose shape best fits each frame. A value can be a path or `{path, focus, subject}`. `subject` is the main subject's bounds `{x0, y0, x1, y1}` (fractions); without it, a box around `focus` is assumed. Leave it empty for photo-free ads (`card`, `centered`, `stats`, `type_only`). |
| `mode` | no | `plain` (default) or `ad`. |
| `stage` | no | `concepts` or `final` (default). |
| `brand` | ad mode | Path to `brand.json` (see `brand.md`) or the same object inline. |
| `concepts` | no | Layouts to show (see `layouts.md`): `editorial`, `full_bleed`, `split`, `band`, `card`, `centered`, `stats`, `type_only`. Default: `editorial`, `full_bleed`, `split` with a photo; `card`, `centered`, `type_only` without. |
| `concept_placement` | no | Size used for concepts. Default `meta_portrait`. |
| `layout` | final, ad mode | The approved layout. |
| `variants` | ad mode | `{id, headline, emphasis?, subhead?, cta?, eyebrow?, facts?}`. `emphasis` must be the end of the headline; those words get the gradient (or the brand's `value` color). `facts` is a list of `{value, label}` (e.g. `{"value": "11.6 g", "label": "protein per 100 cal"}`), shown as stat tiles or menu-style rows. With one variant, file names have no variant suffix. |
| `logo` | no | `{"logo": "logo/logo.png", "logo_on_dark": "logo/logo_on_dark.png"}`, usually from `prepare_logo.py`. Overrides the brand profile's logo files. |
| `use_logo` | no | `false` when the user doesn't want a logo. Default: use the logo if one exists. |
| `show_wordmark` | no | `false` to also drop the brand name shown as text when there's no logo. |
| `logo_position` | no | Plain mode: `top-right` (default), `top-left`, `bottom-right`, `bottom-left`. |
| `photo_fallback` | no | What replaces the photo when its subject wouldn't be visible: `auto` (default: brand gradient, else pattern, else color), `gradient`, `pattern`, `color`, or `never` to always use the photo. |
| `min_subject_visible` | no | Share of the subject that must stay in the crop (default 0.6). |
| `min_subject_size` | no | Smallest subject height, as a share of the ad's short side (default 0.12). |
| `show_url` | no | `false` to leave the website address off the ads. |
| `url_text` | no | Address to show instead of the brand domain, e.g. `"snhu.edu/business"`. |
| `contrast` | no | `fix` (default): every line of text is measured against the pixels behind it, and colors below WCAG 2.2 AA (4.5:1, or 3:1 for headline-size text) are adjusted within the same hue. `warn`: report only. `off`: no check (not recommended). |
| `facts_on_photo_layouts` | no | Show `facts` in `editorial`, `full_bleed`, `split` and `band` too. Default false. |
| `placements` | no | Keys from `placements.md`. Default: all. |
| `format` | no | `webp` (default), `png`, `jpg`. |
| `quality` | no | WebP/JPG quality, default 85. |
| `fill` | no | `auto` (default): crop unless too much would be lost, then blur fill. `crop`, `blur`, `color` force one style. |
| `max_crop_loss` | no | 0–1. Default 0.75 in ad mode, 0.6 in plain mode. |
| `link`, `campaign` | no | Builds a tracking (UTM) link for each platform in the manifest. |
| `post_content` | no | Captions, alt text, pin titles; copied into `manifest.json`. |
| `only` | no | Re-render just these, e.g. `["pinterest_B"]` or `["meta_story"]`; the manifest is merged. |
| `logo_on_plain` | no | Plain mode: add the logo in a corner (default true when a logo exists and `use_logo` isn't false). |

## Contrast report

Both stages print a `contrast` section (also saved in `manifest.json`):

```json
"contrast": {"standard": "WCAG 2.2 AA ...", "mode": "fix",
  "issues": [{"from": "#FDB913", "to": "#BE8802", "ratio_before": 1.7, "ratio_after": 3.07,
              "needed": 3.0, "example_text": "grow a business.", "where": ["concept A", "concept B"]}]}
```

## Brand report

Both stages write `<Name>_brand-report.png` and return `brand_report`:

```json
"brand_report": {
  "colors": [{"hex": "#0A2551", "used_for": ["button", "color band", "headline"]}, ...],
  "fonts": [{"family": "Inter", "style": "Bold", "file": "Inter-Bold.otf", "used_for": ["headline"]}, ...],
  "logos": {"logo": ["light background"], "logo_on_dark": ["dark background"]},
  "contrast_fixes": [{"from": "#FDB913", "to": "#BE8802", "ratio": "1.7:1 → 3.07:1"}]
}
```

The final stage also saves it in `manifest.json`.

## Minimum text sizes

Text never goes below these sizes. They're a share of the image width, so they read at about 10–11 px on a phone:
- tags and labels: 2.6%
- domain: 2.4%
- body and subhead: 2.9%
- facts and CTA: 2.8%
- headline: 5%

If copy doesn't fit, the subhead, facts, tag and wordmark are left out in that order, with a warning.

## Warnings the script prints
- A photo was enlarged (soft result).
- Contrast fixes (or, in `warn` mode, contrast failures) for any text, including buttons, tags and text over photos.
- Copy left out to keep the rest legible at a size.
- Text too long for a size.
- A brand file (font, logo) was not found, so the default was used.
