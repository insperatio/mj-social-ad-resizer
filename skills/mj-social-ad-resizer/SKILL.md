---
name: mj-social-ad-resizer
description: Turn a brand's website and photos into on-brand social images or ads for Meta (Facebook/Instagram), LinkedIn, X and Pinterest. Reads colors, fonts, graphic style and layout patterns from the site, works with the user's photo, photos from their own site or no photo at all, shows a snapshot of every option (an ad modeled on the brand's own website, 11 HTML templates and 8 classic layouts) so the user picks the ones they want, then exports every size of those (PNG, JPG or WebP) to a folder the user picks. Does not generate photos or publish posts.
---

# MJ Social Ad Resizer

Two modes:
- **Plain:** crop and resize the user's photo for each placement. No text.
- **Ad:** design on-brand ads. The colors, fonts, graphic elements and **layout patterns** come from the brand's website. The user sees **every option in one snapshot** and picks which ones to build:
  - **Website style** (`site`): an ad modeled on the brand's own homepage hero. Not a template; written per brand (`references/site-style.md`).
  - **11 HTML templates**: headline + 3 bullets, icon list, question + checks, diagonal photo, chevron photo, punchy photo, type + emoji, stacked poster, gradient minimal, mosaic, highlight box (`references/templates.md`).
  - **8 classic layouts**: editorial, full bleed, split, band, card, centered, stats, type only (`references/layouts.md`).

  Only the picked options are rendered at every size.

The skill never generates photos and never publishes or schedules posts.

## Setup (once)

The templates and the website-style option are rendered in headless Chrome:

```bash
pip install playwright pillow
python3 -c "import playwright"  # uses installed Google Chrome; if there's none: playwright install chromium
```

The classic layouts need only Pillow. If Playwright can't be installed, say so and show the classic layouts only.

## Step 1: Gather inputs

Ask in one message, leaving out anything already given:

1. **Photo.**
   - Plain mode needs one.
   - For ads it's optional. Ideally one landscape and one portrait.
   - If there's no photo, offer two options: use photos from their own website (Step 3), or make photo-free designs (card, typographic poster, stat tiles).
2. **Platforms.** Any of Meta, LinkedIn, X, Pinterest. Map them with `references/placements.md`. No TikTok.
3. **Plain or ad?**
4. **Ad copy (ad mode).**
   - Headline, optional subhead or tagline, and a call to action.
   - If the user lets you write the copy, write it for **every** option so the snapshot is complete: 3 benefit bullets, a question + one-line answer, an all-caps punchline, poster words, an emoji, a phrase to highlight, and fine print when the offer needs it (fields in `references/templates.md`). Use only claims the site or the user supports.
   - Who the ad is for. This shapes the wording and is not printed.
   - Optional **key facts or numbers**, e.g. "11.6 g protein per 100 cal" or "+134% referral lift". These become stat tiles or menu-style rows.
5. **Brand source (ad mode).** The website URL, plus any brand guidelines or font files.
6. **Logo.** Always ask: "Do you want your logo on the ads?"
   - **No:** set `"use_logo": false`. The brand name may still appear as text; set `"show_wordmark": false` to remove it too.
   - **Yes:** ask "Should I grab it from your website, or would you like to upload it?" Uploading is best for exact colors: SVG, or a PNG with a transparent background at least 600 px wide. A reversed (white) version for dark backgrounds is welcome too.
   - A logo, when used, is **at least one third of the ad's width**. Tell the user so they know what to expect.
7. **Website address.** Ask: "Do you want your website address on the ads?"
   - **No:** set `"show_url": false`.
   - **Yes:** use the domain, or a specific page they give, e.g. `"url_text": "snhu.edu/business"`.
8. **A/B variants?** If yes, write 2–3 headline/CTA versions (the user's is A) and get approval before rendering.
9. **Post text for each platform?**
10. **Format:** PNG, JPG or WebP (WebP quality 85 by default).
11. **Link (optional)** for tracking links in the manifest.

## Step 2: Build the brand profile (ad mode)

Follow `references/brand.md` and `references/layouts.md` to write `brand.json`.

**What to capture:**
- **Look:** colors, gradient, glows and grid, fonts, button style, motifs.
- **Layout DNA** (`style`):
  - alignment
  - photo shape and corner radius
  - frames and dividers
  - label style (pills or uppercase tracked caps)
  - italic taglines
  - CTA style (solid, outline, gradient or text link)
  - card and shadow treatment
  - tile colors

**How to read the site, best first:**
1. A **browser tool**: open the site, run the extraction script in `brand.md`, take screenshots of the hero and main sections, and list the page's images. This works on JavaScript-built sites.
2. **Web fetch** for the HTML and CSS.
3. A **homepage screenshot** from the user.

**Fonts:**
- Google Fonts: `python3 scripts/fetch_font.py "Family" fonts/`. This downloads the upright and italic versions.
- Paid or system fonts: use the closest free match (bundled Inter for clean sans-serifs, or a similar Google Font). Say which font you substituted, and offer to use the user's own font files.

**Confirm with the user:** summarize the look and the layout DNA in plain words. For example: "Centered, menu-card style: cream paper card with a double rule on espresso, serif headline, italic tagline, small caps labels, ornament divider, red text-link CTA."

## Step 2a: Build the website-style option

Study the homepage hero and write `site_layout.html` following `references/site-style.md`: the hero's background (photo, tint, texture and blend mode, gradient), composition, type and button, rebuilt with the brand tokens and placeholders. Save the hero's background images next to the spec. Set `"site_layout": "site_layout.html"` in the spec.

Fill `brand.json → html` only where the derived tokens look off (e.g. the emphasis color on light backgrounds, the dark panel color).

## Step 2b: Prepare the logo (if they want one)

**Uploaded logo:** run `python3 scripts/prepare_logo.py prepare <file> logo/`.

**From the website:** run `python3 scripts/prepare_logo.py from-url <url> logo/`. It looks for a header or nav logo (an image or inline SVG), then the JSON-LD logo, then the site icon. If the sandbox can't reach the site, use a browser tool:
1. Open the site and run:
   ```js
   const el = document.querySelector('header [class*=logo], header a[href="/"] svg, header a[href="/"] img, [class*=logo] svg, [class*=logo] img, a[aria-label*=home i] svg');
   el ? (el.tagName.toLowerCase() === 'svg' ? el.outerHTML : (el.currentSrc || el.src)) : 'none'
   ```
2. For an inline SVG, save the returned markup to `logo/logo_download.svg` and run `prepare` on it.
3. For an image URL, open it on its own and take a screenshot saved to disk, crop to the logo, and run `prepare` on that. The solid background is removed automatically; use `--bg #RRGGBB` if it isn't.
4. If none of that works, ask the user to upload the logo.

**What `prepare` does:**
- converts SVG to PNG and removes a solid background
- trims empty space
- returns `logo` (for light backgrounds) and `logo_on_dark`
- for a single-color logo, makes the opposite version automatically (e.g. white for dark backgrounds)
- for a multi-color logo, it can't, so ask the user for a reversed version

**The right logo for each background:** the renderer measures the pixels behind the logo every time and uses whichever version stands out more: `logo` on light, `logo_on_dark` on dark or busy photos. Give it both versions whenever you can.

**Show the prepared logo to the user and confirm it's the right one.** If a reversed version was generated, ask whether their brand allows a white logo.

Put the paths in `brand.json` (`logo`, `logo_on_dark`) or in the spec's `"logo": {"logo": ..., "logo_on_dark": ...}`.

**How the renderer places it:**
- The logo replaces the text wordmark in each layout.
- If a logo would be hard to see, it sits on a small contrasting chip and a warning is shown.
- In plain mode, it goes in a corner (`"logo_position": "top-right"` by default).

## Step 3: Photos from the brand's own site (when the user has none)

Only use images from the user's own site. Show the candidates and let the user choose.

1. Try `python3 scripts/fetch_site_images.py <url> photos/`.
2. If the sandbox can't reach the site, use a browser tool:
   - open the image URL (pick the largest version from the page's image list)
   - make it fill the window with `img.style.cssText='position:fixed;left:0;top:0;height:'+innerHeight+'px;width:auto'`
   - take a screenshot saved to disk and crop it to the image
3. If neither works, ask the user to download and attach the photos, and give them the links.

If they'd rather not use a photo, go photo-free.

## Step 4: Connect an export folder

Ask the user to connect the folder for the files (e.g. Downloads). In the Claude desktop app, use `device_request_folder_access` when available. Otherwise, render in the working directory and send the files in the chat.

## Step 5: Look at the photos

Open each photo and mark the main subject:
- `focus`: its center, with x and y from 0 to 1.
- `subject`: its bounds, `{"x0", "y0", "x1", "y1"}` as fractions from the top left. Include the whole person or product, e.g. head to hands for someone at a laptop.

Warn if the short side is under 1080 px.

**Photo rules:**
- **Never distort a photo.** Photos and logos are only cropped or scaled evenly (the renderer enforces this). Don't stretch or squash an image in any other step either.
- **If the subject wouldn't be visible, don't use the photo.** When a crop would cut off more than 40% of the subject, or show it too small to recognize (under 12% of the ad's short side), the renderer uses a brand gradient, pattern or plain color in that spot instead and says so.
  - Choose the replacement with `"photo_fallback": "gradient" | "pattern" | "color"`.
  - The default `auto` uses the gradient if the brand has one, then a pattern, then a color.
  - Mention these swaps to the user. A different crop or a second photo (wide or tall) usually brings the photo back.

## Step 6: Snapshot of every option (ad mode)

Write the spec (`references/spec.md`) with all the copy fields, the photos, `site_layout`, and `snapshot_placement` (default `meta_portrait`; use the user's main placement). Run:

```bash
python3 scripts/html_ads.py snapshot spec.json
```

It renders **every option** at one size and writes one numbered sheet, `<Name>_snapshot.png`: 1 is the website style, then the templates, then the classic layouts. Options whose copy or photo is missing are left out with a warning; fix the copy and re-run so the user sees everything.

**Look at the sheet yourself before showing it.** Fix anything off: text crowding a face, a weak crop, a template that clearly doesn't suit the brand's tone (say so instead of hiding it).

**Contrast and legibility** are checked on every option, on the rendered pixels:
- Normal text needs 4.5:1. Headline-size text needs 3:1.
- A failing color is darkened or lightened within the same hue. The output lists each fix in `contrast_fixes`, with the original and new color and the ratio before and after.
- Text never goes below the minimum sizes (about 10–11 px on a phone). When copy doesn't fit, type shrinks a little, then the tag, subhead and URL are left out in that order, with a warning.

Tell the user about the fixes in plain words. For example: "Your yellow (#FDB913) is only 1.7:1 on white, so I darkened it to #BE8802 for the headline on light backgrounds. It stays bright yellow on navy." Offer alternatives: their own replacement (`colors.value_on_light`, `html.text_accent`) or the options where the brand color sits on a dark background. Never turn the check off to keep a brand color. `"contrast": "warn"` only reports; use it only if the user explicitly asks, and tell them the files won't meet AA.

**Show the snapshot and ask which numbers they want.** They can pick any number of options. Make changes they ask for (copy, colors, the website-style layout, a different photo) and re-run the snapshot, or just the changed options with `"templates"` / `"classic"` limits.

**Don't render the final sizes until the user picks.**

## Step 7: Render every size of the picked options

Set `"picks"` to the chosen ids (from the snapshot output, e.g. `["site", "headline_3_bullets", "split"]`) and `"placements"`, then run:

```bash
python3 scripts/html_ads.py final spec.json
```

You get one subfolder per pick with one file per placement and variant, `<Name>_contact-sheet.png`, and one `manifest.json`.

**Look at the contact sheet yourself** (every size, especially Stories and 1.91:1) before showing it. Fix single files with `"only": ["site:meta_story"]`.

**Warnings:** contrast fixes, copy left out to stay legible, enlarged photos, a photo swapped for a gradient, a height-capped logo, contrast that couldn't be fixed on a busy photo. Tell the user about the ones that matter, once, not once per size.

Plain mode skips Steps 2, 3 and 6 and uses `make_images.py` with `"stage": "final"` and no layout.

## Step 8: Post text (only if the user said yes)

For each platform, write the following, add it to the spec under `post_content`, and re-run. Also show it in your reply.
- A caption within the limits in `references/placements.md`, plus hashtags.
- X: the link goes in a reply.
- Pinterest: a title and description.
- Alt text that describes the image and repeats the on-image text word for word.

**Ad copy checks:** flag restricted claims (health results, income promises, before/after) and anything that breaks the brand's house rules or spelling (e.g. a brand name written as one word).

## Step 9: Brand report

The classic renderer writes `<Name>_brand-report.png`, a small card listing:
- every color used, with what it was used for
- the fonts, shown in themselves
- which logo version went on which kind of background
- contrast fixes

The same data is under `brand_report` in the output and `manifest.json`. Show it with the snapshot and again with the final files. The HTML options' colors are in `manifest.json → tokens`. Summarize it in a few lines, e.g. "Navy #0A2551 for headlines and buttons, yellow #FDB913 on navy (#BE8802 on white for contrast), Inter Bold/SemiBold/Regular."

## Step 10: Deliver

Confirm the files are in the folder. Summarize: the number of images, the sizes, the options used, and any warnings left. Don't post or schedule anything.

## Notes
- All text is set by the renderers (Chrome for HTML options, Pillow for classic layouts), so it's spelled exactly as written.
- Photos and logos keep their proportions. A logo is at least a third of the ad's width, and the version that matches the background is used.
- Accessibility is not optional. Every exported image meets WCAG 2.2 AA text contrast and the minimum text sizes, unless the user explicitly chose `"contrast": "warn"`.
- Make each brand look like itself. The website-style option should be recognizable next to the brand's homepage; if it could belong to any brand, go back to the hero.
- Bundled fonts: Inter, Instrument Serif and Oswald (SIL Open Font License). Downloaded Google Fonts are OFL or Apache licensed.
