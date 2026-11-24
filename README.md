# mj-social-ad-resizer

Free agent skill that turns your website and photos into on-brand social images and ads for Meta (Facebook/Instagram), LinkedIn, X and Pinterest.

- **Plain mode:** crops and resizes your photo for every placement you pick.
- **Ad mode:** reads your website's look (colors, fonts, gradients, background patterns, button style) **and its layout patterns** (centered or left-aligned, photo shapes, frames, dividers, label and link styles), so each brand gets its own structure.
- **No photo? No problem:** use photos from your own site, or go photo-free with menu-style cards, typographic posters or stat tiles.
- **Every option in one snapshot:** one numbered sheet with
  - an ad modeled on **your own website's hero** (not a template),
  - **11 HTML templates** (headline + 3 bullets, icon list, question + checks, diagonal photo, chevron photo, punchy photo, type + emoji, stacked poster, gradient minimal, mosaic, highlight box),
  - **8 classic layouts** (editorial, full bleed, split, band, card, centered, stats, type only).

  Pick as many as you like; only those are built in every size.
- Optional **A/B variants** and **post text for each platform** (captions, alt text, hashtags, UTM links).
- Exports **PNG, JPG or WebP** to a folder you choose, with a contact sheet and a `manifest.json`.
- **Accessible by default:** every line of text is checked against the pixels behind it (WCAG 2.2 AA), and failing brand colors are adjusted within the same hue. Text never goes below a size that's readable on a phone; extra copy is left out first, and you're told.
- **Photos stay true:** photos and logos are never stretched. If a crop would cut off the subject or make it too small to recognize, a brand gradient, pattern or color is used there instead.
- **Logo done right:** at least a third of the ad's width, with the light or dark version chosen to stand out on each background.
- **Brand report:** a small card listing every color and font used, which logo version went where, and any contrast fixes.
- Warns about low-resolution photos.

No AI image generation, no API keys, and it never publishes or schedules anything.

**Requirements:** Python 3 with Pillow, plus Playwright and Google Chrome (or `playwright install chromium`) for the website-style option and the HTML templates.

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

> Build me an ad for Meta. Headline: "Let's work together". CTA: "Book a call". Use marianajohnels.com for branding (colors, fonts, graphic elements). Show me all the options, then save PNGs to my Downloads folder.

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
| Website address? | Yes or no. If yes, show your domain or a specific page (e.g. "snhu.edu/business") |
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

### 4. Pick from the snapshot

You get one numbered sheet with every option at one size:

| # | Option | What it is | Needs a photo |
|---|---|---|---|
| 1 | Website style | Modeled on your homepage hero: its background, overlays, type, button and composition. Built for your brand, not a template | uses the hero's own images |
| | Headline + 3 bullets | Photo, headline, three icon bullets, footer band with your logo and brand shapes | yes |
| | Icon list | Two-tone headline over large icon rows | no |
| | Question + checks | "Tired of…?" question, one-line answer, check list | no |
| | Diagonal photo | Photo wedge, accent corner holding the logo, fine print | yes |
| | Chevron photo | Photo with a V-cut edge, centered headline and button | yes |
| | Punchy photo | Dark full-bleed photo, all-caps punchline | yes |
| | Type + emoji | Big headline mixing your font with an italic serif, emoji sticker | no |
| | Stacked poster | Condensed caps stack with pointing emoji | no |
| | Gradient minimal | One line on your brand gradient | no |
| | Mosaic | Headline over a grid of shapes, photo crops and your logo | yes |
| | Highlight box | Key phrase in a solid box | no |
| | Classic: editorial, full bleed, split, band, card, centered, stats, type only | The original layouts, styled by your site's layout DNA | some |

Pick any numbers ("1, 2 and 15"), or ask for changes first. Nothing else is rendered until you pick.

### 5. Choose where to save

Claude asks you to connect a folder (e.g. Downloads). In the Claude desktop app, approve the folder-access prompt. If no folder can be connected, Claude sends the files in the chat instead.

### 6. Review every size

A contact sheet shows every size of every option you picked. Ask for fixes in plain words, and only that size is redone:

> The Pinterest pin cuts off his face, move the crop up.

> Shorten the headline on the link preview.

### 7. Get your files

The folder will contain:

```
site/Mariana_Johnels_site_IG-1x1_A.png    One folder per option you picked
site/Mariana_Johnels_site_IG-4x5_A.png    Meta feed 1080×1350
site/Mariana_Johnels_site_STORY_A.png     Meta Stories/Reels 1080×1920
headline_3_bullets/...                    (LI-1x1 1200×1200, X 1600×900, PT 1000×1500, FB 1200×630)
Mariana_Johnels_contact-sheet.png
Mariana_Johnels_brand-report.png  Colors, fonts, logo versions and contrast fixes used
manifest.json                    Sizes, tracking links, captions, alt text
Mariana_Johnels_snapshot.png     Every option you chose from
snapshot/                        The option images
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
  scripts/html_ads.py       Snapshot of every option, website style + HTML templates, final sizes for your picks
  scripts/make_images.py    Classic layouts and plain photo resizing
  scripts/fetch_font.py     Downloads Google Fonts (upright + italic) for the brand profile
  scripts/fetch_site_images.py  Downloads photos from your own site when you have none
  scripts/prepare_logo.py   Finds your logo on your site or prepares an uploaded one
  references/brand.md       How the brand profile is read from a website
  references/site-style.md  How the website-style option is built from your homepage hero
  references/templates.md   The 11 HTML templates, their copy fields and brand tokens
  references/layouts.md     The classic layouts and layout DNA
  references/placements.md  Sizes, safe zones, caption limits
  references/spec.md        Settings the script accepts
  assets/fonts/             Inter (default), Instrument Serif and Oswald (companion fonts), with licenses
```

## License

MIT, see [LICENSE](LICENSE). The bundled Inter font is under the SIL Open Font License 1.1 (see `skills/mj-social-ad-resizer/assets/fonts/LICENSE-Inter.txt`).

Made by [Mariana Johnels](https://marianajohnels.com).
