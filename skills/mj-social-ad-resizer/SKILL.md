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
5. **Brand source (ad mode).** The website URL, plus any brand guidelines, logo or font files.
6. **A/B variants?** If yes, write 2–3 headline/CTA versions (the user's is A) and get approval before rendering.
7. **Post text for each platform?**
8. **Format:** PNG, JPG or WebP (WebP quality 85 by default).
9. **Link (optional)** for tracking links.

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

Show the concept sheet and ask which direction to use. Make any changes the user asks for (copy, `emphasis`, colors, layout DNA) and re-run until they approve.

**Don't render the final sizes until the user approves a concept.**

## Step 7: Render every size

Set `"stage": "final"` and `"layout": "<approved>"`, list the placements, and run the script. You get:
- one file per placement and variant
- `<Name>_contact-sheet.png`
- `manifest.json`

Show the contact sheet. Fix single sizes on request with `"only": ["pinterest_B"]`. You can also move the focus point, change `fill`, or shorten text.

**Warnings:** the script prints them (enlarged photos, low contrast, text too long, missing fonts). Tell the user about the ones that matter.

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
- Make each brand look like itself. If two brands' concepts come out structurally the same, the layout DNA wasn't captured; go back to the site.
- Bundled font: Inter (SIL Open Font License). Downloaded Google Fonts are OFL or Apache licensed.
