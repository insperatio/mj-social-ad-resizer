---
name: mj-social-ad-resizer
description: Turn a photo the user supplies into ready-to-post social images or ads for Meta (Facebook/Instagram), LinkedIn, X and Pinterest, sized per placement, with optional headline/CTA, A/B variants and per-platform captions, exported to a folder the user connects. Use when someone wants social media images, ad creatives or resized post images from their own photo. Does not generate images or publish posts.
---

# MJ Social Ad Resizer

Turns the user's own photo into correctly sized social images. In **plain** mode it only crops and resizes. In **ad** mode it adds a brand-colored text band with a headline, an optional subhead, and a call-to-action button. It exports everything to a folder the user connects, along with a contact sheet and a `manifest.json`.

It never generates images with AI and never publishes or schedules posts.

## Step 1: Gather inputs

Ask for everything in one message. Leave out questions the user has already answered.

1. **Photo (required).** Ask for one **landscape** and one **portrait** photo for the best crops; one photo also works. If they have no photo, explain that this skill needs one and stop.
2. **Link (optional).** The URL the posts promote. It's used for UTM links and captions.
3. **Platforms.** Any of Meta, LinkedIn, X, Pinterest. Map them to placements with `references/placements.md`. No TikTok.
4. **Plain image or ad?**
5. **Ad details (ad mode only).** Headline, subhead (optional), call to action, and target persona. The persona shapes the wording; it is not printed on the image.
6. **Brand (optional).** Colors (primary, accent), logo file, fonts (TTF/OTF files), or brand guidelines / a design system link to read them from. If there's no brand input, use a neutral dark band and the bundled Inter font.
7. **A/B variants?** Ask: "Want A/B variants?" If yes, write 2–3 headline/CTA versions yourself (the user's version is A) and show them for approval before rendering.
8. **Post content?** Ask: "Want the post text for each platform too (captions, alt text, hashtags)?"
9. **Export format.** WebP (default, quality 85), PNG or JPG.

If they give brand guidelines, pull out the hex colors, font names, logo rules and house rules (spelling, banned words, things never to mention). Follow the house rules in everything you write.

## Step 2: Connect an export folder

Ask the user to connect the folder the images should go into. In the Claude desktop app, request access with `device_request_folder_access` when that tool is available. Otherwise ask them to add a folder. If no folder can be connected, render into the working directory and send the files with the file-sharing tool instead.

## Step 3: Look at the photos and set the focus point

Open each photo and find the main subject. Set `focus` to the subject's center as fractions (x and y from 0 to 1, measured from the top left), so the crops keep it in frame. Note the pixel size: if the short side is under 1080 px, tell the user the larger sizes will be soft.

## Step 4: Write the spec and render

Write a spec JSON (full field list in `references/spec.md`) and run:

```bash
python3 scripts/make_images.py spec.json
```

Requires Python 3 with Pillow (`pip install pillow` if it's missing).

Output in `output_dir`: one image per placement (and per variant), `<Name>_contact-sheet.png` and `manifest.json`. The command prints a JSON summary with **warnings**. Read them and pass on anything that matters: low resolution, weak contrast, or text too long for a size.

## Step 5: Review with the user

Show the contact sheet. Each tile is labeled with its fit:
- `crop`: the photo was cropped to fill the frame.
- `blur` / `color`: the photo couldn't fill the shape without losing too much, so it sits on a blurred copy of itself or on a brand-color fill.

Offer fixes for a single size without redoing everything: move the focus point, switch fill style (`"fill": "crop" | "blur" | "color"`), or shorten text. Re-render one file by adding `"only": ["pinterest_B"]` (placement key, plus `_<variant id>` when there are variants).

## Step 6: Post content (only if they said yes)

For each platform, write the following and put it in the spec under `post_content`, then re-run so it lands in `manifest.json`. Also show it in your reply.
- **Caption** within the platform's limit (see `references/placements.md`), plus 3–5 relevant hashtags (fewer on LinkedIn and X).
- **X:** main post without the link; the link goes in a reply.
- **Pinterest:** pin title (up to 100 characters) and description (up to 500).
- **Alt text** for each image: describe the photo and include the on-image text word for word.
- Use the UTM link for each platform from the manifest's `link` field.

**Ad copy checks:** flag restricted claims (health outcomes, income or finance promises, before/after) and anything that breaks the brand's house rules.

## Step 7: Export

Make sure the final files are in the connected folder, and give a short summary: how many images, which placements, any warnings left. Don't post or schedule anything.

## Notes
- Placement sizes are common defaults. If the user mentions a platform changed its specs, use theirs.
- Text is drawn by the script, not by an AI model, so it's always spelled exactly as written. Check spelling before rendering.
- Default font: Inter (SIL Open Font License, in `assets/fonts`).
