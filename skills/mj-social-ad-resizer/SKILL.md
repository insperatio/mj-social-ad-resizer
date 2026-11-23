---
name: mj-social-ad-resizer
description: Turn a brand's website and photos into on-brand social images or ads for Meta (Facebook/Instagram), LinkedIn, X and Pinterest. Reads colors, fonts, graphic style and layout patterns from the site, works with the user's photo, photos from their own site or no photo at all, shows concepts for approval, then exports every size (PNG, JPG or WebP) to a folder the user picks. Does not generate photos or publish posts.
---

# MJ Social Ad Resizer

Two modes:
- **Plain:** crop and resize the user's photo for each placement. No text.
- **Ad:** design on-brand ads. The colors, fonts, graphic elements and **layout patterns** come from the brand's website, so each brand gets its own structure, not just its own colors. The user approves a concept before every size is rendered.

The skill never generates photos and never publishes or schedules posts.

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
   - Who the ad is for. This shapes the wording and is not printed.
   - Optional **key facts or numbers**, e.g. "11.6 g protein per 100 cal" or "+134% referral lift". These become stat tiles or menu-style rows.
5. **Brand source (ad mode).** The website URL, plus any brand guidelines or font files.
6. **Logo.** Always ask: "Do you want your logo on the ads?"
   - **No:** set `"use_logo": false`. The brand name may still appear as text; set `"show_wordmark": false` to remove it too.
   - **Yes:** ask "Should I grab it from your website, or would you like to upload it?" Uploading is best for exact colors: SVG, or a PNG with a transparent background at least 600 px wide. A reversed (white) version for dark backgrounds is welcome too.
7. **A/B variants?** If yes, write 2–3 headline/CTA versions (the user's is A) and get approval before rendering.
8. **Post text for each platform?**
9. **Format:** PNG, JPG or WebP (WebP quality 85 by default).
10. **Link (optional)** for tracking links.

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

**Show the prepared logo to the user and confirm it's the right one.** If a reversed version was generated, ask whether their brand allows a white logo.

Put the paths in `brand.json` (`logo`, `logo_on_dark`) or in the spec's `"logo": {"logo": ..., "logo_on_dark": ...}`.

**How the renderer places it:**
- The logo replaces the text wordmark in each layout.
- The renderer picks the right version for each background.
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

Open each photo and set `focus` (x and y from 0 to 1) on the main subject. Warn if the short side is under 1080 px.

## Step 6: Concepts for approval (ad mode)

**Choose 3–4 concepts from `references/layouts.md` that fit this brand's DNA**, and make them clearly different from each other. Examples:
- A centered, framed, serif brand gets `card`, `centered`, `full_bleed`.
- A left-aligned SaaS brand gets `editorial`, `split`, `stats`.
- With no photo, use `card`, `centered`, `type_only`, plus `stats` if there are facts.

Write the spec (see `references/spec.md`) with `"stage": "concepts"` and run:

```bash
python3 scripts/make_images.py spec.json
```

**Check contrast and legibility before showing anything.** The script measures every line of text against the pixels behind it and fixes colors that fail WCAG 2.2 AA:
- Normal text needs 4.5:1. Headline-size text needs 3:1.
- A failing color is darkened or lightened within the same hue.
- The `contrast` section of the output lists each fix: the original and new color, and the ratio before and after.

Tell the user about each fix in plain words. For example: "Your yellow (#FDB913) is only 1.7:1 on white, so I darkened it to #BE8802 for the headline on light backgrounds. It stays bright yellow on navy." Then offer the alternatives:
- choose their own replacement with `colors.value_on_light` / `colors.link_on_light`
- or pick a layout where the brand color sits on a dark background (`band`, `card`, `full_bleed`)

Never turn the check off to keep a brand color. `"contrast": "warn"` only reports problems without fixing them. Use it only if the user explicitly asks, and tell them the files won't meet AA.

Text never goes below a minimum legible size. That is about 10–11 px when the image is shown 375 px wide on a phone, i.e. 2.4–2.9% of the image width. If the copy doesn't fit, the script leaves out optional copy first (subhead, then facts, then the small tag above the headline) and says so. Tell the user, and suggest shorter copy.

Show the concept sheet and ask which direction to use. Make any changes the user asks for (copy, `emphasis`, colors, layout DNA) and re-run until they approve.

**Don't render the final sizes until the user approves a concept.**

## Step 7: Render every size

Set `"stage": "final"` and `"layout": "<approved>"`, list the placements, and run the script. You get:
- one file per placement and variant
- `<Name>_contact-sheet.png`
- `manifest.json`

Show the contact sheet. Fix single sizes on request with `"only": ["pinterest_B"]`. You can also move the focus point, change `fill`, or shorten text.

**Warnings:** the script prints them (contrast fixes, copy left out to stay legible, enlarged photos, missing fonts). Tell the user about the ones that matter, and summarize the contrast fixes once rather than once per size.

Plain mode skips Steps 2, 3 and 6. Use `"stage": "final"` with no layout.

## Step 8: Post text (only if the user said yes)

For each platform, write the following, add it to the spec under `post_content`, and re-run. Also show it in your reply.
- A caption within the limits in `references/placements.md`, plus hashtags.
- X: the link goes in a reply.
- Pinterest: a title and description.
- Alt text that describes the image and repeats the on-image text word for word.

**Ad copy checks:** flag restricted claims (health results, income promises, before/after) and anything that breaks the brand's house rules or spelling (e.g. a brand name written as one word).

## Step 9: Deliver

Confirm the files are in the folder. Summarize: the number of images, the sizes, the layout used, and any warnings left. Don't post or schedule anything.

## Notes
- The script draws all text itself, so it's spelled exactly as written.
- Accessibility is not optional. Every exported image meets WCAG 2.2 AA text contrast and the minimum text sizes, unless the user explicitly chose `"contrast": "warn"`.
- Make each brand look like itself. If two brands' concepts come out structurally the same, the layout DNA wasn't captured; go back to the site.
- Bundled font: Inter (SIL Open Font License). Downloaded Google Fonts are OFL or Apache licensed.
