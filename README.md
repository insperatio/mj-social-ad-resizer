# mj-social-ad-resizer

Free agent skill that turns your own photo into ready-to-post social images and ads for Meta (Facebook/Instagram), LinkedIn, X and Pinterest.

- **Plain mode:** crops and resizes your photo for every placement you pick.
- **Ad mode:** adds a brand-colored text band with a headline, subhead and call-to-action button.
- Optional **A/B variants** and **post text for each platform** (captions, alt text, hashtags, UTM links).
- Exports **WebP, PNG or JPG** to a folder you choose, with a contact sheet and a `manifest.json`.
- Checks text contrast (WCAG AA) and warns about low-resolution photos and text that doesn't fit.

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

### 1. Start with a photo

Attach your photo and ask, for example:

> Make social images for this photo for Instagram, LinkedIn and Pinterest.

> Turn this photo into ads for Meta and X. Headline: "Fresh spring styles, 30% off this week". CTA: "Shop now". Link: https://example.com/sale

For the best crops, attach **two photos**: one landscape (wide) and one portrait (tall), each at least **1080 px** on the short side. One photo also works.

### 2. Answer a few questions

Claude asks only for what you haven't already given it:

| Question | What to answer |
|---|---|
| Platforms | Any of Meta (Facebook/Instagram), LinkedIn, X, Pinterest |
| Plain image or ad? | **Plain** = just resized photos. **Ad** = photo plus a text band with headline and button |
| Ad details | Headline, optional subhead, call to action, and who the ad is for |
| Link | The page the posts promote (optional; used for captions and tracking links) |
| Brand | Colors (hex codes), logo (PNG with a transparent background), font files (TTF/OTF), or your brand guidelines. All optional |
| A/B variants? | Yes = Claude writes 2–3 headline versions for you to approve |
| Post text for each platform? | Yes = captions, hashtags, alt text and pin titles |
| Format | WebP (default), PNG or JPG |

### 3. Choose where to save

Claude asks you to connect a folder. In the Claude desktop app, approve the folder-access prompt. If no folder can be connected, Claude sends the files in the chat instead.

### 4. Review the contact sheet

You get one overview image showing every size side by side. Each tile is labeled:
- **crop**: your photo was cropped to fill the frame.
- **blur**: the photo didn't fit the shape well, so it sits on a blurred copy of itself.

Ask for fixes in plain words, and only that size is redone:

> The Pinterest pin cuts off her face, move the crop up.

> Use a solid brand-color background instead of the blur on the Story.

> Shorten the headline on the link preview.

### 5. Get your files

The folder will contain:

```
Spring_Sale_IG-1x1_A.webp      Meta feed 1080×1080
Spring_Sale_IG-4x5_A.webp      Meta feed 1080×1350
Spring_Sale_STORY_A.webp       Meta Stories/Reels 1080×1920
Spring_Sale_LI-1x1_A.webp      LinkedIn 1200×1200
Spring_Sale_X_A.webp           X 1600×900
Spring_Sale_PT_A.webp          Pinterest 1000×1500
Spring_Sale_FB_A.webp          Link preview 1200×630
Spring_Sale_contact-sheet.png  Overview of every image
manifest.json                  Sizes, tracking links, captions, alt text
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
- **Logos:** use a PNG with a transparent background.
- **Contrast warnings** mean the text may be hard to read. Pick a darker band color or lighter text.

## Troubleshooting

| Problem | Fix |
|---|---|
| "No module named PIL" | Claude installs it with `pip install pillow`; on your own machine run that once |
| Skill doesn't start on Claude.ai | Check that code execution is on and the skill is enabled in Settings → Capabilities |
| Text cut off or very small | Shorten the headline or subhead |
| Subject cropped out | Tell Claude where the subject is ("keep the product on the left") |

---

## What's in this repo

```
skills/mj-social-ad-resizer/
  SKILL.md                  Instructions Claude follows
  scripts/make_images.py    Crops, resizes, adds text, writes the files
  references/placements.md  Sizes, safe zones, caption limits
  references/spec.md        Settings the script accepts
  assets/fonts/             Inter (default font) and its license
```

## License

MIT, see [LICENSE](LICENSE). The bundled Inter font is under the SIL Open Font License 1.1 (see `skills/mj-social-ad-resizer/assets/fonts/LICENSE-Inter.txt`).

Made by [Mariana Johnels](https://marianajohnels.com).
