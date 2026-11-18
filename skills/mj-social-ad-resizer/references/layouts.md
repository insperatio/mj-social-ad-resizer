# Layouts and how to pick them

Every layout reads the brand profile: colors, fonts, motifs and the **layout DNA** in `brand.json → style` (alignment, photo shape, frames, dividers, label style, button style). The same layout looks different for each brand, and the brand's DNA decides which layouts to offer.

## The layouts

| Layout | Photo | What it looks like | Good for |
|---|---|---|---|
| `editorial` | required | Brand background (grid, glows) with the headline on top and the photo below; on wide sizes, side by side. Uses the brand's photo shape (rounded, arch) | Clean modern sites, portfolios, SaaS |
| `full_bleed` | required | Photo fills the frame with a dark gradient behind the text. Centered brands get centered text over an evenly darkened photo | Strong photography, food, travel, fashion |
| `split` | required | Brand panel on one side, photo on the other, with a gradient or accent divider. Tall sizes stack the panel above the photo | Brands with a clear accent color or gradient |
| `band` | required | Photo with a solid brand-color band holding the text | Brands with one strong solid color |
| `card` | optional | A surface card (paper, white, tinted) floating over the photo or a dark brand background, with a frame and divider when the brand uses them. Facts show as menu-style rows with dotted leaders | Editorial, restaurant, boutique and print-feeling brands; ads with key facts |
| `centered` | optional | Centered stack: wordmark, label, headline, divider, the photo in the brand's shape, then tagline and CTA. Without a photo it's a typographic poster | Classic, symmetrical, luxury and editorial brands |
| `stats` | none | Headline plus 1–4 big-number tiles from `facts` | Results, metrics, B2B, case studies, nutrition numbers |
| `type_only` | none | A large headline on the brand background, with optional frame, facts and CTA | Bold statements, quotes, announcements, no photo |

**Without a photo**, use `card`, `centered`, `stats`, `type_only`. First try to get photos from the brand's own site (see SKILL.md).

## Reading the layout DNA from a site

Look at the hero and the main content blocks:

| What you see on the site | Set in `style` |
|---|---|
| Hero text centered, symmetrical sections | `"align": "center"` |
| Left-aligned hero, asymmetric grid | `"align": "left"` |
| Rounded image cards | `"photo_shape": "rounded"`, `"radius"`: the card radius in px |
| Circular portraits or round images | `"photo_shape": "circle"` |
| Arched windows or doorway shapes | `"photo_shape": "arch"` |
| Square-cornered, edge-to-edge images | `"photo_shape": "rect"` |
| Thin rules around boxes, double borders, menu or print feel | `"frame": "single"` or `"double"` |
| Line with an ornament (❦, ◆) between sections | `"divider": "ornament"` |
| Plain hairline between sections | `"divider": "line"` |
| Gradient bar or rule | `"divider": "gradient"` |
| Small uppercase, letter-spaced labels | `"eyebrow": "caps"` |
| Small rounded tag above the headline | `"eyebrow": "pill"` |
| Italic serif taglines | `"subhead_italic": true` plus `fonts.accent` (the italic file) |
| Calls to action as underlined uppercase text links | `button.style: "link"` |
| Solid filled buttons | `button.style: "solid"`, `radius: "pill"` or px |
| Gradient buttons | `button.style: "gradient"` (check the contrast warning) |
| Outline buttons | `button.style: "outline"` |
| Cards that float on dark backgrounds with deep shadows | `"shadow": true`, `dark_background` set to that dark color |
| Colored metric tiles | `tiles`: one `{bg, fg}` per tile color |

## Choosing the concepts to show

Pick 3–4 layouts that fit the DNA and the material. Make sure they differ from each other: don't offer three photo-on-top layouts.

- **Centered, framed, serif brands** (restaurants, editorial, boutique): `card`, `centered`, `full_bleed`; add `type_only` or `stats` when there are facts.
- **Left-aligned modern brands** (SaaS, portfolios, agencies): `editorial`, `split`, `full_bleed`; add `stats` when there are numbers.
- **Brands with one strong solid color**: include `band`.
- **No photo**: `card`, `centered`, `type_only`, and `stats` if there are facts.
- **Metrics in the copy** (revenue, %, grams, minutes): include `stats`, and pass them as `facts`.

`facts` show in `card`, `centered`, `stats` and `type_only`. Photo layouts skip them unless the spec sets `"facts_on_photo_layouts": true`.
