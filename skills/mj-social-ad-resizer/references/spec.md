# Spec file reference

## Concepts stage (ad mode)

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
| `images` | plain mode, photo layouts | One or more photos. The script picks the photo whose shape best fits each frame. A value can be a path or `{path, focus}`. Leave it empty for photo-free ads (`card`, `centered`, `stats`, `type_only`). |
| `mode` | no | `plain` (default) or `ad`. |
| `stage` | no | `concepts` or `final` (default). |
| `brand` | ad mode | Path to `brand.json` (see `brand.md`) or the same object inline. |
| `concepts` | no | Layouts to show (see `layouts.md`): `editorial`, `full_bleed`, `split`, `band`, `card`, `centered`, `stats`, `type_only`. Default: `editorial`, `full_bleed`, `split` with a photo; `card`, `centered`, `type_only` without. |
| `concept_placement` | no | Size used for concepts. Default `meta_portrait`. |
| `layout` | final, ad mode | The approved layout. |
| `variants` | ad mode | `{id, headline, emphasis?, subhead?, cta?, eyebrow?, facts?}`. `emphasis` must be the end of the headline; those words get the gradient (or the brand's `value` color). `facts` is a list of `{value, label}` (e.g. `{"value": "11.6 g", "label": "protein per 100 cal"}`), shown as stat tiles or menu-style rows. With one variant, file names have no variant suffix. |
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
| `logo_on_plain` | no | Plain mode: add the brand logo in a corner (default true when a logo exists). |

## Contrast report

Both stages print a `contrast` section (also saved in `manifest.json`):

```json
"contrast": {"standard": "WCAG 2.2 AA ...", "mode": "fix",
  "issues": [{"from": "#FDB913", "to": "#BE8802", "ratio_before": 1.7, "ratio_after": 3.07,
              "needed": 3.0, "example_text": "grow a business.", "where": ["concept A", "concept B"]}]}
```

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
