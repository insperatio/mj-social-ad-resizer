# mj-social-ad-resizer

Free agent skill that turns your website and photos into on-brand social images and ads for Meta (Facebook/Instagram), LinkedIn, X and Pinterest.

- **Plain mode:** crops and resizes your photo for every placement you pick.
- **Ad mode:** reads your website's look (colors, fonts, gradients, background patterns, button style) **and its layout patterns** (centered or left-aligned, photo shapes, frames, dividers, label and link styles), so each brand gets its own structure.
- **No photo? No problem:** use photos from your own site, or go photo-free with menu-style cards, typographic posters or stat tiles.
- **Concepts first:** see 3–4 layout directions side by side, pick one, then every size is rendered in that style.
- Optional **A/B variants** and **post text for each platform** (captions, alt text, hashtags, UTM links).
- Exports **PNG, JPG or WebP** to a folder you choose, with a contact sheet and a `manifest.json`.
- **Accessible by default:** every line of text is checked against the pixels behind it (WCAG 2.2 AA), and failing brand colors are adjusted within the same hue. Text never goes below a size that's readable on a phone; extra copy is left out first, and you're told.
- Warns about low-resolution photos.

No AI image generation, no API keys, and it never publishes or schedules anything.

---

## Install

### Claude Code, Cursor, Codex and other agents

```bash
npx skills add insperatio/mj-social-ad-resizer
```

### Claude.ai (web or desktop app)

1. Download this repo: **Code → Download ZIP**, then unzip it.
2. Zip just the `skills/mj-social-ad-resizer` folder.
3. In Claude, go to **Settings → Capabilities → Skills** and upload that ZIP.
4. Make sure code execution is turned on in the same settings page; the skill runs a small Python script.

---

## How to use it

### 1. Start with a photo and your website

Attach your photo and ask, for example:

> Build me an ad for Meta. Headline: "Let's work together". CTA: "Book a call". Use marianajohnels.com for branding (colors, fonts, graphic elements). Show concepts for approval, then save PNGs to my Downloads folder.

> Resize this photo for Meta, LinkedIn and X. No text.

For the best crops, attach **two photos**: one landscape (wide) and one portrait (tall), each at least **1080 px** on the short side. One photo also works.

**No photo?** Just give the website:

> Make Meta ads for glpkitchen.com. Headline: "What to eat when you don't feel like eating." No photo.

Claude offers photos from your own site, or photo-free designs.

### 2. Answer a few questions

Claude asks only for what you haven't already given it:

| Question | What to answer |
|---|---|
| Platforms | Any of Meta (Facebook/Instagram), LinkedIn, X, Pinterest |
| Plain image or ad? | **Plain** = just resized photos. **Ad** = on-brand design with headline and button |
| Ad copy | Headline, optional subhead, call to action, and who the ad is for. Add key numbers (e.g. "11.6 g protein per 100 cal", "+134% lift") to get stat tiles or menu-style fact rows |
| Branding | Your website URL. Brand guidelines and font files are optional extras |
| Logo? | Yes or no. If yes, Claude can **grab it from your website** or you can **upload it** (SVG, or a PNG with a transparent background, is best). It removes backgrounds, trims the logo, and makes a white version for dark backgrounds when your logo is one color |
| A/B variants? | Yes = Claude writes 2–3 headline versions for you to approve |
| Post text for each platform? | Yes = captions, hashtags, alt text and pin titles |
| Format | PNG, JPG or WebP |

### 3. Check the brand summary

Claude reads your site and sums up both the look and the layout patterns, for example:

- *marianajohnels.com:* "Left-aligned, black headlines with a blue → violet → amber gradient on the key words, white background with a faint blue grid, rounded photos, pastel stat tiles, black pill buttons."
- *glpkitchen.com:* "Centered menu-card style: cream paper card with a double rule on espresso, serif headline, italic tagline, small caps labels, ornament divider, red text-link CTA."

Correct anything that's off.

Sites built with JavaScript read best when Claude has a browser tool. Without one, Claude may ask for a screenshot of your homepage.

**Fonts:** Google Fonts are downloaded automatically. Paid or system fonts can't be downloaded, so Claude uses the closest free match and tells you which one. Upload your font files if you want an exact match.

### 4. Pick a concept

You get a concept sheet with 3–4 directions at one size. Claude picks them to fit your brand's layout patterns:

| Concept | Look | Needs a photo |
|---|---|---|
| Editorial | Your site's background, headline on top, photo below (in your photo shape) | yes |
| Full bleed | Photo fills the frame, dark gradient behind the text | yes |
| Split panel | Brand panel on one side, photo on the other | yes |
| Color band | Photo with a solid brand-color band holding the text | yes |
| Card | A paper or white card over the photo or a dark background, with your frame, divider and fact rows | optional |
| Centered | Symmetrical stack, photo in your brand's shape, or a typographic poster | optional |
| Stat tiles | Headline plus big-number tiles in your colors | no |
| Type only | A large headline on your brand background | no |

Pick one, or ask for changes ("put *together* in the gradient", "use the gradient on the button"). Nothing else is rendered until you approve.

### 5. Choose where to save

Claude asks you to connect a folder (e.g. Downloads). In the Claude desktop app, approve the folder-access prompt. If no folder can be connected, Claude sends the files in the chat instead.

### 6. Review every size

A contact sheet shows all sizes in your chosen style. Ask for fixes in plain words, and only that size is redone:

> The Pinterest pin cuts off his face, move the crop up.

> Shorten the headline on the link preview.

### 7. Get your files

The folder will contain:

```
Mariana_Johnels_IG-1x1_A.png     Meta feed 1080×1080
Mariana_Johnels_IG-4x5_A.png     Meta feed 1080×1350
Mariana_Johnels_STORY_A.png      Meta Stories/Reels 1080×1920
Mariana_Johnels_LI-1x1_A.png     LinkedIn 1200×1200
Mariana_Johnels_X_A.png          X 1600×900
Mariana_Johnels_PT_A.png         Pinterest 1000×1500
Mariana_Johnels_FB_A.png         Link preview 1200×630
Mariana_Johnels_contact-sheet.png
manifest.json                    Sizes, tracking links, captions, alt text
concepts/                        The concept images you chose from
```

`_A`, `_B` mark A/B variants (no suffix when there's only one version). Upload the images and paste the captions yourself. The skill never posts for you.

---

## Sizes

| Placement | Size | Used for |
|---|---|---|
| Meta feed 1:1 | 1080 × 1080 | Facebook / Instagram feed |
| Meta feed 4:5 | 1080 × 1350 | Facebook / Instagram feed (more screen space) |
| Meta Stories / Reels | 1080 × 1920 | Stories, Reels cover (text kept clear of the app's buttons) |
| LinkedIn 1:1 | 1200 × 1200 | LinkedIn feed image |
| X 16:9 | 1600 × 900 | X in-feed image |
| Pinterest 2:3 | 1000 × 1500 | Standard pin |
| Link preview | 1200 × 630 | Shared links on Facebook, X, LinkedIn |

Platforms change their specs from time to time; tell Claude if you need a different size.

---

## Tips

- **Bigger photos look better.** If Claude warns that a photo was upscaled, use a larger original.
- **Short headlines work best.** Aim for under about 40 characters so the text stays large on small sizes.
- **Check the spelling before rendering.** Text is printed exactly as written.
- **Logos:** an SVG is best. A PNG with a transparent background works too.
- **Contrast fixes:** if a brand color fails on a background (e.g. yellow on white), Claude tells you what it changed. You can give your own accessible version instead, or pick a layout where that color sits on a dark background.

## Troubleshooting

| Problem | Fix |
|---|---|
| "No module named PIL" | Claude installs it with `pip install pillow`; on your own machine run that once |
| Skill doesn't start on Claude.ai | Check that code execution is on and the skill is enabled in Settings → Capabilities |
| Text cut off or very small | Shorten the headline or subhead |
| Subject cropped out | Tell Claude where the subject is ("keep the product on the left") |
| Ads don't look like my site | Give Claude a homepage screenshot, or say what's missing ("we use a serif font", "add the gradient underline") |
| Wrong font | Upload your font files (TTF/OTF) |
| Logo looks wrong or is on a white box | Upload an SVG, or a reversed (white) version for dark backgrounds |

---

## What's in this repo

```
skills/mj-social-ad-resizer/
  SKILL.md                  Instructions Claude follows
  scripts/make_images.py    Crops, resizes, adds text, writes the files
  scripts/fetch_font.py     Downloads Google Fonts (upright + italic) for the brand profile
  scripts/fetch_site_images.py  Downloads photos from your own site when you have none
  scripts/prepare_logo.py   Finds your logo on your site or prepares an uploaded one
  references/brand.md       How the brand profile is read from a website
  references/layouts.md     The layouts, layout DNA, and how concepts are chosen
  references/placements.md  Sizes, safe zones, caption limits
  references/spec.md        Settings the script accepts
  assets/fonts/             Inter (default font) and its license
```

## License

MIT, see [LICENSE](LICENSE). The bundled Inter font is under the SIL Open Font License 1.1 (see `skills/mj-social-ad-resizer/assets/fonts/LICENSE-Inter.txt`).

Made by [Mariana Johnels](https://marianajohnels.com).
