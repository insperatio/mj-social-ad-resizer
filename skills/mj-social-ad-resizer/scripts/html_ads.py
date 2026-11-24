#!/usr/bin/env python3
"""
mj-social-ad-resizer: HTML renderer, snapshot and final export.

Usage:
    python3 html_ads.py snapshot spec.json   # every option at one size, numbered, for the user to pick from
    python3 html_ads.py final spec.json      # only the picked options (spec["picks"]) at every placement

Three kinds of options:
  site      A layout modeled on the brand's own website hero, written per brand as an HTML file
            (spec["site_layout"]; see references/site-style.md). Not a template.
  template  The HTML templates in this file (TEMPLATES), driven by brand tokens + copy.
  classic   The original layouts drawn by make_images.py (editorial, split, ...).

HTML options are rendered in headless Chrome and checked on the rendered pixels:
  - WCAG 2.2 AA text contrast against the pixels behind every line (fixed within the hue when it fails)
  - minimum text sizes (share of image width, same rules as make_images.py)
  - text, logo and emoji never overlap and stay inside the frame and the Stories safe zone
  - logo at least a third of the ad width (capped by height for tall logos)
  - photos are never distorted; a photo whose subject would be cropped away is replaced by a brand gradient
"""
import html as _html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_images as MI  # noqa: E402  (placements, brand loader, contact sheet)

FONT_DIR = MI.FONT_DIR
PLACEMENTS = MI.PLACEMENTS
CLASSIC = MI.LAYOUTS
CLASSIC_NEEDS_PHOTO = MI.NEEDS_PHOTO
MIN_SHARE = {"h": 0.05, "b": 0.029, "c": 0.028, "l": 0.026, "u": 0.024}  # headline, body, CTA, label/tag, url
FORMATS = MI.FORMATS
def furl(p):
    return "file://" + quote(os.path.abspath(p))


EMOJI_FONTS = "'Apple Color Emoji','Noto Color Emoji','Segoe UI Emoji',sans-serif"

warnings = []
contrast_fixes = []


def warn(msg):
    if msg not in warnings:
        warnings.append(msg)


# ============================================================ color helpers
def rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexc(c):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in c[:3])


def mix(a, b, t):
    a, b = rgb(a) if isinstance(a, str) else a, rgb(b) if isinstance(b, str) else b
    return hexc([a[i] + (b[i] - a[i]) * t for i in range(3)])


def lum(c):
    c = rgb(c) if isinstance(c, str) else c
    f = lambda v: (v / 255) / 12.92 if v / 255 <= .03928 else (((v / 255) + .055) / 1.055) ** 2.4
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2])


def ratio(a, b):
    x, y = sorted([lum(a), lum(b)], reverse=True)
    return (x + .05) / (y + .05)


def is_light(c):
    return lum(c) > 0.4


def ensure(c, bg, need):
    """Darken or lighten c (same hue) until it reaches `need` against bg."""
    if ratio(c, bg) >= need:
        return c
    for t in [i / 40 for i in range(1, 41)]:
        for target in (("#000000", "#FFFFFF") if is_light(bg) else ("#FFFFFF", "#000000")):
            cand = mix(c, target, t)
            if ratio(cand, bg) >= need:
                return cand
    return "#000000" if is_light(bg) else "#FFFFFF"


# ============================================================ brand tokens
WEIGHTS = {"thin": 100, "extralight": 200, "light": 300, "regular": 400, "book": 400, "medium": 500,
           "semibold": 600, "bold": 700, "extrabold": 800, "black": 900, "heavy": 900}


def _weight_of(entry, default):
    if not entry:
        return default
    v = (entry.get("variation") or "").lower().replace(" ", "").replace("-", "")
    if v in WEIGHTS:
        return WEIGHTS[v]
    name = os.path.basename(entry.get("path") or "").lower()
    for k in sorted(WEIGHTS, key=len, reverse=True):
        if k in name.replace("-", "").replace("_", ""):
            return WEIGHTS[k]
    return default


def brand_tokens(brand):
    """HTML tokens. brand.json -> "html" may set any of these; the rest are derived from "colors"."""
    c = brand["colors"]
    given = brand.get("html") or {}
    light_bgs = [x for x in (c.get("surface"), c.get("background"), c.get("background_2")) if x and is_light(x)]
    surface = given.get("surface") or (light_bgs[0] if light_bgs else "#FFFFFF")
    darks = [x for x in (c.get("text"), c.get("surface_text"), c.get("background"), c.get("scrim"), c.get("primary"),
                         (brand.get("style") or {}).get("dark_background")) if x and not is_light(x)]
    darkest = min(darks, key=lum) if darks else "#111111"
    ink = given.get("ink") or (c["surface_text"] if c.get("surface_text") and ratio(c["surface_text"], surface) >= 7 else ensure(darkest, surface, 7))
    primary = given.get("primary") or c["primary"]
    dark = given.get("dark") or (brand.get("style") or {}).get("dark_background") or (darkest if lum(darkest) < 0.06 else mix(primary, "#000000", 0.6))
    grad = brand.get("gradient") or []
    t = {
        "ink": ink,
        "ink_alt": given.get("ink_alt") or ensure(primary if not is_light(primary) else dark, surface, 7),
        "primary": primary,
        "on_primary": given.get("on_primary") or c.get("on_primary") or ("#111111" if is_light(primary) else "#FFFFFF"),
        "text_accent": given.get("text_accent") or ensure(c.get("value_on_light") or primary, surface, 4.5),
        "text_accent_dark": given.get("text_accent_dark") or ensure(c.get("value") if c.get("value") and not is_light(primary) else mix(primary, "#FFFFFF", 0.55), dark, 4.5),
        "surface": surface,
        "tint": given.get("tint") or mix(primary, "#FFFFFF", 0.92),
        "dark": dark,
        "shape2": given.get("shape2") or c.get("accent") or mix(primary, "#FFFFFF", 0.35),
        "shape3": given.get("shape3") or mix(primary, "#FFFFFF", 0.65),
        "cream": given.get("cream") or mix(primary, "#FBFAF7", 0.96),
        "grey": given.get("grey") or mix(ink, "#FFFFFF", 0.9),
        "grad_a": given.get("grad_a") or (grad[0] if grad else dark),
        "grad_b": given.get("grad_b") or (grad[-1] if grad else primary),
        "radius": given.get("radius", {"pill": 999, "square": 0}.get((brand.get("button") or {}).get("radius"), (brand.get("button") or {}).get("radius", 8))),
    }
    if not isinstance(t["radius"], (int, float)):
        t["radius"] = 8
    t["grad_text"] = given.get("grad_text") or ("#FFFFFF" if ratio("#FFFFFF", t["grad_a"]) >= 4.5 else ink)
    return t


def fonts_css(brand):
    f = brand["fonts"]
    css, fam = [], {}
    seen = {}
    for role, fallback in (("heading", 700), ("body", 400), ("label", 600)):
        e = f.get(role) or f["body"]
        p = e["path"]
        name = seen.get(p)
        if not name:
            name = f"Brand{role.title()}"
            seen[p] = name
            variable = "_wght" in os.path.basename(p) or "[wght]" in p or "Variable" in p or "_opsz" in p
            wr = "100 900" if variable else str(_weight_of(e, fallback))
            css.append(f"@font-face {{ font-family: '{name}'; src: url('{furl(p)}'); font-weight: {wr}; }}")
        fam[role] = (name, _weight_of(e, fallback))
    extras = (brand.get("html") or {}).get("fonts") or {}
    serif_i = extras.get("serif_italic") or os.path.join(FONT_DIR, "InstrumentSerif-Italic.ttf")
    serif_r = extras.get("serif") or os.path.join(FONT_DIR, "InstrumentSerif-Regular.ttf")
    cond = extras.get("condensed") or os.path.join(FONT_DIR, "Oswald_wght.ttf")
    css.append(f"@font-face {{ font-family: 'CompanionSerif'; src: url('{furl(serif_i)}'); font-style: italic; }}")
    css.append(f"@font-face {{ font-family: 'CompanionSerif'; src: url('{furl(serif_r)}'); font-style: normal; }}")
    css.append(f"@font-face {{ font-family: 'CompanionCondensed'; src: url('{furl(cond)}'); font-weight: 200 700; }}")
    return "\n".join(css), fam


# ============================================================ icons (simple line icons drawn here)
ICONS = {
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "zap": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
    "layout": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 9v11"/>',
    "trend": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "chat": '<path d="M4 5h16v11H9l-5 4z"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "phone": '<rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M11 18h2"/>',
    "coin": '<circle cx="12" cy="12" r="9"/><path d="M14.5 9.5c-.5-1-1.5-1.5-2.5-1.5-1.7 0-2.8 1-2.8 2.1 0 2.8 5.6 1.4 5.6 4.1 0 1.2-1.2 2.3-2.8 2.3-1.2 0-2.3-.6-2.8-1.6M12 6.5V8m0 8.5V18"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.5-3.5 3.2-5.5 6.5-5.5s6 2 6.5 5.5"/><circle cx="17" cy="9" r="2.5"/><path d="M17 14c2.5 0 4.2 1.6 4.5 4.5"/>',
    "star": '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "card": '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19M6 15h4"/>',
    "heart": '<path d="M12 20s-7.5-4.6-7.5-10A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 7.5 3c0 5.4-7.5 10-7.5 10z"/>',
    "book": '<path d="M4 4.5h6a2 2 0 0 1 2 2V20a2 2 0 0 0-2-2H4zM20 4.5h-6a2 2 0 0 0-2 2V20a2 2 0 0 1 2-2h6z"/>',
    "home": '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
}
ICON_WORDS = [
    ("coin", r"pay|money|saving|price|cost|\$|fee|earn|income|rate|cd\b|budget|financ"),
    ("card", r"card|checkout|payment processing|pos\b|point of sale"),
    ("shield", r"secur|safe|insur|protect|trust|fdic|privacy|guarant"),
    ("phone", r"phone|mobile|online|app\b|digital|anywhere"),
    ("chat", r"brand|messag|voice|story|talk|support|coach|1:1|advis"),
    ("layout", r"web|site|design|ux|ui\b|page|template"),
    ("trend", r"market|growth|grow|result|plan|scale|convert|revenue|roi|lift"),
    ("clock", r"time|week|month|hour|fast|quick|day|minute|part.?time|schedule"),
    ("users", r"team|people|network|community|employ|hire|talent|staff|payroll"),
    ("target", r"goal|target|focus|strateg|priorit"),
    ("book", r"learn|course|train|class|skill|education|certif"),
    ("home", r"home|mortgage|house|local|branch|in person"),
    ("calendar", r"book|consult|call|meeting|event|calendar"),
    ("heart", r"care|health|wellness|love|family"),
    ("star", r"award|best|top|rated|quality|premium"),
]


def pick_icon(text):
    t = text.lower()
    for name, pat in ICON_WORDS:
        if re.search(pat, t):
            return name
    return "check"


def icon(name, color, size):
    return (f"<svg viewBox='0 0 24 24' width='{size:.0f}' height='{size:.0f}' fill='none' stroke='{color}' stroke-width='2' "
            f"stroke-linecap='round' stroke-linejoin='round' style='flex:0 0 auto'>{ICONS.get(name, ICONS['check'])}</svg>")


# ============================================================ copy
def esc(s):
    return _html.escape(s or "", quote=False)


def with_emphasis(text, emphasis=None):
    """'*word*' marks emphasis. A classic-style `emphasis` (end of the headline) is converted."""
    text = text or ""
    if "*" not in text and emphasis and text.rstrip().endswith(emphasis.strip()):
        i = text.rstrip().rfind(emphasis.strip())
        text = text[:i] + "*" + emphasis.strip() + "*" + text.rstrip()[i + len(emphasis.strip()):]
    return text


def em_html(text, style):
    parts = text.split("*")
    return "".join(f"<span class='emph' style=\"{style}\">{esc(p)}</span>" if i % 2 else esc(p) for i, p in enumerate(parts))


def plain(text):
    return (text or "").replace("*", "")


def resolve_copy(v):
    c = dict(v or {})
    c["headline"] = with_emphasis(c.get("headline", ""), c.get("emphasis"))
    bl = []
    for b in c.get("bullets") or [f"{f.get('value', '')} {f.get('label', '')}".strip() for f in (c.get("facts") or [])][:3]:
        if isinstance(b, dict):
            bl.append({"text": b.get("text", ""), "icon": b.get("icon") or pick_icon(b.get("text", ""))})
        else:
            bl.append({"text": b, "icon": pick_icon(b)})
    c["bullets"] = bl
    return c


# ============================================================ photos
class Photos:
    def __init__(self, spec, spec_dir):
        self.items = []
        for key, val in (spec.get("images") or {}).items():
            e = dict(val) if isinstance(val, dict) else {"path": val}
            p = e["path"] if os.path.isabs(e["path"]) else os.path.join(spec_dir, e["path"])
            if not os.path.exists(p):
                warn(f"Photo not found: {p}")
                continue
            with Image.open(p) as im:
                iw, ih = im.size
            f = e.get("focus") or {"x": 0.5, "y": 0.45}
            sub = e.get("subject") or {"x0": max(0, f["x"] - 0.2), "y0": max(0, f["y"] - 0.25), "x1": min(1, f["x"] + 0.2), "y1": min(1, f["y"] + 0.25)}
            self.items.append({"key": key, "path": p, "w": iw, "h": ih, "focus": f, "subject": sub})
        self.min_visible = spec.get("min_subject_visible", 0.6)

    def __bool__(self):
        return bool(self.items)

    def css(self, fw, fh, fallback, tag="", prefer=None):
        """CSS background for a frame of fw x fh (device px): cover crop around the focus point."""
        if not self.items:
            return fallback
        cands = sorted(self.items, key=lambda e: abs((e["w"] / e["h"]) - (fw / max(fh, 1))))
        if prefer:
            cands = [e for e in cands if e["key"] == prefer] + [e for e in cands if e["key"] != prefer]
        e = cands[0]
        sc = max(fw / e["w"], fh / e["h"])
        vw, vh = fw / sc, fh / sc
        left = min(max(e["focus"]["x"] * e["w"] - vw / 2, 0), e["w"] - vw)
        top = min(max(e["focus"]["y"] * e["h"] - vh / 2, 0), e["h"] - vh)
        s = e["subject"]
        sx0, sy0, sx1, sy1 = s["x0"] * e["w"], s["y0"] * e["h"], s["x1"] * e["w"], s["y1"] * e["h"]
        inter = max(0, min(sx1, left + vw) - max(sx0, left)) * max(0, min(sy1, top + vh) - max(sy0, top))
        area = max(1, (sx1 - sx0) * (sy1 - sy0))
        if inter / area < self.min_visible:
            warn(f"{tag}: only {inter / area:.0%} of the photo's subject would be in frame, so a brand gradient is used instead.")
            return fallback
        if sc > 1.5:
            warn(f"{tag}: photo enlarged {sc:.1f}x and may look soft. A larger photo will be sharper.")
        px = 0 if e["w"] - vw < 1 else left / (e["w"] - vw) * 100
        py = 0 if e["h"] - vh < 1 else top / (e["h"] - vh) * 100
        return f"url({furl(e['path'])}) {px:.1f}% {py:.1f}% / cover no-repeat"


# ============================================================ render context
class Ctx:
    def __init__(self, brand, tokens, fam, photos, copy, w, h, placement, fit=1.0, drop=(), tag="", url=""):
        self.b, self.T, self.fam, self.photos, self.c = brand, tokens, fam, photos, copy
        self.w, self.h, self.fit, self.drop, self.tag, self.url = w, h, fit, set(drop), tag, url
        r = h / w
        self.kind = "wide" if r < 0.75 else "sq" if r < 1.12 else "portrait" if r < 1.4 else "tall" if r < 1.7 else "story"
        self.s = (h / 1080 * 1.3) if self.kind == "wide" else (w / 1080) * {"story": 1.16, "tall": 1.07}.get(self.kind, 1.0)
        p = PLACEMENTS.get(placement, {})
        self.pt = round(h * p.get("safe_top", 0))
        self.pb = round(h * p.get("safe_bottom", 0))

    def px(self, n):
        return n * self.s

    def fs(self, n, kind="b"):
        """Font size: scaled, shrunk by fit, never below the minimum share of the image width."""
        return max(n * self.s * self.fit, MIN_SHARE[kind] * self.w)

    def head(self, weight=None):
        n, wgt = self.fam["heading"]
        return f"font-family:'{n}';font-weight:{weight or wgt}"

    def body(self, weight=None):
        n, wgt = self.fam["body"]
        return f"font-family:'{n}';font-weight:{weight or wgt}"

    def label(self, weight=None):
        n, wgt = self.fam["label"]
        return f"font-family:'{n}';font-weight:{weight or wgt}"

    def logo(self, on_dark, width=None, center=False):
        """Logo at least 1/3 of the ad width (capped so a tall logo stays reasonable)."""
        b = self.b
        width = max(width or 0, self.w * 0.34)
        src = (b.get("logo_on_dark") if on_dark else b.get("logo"))
        chip = None
        if not src:
            other = b.get("logo") if on_dark else b.get("logo_on_dark")
            if other:
                src, chip = other, ("#FFFFFF" if on_dark else self.T["dark"])
        if not src:
            if not b.get("name"):
                return ""
            col = "#FFFFFF" if on_dark else self.T["ink"]
            return (f"<div class='logo wordmark' data-check='l' style=\"{self.head()};color:{col};font-size:{self.fs(46, 'l'):.0f}px;"
                    f"letter-spacing:-.01em;white-space:nowrap\">{esc(b['name'])}</div>")
        with Image.open(src) as im:
            lw, lh = im.size
        width = min(width, (self.h * (0.15 if self.kind != "wide" else 0.2)) * lw / lh)
        if width < self.w / 3 - 1:
            warn(f"{self.tag}: the logo is tall, so it's {width / self.w:.0%} of the ad width (height-capped) instead of a third.")
        img = f"<img class='logo' src='{furl(src)}' style='width:{width:.0f}px;height:auto;display:block'>"
        if chip:
            pad = self.px(18)
            return f"<div class='logo' style='background:{chip};padding:{pad:.0f}px {pad * 1.4:.0f}px;border-radius:{self.px(14):.0f}px;display:inline-block'>{img}</div>"
        return img

    def url_el(self, color, align="left", extra=""):
        if not self.url or "url" in self.drop:
            return ""
        return (f"<div data-check='u' data-optional='url' style=\"{self.label()};color:{color};font-size:{self.fs(26, 'u'):.0f}px;"
                f"text-align:{align};letter-spacing:.02em;{extra}\">{esc(self.url)}</div>")

    def photo(self, fw, fh, prefer=None):
        T = self.T
        return self.photos.css(fw, fh, f"linear-gradient(135deg,{T['grad_a']},{T['grad_b']})", self.tag, prefer)

    def opt(self, key, html_):
        return "" if key in self.drop else html_


def base_css(x):
    return (f"* {{ box-sizing: border-box; margin: 0; padding: 0; }} html, body {{ width: {x.w}px; height: {x.h}px; overflow: hidden; position: relative; }}"
            f" .emo, .e {{ font-family: {EMOJI_FONTS}; line-height: 1; }} ul {{ list-style: none; }}")


# ============================================================ templates
# Each returns body HTML. Text that must pass checks carries data-check: h (headline), b (body), c (CTA), l (label), u (url).
# Optional copy carries data-optional so the fitter can drop it when space runs out.

def t_headline_3_bullets(x):
    T, c, s = x.T, x.c, x.s
    bl = c["bullets"][:3]
    dot = x.px(64)
    items = "".join(f"<li style='display:flex;align-items:center;gap:{x.px(24):.0f}px'><span style='flex:0 0 {dot:.0f}px;height:{dot:.0f}px;border-radius:50%;background:{T['primary']};display:grid;place-items:center'>{icon(b['icon'], T['on_primary'], dot * .53)}</span>"
                    f"<span data-check='b' style=\"{x.body(500)};color:{T['ink']};font-size:{x.fs(42):.0f}px;line-height:1.2\">{esc(b['text'])}</span></li>" for b in bl)
    head = f"<h1 data-check='h' style=\"{x.head(700)};color:{T['ink']};font-size:{x.fs(84, 'h'):.0f}px;line-height:1.06;letter-spacing:-.02em\">{em_html(c['headline'], 'color:' + T['text_accent'])}</h1>"
    lst = f"<ul style='display:flex;flex-direction:column;gap:{x.px(22):.0f}px'>{items}</ul>"
    foot_h = x.px(150) if x.kind != "wide" else x.h * 0.2
    shapes = (f"<div style='flex:1.2;background:{T['primary']};border-radius:0 {foot_h / 2:.0f}px {foot_h / 2:.0f}px 0;margin-left:-{foot_h / 2:.0f}px;position:relative;z-index:0'></div>"
              f"<div style='flex:0 0 {foot_h:.0f}px;background:{T['shape2']};border-radius:50%'></div>"
              f"<div style='flex:0 0 {foot_h:.0f}px;background:{T['shape3']};border-radius:{foot_h / 2:.0f}px 0 0 0'></div>")
    foot = (f"<div style='flex:0 0 {foot_h:.0f}px;display:flex;margin-bottom:{x.pb:.0f}px'><div style='flex:0 0 auto;min-width:46%;background:{T['dark']};border-radius:0 {foot_h / 2:.0f}px {foot_h / 2:.0f}px 0;"
            f"display:flex;align-items:center;padding:0 {x.px(60):.0f}px 0 {x.px(70):.0f}px;position:relative;z-index:1'>{x.logo(True, min(x.w * .34, foot_h * 3.2))}</div>{shapes}</div>")
    if x.kind == "wide":
        return (f"<div style='display:flex;height:100%'><div style='flex:0 0 40%;background:{x.photo(x.w * .4, x.h)}'></div>"
                f"<div style='flex:1;display:flex;flex-direction:column;background:{T['surface']}'><div style='flex:1;padding:{x.px(40):.0f}px {x.px(50):.0f}px;display:flex;flex-direction:column;justify-content:center;gap:{x.px(26):.0f}px'>{head}{lst}</div>{foot}</div></div>")
    ph_h = x.h * (0.36 if x.kind in ("sq", "portrait") else 0.38) + x.pt
    return (f"<div style='display:flex;flex-direction:column;height:100%;background:{T['surface']}'>"
            f"<div style='flex:0 0 {ph_h:.0f}px;background:{x.photo(x.w, ph_h)}'></div>"
            f"<div style='flex:1;padding:{x.px(40):.0f}px {x.px(70):.0f}px 0;display:flex;flex-direction:column;justify-content:center;gap:{x.px(34):.0f}px'>{head}{lst}{x.url_el(T['ink'])}</div>"
            f"<div style='height:{x.px(30):.0f}px'></div>{foot}</div>")


def t_icon_list(x):
    T, c = x.T, x.c
    bl = c["bullets"][:4]
    rows = "".join(f"<div style='display:flex;align-items:center;gap:{x.px(34):.0f}px'>{icon(b['icon'], T['primary'], x.px(84))}"
                   f"<span data-check='b' style=\"{x.label(600)};color:{T['ink']};font-size:{x.fs(52 if len(bl) < 4 else 46):.0f}px;line-height:1.15\">{esc(b['text'])}</span></div>" for b in bl)
    head_txt = c.get("list_headline") or c["headline"]
    head = f"<h1 data-check='h' style=\"{x.head(700)};color:{T['ink']};font-size:{x.fs(84, 'h'):.0f}px;line-height:1.08;letter-spacing:-.02em;text-align:{'left' if x.kind == 'wide' else 'center'}\">{em_html(head_txt, 'color:' + T['text_accent'])}</h1>"
    cap = f"<div style='position:absolute;left:{x.px(40):.0f}px;right:{x.px(40):.0f}px;top:0;height:{x.px(56) + x.pt:.0f}px;background:{T['dark']};border-radius:0 0 {x.px(40):.0f}px {x.px(40):.0f}px'></div>"
    lg = f"<div style='position:absolute;right:{x.px(70):.0f}px;bottom:{x.px(60) + x.pb:.0f}px;display:flex;align-items:center;gap:{x.px(30):.0f}px'>{x.url_el(T['ink'])}{x.logo(False)}</div>"
    if x.kind == "wide":
        return (f"<div style='height:100%;background:{T['surface']}'>{cap}<div style='position:absolute;left:{x.px(60):.0f}px;right:{x.px(60):.0f}px;top:{x.px(90):.0f}px;bottom:{x.h * .26:.0f}px;display:flex;gap:{x.px(60):.0f}px;align-items:center'>"
                f"<div style='flex:1'>{head}</div><div style='flex:1.1;display:flex;flex-direction:column;gap:{x.px(26):.0f}px'>{rows}</div></div>{lg}</div>")
    return (f"<div style='height:100%;background:{T['surface']}'>{cap}<div style='position:absolute;left:{x.px(80):.0f}px;right:{x.px(80):.0f}px;top:{x.px(120) + x.pt:.0f}px;bottom:{x.px(190) + x.pb:.0f}px;display:flex;flex-direction:column;gap:{x.px(50):.0f}px'>"
            f"{head}<div style='flex:1;display:flex;flex-direction:column;justify-content:space-evenly;padding-left:{x.px(20):.0f}px'>{rows}</div></div>{lg}</div>")


def t_question_checks(x):
    T, c = x.T, x.c
    q = c.get("question") or c["headline"]
    ans = c.get("answer") or c.get("subhead")
    checks = "".join(f"<li style='display:flex;align-items:center;gap:{x.px(18):.0f}px'>{icon('check', T['text_accent'], x.px(46))}"
                     f"<span data-check='b' style=\"{x.label(600)};color:{T['ink']};font-size:{x.fs(42):.0f}px\">{esc(b['text'])}</span></li>" for b in c["bullets"][:3])
    deco = (f"<div style='position:absolute;right:-{x.px(180):.0f}px;top:-{x.px(120):.0f}px;width:{x.px(620):.0f}px;height:{x.px(620):.0f}px;border-radius:{x.px(120):.0f}px;background:{T['tint']};transform:rotate(28deg)'></div>"
            f"<div style='position:absolute;left:-{x.px(220):.0f}px;bottom:-{x.px(260):.0f}px;width:{x.px(620):.0f}px;height:{x.px(620):.0f}px;border-radius:{x.px(120):.0f}px;background:{T['tint']};transform:rotate(28deg)'></div>")
    head = f"<h1 data-check='h' style=\"{x.head(700)};color:{T['ink']};font-size:{x.fs(88, 'h'):.0f}px;line-height:1.08;letter-spacing:-.02em\">{em_html(q, 'color:' + T['text_accent'])}</h1>"
    sub = x.opt("subhead", f"<p data-check='b' data-optional='subhead' style=\"{x.body()};color:{T['ink']};font-size:{x.fs(40):.0f}px;line-height:1.3\">{esc(ans)}</p>") if ans else ""
    ul = f"<ul style='display:flex;flex-direction:column;gap:{x.px(16):.0f}px;align-items:flex-start'>{checks}</ul>"
    if x.kind == "wide":
        return (f"<div style='height:100%;background:{T['surface']}'>{deco}<div style='position:absolute;inset:{x.px(60):.0f}px {x.px(70):.0f}px;display:flex;gap:{x.px(60):.0f}px;align-items:center'>"
                f"<div style='flex:1.2;display:flex;flex-direction:column;gap:{x.px(24):.0f}px'>{head}{sub}</div>"
                f"<div style='flex:1;display:flex;flex-direction:column;gap:{x.px(40):.0f}px'>{ul}{x.logo(False, x.w * .3)}</div></div></div>")
    return (f"<div style='height:100%;background:{T['surface']}'>{deco}<div style='position:absolute;left:{x.px(90):.0f}px;right:{x.px(90):.0f}px;top:{x.px(110) + x.pt:.0f}px;bottom:{x.px(90) + x.pb:.0f}px;"
            f"display:flex;flex-direction:column;align-items:center;text-align:center;gap:{x.px(34):.0f}px'>{head}{sub}{ul}<div style='margin-top:auto;display:flex;flex-direction:column;align-items:center;gap:{x.px(14):.0f}px'>{x.logo(False)}{x.url_el(T['ink'], 'center')}</div></div></div>")


def t_diagonal_photo(x):
    T, c = x.T, x.c
    wide = x.kind == "wide"
    ph_bot = {"wide": 78, "story": 44, "tall": 52}.get(x.kind, 62)
    ph = f"<div style='position:absolute;inset:0;background:{x.photo(x.w * (.78 if not wide else .7), x.h * ph_bot / 100)};clip-path:polygon({30 if wide else 22}% 0,100% 0,100% {ph_bot}%)'></div>"
    ax = {"wide": (25, 30), "story": (40, 0), "tall": (44, 18)}.get(x.kind, (50, 40))
    navy = f"<div style='position:absolute;inset:0;background:{T['dark']};clip-path:polygon(100% {max(ax[0] - 8, 5)}%,100% {ax[0] + 16}%,{90 if wide else 86}% {ax[0] + 6}%)'></div>"
    ax = {"wide": (25, 30), "story": (40, 0), "tall": (44, 18)}.get(x.kind, (50, 40))
    acc = f"<div style='position:absolute;inset:0;background:{T['primary']};clip-path:polygon(100% {ax[0]}%,100% 100%,{ax[1]}% 100%)'></div>"
    head = f"<h1 data-check='h' style=\"{x.head(600)};color:{T['ink']};font-size:{x.fs(80, 'h'):.0f}px;line-height:1.12;letter-spacing:-.015em\">{em_html(c['headline'], 'color:' + T['text_accent'])}</h1>"
    fine = f"<div data-check='l' style=\"{x.body()};color:{T['ink']};font-size:{x.fs(30, 'l'):.0f}px\">{esc(c['fine'])}</div>" if c.get("fine") else ""
    sub = x.opt("subhead", f"<p data-check='b' data-optional='subhead' style=\"{x.body()};color:{T['ink']};font-size:{x.fs(36):.0f}px;line-height:1.3\">{esc(c['subhead'])}</p>") if c.get("subhead") else ""
    top = x.h * {"wide": 0.16, "story": 0.12, "tall": 0.26}.get(x.kind, 0.34) + x.pt
    cw = .56 if not wide else .5
    # bottom of the copy stays above the accent corner's edge at the copy's right side
    edge_y = x.h * (ax[0] / 100) + (x.h * (1 - ax[0] / 100)) * (1 - (64 * x.s + cw * x.w - ax[1] / 100 * x.w) / max(1, x.w * (1 - ax[1] / 100)))
    bottom = max(x.h - edge_y + x.px(30), x.h * (.2 if not wide else .1) + x.pb)
    copy = (f"<div style='position:absolute;left:{x.px(64):.0f}px;top:{top:.0f}px;width:{x.w * cw:.0f}px;bottom:{bottom:.0f}px;display:flex;flex-direction:column;gap:{x.px(22):.0f}px'>{head}{sub}{fine}{x.url_el(T['ink'])}</div>")
    lw = x.w * 0.34
    lg = f"<div style='position:absolute;right:{x.px(56):.0f}px;bottom:{x.px(56) + x.pb:.0f}px'>{x.logo(True, lw)}</div>"
    return f"<div style='height:100%;background:{T['surface']}'>{ph}{navy}{acc}{copy}{lg}</div>"


def t_chevron_photo(x):
    T, c = x.T, x.c
    btn = (f"<div style='background:{T['primary']};padding:{x.px(20):.0f}px {x.px(44):.0f}px;border-radius:{min(T['radius'], 999) * x.s:.0f}px'>"
           f"<span data-check='c' style=\"{x.label(700)};color:{T['on_primary']};font-size:{x.fs(34, 'c'):.0f}px\">{esc(c.get('cta') or '')}</span></div>") if c.get("cta") else ""
    head = f"<h1 data-check='h' style=\"{x.head(600)};color:{T['ink']};font-size:{x.fs(74, 'h'):.0f}px;line-height:1.12;letter-spacing:-.015em\">{em_html(c['headline'], 'color:' + T['text_accent'])}</h1>"
    sub = x.opt("subhead", f"<p data-check='b' data-optional='subhead' style=\"{x.body()};color:{T['ink']};font-size:{x.fs(36):.0f}px;line-height:1.3\">{esc(c['subhead'])}</p>") if c.get("subhead") else ""
    if x.kind == "wide":
        pw = x.w * 0.46
        return (f"<div style='height:100%;background:{T['surface']}'>"
                f"<div style='position:absolute;left:0;top:0;bottom:0;width:{pw + x.px(22):.0f}px;background:{T['primary']};clip-path:polygon(0 0,86% 0,100% 50%,86% 100%,0 100%)'></div>"
                f"<div style='position:absolute;left:0;top:0;bottom:0;width:{pw:.0f}px;background:{x.photo(pw, x.h)};clip-path:polygon(0 0,86% 0,100% 50%,86% 100%,0 100%)'></div>"
                f"<div style='position:absolute;left:{pw + x.px(60):.0f}px;right:{x.px(60):.0f}px;top:{x.px(50):.0f}px;bottom:{x.px(50):.0f}px;display:flex;flex-direction:column;justify-content:center;gap:{x.px(24):.0f}px;align-items:flex-start'>"
                f"{head}{sub}{btn}<div style='margin-top:{x.px(10):.0f}px'>{x.logo(False, x.w * .3)}</div></div></div>")
    ph_h = x.h * (0.44 if x.kind == "sq" else 0.42) + x.pt
    return (f"<div style='height:100%;background:{T['surface']}'>"
            f"<div style='position:absolute;left:0;right:0;top:0;height:{ph_h + x.px(22):.0f}px;background:{T['primary']};clip-path:polygon(0 0,100% 0,100% 86%,50% 100%,0 86%)'></div>"
            f"<div style='position:absolute;left:0;right:0;top:0;height:{ph_h:.0f}px;background:{x.photo(x.w, ph_h)};clip-path:polygon(0 0,100% 0,100% 84%,50% 100%,0 84%)'></div>"
            f"<div style='position:absolute;left:{x.px(90):.0f}px;right:{x.px(90):.0f}px;top:{ph_h + x.px(50):.0f}px;bottom:{x.px(56) + x.pb:.0f}px;display:flex;flex-direction:column;align-items:center;text-align:center;gap:{x.px(26):.0f}px'>"
            f"{head}{sub}{btn}<div style='margin-top:auto;display:flex;flex-direction:column;align-items:center;gap:{x.px(12):.0f}px'>{x.logo(False)}{x.url_el(T['ink'], 'center')}</div></div></div>")


def t_punchy_photo(x):
    T, c = x.T, x.c
    punch = c.get("punchline") or plain(c["headline"])
    shade = "linear-gradient(180deg,rgba(0,0,0,.82) 0%,rgba(0,0,0,.4) 48%,rgba(0,0,0,.25) 62%,rgba(0,0,0,.88) 100%)"
    wide = x.kind == "wide"
    head = (f"<h1 data-check='h' style=\"{x.head(800)};color:#FFFFFF;text-transform:uppercase;font-size:{x.fs(70 if not wide else 62, 'h'):.0f}px;line-height:1.1;"
            f"text-align:{'left' if wide else 'center'}\">{esc(punch).replace(chr(10), '<br>')}</h1>")
    if wide:
        shade = "linear-gradient(90deg,rgba(0,0,0,.88) 0%,rgba(0,0,0,.62) 48%,rgba(0,0,0,.2) 100%),linear-gradient(0deg,rgba(0,0,0,.55) 0%,rgba(0,0,0,0) 30%)"
        return (f"<div style='height:100%;background:#111 ;'><div style='position:absolute;inset:0;background:{x.photo(x.w, x.h)}'></div><div style='position:absolute;inset:0;background:{shade}'></div>"
                f"<div style='position:absolute;left:{x.px(60):.0f}px;top:{x.px(60):.0f}px;width:{x.w * .55:.0f}px'>{head}</div>"
                f"<div style='position:absolute;left:{x.px(60):.0f}px;bottom:{x.px(50):.0f}px;display:flex;align-items:center;gap:{x.px(30):.0f}px'>{x.logo(True)}{x.url_el('#FFFFFF')}</div></div>")
    return (f"<div style='height:100%;background:#111'><div style='position:absolute;inset:0;background:{x.photo(x.w, x.h)}'></div><div style='position:absolute;inset:0;background:{shade}'></div>"
            f"<div style='position:absolute;left:{x.px(80):.0f}px;right:{x.px(80):.0f}px;top:{x.px(90) + x.pt:.0f}px'>{head}</div>"
            f"<div style='position:absolute;left:0;right:0;bottom:{x.px(70) + x.pb:.0f}px;display:flex;flex-direction:column;align-items:center;gap:{x.px(14):.0f}px'>{x.logo(True)}{x.url_el('#FFFFFF', 'center')}</div></div>")


def t_type_emoji(x):
    T, c = x.T, x.c
    serif = f"font-family:CompanionSerif;font-style:italic;font-weight:400;letter-spacing:-.01em;color:{T['ink_alt']}"
    emo = c.get("emoji") or "✨"
    n_chars = max(8, len(plain(c["headline"])))
    lines_target = 3 if x.kind != "wide" else 2
    size = min(175, (1080 * (0.78 if x.kind != "wide" else 0.62)) * lines_target / (n_chars * 0.48))
    head = (f"<h1 style=\"{x.head(500)};font-size:{x.fs(size, 'h'):.0f}px;line-height:1.02;letter-spacing:-.025em;text-align:center\">"
            f"<span data-check='h' style='color:{T['text_accent']}'>{em_html(c['headline'], serif)}</span>"
            f"<span class='emo' style='display:inline-block;font-size:{x.fs(size * .86, 'h'):.0f}px;transform:rotate(-10deg) translateY(-{x.px(6):.0f}px);margin-left:{x.px(14):.0f}px;vertical-align:middle'>{emo}</span></h1>")
    sub_txt = c.get("subhead") or ""
    sub = x.opt("subhead", f"<div data-check='b' data-optional='subhead' style=\"{x.body()};color:{T['ink_alt']};font-size:{x.fs(34):.0f}px;text-align:center\">{esc(sub_txt)}</div>") if sub_txt else ""
    return (f"<div style='height:100%;background:{T['cream']};display:flex;flex-direction:column;align-items:center;padding:{x.px(70) + x.pt:.0f}px {x.px(80):.0f}px {x.px(60) + x.pb:.0f}px'>"
            f"<div style='flex:1;display:flex;align-items:center;justify-content:center'>{head}</div>"
            f"<div style='display:flex;flex-direction:column;align-items:center;gap:{x.px(22):.0f}px'>{sub}{x.logo(False, x.w * (.34 if x.kind != 'wide' else .28))}</div></div>")


def poster_lines(c):
    if c.get("poster"):
        out = []
        for p in c["poster"]:
            word, wt = (p, 1) if isinstance(p, str) else (p[0], p[1] if len(p) > 1 else 1)
            out.append((word, wt))
        return out
    words = plain(c["headline"]).replace(".", "").replace(",", "").split()
    if len(words) > 5:
        return None
    longest = max(words, key=len)
    return [(w, 2 if w == longest else 1) for w in words]


def t_stacked_poster(x):
    T, c = x.T, x.c
    lines = poster_lines(c) or []
    avail_h = (x.h - x.pt - x.pb) * (0.56 if x.kind != "wide" else 0.6)
    unit = avail_h / max(1, sum(0.9 * (1.6 if wt >= 2 else 1.0) for _, wt in lines))
    key_i = next((i for i, (_, wt) in enumerate(lines) if wt >= 2), 0)
    e_size = x.px(110 if x.kind != "wide" else 90)
    rows = ""
    for i, (word, wt) in enumerate(lines):
        maxw = x.w * (0.8 if x.kind != "wide" else 0.5) - (2 * (e_size + x.px(20)) if i == key_i else 0)
        sz = min(unit * (1.6 if wt >= 2 else 1.0), maxw / max(1, len(word) * 0.52))  # condensed caps run about 0.5em wide
        sz = max(sz * x.fit, MIN_SHARE["h"] * x.w)
        col = T["text_accent"] if wt >= 2 else T["ink"]
        word_el = f"<span data-check='h' style=\"font-size:{sz:.0f}px;color:{col};line-height:.9\">{esc(word)}</span>"
        if i == key_i:
            word_el = (f"<span class='e' style='font-size:{e_size:.0f}px;transform:rotate(-10deg)'>👉</span>{word_el}"
                       f"<span class='e' style='font-size:{e_size:.0f}px;transform:rotate(10deg)'>👈</span>")
        rows += f"<div style='display:flex;align-items:center;gap:{x.px(18):.0f}px'>{word_el}</div>"
    stack = f"<div style=\"font-family:CompanionCondensed;font-weight:700;text-transform:uppercase;letter-spacing:-.01em;display:flex;flex-direction:column;align-items:center\">{rows}</div>"
    sub = x.opt("subhead", f"<div data-check='b' data-optional='subhead' style=\"{x.body()};color:{T['ink']};font-size:{x.fs(36):.0f}px;line-height:1.3;text-align:center\">{esc(c.get('subhead') or '')}</div>") if c.get("subhead") else ""
    return (f"<div style='height:100%;background:{T['grey']};display:flex;flex-direction:column;align-items:center;gap:{x.px(20):.0f}px;padding:{x.px(60) + x.pt:.0f}px {x.px(60):.0f}px {x.px(60) + x.pb:.0f}px'>"
            f"{x.logo(False, x.w * (.34 if x.kind != 'wide' else .26))}<div style='flex:1;width:100%;display:flex;align-items:center;justify-content:center'>{stack}</div>{sub}</div>")


def t_gradient_minimal(x):
    T, c = x.T, x.c
    head = (f"<h1 data-check='h' style=\"{x.head(500)};color:{T['grad_text']};font-size:{x.fs(104 if x.kind != 'wide' else 96, 'h'):.0f}px;line-height:1.12;letter-spacing:-.02em;text-align:center\">"
            f"{em_html(c['headline'], '')}</h1>")
    return (f"<div style='height:100%;background:linear-gradient(180deg,{T['grad_a']} 0%,{T['grad_b']} 100%);display:flex;flex-direction:column;align-items:center;padding:{x.px(90) + x.pt:.0f}px {x.px(80):.0f}px {x.px(80) + x.pb:.0f}px'>"
            f"<div style='flex:1;display:flex;align-items:center'>{head}</div><div style='display:flex;flex-direction:column;align-items:center;gap:{x.px(14):.0f}px'>{x.logo(not is_light(T['grad_b']))}{x.url_el(T['grad_text'], 'center')}</div></div>")


def t_mosaic(x):
    T, c = x.T, x.c
    wide = x.kind == "wide"
    cols, rows = (2, 2) if wide else (3, 2)
    t = (x.h / rows) if wide else (x.w / cols)
    gw = t * cols
    gh = t * rows
    def ph(prefer_focus):
        return x.photo(t, t)
    if wide:
        cells = (f"<div style='grid-column:span 2;background:{T['primary']};border-radius:0 0 0 {t / 2:.0f}px;display:grid;place-items:center'>{x.logo(True, min(x.w * .34, t * 1.7))}</div>"
                 f"<div style='background:{ph(0)};border-radius:0 {t / 2:.0f}px 0 0'></div><div style='background:{T['shape2']};border-radius:50%'></div>")
    else:
        cells = (f"<div style='grid-column:span 2;background:{T['primary']};border-radius:0 0 0 {t / 2:.0f}px;display:grid;place-items:center'>{x.logo(True, min(x.w * .34, t * 1.7))}</div>"
             f"<div style='background:{ph(0)};border-radius:0 {t / 2:.0f}px 0 0'></div>"
             f"<div style='background:{T['shape2']};border-radius:50%'></div>"
             f"<div style='background:{ph(1)};border-radius:{t / 2:.0f}px 0 0 0'></div>"
             f"<div style='background:{T['shape3']};border-radius:0 0 {t / 2:.0f}px {t / 2:.0f}px'></div>")
    cols_css = f"repeat({cols},{t:.0f}px)"
    grid = f"<div style='position:absolute;{'right:0;top:0;bottom:0' if wide else f'left:0;right:0;bottom:{x.pb:.0f}px'};width:{gw:.0f}px;height:{gh if not wide else x.h:.0f}px;display:grid;grid-template-columns:{cols_css};grid-template-rows:repeat(2,{t:.0f}px)'>{cells}</div>"
    head = f"<h1 data-check='h' style=\"{x.head(500)};color:#FFFFFF;font-size:{x.fs(72, 'h'):.0f}px;line-height:1.12;letter-spacing:-.015em;text-align:{'left' if wide else 'center'}\">{em_html(c['headline'], 'color:' + T['text_accent_dark'])}</h1>"
    sub = x.opt("subhead", f"<p data-check='b' data-optional='subhead' style=\"{x.body()};color:#FFFFFF;font-size:{x.fs(34):.0f}px;line-height:1.3;text-align:{'left' if wide else 'center'}\">{esc(c['subhead'])}</p>") if c.get("subhead") else ""
    if wide:
        return (f"<div style='height:100%;background:{T['dark']}'>{grid}<div style='position:absolute;left:{x.px(60):.0f}px;top:{x.px(60):.0f}px;bottom:{x.px(60):.0f}px;width:{x.w - gw - x.px(110):.0f}px;display:flex;flex-direction:column;justify-content:center;gap:{x.px(20):.0f}px'>{head}{sub}{x.url_el('#FFFFFF')}</div></div>")
    top_h = x.h - gh - x.pb
    return (f"<div style='height:100%;background:{T['dark']}'><div style='position:absolute;left:{x.px(80):.0f}px;right:{x.px(80):.0f}px;top:{x.pt:.0f}px;height:{top_h - x.pt:.0f}px;display:flex;flex-direction:column;justify-content:center;gap:{x.px(18):.0f}px'>{head}{sub}{x.url_el('#FFFFFF', 'center')}</div>{grid}</div>")


def t_highlight_box(x):
    T, c = x.T, x.c
    full = plain(c["headline"])
    key = c.get("highlight") or (re.search(r"\*(.+?)\*", c["headline"]).group(1) if "*" in c["headline"] else None)
    if not key or key not in full:
        words = full.split()
        key = " ".join(words[len(words) // 3: len(words) // 3 + max(2, len(words) // 3)])
    pre, post = full.split(key, 1)
    sz = x.fs(92 if len(full) < 48 else 78, "h")
    line = lambda t: f"<div data-check='h' style=\"{x.head(500)};color:{T['ink']};font-size:{sz:.0f}px;line-height:1.12;letter-spacing:-.02em\">{esc(t.strip())}</div>" if t.strip() else ""
    box = (f"<div style='background:{T['dark']};padding:{x.px(4):.0f}px {x.px(26):.0f}px {x.px(12):.0f}px'><span data-check='h' style=\"{x.head(600)};color:#FFFFFF;font-size:{sz:.0f}px;letter-spacing:-.02em\">{esc(key)}</span></div>")
    return (f"<div style='height:100%;background:{T['cream']};display:flex;flex-direction:column;align-items:center;padding:{x.px(100) + x.pt:.0f}px {x.px(80):.0f}px {x.px(80) + x.pb:.0f}px'>"
            f"<div style='flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:{x.px(10):.0f}px'>{line(pre)}{box}{line(post)}</div>"
            f"<div style='display:flex;flex-direction:column;align-items:center;gap:{x.px(12):.0f}px'>{x.logo(False)}{x.url_el(T['ink'], 'center')}</div></div>")


# name -> (function, label, needs, short description)
TEMPLATES = {
    "headline_3_bullets": (t_headline_3_bullets, "Headline + 3 bullets", {"photo", "bullets"}, "Photo, headline, 3 icon bullets, brand-shape footer"),
    "icon_list": (t_icon_list, "Icon list", {"bullets"}, "Two-tone headline over large icon rows"),
    "question_checks": (t_question_checks, "Question + checks", {"bullets"}, "Question headline, answer line, check list"),
    "diagonal_photo": (t_diagonal_photo, "Diagonal photo", {"photo"}, "Photo wedge, accent corner holding the logo"),
    "chevron_photo": (t_chevron_photo, "Chevron photo", {"photo"}, "Photo with a V-cut edge, centered copy and button"),
    "punchy_photo": (t_punchy_photo, "Punchy photo", {"photo"}, "Dark full-bleed photo, all-caps punchline"),
    "type_emoji": (t_type_emoji, "Type + emoji", {"emoji"}, "Big sans + italic serif headline with an emoji sticker"),
    "stacked_poster": (t_stacked_poster, "Stacked poster", {"poster"}, "Condensed caps stack with pointing emoji"),
    "gradient_minimal": (t_gradient_minimal, "Gradient minimal", set(), "One centered line on a deep brand gradient"),
    "mosaic": (t_mosaic, "Mosaic", {"photo"}, "Headline over a tile grid of shapes, photo crops and logo"),
    "highlight_box": (t_highlight_box, "Highlight box", set(), "Key phrase reversed out in a solid box"),
}


def template_missing(name, copy, photos):
    needs = TEMPLATES[name][2]
    miss = []
    if "photo" in needs and not photos:
        miss.append("a photo")
    if "bullets" in needs and len(copy["bullets"]) < 3:
        miss.append("3 bullets")
    if "emoji" in needs and not copy.get("emoji"):
        miss.append("an emoji")
    if "poster" in needs and not poster_lines(copy):
        miss.append("poster words (or a headline of 5 words or fewer)")
    return miss


# ============================================================ site-style layout (per brand HTML, see references/site-style.md)
def site_html(x, template_text):
    T, c = x.T, x.c
    sub = {
        "headline": em_html(c["headline"], ""),
        "headline_plain": esc(plain(c["headline"])),
        "subhead": "" if "subhead" in x.drop else esc(c.get("subhead") or ""),
        "eyebrow": "" if "eyebrow" in x.drop else esc(c.get("eyebrow") or ""),
        "cta": esc(c.get("cta") or ""),
        "fine": esc(c.get("fine") or ""),
        "url": "" if "url" in x.drop else esc(x.url),
        "logo": x.logo(False),
        "logo_on_dark": x.logo(True),
        "bullets": "".join(f"<li><span data-check='b'>{esc(b['text'])}</span></li>" for b in c["bullets"]),
    }
    for k, (fw, fh) in {"photo": (x.w, x.h), "photo_wide": (x.w, x.h * 0.5), "photo_half": (x.w * 0.5, x.h)}.items():
        if "{{" + k + "}}" in template_text:
            sub[k] = x.photo(fw, fh)
    out = template_text
    for k, v in sub.items():
        out = out.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{(\w+)\}\}", out)
    if left:
        warn(f"site layout: unknown placeholders {sorted(set(left))}")
    vars_ = "".join(f"--{k.replace('_', '-')}:{v};" for k, v in T.items() if isinstance(v, str))
    m = {k: max(MIN_SHARE[k] * x.w, 0) for k in MIN_SHARE}
    root = (f":root{{{vars_}--w:{x.w}px;--h:{x.h}px;--s:{x.s:.4f};--fit:{x.fit:.3f};--pt:{x.pt}px;--pb:{x.pb}px;"
            f"--min-h:{m['h']:.0f}px;--min-b:{m['b']:.0f}px;--min-c:{m['c']:.0f}px;--min-l:{m['l']:.0f}px;--min-u:{m['u']:.0f}px;"
            f"--font-head:'{x.fam['heading'][0]}';--font-body:'{x.fam['body'][0]}';--font-label:'{x.fam['label'][0]}';"
            f"--w-head:{x.fam['heading'][1]};--w-body:{x.fam['body'][1]};--w-label:{x.fam['label'][1]};--radius:{T['radius']}px}}")
    return f"<style>{root}</style>" + out


# ============================================================ browser + checks
CHECK_JS = r"""
() => {
  const out = {runs: [], boxes: [], vw: innerWidth, vh: innerHeight};
  const roots = [...document.querySelectorAll('[data-check]')];
  roots.forEach((root, ri) => {
    const kind = root.dataset.check;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = walker.nextNode())) {
      if (!n.textContent.trim()) continue;
      const el = n.parentElement;
      if (el.closest('.emo,.e')) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none') continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      const rects = [...rg.getClientRects()].filter(r => r.width > 2 && r.height > 2).map(r => [r.x, r.y, r.width, r.height]);
      if (!el.dataset.cid) el.dataset.cid = 'c' + Math.random().toString(36).slice(2, 9);
      out.runs.push({root: ri, kind, cid: el.dataset.cid, color: cs.color, size: parseFloat(cs.fontSize),
                     text: n.textContent.trim().slice(0, 40), rects});
    }
    const r = root.getBoundingClientRect();
    // tight box of text lines (inline content), not the block width
    const rg = document.createRange(); rg.selectNodeContents(root);
    const lh = parseFloat(getComputedStyle(root).lineHeight);
    const lr = [...rg.getClientRects()].filter(q => q.width > 2 && q.height > 2).map(q => {
      // use the line box (line-height), not the font's full ascent/descent, so tight display leading isn't a collision
      if (!lh || lh >= q.height) return q;
      const mid = q.y + q.height / 2; return {x: q.x, y: mid - lh / 2, right: q.right, bottom: mid + lh / 2, width: q.width, height: lh};
    });
    let box = [r.x, r.y, r.right, r.bottom];
    if (lr.length) box = [Math.min(...lr.map(q => q.x)), Math.min(...lr.map(q => q.y)), Math.max(...lr.map(q => q.right)), Math.max(...lr.map(q => q.bottom))];
    out.boxes.push({id: 'text' + ri, kind: 'text', text: root.innerText.trim().slice(0, 30), box, optional: root.closest('[data-optional]')?.dataset.optional || null});
  });
  document.querySelectorAll('img.logo, div.logo:not(.wordmark)').forEach((el, i) => {
    const r = el.getBoundingClientRect(); out.boxes.push({id: 'logo' + i, kind: 'logo', box: [r.x, r.y, r.right, r.bottom], width: r.width});
  });
  document.querySelectorAll('.emo, .e').forEach((el, i) => {
    const r = el.getBoundingClientRect(); const pad = r.width * 0.12;
    out.boxes.push({id: 'emoji' + i, kind: el.classList.contains('emo') ? 'sticker' : 'emoji', box: [r.x + pad, r.y + pad, r.right - pad, r.bottom - pad]});
  });
  return out;
}
"""


def _px(im):
    f = getattr(im, "get_flattened_data", None)
    return list(f() if f else im.getdata())


def _css_rgb(s):
    return tuple(int(float(v)) for v in re.findall(r"[\d.]+", s)[:3])


def _overlap(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("The HTML templates need Playwright: pip install playwright (then `playwright install chromium` if Chrome isn't installed).")
    pw = sync_playwright().start()
    args = ["--allow-file-access-from-files", "--font-render-hinting=none"]
    for exe in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
                r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if os.path.exists(exe):
            try:
                return pw, pw.chromium.launch(executable_path=exe, args=args)
            except Exception:
                pass
    try:
        return pw, pw.chromium.launch(args=args)
    except Exception as e:
        sys.exit(f"Couldn't start Chrome for rendering ({e}). Install Google Chrome, or run: playwright install chromium")


def render_one(br, build, w, h, out_png, tag, contrast_mode="fix", tmpdir=None):
    """build(fit, drop) -> full HTML. Renders, checks, fixes contrast, retries smaller/dropping optional copy on collisions."""
    fit, drop = 1.0, []
    drops_order = ["eyebrow", "subhead", "url"]
    final_issues = []
    for attempt in range(9):
        html_doc = build(fit, drop)
        f = os.path.join(tmpdir, "page.html")
        with open(f, "w") as fh:
            fh.write(html_doc)
        pg = br.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        pg.goto(furl(f))
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(150)
        info = pg.evaluate(CHECK_JS)
        # --- layout checks: frame, safe zone, collisions
        layout_issues = []
        boxes = info["boxes"]
        for bx in boxes:
            x0, y0, x1, y1 = bx["box"]
            if x0 < -1 or y0 < -1 or x1 > w + 1 or y1 > h + 1:
                layout_issues.append(f"{bx['kind']} '{bx.get('text', '')}' goes outside the frame")
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a["kind"] == "emoji" and b["kind"] == "emoji":
                    continue
                if "sticker" in (a["kind"], b["kind"]):
                    continue
                ov = _overlap(a["box"], b["box"])
                small = min((a["box"][2] - a["box"][0]) * (a["box"][3] - a["box"][1]), (b["box"][2] - b["box"][0]) * (b["box"][3] - b["box"][1]))
                if ov > 0.06 * max(small, 1):
                    layout_issues.append(f"'{a.get('text') or a['kind']}' overlaps '{b.get('text') or b['kind']}'")
        if os.environ.get("ADS_DEBUG") and layout_issues:
            print(tag, attempt, fit, drop, layout_issues, file=sys.stderr)
        if layout_issues and attempt < 8:
            pg.close()
            if fit > 0.7:
                fit *= 0.92
            else:
                opts = [o for o in drops_order if o not in drop and any(bx.get("optional") == o for bx in boxes)]
                if not opts:
                    break
                drop.append(opts[0])
                fit = 1.0
            continue
        # --- contrast (on pixels behind each line) + minimum sizes
        pg.screenshot(path=out_png)
        pg.add_style_tag(content="[data-check], [data-check] * { color: transparent !important; text-shadow: none !important; } .emo, .e { visibility: hidden !important; }")
        bgp = out_png + ".bg.png"
        pg.screenshot(path=bgp)
        bg = Image.open(bgp).convert("RGB")
        issues, fixes = [], {}
        for run in info["runs"]:
            need = 3.0 if run["kind"] == "h" or run["size"] >= 0.045 * w else 4.5
            col = _css_rgb(run["color"])
            worst, worst_px = 99, None
            for (rx, ry, rw, rh) in run["rects"]:
                box = (max(0, int(rx)), max(0, int(ry)), min(w, int(rx + rw)), min(h, int(ry + rh)))
                if box[2] - box[0] < 2 or box[3] - box[1] < 2:
                    continue
                for p in _px(bg.crop(box).resize((32, 6))):
                    r_ = ratio(col, p)
                    if r_ < worst:
                        worst, worst_px = r_, p
            if worst_px is None:
                continue
            kind = run["kind"]
            if run["size"] < MIN_SHARE[kind] * w - 0.5:
                issues.append(f"text too small ({run['size']:.0f}px) '{run['text']}'")
            if worst < need:
                if contrast_mode == "fix":
                    # color that passes against every sampled background pixel along the line
                    pxs = []
                    for (rx, ry, rw, rh) in run["rects"]:
                        box = (max(0, int(rx)), max(0, int(ry)), min(w, int(rx + rw)), min(h, int(ry + rh)))
                        if box[2] - box[0] >= 2 and box[3] - box[1] >= 2:
                            pxs += _px(bg.crop(box).resize((32, 6)))
                    cand = hexc(col)
                    for t in [i / 30 for i in range(1, 31)]:
                        best = None
                        for target in ("#000000", "#FFFFFF"):
                            cc = mix(hexc(col), target, t)
                            if min(ratio(cc, p) for p in pxs) >= need:
                                best = cc
                                break
                        if best:
                            cand = best
                            break
                    after = min(ratio(cand, p) for p in pxs)
                    if after >= need:
                        fixes[run["cid"]] = cand
                        contrast_fixes.append({"where": tag, "text": run["text"], "from": hexc(col), "to": cand,
                                               "ratio_before": round(worst, 2), "ratio_after": round(after, 2), "needed": need})
                    else:
                        issues.append(f"contrast {worst:.1f}:1 (needs {need}:1) on a busy background: '{run['text']}'")
                else:
                    issues.append(f"contrast {worst:.1f}:1 (needs {need}:1): '{run['text']}'")
        if fixes:
            pg.close()
            with open(f, "w") as fh:
                fh.write(html_doc + "<script>" + _apply_fix_js(info["runs"], fixes) + "</script>")
            pg = br.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
            pg.goto(furl(f))
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(120)
            pg.screenshot(path=out_png)
        pg.close()
        os.remove(bgp)
        final_issues = issues
        logo_boxes = [bx for bx in boxes if bx["kind"] == "logo"]
        return {"issues": issues, "dropped": drop, "fit": round(fit, 2), "logo_share": round(max([lb["width"] for lb in logo_boxes] or [0]) / w, 2)}
    return {"issues": final_issues + layout_issues, "dropped": drop, "fit": round(fit, 2)}


def _apply_fix_js(runs, fixes):
    """Re-identify text runs in document order and recolor the ones that were fixed."""
    order = [r["cid"] for r in runs]
    want = {i: fixes[c] for i, c in enumerate(order) if c in fixes}
    return ("(() => { const roots=[...document.querySelectorAll('[data-check]')]; let i=0; const want=" + json.dumps(want) + ";"
            "roots.forEach(root=>{const wk=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let n;"
            "while((n=wk.nextNode())){ if(!n.textContent.trim()) continue; const el=n.parentElement; if(el.closest('.emo,.e')) continue;"
            "const cs=getComputedStyle(el); if(cs.visibility==='hidden'||cs.display==='none') continue;"
            "const rg=document.createRange(); rg.selectNodeContents(n); if(![...rg.getClientRects()].some(r=>r.width>2&&r.height>2)) continue;"
            "if(want[i]) el.style.setProperty('color', want[i], 'important'); i++; }}); })();")


# ============================================================ classic layouts (make_images.py)
def run_classic(spec, spec_dir, layouts, out_dir, stage, placement=None, placements=None, name=None):
    sub = json.loads(json.dumps({k: v for k, v in spec.items() if k not in ("picks", "site_layout", "templates", "stage", "concepts", "layout")}))
    for k in ("brand",):
        if isinstance(sub.get(k), str) and not os.path.isabs(sub[k]):
            sub[k] = os.path.join(spec_dir, sub[k])
    for key, val in (sub.get("images") or {}).items():
        if isinstance(val, dict) and not os.path.isabs(val["path"]):
            val["path"] = os.path.join(spec_dir, val["path"])
        elif isinstance(val, str) and not os.path.isabs(val):
            sub["images"][key] = os.path.join(spec_dir, val)
    if sub.get("logo"):
        for k in ("logo", "logo_on_dark"):
            if sub["logo"].get(k) and not os.path.isabs(sub["logo"][k]):
                sub["logo"][k] = os.path.join(spec_dir, sub["logo"][k])
    sub["mode"], sub["output_dir"] = "ad", out_dir
    if name:
        sub["name"] = name
    for v in sub.get("variants") or []:
        hl = v.get("headline", "")
        m = re.search(r"\*(.+?)\*", hl)
        if m:
            v["headline"] = hl.replace("*", "")
            if v["headline"].rstrip(" .!?").endswith(m.group(1)):
                v.setdefault("emphasis", m.group(1))
    if stage == "concepts":
        sub.update({"stage": "concepts", "concepts": layouts, "concept_placement": placement})
    else:
        sub.update({"stage": "final", "layout": layouts[0], "placements": placements})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=spec_dir) as tf:
        json.dump(sub, tf)
        tpath = tf.name
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "make_images.py"), tpath], capture_output=True, text=True)
    finally:
        os.remove(tpath)
    if r.returncode != 0:
        warn(f"classic layouts {layouts}: {r.stderr.strip()[-300:] or r.stdout.strip()[-300:]}")
        return None
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


# ============================================================ snapshot / final
def load(spec_path):
    spec_path = os.path.abspath(spec_path)
    spec_dir = os.path.dirname(spec_path)
    with open(spec_path) as f:
        spec = json.load(f)
    brand = MI.load_brand(spec, spec_dir)
    if spec.get("logo"):
        for k in ("logo", "logo_on_dark"):
            if spec["logo"].get(k):
                p = spec["logo"][k] if os.path.isabs(spec["logo"][k]) else os.path.join(spec_dir, spec["logo"][k])
                if os.path.exists(p):
                    brand[k] = p
    if spec.get("use_logo") is False:
        brand["logo"] = brand["logo_on_dark"] = None
    if spec.get("show_wordmark") is False and not brand.get("logo"):
        brand["name"] = ""
    url = "" if spec.get("show_url") is False else (spec.get("url_text") or brand.get("domain") or "")
    return spec, spec_dir, brand, url


def all_options(spec, spec_dir, photos, copy):
    opts = []
    sl = spec.get("site_layout")
    if sl:
        p = sl if os.path.isabs(sl) else os.path.join(spec_dir, sl)
        if os.path.exists(p):
            opts.append(("site", "site", "Your website style"))
        else:
            warn(f"site_layout not found: {p}")
    else:
        warn("No site_layout in the spec: the website-style option is missing. Build one (references/site-style.md) unless the site has no clear hero.")
    wanted = spec.get("templates") or list(TEMPLATES)
    for t in wanted:
        if t not in TEMPLATES:
            warn(f"unknown template {t}")
            continue
        miss = template_missing(t, copy, photos)
        if miss:
            warn(f"template {t} skipped: needs {', '.join(miss)} in the copy/photos.")
            continue
        opts.append(("template", t, TEMPLATES[t][1]))
    classic = spec.get("classic", CLASSIC)
    for l in classic:
        if l in CLASSIC_NEEDS_PHOTO and not photos:
            continue
        if l == "stats" and not (copy.get("facts")):
            continue
        opts.append(("classic", l, MI.LAYOUT_LABELS[l]))
    return opts


def option_id(kind, key):
    return "site" if kind == "site" else key


def build_fn(kind, key, spec, spec_dir, brand, tokens, fcss, fam, photos, copy, w, h, placement, tag, url):
    site_text = None
    if kind == "site":
        p = spec["site_layout"] if os.path.isabs(spec["site_layout"]) else os.path.join(spec_dir, spec["site_layout"])
        with open(p) as fh:
            site_text = fh.read()

    def build(fit, drop):
        x = Ctx(brand, tokens, fam, photos, copy, w, h, placement, fit, drop, tag, url)
        body = site_html(x, site_text) if kind == "site" else TEMPLATES[key][0](x)
        base = f"<base href='{furl(spec_dir)}/'>" if kind == "site" else ""
        return f"<!doctype html><html><head><meta charset='utf-8'>{base}<style>{fcss}\n{base_css(x)}</style></head><body class='r-{x.kind}'>{body}</body></html>"
    return build


def snapshot(spec_path):
    spec, spec_dir, brand, url = load(spec_path)
    name = spec.get("name", "Social").replace(" ", "_")
    out_dir = spec["output_dir"]
    sdir = os.path.join(out_dir, "snapshot")
    os.makedirs(sdir, exist_ok=True)
    photos = Photos(spec, spec_dir)
    variants = spec.get("variants") or []
    if not variants:
        sys.exit("Add at least one variant with a headline (and bullets, question, punchline, emoji, poster for the templates).")
    copy = resolve_copy(variants[0])
    tokens = brand_tokens(brand)
    fcss, fam = fonts_css(brand)
    cp = spec.get("snapshot_placement") or spec.get("concept_placement") or "meta_portrait"
    P = PLACEMENTS[cp]
    opts = all_options(spec, spec_dir, photos, copy)
    items, listing = [], []
    pw, br = browser()
    tmp = tempfile.mkdtemp()
    n = 0
    try:
        for kind, key, label in opts:
            if kind == "classic":
                continue
            n += 1
            out = os.path.join(sdir, f"{n:02d}_{key}.png")
            tag = f"option {n} ({key})"
            res = render_one(br, build_fn(kind, key, spec, spec_dir, brand, tokens, fcss, fam, photos, copy, P["w"], P["h"], cp, tag, url),
                             P["w"], P["h"], out, tag, spec.get("contrast", "fix"), tmp)
            listing.append({"number": n, "id": option_id(kind, key), "kind": kind, "label": label, "file": out, **res})
            items.append((out, f"{n} · {label.upper()}\n{'website style' if kind == 'site' else 'template'}: {option_id(kind, key)}"))
    finally:
        br.close()
        pw.stop()
        shutil.rmtree(tmp, ignore_errors=True)
    classic = [key for kind, key, _ in opts if kind == "classic"]
    if classic:
        r = run_classic(spec, spec_dir, classic, os.path.join(sdir, "_classic"), "concepts", placement=cp, name=name)
        if r:
            for e in r.get("concepts", []):
                n += 1
                dst = os.path.join(sdir, f"{n:02d}_{e['layout']}.png")
                shutil.move(e["file"], dst)
                lab = MI.LAYOUT_LABELS[e["layout"]]
                listing.append({"number": n, "id": e["layout"], "kind": "classic", "label": lab, "file": dst})
                items.append((dst, f"{n} · {lab.upper()}\nclassic: {e['layout']}"))
            for w_ in r.get("warnings", []):
                warn("classic: " + w_)
            for cf in (r.get("contrast") or {}).get("issues", []):
                contrast_fixes.append({"where": "classic " + ", ".join(cf.get("where", [])), "text": cf.get("example_text"), "from": cf.get("from"),
                                       "to": cf.get("to"), "ratio_before": cf.get("ratio_before"), "ratio_after": cf.get("ratio_after"), "needed": cf.get("needed")})
            if r.get("brand_report_image") and os.path.exists(r["brand_report_image"]):
                shutil.move(r["brand_report_image"], os.path.join(out_dir, f"{name}_brand-report.png"))
        shutil.rmtree(os.path.join(sdir, "_classic"), ignore_errors=True)
    sheet_path = os.path.join(out_dir, f"{name}_snapshot.png")
    MI.sheet(items, sheet_path, f"{name.replace('_', ' ')}: every option",
             f"{P['label']} · {P['w']}×{P['h']} · pick the numbers you want, then every size is built for those", thumb_h=520)
    with open(os.path.join(sdir, "options.json"), "w") as fh:
        json.dump(listing, fh, indent=2)
    print(json.dumps({"stage": "snapshot", "snapshot_sheet": sheet_path, "options": [{k: v for k, v in o.items() if k != "file"} for o in listing],
                      "contrast_fixes": contrast_fixes, "warnings": warnings}, indent=2))


def final(spec_path):
    spec, spec_dir, brand, url = load(spec_path)
    name = spec.get("name", "Social").replace(" ", "_")
    out_dir = spec["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    picks = spec.get("picks")
    if not picks:
        sys.exit('Set "picks" to the option ids the user chose, e.g. ["site", "headline_3_bullets", "split"].')
    keys = spec.get("placements") or list(PLACEMENTS)
    bad = [k for k in keys if k not in PLACEMENTS]
    if bad:
        sys.exit(f"Unknown placements {bad}. Valid: {list(PLACEMENTS)}")
    pil_fmt, ext = FORMATS[spec.get("format", "png").lower()]
    quality = spec.get("quality", 85)
    photos = Photos(spec, spec_dir)
    variants = spec.get("variants") or []
    multi = len(variants) > 1
    tokens = brand_tokens(brand)
    fcss, fam = fonts_css(brand)
    only = set(spec.get("only") or [])
    manifest = {"name": name, "picks": picks, "format": ext, "link": spec.get("link"), "brand": brand.get("name"), "images": []}
    all_items = []
    pw = br = None
    tmp = tempfile.mkdtemp()
    try:
        for pick in picks:
            kind = "site" if pick == "site" else "template" if pick in TEMPLATES else "classic" if pick in CLASSIC else None
            if not kind:
                warn(f"unknown pick {pick}")
                continue
            pdir = os.path.join(out_dir, pick)
            os.makedirs(pdir, exist_ok=True)
            if kind == "classic":
                r = run_classic(spec, spec_dir, [pick], pdir, "final", placements=keys, name=f"{name}_{pick}")
                if r:
                    for fn in r.get("files", []):
                        p = os.path.join(pdir, fn)
                        manifest["images"].append({"file": os.path.join(pick, fn), "option": pick, "kind": "classic"})
                        all_items.append((p, f"{pick}\n{fn.rsplit('.', 1)[0].replace(name + '_' + pick + '_', '')}"))
                    for w_ in r.get("warnings", []):
                        warn("classic: " + w_)
                continue
            if br is None:
                pw, br = browser()
            for v in variants:
                copy = resolve_copy(v)
                vt = f"_{v.get('id')}" if multi else ""
                for key in keys:
                    P = PLACEMENTS[key]
                    tag = f"{pick} {key}{vt}"
                    if only and f"{pick}:{key}{vt}" not in only and pick not in only and key not in only:
                        continue
                    if kind == "template":
                        miss = template_missing(pick, copy, photos)
                        if miss:
                            warn(f"{pick}: needs {', '.join(miss)}; skipped.")
                            break
                    png = os.path.join(tmp, "out.png")
                    res = render_one(br, build_fn(kind, pick, spec, spec_dir, brand, tokens, fcss, fam, photos, copy, P["w"], P["h"], key, tag, url),
                                     P["w"], P["h"], png, tag, spec.get("contrast", "fix"), tmp)
                    fname = f"{name}_{pick}_{P['suffix']}{vt}.{ext}"
                    dst = os.path.join(pdir, fname)
                    MI.save(Image.open(png).convert("RGB"), dst, pil_fmt, quality)
                    for iss in res["issues"]:
                        warn(f"{tag}: {iss}")
                    if res.get("dropped"):
                        warn(f"{tag}: left out {', '.join(res['dropped'])} so the rest stays legible.")
                    manifest["images"].append({"file": os.path.join(pick, fname), "option": pick, "kind": kind, "placement": key, "label": P["label"],
                                               "platform": P["platform"], "width": P["w"], "height": P["h"], "variant": v.get("id") if multi else None,
                                               "link": MI.utm_link(spec.get("link"), P["platform"], spec.get("campaign", name.lower())),
                                               "headline": plain(copy["headline"]), "cta": copy.get("cta"), **res})
                    all_items.append((dst, f"{pick}\n{P['suffix']}{vt} · {P['w']}×{P['h']}"))
    finally:
        if br:
            br.close()
            pw.stop()
        shutil.rmtree(tmp, ignore_errors=True)
    if spec.get("post_content"):
        manifest["post_content"] = spec["post_content"]
    manifest["warnings"], manifest["contrast_fixes"] = warnings, contrast_fixes
    manifest["tokens"] = tokens
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    sheet_path = os.path.join(out_dir, f"{name}_contact-sheet.png")
    if all_items:
        MI.sheet(all_items, sheet_path, f"{name.replace('_', ' ')}: {len(all_items)} images", f"Options: {', '.join(picks)}", thumb_h=420)
    print(json.dumps({"stage": "final", "output_dir": out_dir, "contact_sheet": sheet_path if all_items else None,
                      "files": [e["file"] for e in manifest["images"]], "contrast_fixes": contrast_fixes, "warnings": warnings}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("snapshot", "final"):
        sys.exit(__doc__)
    (snapshot if sys.argv[1] == "snapshot" else final)(sys.argv[2])
