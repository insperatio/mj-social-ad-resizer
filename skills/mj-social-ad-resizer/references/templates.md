# HTML templates

Eleven templates modeled on real ad sets (Simpay, SV Academy, "Tech wants you"). They live in `scripts/html_ads.py`, are rendered in headless Chrome, and use only the brand tokens (`brand.json → html`, or derived from `colors`) plus the copy. Each one adapts to every placement: square, 4:5, Stories (safe zones respected), 2:3 pins, 1.91:1 link previews and 16:9.

| Id | Looks like | Needs | Good for |
|---|---|---|---|
| `headline_3_bullets` | Photo on top, headline, 3 icon bullets, footer band with the logo and brand shapes. Wide: photo left, copy right | photo, 3 bullets | Programs, services, offers with three clear benefits |
| `icon_list` | Two-tone headline over 3–4 large icon rows, logo in the corner | 3+ bullets | "Everything you get" ads, service menus |
| `question_checks` | Question headline with the pain point in the accent color, one-line answer, check list | 3 bullets (and ideally `question`, `answer`) | Problem/solution, "Tired of…?" |
| `diagonal_photo` | Photo wedge top-right, accent corner holding the logo, left-aligned headline, fine print | photo | Offers with a disclaimer ("SaaS fees apply", "Member FDIC") |
| `chevron_photo` | Photo with a V-cut edge over an accent stripe, centered headline and button | photo | Clear single CTA |
| `punchy_photo` | Dark full-bleed photo, all-caps punchline on top, logo at the bottom | photo (and ideally `punchline`) | Witty, confident brands; restaurants, consumer |
| `type_emoji` | Big headline mixing the brand sans with an italic serif, emoji sticker | `emoji` | Playful, social-native brands |
| `stacked_poster` | Condensed all-caps words stacked at different sizes, pointing emoji at the key word | `poster` words, or a headline of 5 words or fewer | Hiring, bold announcements |
| `gradient_minimal` | One centered line on a deep brand gradient, logo below | — | Strong single message, retargeting |
| `mosaic` | Headline over a tile grid: brand circles, photo crops, logo tile | photo | Community, people-focused brands |
| `highlight_box` | Key phrase reversed out in a solid box, centered | — (ideally `highlight`) | Positioning statements |

**Tone fit:** `type_emoji` and `stacked_poster` are playful. Say so when you show them for a formal brand (bank, university, legal, health); the user decides.

## Copy fields (per variant)

All templates read the same variant. Write copy for every template so every option can be shown in the snapshot.

| Field | Used by | Notes |
|---|---|---|
| `headline` | all | Mark the emphasized words with asterisks: `"Grow with clarity, *not chaos*"`. The classic `emphasis` field still works. |
| `subhead` | most | One short line. Left out first when space runs out (with a warning). |
| `eyebrow` | site style, classic | 2–4 word tag. |
| `cta` | chevron, site style, classic | Button text. |
| `bullets` | headline_3_bullets, icon_list, question_checks | 3 short benefit lines (≤ 40 characters reads best). Strings, or `{"text", "icon"}` to choose the icon. Icons are otherwise picked from the words: coin, card, shield, phone, chat, layout, trend, clock, users, target, book, home, calendar, heart, star, check. Without bullets, `facts` are used. |
| `question` / `answer` | question_checks | Falls back to `headline` / `subhead`. |
| `punchline` | punchy_photo | Short all-caps line; `\n` for line breaks. Falls back to the headline. |
| `emoji` | type_emoji | One emoji. |
| `poster` | stacked_poster | `[["Your",1],["brand",2],["deserves",1],["better",2]]`. 2 = big, accent color; the first big word gets the pointing emoji. |
| `highlight` | highlight_box | The phrase to box; must appear in the headline. Defaults to the starred words. |
| `fine` | diagonal_photo, site style | Disclaimer or small print ("Member FDIC", "*SaaS fees apply"). Always kept. |

## Brand tokens (`brand.json → html`, all optional)

Derived from `colors` when missing; set them when the derived ones look off.

| Token | Meaning |
|---|---|
| `ink` / `ink_alt` | Main text on light backgrounds / second text color (serif words, subtitles) |
| `primary` / `on_primary` | Accent shapes and buttons / text on them |
| `text_accent` | Emphasis color on light backgrounds (must pass 4.5:1; derived by darkening `primary`) |
| `text_accent_dark` | Emphasis color on dark backgrounds |
| `surface`, `tint`, `cream`, `grey` | Light backgrounds: main, very light brand tint, warm off-white, neutral grey |
| `dark` | Dark panels and boxes |
| `shape2`, `shape3` | Extra shape colors (circles, tiles) |
| `grad_a`, `grad_b`, `grad_text` | Gradient top/bottom and the text on it |
| `radius` | Button corner radius in px at 1080 |
| `fonts.serif`, `fonts.serif_italic`, `fonts.condensed` | Companion fonts for `type_emoji` and `stacked_poster`. Defaults: Instrument Serif and Oswald (bundled, OFL). Use the brand's own serif/condensed face when it has one. |

## Checks (same standard as the classic renderer)

Every HTML render is checked on the rendered pixels:
- **Contrast:** each line of text against the pixels behind it. Below WCAG 2.2 AA (4.5:1, or 3:1 for headline-size text) the color is darkened or lightened within its hue and reported in `contrast_fixes`. If no color can pass (busy photo), it's reported as an issue: move the text or darken the area.
- **Minimum size:** headline 5%, body 2.9%, CTA 2.8%, labels 2.6%, URL 2.4% of the image width. Font sizes never go below these.
- **Collisions:** text, logo and emoji must not overlap, leave the frame, or enter the Stories safe zones. The renderer shrinks type step by step, then leaves out eyebrow, subhead and URL (in that order), with a warning.
- **Logo:** at least a third of the ad width, capped by height for tall logos (warned). A logo without the right version for the background sits on a chip.
- **Photos:** cover-cropped around `focus`, never distorted. If less than 60% of `subject` stays in frame, a brand gradient is used and you're told. Enlargements over 1.5× are warned.
