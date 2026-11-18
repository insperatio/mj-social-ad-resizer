---
name: mj-social-ad-resizer
description: Turn a photo the user supplies into on-brand social images or ads for Meta (Facebook/Instagram), LinkedIn, X and Pinterest. Reads the brand's colors, fonts and graphic style from their website, shows ad concepts on a contact sheet for approval, then exports every size (PNG, JPG or WebP) to a folder the user picks. Use for social ads, ad creatives or resized post images from the user's own photo. Does not generate photos or publish posts.
---

# MJ Social Ad Resizer

Two modes:
- **Plain:** crop and resize the user's photo for each placement. No text.
- **Ad:** build on-brand ads from the user's photo. Colors, fonts and graphic elements come from their website or brand guidelines. The user sees concepts first and picks one direction, then every size is rendered.

The skill never generates photos and never publishes or schedules posts.

## Step 1: Gather inputs

Ask in one message, leaving out anything already given:

1. **Photo (required).** Ask for one **landscape** and one **portrait** photo for the best crops; one also works. With no photo, explain that the skill needs one and stop.
2. **Platforms.** Any of Meta, LinkedIn, X, Pinterest. Map them to placements with `references/placements.md`. No TikTok.
3. **Plain or ad?**
4. **Ad copy (ad mode).** Headline, optional subhead, call to action, and who it's for. The audience shapes the wording only and is not printed.
5. **Brand source (ad mode).** The website URL to pull the look from, and/or brand guidelines, a logo file and font files.
6. **A/B variants?** If yes, write 2–3 headline/CTA versions (the user's is A) and get approval before rendering.
7. **Post text for each platform?** Captions, hashtags and alt text.
8. **Format:** PNG, JPG or WebP (WebP quality 85 by default).
9. **Link (optional):** the page the posts promote, used for tracking links.

## Step 2: Build the brand profile (ad mode)

Follow `references/brand.md` to turn the website into `brand.json`:
- colors (background, text, primary, accent, borders)
- the brand gradient, if it has one
- background glows and grid pattern
- fonts
- button shape and style
- motifs: gradient headline words, underline, tag pills, colored dots
- the brand's name, domain and a short tagline for the tag

**How to read the site, best first:**
1. A **browser tool**, if available. Open the site, run the style-extraction script in `references/brand.md`, and take a screenshot. This works on JavaScript-built sites, where plain fetching returns an empty page.
2. **Web fetch** for the HTML and the linked CSS files.
3. If neither works, ask the user for a **screenshot of the homepage** and read the colors and style from it.

**Fonts:**
- If the site uses a Google Font, download it with `python3 scripts/fetch_font.py "Family Name" fonts/`.
- If the font is proprietary or a system font (SF Pro, Adobe Clean, system-ui, Helvetica), or the download fails, use the closest match: the bundled Inter for clean sans-serifs, or a similar Google Font. Tell the user which font you substituted, and offer to use their font files if they upload them.

Show the user a short summary of the profile in plain words before rendering, for example: "Black headlines with a blue → violet → amber gradient on the key words, white background with a faint blue grid, black pill buttons."

## Step 3: Connect an export folder

Ask the user to connect the folder for the files (e.g. Downloads). In the Claude desktop app, request access with `device_request_folder_access` when available. If no folder can be connected, render in the working directory and send the files in the chat.

## Step 4: Look at the photos

Open each photo and find the main subject. Set `focus` (x and y from 0 to 1, from the top left) to the subject's center so every crop keeps it in frame. If the short side is under 1080 px, warn that large sizes will be soft.

## Step 5: Concepts for approval (ad mode)

Write the spec (see `references/spec.md`) with `"stage": "concepts"` and run:

```bash
python3 scripts/make_images.py spec.json
```

This renders each layout at one size (Meta 4:5 by default) on a concept sheet:

| Layout | Look |
|---|---|
| `editorial` | Brand background with its grid and glows, headline on top, photo below (side by side on wide sizes) |
| `full_bleed` | Photo fills the frame, dark gradient behind white text |
| `split` | Brand panel on one side, photo on the other, gradient divider |
| `band` | Photo with a solid brand-color band holding the text |

Default concepts: `editorial`, `full_bleed`, `split`. Add `band` when the brand has a strong solid color.

Show the concept sheet and ask which direction to use. Make any changes they ask for (copy, which words get the gradient via `emphasis`, colors, button style, eyebrow text) and re-run concepts until they approve.

**Don't render the final sizes until the user approves a concept.**

## Step 6: Render every size

Set `"stage": "final"` and `"layout": "<approved layout>"`, list the placements, and run the script again. You get:
- one file per placement and variant
- `<Name>_contact-sheet.png`
- `manifest.json`

Show the contact sheet. Fix single sizes on request with `"only": ["pinterest_B"]`. You can also move the focus point, set `"fill": "crop" | "blur" | "color"`, or shorten text.

**Warnings:** the script prints them (enlarged photos, low contrast, text too long). Tell the user about the ones that matter.

Plain mode skips Steps 2 and 5. Use `"stage": "final"` with no layout.

## Step 7: Post text (only if the user said yes)

For each platform, write the following, add it to the spec under `post_content`, and re-run so it lands in `manifest.json`. Also show it in your reply.
- A caption within the limits in `references/placements.md`, plus 3–5 hashtags (fewer on LinkedIn and X).
- X: the link goes in a reply.
- Pinterest: a pin title and description.
- Alt text that describes the photo and repeats the on-image text word for word.

**Ad copy checks:** flag restricted claims (health results, income promises, before/after) and anything that breaks the brand's house rules.

## Step 8: Deliver

Confirm the files are in the connected folder. Summarize: the number of images, the sizes, and any warnings left. Don't post or schedule anything.

## Notes
- The script draws all text itself, so it's spelled exactly as written. Check the copy before rendering.
- Each brand gets its own look from its profile. Don't fall back to plain black-and-white when the site has a stronger style; capture it in `brand.json`.
- Bundled font: Inter (SIL Open Font License). Downloaded Google Fonts are OFL or Apache licensed.
