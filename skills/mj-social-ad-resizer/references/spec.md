# Spec file reference

```json
{
  "name": "Spring Sale",
  "output_dir": "/path/to/connected/folder/spring-sale",
  "mode": "ad",
  "format": "webp",
  "quality": 85,
  "link": "https://example.com/sale",
  "campaign": "spring-sale",
  "images": {
    "landscape": {"path": "photo-wide.jpg", "focus": {"x": 0.7, "y": 0.45}},
    "portrait": "photo-tall.jpg"
  },
  "placements": ["meta_square", "meta_portrait", "meta_story", "pinterest", "link_preview", "x_post"],
  "fill": "auto",
  "max_crop_loss": 0.45,
  "brand": {
    "primary": "#1E3A5F",
    "on_primary": "#FFFFFF",
    "accent": "#F2B705",
    "on_accent": "#111111",
    "logo": "logo.png",
    "logo_position": "top-right",
    "logo_scale": 0.16,
    "font_heading": "fonts/Brand-Bold.ttf",
    "font_body": "fonts/Brand-Regular.ttf",
    "font_cta": "fonts/Brand-SemiBold.ttf"
  },
  "variants": [
    {"id": "A", "headline": "Fresh spring styles, 30% off this week", "subhead": "Free shipping over $50", "cta": "Shop now"},
    {"id": "B", "headline": "Your spring refresh starts here", "cta": "See the collection"}
  ],
  "post_content": {},
  "only": []
}
```

| Field | Required | Notes |
|---|---|---|
| `name` | yes | Used in file names (`Spring_Sale_PT_A.webp`). |
| `output_dir` | yes | The connected export folder (or a subfolder). |
| `images` | yes | One or more photos. Keys are free labels. The script picks the photo whose shape best matches each frame. A value can be a path or `{path, focus}`. |
| `mode` | no | `plain` (default) or `ad`. |
| `variants` | ad mode | One or more `{id, headline, subhead?, cta?}`. With one variant, file names have no variant suffix. |
| `placements` | no | Keys from `placements.md`. Default: all. |
| `format` | no | `webp` (default), `png`, `jpg`. |
| `quality` | no | WebP/JPG quality, default 85. |
| `fill` | no | `auto` (default): crop unless more than `max_crop_loss` of the photo would be cut, then blur fill. `crop`, `blur` or `color` force one style. |
| `max_crop_loss` | no | 0–1, default 0.45. |
| `brand.*` | no | All optional. Text color is picked automatically for contrast if `on_primary` / `on_accent` are missing. Logo should be a PNG with transparency. |
| `link`, `campaign` | no | Builds a UTM link for each platform in the manifest. |
| `post_content` | no | Captions, alt text, pin titles. Copied into `manifest.json` as is. |
| `only` | no | Re-render just these, e.g. `["pinterest_B"]` or `["meta_story"]`. |

## Layouts (ad mode)
- **Tall and square frames:** photo on top, brand band at the bottom with the headline, subhead and CTA button.
- **Wide frames (link preview, X):** photo on the left, band on the right.
- **Stories:** the band grows upward so the text stays above the bottom safe zone.

## Warnings the script reports
- The photo was upscaled (soft result).
- Text contrast or CTA contrast is under WCAG AA 4.5:1.
- The CTA color blends into the band.
- Text too long to fit.
