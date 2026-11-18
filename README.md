# mj-social-ad-resizer

A Claude skill that turns your own photo into ready-to-post social images and ads for Meta (Facebook/Instagram), LinkedIn, X and Pinterest.

- **Plain mode:** crops and resizes your photo for every placement you pick.
- **Ad mode:** adds a brand-colored text band with a headline, subhead and call-to-action button.
- Optional A/B variants and post text for each platform (captions, alt text, hashtags, UTM links).
- Exports WebP, PNG or JPG to a folder you choose, with a contact sheet and a `manifest.json`.
- Checks text contrast (WCAG AA), warns about low-resolution photos and text that doesn't fit.

No AI image generation, no API keys, and it never publishes or schedules anything.

## Sizes

| Placement | Size |
|---|---|
| Meta feed 1:1 | 1080 × 1080 |
| Meta feed 4:5 | 1080 × 1350 |
| Meta Stories / Reels | 1080 × 1920 |
| LinkedIn feed 1:1 | 1200 × 1200 |
| X in-feed 16:9 | 1600 × 900 |
| Pinterest pin 2:3 | 1000 × 1500 |
| Link preview (Facebook, X, LinkedIn) | 1200 × 630 |

## Install

Download this repo as a ZIP and upload it in Claude under **Settings → Capabilities → Skills**, or copy the folder into your skills directory for Claude Code.

## Use

Ask Claude something like: *"Make social ads for this photo for Instagram and Pinterest."* It will ask for anything it needs, including the folder to export to.

Works best with one landscape and one portrait photo, each at least 1080 px on the short side.

## Requirements

Python 3 with Pillow (available in Claude's sandbox).

## License

Font: Inter, SIL Open Font License 1.1 (see `assets/fonts/LICENSE-Inter.txt`).
