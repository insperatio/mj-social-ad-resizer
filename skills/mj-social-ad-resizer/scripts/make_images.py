#!/usr/bin/env python3
"""
mj-social-ad-resizer renderer.

Usage:
    python3 make_images.py spec.json

Stages (spec["stage"]):
  concepts  Render each layout in spec["concepts"] at one placement and
            write a concept sheet so the user can pick a direction.
  final     Render every placement (and A/B variant) in spec["layout"],
            plus a contact sheet and manifest.json.

Photos are optional for the photo-free layouts (card, centered, stats,
type_only). See references/spec.md, references/brand.md, references/layouts.md.
"""
import json
import os
import sys
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.normpath(os.path.join(HERE, "..", "assets", "fonts"))
DEFAULT_FONTS = {
    "heading": os.path.join(FONT_DIR, "Inter-Bold.otf"),
    "body": os.path.join(FONT_DIR, "Inter-Regular.otf"),
    "label": os.path.join(FONT_DIR, "Inter-SemiBold.otf"),
}

PLACEMENTS = {
    "meta_square":     {"w": 1080, "h": 1080, "platform": "meta",      "suffix": "IG-1x1", "label": "Meta feed 1:1",           "safe_top": 0.0,  "safe_bottom": 0.0},
    "meta_portrait":   {"w": 1080, "h": 1350, "platform": "meta",      "suffix": "IG-4x5", "label": "Meta feed 4:5",           "safe_top": 0.0,  "safe_bottom": 0.0},
    "meta_story":      {"w": 1080, "h": 1920, "platform": "meta",      "suffix": "STORY",  "label": "Meta Stories/Reels 9:16", "safe_top": 0.14, "safe_bottom": 0.20},
    "pinterest":       {"w": 1000, "h": 1500, "platform": "pinterest", "suffix": "PT",     "label": "Pinterest pin 2:3",       "safe_top": 0.0,  "safe_bottom": 0.0},
    "link_preview":    {"w": 1200, "h": 630,  "platform": "link",      "suffix": "FB",     "label": "Link preview 1.91:1",     "safe_top": 0.0,  "safe_bottom": 0.0},
    "linkedin_square": {"w": 1200, "h": 1200, "platform": "linkedin",  "suffix": "LI-1x1", "label": "LinkedIn feed 1:1",       "safe_top": 0.0,  "safe_bottom": 0.0},
    "x_post":          {"w": 1600, "h": 900,  "platform": "x",         "suffix": "X",      "label": "X in-feed 16:9",          "safe_top": 0.0,  "safe_bottom": 0.0},
}
LAYOUT_LABELS = {
    "editorial": "Editorial", "full_bleed": "Full bleed", "split": "Split panel", "band": "Color band",
    "card": "Card", "centered": "Centered", "stats": "Stat tiles", "type_only": "Type only",
}
LAYOUTS = list(LAYOUT_LABELS)
NEEDS_PHOTO = {"editorial", "full_bleed", "split", "band"}
UTM_SOURCE = {"meta": "facebook", "pinterest": "pinterest", "link": "social", "linkedin": "linkedin", "x": "x"}
FORMATS = {"webp": ("WEBP", "webp"), "png": ("PNG", "png"), "jpg": ("JPEG", "jpg"), "jpeg": ("JPEG", "jpg")}

warnings = []
_boost = {"k": 1.0}  # text scale-up for tall frames (stories, pins) so they don't feel empty
_ctx = {"W": 1080, "tag": "", "contrast": "fix"}
contrast_report = []

# Smallest legible text, as a fraction of the image WIDTH. Social images are shown
# about 375 px wide on a phone, so 0.027 x 1080 = 29 px renders at roughly 10 px.
MIN_TEXT = {"label": 0.026, "footer": 0.024, "body": 0.029, "fact": 0.028, "cta": 0.028, "headline": 0.05}


def mp(role):
    return int(_ctx["W"] * MIN_TEXT[role])


def warn(msg):
    if msg not in warnings:
        warnings.append(msg)


# ================================================================ color
def rgb(h):
    if isinstance(h, (list, tuple)):
        return tuple(h[:3])
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in rgb(c))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable_on(bg):
    return (255, 255, 255) if contrast((255, 255, 255), bg) >= contrast((10, 10, 10), bg) else (10, 10, 10)


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lighten(c, t):
    return mix(c, (255, 255, 255), t)


def gradient_image(w, h, colors, horizontal=True):
    colors = [rgb(c) for c in colors] or [(0, 0, 0)]
    w, h = max(w, 1), max(h, 1)
    if len(colors) == 1:
        return Image.new("RGB", (w, h), colors[0])
    n = max(w if horizontal else h, 2)
    strip = Image.new("RGB", (n, 1))
    px = strip.load()
    segs = len(colors) - 1
    for i in range(n):
        t = i / (n - 1) * segs
        k = min(int(t), segs - 1)
        f = t - k
        px[i, 0] = tuple(round(colors[k][j] + (colors[k + 1][j] - colors[k][j]) * f) for j in range(3))
    if horizontal:
        return strip.resize((w, h), Image.BILINEAR)
    return strip.resize((h, w), Image.BILINEAR).rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)


# ================================================================ brand
BRAND_DEFAULTS = {
    "name": "", "domain": "",
    "colors": {
        "background": "#FFFFFF", "background_2": None, "text": "#111111", "muted": "#555555",
        "primary": "#111111", "on_primary": None, "accent": None, "border": "#E5E7EB",
        "scrim": "#0A0A0A", "band": None, "on_dark": "#FFFFFF", "surface": None, "surface_text": None,
        "link": None, "value": None,
    },
    "gradient": [], "glows": [], "grid": None, "tiles": [],
    "fonts": {},
    "headline_tracking": -0.02, "headline_leading": 1.08, "headline_case": "none",
    "button": {"style": "solid", "radius": "pill"},
    "motifs": [], "eyebrow": "", "logo": None, "logo_on_dark": None,
    "style": {
        "align": "left",            # left | center
        "photo_shape": "rect",      # rect | rounded | circle | arch
        "radius": 24,               # px at 1080 for rounded photos and cards
        "frame": None,              # null | "single" | "double"  (rule border inside cards / around the ad)
        "divider": None,            # null | "line" | "ornament" | "gradient"
        "eyebrow": None,            # null | "pill" | "caps"
        "shadow": True,             # drop shadow under cards
        "dark_background": None,    # background color for photo-free dark layouts (default colors.scrim)
        "subhead_italic": False,    # use the accent font (italic) for subheads
    },
}


def load_brand(spec, spec_dir):
    raw = spec.get("brand") or {}
    base = spec_dir
    if isinstance(raw, str):
        path = raw if os.path.isabs(raw) else os.path.join(spec_dir, raw)
        if not os.path.exists(path):
            sys.exit(f"Brand profile not found: {path}. Paths in the spec are relative to the spec file.")
        base = os.path.dirname(path)
        with open(path) as f:
            raw = json.load(f)
    if "colors" not in raw and any(k in raw for k in ("primary", "accent", "on_primary")):  # v1 flat format
        raw = {"colors": {k: raw[k] for k in ("primary", "on_primary", "accent") if k in raw}, "logo": raw.get("logo"),
               "fonts": {k: raw.get("font_" + k) for k in ("heading", "body") if raw.get("font_" + k)}}
    b = json.loads(json.dumps(BRAND_DEFAULTS))
    for k, v in raw.items():
        if isinstance(v, dict) and isinstance(b.get(k), dict):
            b[k].update({kk: vv for kk, vv in v.items() if vv is not None})
        elif v is not None:
            b[k] = v
    c = b["colors"]
    c["background_2"] = c["background_2"] or c["background"]
    c["on_primary"] = c["on_primary"] or "#%02x%02x%02x" % readable_on(rgb(c["primary"]))
    c["accent"] = c["accent"] or (b["gradient"][len(b["gradient"]) // 2] if b["gradient"] else c["primary"])
    c["band"] = c["band"] or c["primary"]
    c["surface"] = c["surface"] or c["background"]
    c["surface_text"] = c["surface_text"] or c["text"]
    c["link"] = c["link"] or c["accent"]
    c["value"] = c["value"] or c["accent"]
    st = b["style"]
    st["dark_background"] = st.get("dark_background") or c["scrim"]
    if not st.get("eyebrow"):
        st["eyebrow"] = "pill" if "eyebrow_pill" in b["motifs"] else ("caps" if "eyebrow_caps" in b["motifs"] else None)
    if not st.get("divider"):
        st["divider"] = "gradient" if "gradient_divider" in b["motifs"] else None

    def resolve(p):
        if not p:
            return None
        p = p if os.path.isabs(p) else os.path.join(base, p)
        if not os.path.exists(p):
            warn(f"Brand file not found: {p}. Using the default instead.")
            return None
        return p

    fonts = {}
    for role in ("heading", "body", "label", "accent", "wordmark"):
        entry = b["fonts"].get(role)
        if isinstance(entry, dict):
            pth = resolve(entry.get("path"))
            fonts[role] = {"path": pth, "variation": entry.get("variation")} if pth else None
        else:
            pth = resolve(entry)
            fonts[role] = {"path": pth, "variation": None} if pth else None
    fonts["heading"] = fonts["heading"] or {"path": DEFAULT_FONTS["heading"], "variation": None}
    fonts["body"] = fonts["body"] or {"path": DEFAULT_FONTS["body"], "variation": None}
    fonts["label"] = fonts["label"] or ({"path": DEFAULT_FONTS["label"], "variation": None}
                                        if not b["fonts"].get("heading") else fonts["heading"])
    fonts["accent"] = fonts["accent"] or fonts["body"]
    fonts["wordmark"] = fonts["wordmark"] or fonts["label"]
    b["fonts"] = fonts
    b["logo"] = resolve(b.get("logo"))
    b["logo_on_dark"] = resolve(b.get("logo_on_dark"))
    return b


_font_cache = {}


def font(spec, size):
    key = (spec["path"], spec.get("variation"), size)
    if key not in _font_cache:
        f = ImageFont.truetype(spec["path"], max(int(size), 8))
        if spec.get("variation"):
            try:
                f.set_variation_by_name(spec["variation"])
            except Exception:
                warn(f"Font variation '{spec['variation']}' not found in {os.path.basename(spec['path'])}.")
        _font_cache[key] = f
    return _font_cache[key]


def palette(brand, kind):
    """Colors for text sitting on: 'light' brand background, 'dark' photo/dark bg, 'surface' card."""
    c = brand["colors"]
    if kind == "dark":
        od = rgb(c["on_dark"])
        dark_fill = rgb(c["scrim"]) if lum(c["scrim"]) < 0.2 else (10, 10, 10)
        return {"dark": True, "text": od, "muted": mix(od, dark_fill, 0.18), "btn_bg": od,
                "btn_fg": dark_fill, "line": mix(od, dark_fill, 0.35), "pill_text": od,
                "link": lighten(c["link"], 0.45), "value": lighten(c["value"], 0.35), "bg": dark_fill}
    if kind == "surface":
        light = lum(c["surface"]) > 0.35
        return {"dark": False, "text": rgb(c["surface_text"]), "muted": rgb(c["muted"]), "btn_bg": rgb(c["primary"]),
                "btn_fg": rgb(c["on_primary"]), "line": rgb(c["border"]), "pill_text": rgb(c["surface_text"]),
                "link": rgb((c.get("link_on_light") if light else None) or c["link"]),
                "value": rgb((c.get("value_on_light") if light else None) or c["value"]), "bg": rgb(c["surface"])}
    return {"dark": False, "text": rgb(c["text"]), "muted": rgb(c["muted"]), "btn_bg": rgb(c["primary"]),
            "btn_fg": rgb(c["on_primary"]), "line": rgb(c["border"]), "pill_text": rgb(c["text"]),
            "link": rgb(c.get("link_on_light") or c["link"]), "value": rgb(c.get("value_on_light") or c["value"]),
            "bg": rgb(c["background"])}


def bg_palette(brand):
    """Palette for the brand background: light or dark depending on its color."""
    return palette(brand, "light") if lum(brand["colors"]["background"]) > 0.35 else palette(brand, "dark")


# ================================================================ photos
def load_photo(path):
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def pick_source(sources, ratio):
    def dist(r):
        return r / ratio if r >= ratio else ratio / r
    return min(sources, key=lambda k: dist(sources[k]["img"].width / sources[k]["img"].height))


def shape_mask(w, h, shape, radius):
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    if shape == "circle":
        d.ellipse((0, 0, w - 1, h - 1), fill=255)
    elif shape == "arch":
        r = w // 2
        d.rectangle((0, r, w - 1, h - 1), fill=255)
        d.ellipse((0, 0, w - 1, 2 * r), fill=255)
    elif shape == "rounded" and radius:
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    else:
        d.rectangle((0, 0, w - 1, h - 1), fill=255)
    return m


def place_photo(canvas, box, sources, spec, tag, shape="rect", radius=0):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0 or not sources:
        return None
    key = pick_source(sources, w / h)
    src = sources[key]
    img = src["img"]
    fx, fy = src.get("focus", {}).get("x", 0.5), src.get("focus", {}).get("y", 0.5)
    src_r, tgt_r = img.width / img.height, w / h
    kept = min(src_r, tgt_r) / max(src_r, tgt_r)
    mode = spec.get("fill", "auto")
    max_loss = spec.get("max_crop_loss", 0.75 if spec.get("mode") == "ad" else 0.6)
    if mode == "crop" or (mode == "auto" and 1 - kept <= max_loss):
        scale = max(w / img.width, h / img.height)
        nw, nh = round(img.width * scale), round(img.height * scale)
        r = img.resize((nw, nh), Image.LANCZOS)
        left = min(max(round(fx * nw - w / 2), 0), nw - w)
        top = min(max(round(fy * nh - h / 2), 0), nh - h)
        tile, how = r.crop((left, top, left + w, top + h)), "crop"
    else:
        scale = min(w / img.width, h / img.height)
        how = "blur" if mode in ("auto", "blur") else "color"
        if how == "blur":
            s2 = max(w / img.width, h / img.height)
            bg = img.resize((round(img.width * s2), round(img.height * s2)), Image.LANCZOS)
            bx, by = (bg.width - w) // 2, (bg.height - h) // 2
            tile = Image.blend(bg.crop((bx, by, bx + w, by + h)).filter(ImageFilter.GaussianBlur(max(w, h) // 30)),
                               Image.new("RGB", (w, h), 0), 0.2)
        else:
            tile = Image.new("RGB", (w, h), rgb(spec["_brand"]["colors"]["primary"]))
        fg = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        tile.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    if scale > 1.05:
        where = tag.rsplit("_", 1)[0] if len(tag.rsplit("_", 1)[-1]) == 1 else tag
        warn(f"{where}: photo '{key}' was enlarged {scale:.1f}x and may look soft. A larger photo will be sharper.")
    canvas.paste(tile, (x0, y0), shape_mask(w, h, shape, radius))
    return {"source": key, "fit": how, "photo_kept_pct": round(kept * 100), "scale": round(scale, 2)}


# ================================================================ backgrounds, motifs
def paint_brand_bg(canvas, box, brand, dark=False):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    c = brand["colors"]
    if dark:
        base_col = brand["style"]["dark_background"]
        bg = gradient_image(w, h, [lighten(base_col, 0.06), base_col], horizontal=False)
    else:
        bg = gradient_image(w, h, [c["background"], c["background_2"]], horizontal=False)
    base = min(w, h)
    for g in (brand.get("glows") or []):
        rad = max(int(base * g.get("r", 0.45)), 4)
        mask = ImageOps.invert(Image.radial_gradient("L").resize((rad * 2, rad * 2), Image.BILINEAR))
        mask = mask.point(lambda v, s=g.get("strength", 0.9) * (0.35 if dark else 1): int(v * s))
        bg.paste(Image.new("RGB", (rad * 2, rad * 2), rgb(g["color"])), (int(g.get("x", 0.2) * w) - rad, int(g.get("y", 0.1) * h) - rad), mask)
    grid = brand.get("grid")
    if grid:
        step = max(int(grid.get("size", 64) * base / 1080), 12)
        m = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(m)
        a = int(255 * grid.get("opacity", 0.06) * (0.6 if dark else 1))
        for gx in range(0, w, step):
            d.line((gx, 0, gx, h), fill=a)
        for gy in range(0, h, step):
            d.line((0, gy, w, gy), fill=a)
        bg.paste(Image.new("RGB", (w, h), rgb(grid.get("color", "#000000"))), (0, 0), m)
    canvas.paste(bg, (x0, y0))


def scrim(canvas, box, color, direction, strength=0.78):
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return
    horiz = direction in ("left", "right")
    n = w if horiz else h
    strip = Image.new("L", (n, 1))
    for i in range(n):
        t = i / max(n - 1, 1)
        t = t if direction in ("right", "bottom") else 1 - t
        strip.putpixel((i, 0), int(255 * strength * (t ** 1.4)))
    m = strip.resize((w, h)) if horiz else strip.resize((h, w)).rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
    region = canvas.crop((x0, y0, x1, y1))
    region.paste(Image.new("RGB", (w, h), rgb(color)), (0, 0), m)
    canvas.paste(region, (x0, y0))


def darken_all(canvas, box, color, amount):
    x0, y0, x1, y1 = [int(v) for v in box]
    region = canvas.crop((x0, y0, x1, y1))
    canvas.paste(Image.blend(region, Image.new("RGB", region.size, rgb(color)), amount), (x0, y0))


def draw_dots(canvas, x_right, y, brand, base):
    cols = (brand["gradient"] or [brand["colors"]["accent"]]) * 4
    d = ImageDraw.Draw(canvas)
    r = max(int(base * 0.007), 3)
    gap = r * 3
    x = x_right - 3 * gap - r
    for c in cols[:4]:
        d.ellipse((x - r, y - r, x + r, y + r), fill=rgb(c))
        x += gap


def draw_frame(canvas, box, color, style, base):
    if not style:
        return
    d = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = [int(v) for v in box]
    lw = max(int(base * 0.0025), 2)
    d.rectangle((x0, y0, x1, y1), outline=rgb(color), width=lw)
    if style == "double":
        g = max(int(base * 0.008), 5)
        d.rectangle((x0 + g, y0 + g, x1 - g, y1 - g), outline=rgb(color), width=max(lw // 2, 1))


def shadow(canvas, box, radius, base, strength=0.45):
    x0, y0, x1, y1 = [int(v) for v in box]
    off, blur = int(base * 0.02), int(base * 0.04)
    m = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((x0, y0 + off, x1, y1 + off), radius=radius, fill=int(255 * strength))
    m = m.filter(ImageFilter.GaussianBlur(blur))
    canvas.paste(Image.new("RGB", canvas.size, (0, 0, 0)), (0, 0), m)


# ================================================================ text
def text_w(draw, s, f, tracking=0):
    return draw.textlength(s, font=f) + tracking * f.size * max(len(s) - 1, 0)


def wrap(draw, text, f, max_w, tracking=0):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if text_w(draw, trial, f, tracking) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    # avoid a single short word stranded on the last line
    if len(lines) >= 2 and len(lines[-1].split()) == 1 and len(lines[-2].split()) >= 3:
        prev = lines[-2].split()
        cand = prev[-1] + " " + lines[-1]
        if text_w(draw, cand, f, tracking) <= max_w:
            lines[-2], lines[-1] = " ".join(prev[:-1]), cand
    return lines


def line_h(f):
    a, d = f.getmetrics()
    return a + d


def _lum_array(arr):
    import numpy as np
    a = arr.astype("float64") / 255.0
    a = np.where(a <= 0.03928, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def _hex(c):
    return "#%02X%02X%02X" % tuple(rgb(c))


def _shift_lightness(c, dl):
    import colorsys
    r, g, b = (v / 255 for v in rgb(c))
    h, l, s_ = colorsys.rgb_to_hls(r, g, b)
    l = min(max(l + dl, 0.0), 1.0)
    return tuple(int(round(v * 255)) for v in colorsys.hls_to_rgb(h, l, s_))


def _ratio(c_lum, bg_lum):
    return (max(c_lum, bg_lum) + 0.05) / (min(c_lum, bg_lum) + 0.05)


def fix_contrast(color, bg_lums, need):
    """Return (color, before, after). bg_lums = (darkest, median, brightest) luminance behind the text."""
    lo, mid, hi = bg_lums
    cl = lum(color)
    light_text = cl >= mid
    worst = lo if light_text else hi          # the background pixels closest to the text color
    before = _ratio(cl, worst)
    if before >= need:
        return rgb(color), before, before
    c = rgb(color)
    step = 0.02 if light_text else -0.02
    for _ in range(60):
        c = _shift_lightness(c, step)
        if _ratio(lum(c), worst) >= need:
            return c, before, _ratio(lum(c), worst)
    # same hue can't get there: fall back to whichever of near-black / near-white works
    best = max([(10, 10, 10), (255, 255, 255)], key=lambda k: min(_ratio(lum(k), lo), _ratio(lum(k), hi)))
    return best, before, min(_ratio(lum(best), lo), _ratio(lum(best), hi))


def draw_text(canvas, xy, s, f, fill, tracking=0, gradient=None):
    x, y = xy
    probe = ImageDraw.Draw(canvas)
    w = int(text_w(probe, s, f, tracking)) + 6
    h = line_h(f) + 6
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    if tracking:
        cx = 0
        for ch in s:
            md.text((cx, 0), ch, font=f, fill=255)
            cx += md.textlength(ch, font=f) + tracking * f.size
    else:
        md.text((0, 0), s, font=f, fill=255)
    # --- WCAG check against the actual pixels behind the glyphs
    mode = _ctx.get("contrast", "fix")
    if mode != "off" and s.strip():
        import numpy as np
        X, Y = int(x), int(y)
        region = canvas.crop((X, Y, X + w, Y + h))
        near = np.array(mask.filter(ImageFilter.MaxFilter(5))) > 0
        lums = _lum_array(np.array(region))[near]
        if lums.size:
            bg = (float(np.percentile(lums, 5)), float(np.median(lums)), float(np.percentile(lums, 95)))
            large = f.size >= _ctx["W"] * 0.045       # headline-sized: WCAG large text
            need = 3.0 if large else 4.5
            colors = list(gradient) if gradient else [fill]
            fixed = []
            for col in colors:
                new, before, after = fix_contrast(col, bg, need)
                if before < need:
                    entry = {"where": _ctx["tag"], "text": s[:40], "from": _hex(col), "to": _hex(new) if mode == "fix" else None,
                             "ratio_before": round(before, 2), "ratio_after": round(after, 2) if mode == "fix" else None,
                             "needed": need, "size_px": f.size}
                    if not any(e["from"] == entry["from"] and e["where"] == entry["where"] for e in contrast_report):
                        contrast_report.append(entry)
                    if mode == "fix":
                        warn(f"Contrast fixed: {_hex(col)} → {_hex(new)} for \"{s[:30]}\" ({before:.1f}:1 → {after:.1f}:1, needs {need}:1).")
                    else:
                        warn(f"Contrast too low: {_hex(col)} for \"{s[:30]}\" is {before:.1f}:1 (needs {need}:1).")
                fixed.append(new if mode == "fix" else rgb(col))
            if gradient:
                gradient = fixed
            else:
                fill = fixed[0]
    fill_img = gradient_image(w, h, gradient) if gradient else Image.new("RGB", (w, h), fill)
    canvas.paste(fill_img, (int(x), int(y)), mask)


def split_emphasis(headline, emphasis):
    if emphasis and headline.rstrip().endswith(emphasis.strip()):
        return headline.rstrip()[: -len(emphasis.strip())].rstrip(), emphasis.strip()
    return headline, ""


# ================================================================ text block
ALL_PARTS = ("wordmark", "eyebrow", "headline", "divider", "subhead", "facts", "cta")


def build_block(draw, brand, variant, width, scale, pal, parts, base, hscale=1.0):
    """Lay out the text block. Returns (ops, height, headline_line_count)."""
    F = brand["fonts"]
    st = brand["style"]
    motifs = set(brand.get("motifs") or [])
    v = variant or {}
    ops, y = [], 0
    track = brand.get("headline_tracking", 0)
    gap = lambda k: int(base * k * scale)

    if "wordmark" in parts and (brand.get("name") or brand.get("logo")):
        logo = brand.get("logo_on_dark") if pal["dark"] and brand.get("logo_on_dark") else brand.get("logo")
        if logo:
            lg = Image.open(logo).convert("RGBA")
            lh = gap(0.05)
            ops.append(("img", y, lg.resize((max(int(lg.width * lh / lg.height), 1), lh), Image.LANCZOS)))
            y += lh + gap(0.03)
        else:
            f = font(F["wordmark"], max(gap(0.032), mp("label")))
            ops.append(("text", y, brand["name"], f, pal["text"], 0, None))
            y += line_h(f) + gap(0.028)

    eyebrow = v.get("eyebrow", brand.get("eyebrow"))
    if "eyebrow" in parts and eyebrow and st.get("eyebrow"):
        f = font(F["label"], max(gap(0.019), mp("label")))
        s = eyebrow.upper()
        if st["eyebrow"] == "pill":
            px, py = int(f.size * 0.9), int(f.size * 0.55)
            ops.append(("pill", y, s, f, text_w(draw, s, f, 0.06), px, py))
            y += line_h(f) + 2 * py + gap(0.035)
        else:
            ops.append(("text", y, s, f, pal["muted"], 0.16, None))
            y += line_h(f) + gap(0.028)

    n_lines = 0
    if "headline" in parts:
        hl = v.get("headline", "")
        if brand.get("headline_case") == "upper":
            hl = hl.upper()
        emph = v.get("emphasis")
        if emph is None and "gradient_text" in motifs and brand["gradient"] and len(hl.split()) > 1:
            emph = hl.split()[-1]
        lead, emph = split_emphasis(hl, emph or "")
        hsize = max(int(base * 0.092 * scale * hscale), mp("headline"))
        hf = font(F["heading"], hsize)
        lead_l = wrap(draw, lead, hf, width, track) if lead else []
        emph_l = wrap(draw, emph, hf, width, track) if emph else []
        lh = int(hsize * brand.get("headline_leading", 1.08))
        grad = brand["gradient"] if (brand["gradient"] and "gradient_text" in motifs) else None
        if grad and pal["dark"]:
            grad = [lighten(g, 0.35) for g in grad]
        emph_col = pal["text"] if grad or not emph else pal["value"]
        for ln in lead_l:
            ops.append(("text", y, ln, hf, pal["text"], track, None))
            y += lh
        for ln in emph_l:
            ops.append(("text", y, ln, hf, emph_col, track, grad))
            y += lh
        n_lines = len(lead_l) + len(emph_l)
        last = (emph_l or lead_l or [""])[-1]
        if "gradient_underline" in motifs and brand["gradient"]:
            bar_y = (y - lh) + hf.getbbox(last)[3] + int(hsize * 0.12)
            bh = max(int(hsize * 0.09), 4)
            ops.append(("bar", bar_y, int(text_w(draw, last, hf, track)), bh))
            y = max(y, bar_y + bh + int(hsize * 0.1))
        else:
            y += int(hsize * 0.12)

    if "divider" in parts and st.get("divider"):
        y += gap(0.02)
        ops.append(("divider", y, st["divider"], min(width, gap(0.32))))
        y += gap(0.035)

    sub = v.get("subhead")
    if "subhead" in parts and sub:
        y += gap(0.02)
        sf = font(F["accent"] if st.get("subhead_italic") else F["body"], max(gap(0.034), mp("body")))
        for ln in wrap(draw, sub, sf, width)[:3]:
            ops.append(("text", y, ln, sf, pal["muted"], 0, None))
            y += int(line_h(sf) * 1.12)

    facts = v.get("facts") or []
    if "facts" in parts and facts:
        y += gap(0.03)
        lf = font(F["body"], max(gap(0.03), mp("fact")))
        vf = font(F["heading"], max(gap(0.034), int(mp("fact") * 1.1)))
        def need(lf_, vf_):
            return max(text_w(draw, f_.get("label", ""), lf_) + text_w(draw, f_.get("value", ""), vf_) for f_ in facts[:4])
        while need(lf, vf) + lf.size * 2 > width and lf.size > mp("fact"):
            lf, vf = font(F["body"], lf.size - 1), font(F["heading"], vf.size - 1)
        rh = max(line_h(lf), line_h(vf))
        row_w = min(width, int(max(text_w(draw, f_.get("label", ""), lf) + text_w(draw, f_.get("value", ""), vf) for f_ in facts[:4]) + rh * 5))
        for fact in facts[:4]:
            ops.append(("fact", y, fact.get("label", ""), fact.get("value", ""), lf, vf, rh, row_w))
            y += rh + gap(0.018)

    cta = v.get("cta")
    if "cta" in parts and cta:
        y += gap(0.045)
        bstyle = (brand.get("button") or {}).get("style", "solid")
        cf = font(F["label"], max(gap(0.03 if bstyle != "link" else 0.026), mp("cta")))
        if bstyle == "link":
            s = cta.upper()
            ops.append(("link", y, s, cf, text_w(draw, s, cf, 0.12)))
            y += line_h(cf) + gap(0.02)
        else:
            px, py = int(cf.size * 1.25), int(cf.size * 0.75)
            ops.append(("button", y, cta, cf, text_w(draw, cta, cf), px, py))
            y += line_h(cf) + 2 * py
    return ops, y, n_lines


def draw_block(canvas, ops, x, y, width, brand, pal, align="left"):
    btn = brand.get("button") or {}

    def ox_for(w):
        return x + (width - w) / 2 if align == "center" else x

    for op in ops:
        kind, oy = op[0], y + op[1]
        draw = ImageDraw.Draw(canvas)
        if kind == "text":
            _, _, s, f, col, track, grad = op
            draw_text(canvas, (ox_for(text_w(draw, s, f, track)), oy), s, f, col, track, grad)
        elif kind == "img":
            lg = op[2]
            canvas.paste(lg, (int(ox_for(lg.width)), int(oy)), lg)
        elif kind == "bar":
            _, _, uw, bh = op
            m = Image.new("L", (uw, bh), 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, uw - 1, bh - 1), radius=bh // 2, fill=255)
            canvas.paste(gradient_image(uw, bh, brand["gradient"]), (int(ox_for(uw)), int(oy)), m)
        elif kind == "pill":
            _, _, s, f, tw, px, py = op
            w, h = int(tw + 2 * px), line_h(f) + 2 * py
            ox = ox_for(w)
            draw.rounded_rectangle((ox, oy, ox + w, oy + h), radius=h // 2, fill=None if pal["dark"] else (255, 255, 255),
                                   outline=pal["line"] if not pal["dark"] else pal["text"], width=max(2, f.size // 10))
            draw_text(canvas, (ox + px, oy + py - 1), s, f, pal["pill_text"], 0.06)
        elif kind == "divider":
            _, _, style, dw = op
            ox = ox_for(dw)
            lw = max(int(dw * 0.006), 2)
            if style == "gradient" and brand["gradient"]:
                canvas.paste(gradient_image(dw, lw * 2, brand["gradient"]), (int(ox), int(oy)))
            elif style == "ornament":
                cx, r = ox + dw / 2, max(int(dw * 0.025), 5)
                draw.line((ox, oy, cx - r * 2.2, oy), fill=pal["line"], width=lw)
                draw.line((cx + r * 2.2, oy, ox + dw, oy), fill=pal["line"], width=lw)
                draw.polygon([(cx, oy - r), (cx + r, oy), (cx, oy + r), (cx - r, oy)], fill=pal["muted"])
            else:
                draw.line((ox, oy, ox + dw, oy), fill=pal["line"], width=lw)
        elif kind == "fact":
            _, _, label, value, lf, vf, rh, row_w = op
            lw_, vw_ = text_w(draw, label, lf), text_w(draw, value, vf)
            row_w = width if align != "center" else row_w
            ox = ox_for(row_w)
            draw_text(canvas, (ox, oy + (rh - line_h(lf)) / 2), label, lf, pal["text"])
            draw_text(canvas, (ox + row_w - vw_, oy + (rh - line_h(vf)) / 2), value, vf, pal["value"])
            ly = oy + rh * 0.62
            dx, end = ox + lw_ + rh * 0.4, ox + row_w - vw_ - rh * 0.4
            r = max(int(rh * 0.04), 1)
            draw = ImageDraw.Draw(canvas)
            while dx < end:
                draw.ellipse((dx - r, ly - r, dx + r, ly + r), fill=pal["line"] if not pal["dark"] else pal["muted"])
                dx += r * 5
        elif kind == "link":
            _, _, s, f, tw = op
            ox = ox_for(tw)
            draw_text(canvas, (ox, oy), s, f, pal["link"], 0.12)
            ul = oy + f.getbbox(s)[3] + max(int(f.size * 0.25), 3)
            ImageDraw.Draw(canvas).line((ox, ul, ox + tw, ul), fill=pal["link"], width=max(f.size // 12, 2))
        elif kind == "button":
            _, _, s, f, tw, px, py = op
            w, h = int(tw + 2 * px), line_h(f) + 2 * py
            ox = ox_for(w)
            style = btn.get("style", "solid")
            rad = h // 2 if btn.get("radius", "pill") == "pill" else int(btn.get("radius", 8))
            m = Image.new("L", (w, h), 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=rad, fill=255)
            if style == "gradient" and brand["gradient"]:
                face, fg = gradient_image(w, h, brand["gradient"]), (255, 255, 255)
            elif style == "outline":
                face, fg = None, pal["text"]
            else:
                face, fg = Image.new("RGB", (w, h), pal["btn_bg"]), pal["btn_fg"]
            if face is not None:
                canvas.paste(face, (int(ox), int(oy)), m)
            else:
                ImageDraw.Draw(canvas).rounded_rectangle((ox, oy, ox + w, oy + h), radius=rad, outline=pal["text"], width=max(2, f.size // 10))
            draw_text(canvas, (ox + px, oy + py - 1), s, f, fg)


DROP_ORDER = ("subhead", "facts", "eyebrow", "wordmark", "divider")


def fit_block(draw, brand, variant, width, max_h, pal, parts, base, tag, max_lines=4, hscale=1.0):
    """Fit the block without going below the minimum legible sizes. If it still doesn't fit,
    drop optional copy (subhead, facts, eyebrow, wordmark) before giving up."""
    parts = tuple(parts)
    dropped = []
    if _ctx.get("H") and _ctx["W"] / _ctx["H"] >= 1.5:
        max_lines = max(max_lines, 5)  # wide frames use narrow text columns
    while True:
        scale = _boost["k"]
        while True:
            ops, h, n = build_block(draw, brand, variant, width, scale, pal, parts, base, hscale)
            if (h <= max_h and n <= max_lines) or scale <= 0.45:
                break
            scale -= 0.05
        if h <= max_h and n <= max_lines:
            break
        nxt = next((d for d in DROP_ORDER if d in parts and _has_part(variant, brand, d)), None)
        if not nxt:
            break
        parts = tuple(p_ for p_ in parts if p_ != nxt)
        dropped.append(nxt)
    if dropped:
        warn(f"{tag}: left out the {', '.join(dropped)} so the remaining text stays legible at this size.")
    if h > max_h or n > max_lines:
        warn(f"{tag}: the text is too long for this size even at the minimum legible size. Shorten the headline.")
    return ops, h


def _has_part(variant, brand, part):
    v = variant or {}
    return {"subhead": bool(v.get("subhead")), "facts": bool(v.get("facts")),
            "eyebrow": bool(v.get("eyebrow", brand.get("eyebrow")) and brand["style"].get("eyebrow")),
            "wordmark": bool(brand.get("name") or brand.get("logo")), "divider": bool(brand["style"].get("divider"))}.get(part, False)


def footer(canvas, brand, x, y, pal, base, align="left", width=0):
    if not brand.get("domain"):
        return
    f = font(brand["fonts"]["label"], max(int(base * 0.022), mp("footer")))
    s = brand["domain"]
    if align == "center":
        x = x + (width - text_w(ImageDraw.Draw(canvas), s, f)) / 2
    draw_text(canvas, (x, y), s, f, pal["muted"] if not pal["dark"] else pal["text"])


def safe(p, H):
    return int(H * p["safe_top"]), int(H * p["safe_bottom"])


# ================================================================ layouts with a photo
def layout_editorial(canvas, p, sources, spec, brand, v, tag):
    W, H = p["w"], p["h"]
    base, pad = min(W, H), int(min(W, H) * 0.075)
    st_, sb = safe(p, H)
    sty = brand["style"]
    align = sty["align"]
    shape = sty["photo_shape"] if sty["photo_shape"] in ("rounded", "arch", "circle") else "rect"
    rad = int(sty.get("radius", 24) * base / 1080)
    d = ImageDraw.Draw(canvas)
    paint_brand_bg(canvas, (0, 0, W, H), brand)
    pal = bg_palette(brand)
    if W / H >= 1.5:
        tw = int(W * 0.5)
        ops, bh = fit_block(d, brand, v, tw - 2 * pad, H - 2 * pad, pal, ALL_PARTS, base, tag)
        draw_block(canvas, ops, pad, (H - bh) // 2, tw - 2 * pad, brand, pal, align)
        return place_photo(canvas, (tw, pad, W - pad, H - pad), sources, spec, tag, "rounded", max(rad, int(base * 0.03)))
    ops, bh = fit_block(d, brand, v, W - 2 * pad, int(H * 0.5), pal, ALL_PARTS, base, tag)
    top = max(pad, st_ + pad // 2)
    draw_block(canvas, ops, pad, top, W - 2 * pad, brand, pal, align)
    py0 = top + bh + int(pad * 0.8)
    if shape == "rect":
        info = place_photo(canvas, (0, py0, W, H), sources, spec, tag)
        if brand.get("domain") and not sb:
            scrim(canvas, (0, max(py0, H - int(H * 0.18)), W, H), brand["colors"]["scrim"], "bottom", 0.55)
            footer(canvas, brand, pad, H - pad - int(base * 0.022), palette(brand, "dark"), base, align, W - 2 * pad)
    else:
        info = place_photo(canvas, (pad, py0, W - pad, H - max(pad, sb + pad // 2)), sources, spec, tag,
                           "rounded" if shape == "circle" else shape, rad)
    if "dots" in (brand.get("motifs") or []) and align != "center":
        draw_dots(canvas, W - pad, top + int(base * 0.02), brand, base)
    return info


def layout_full_bleed(canvas, p, sources, spec, brand, v, tag):
    W, H = p["w"], p["h"]
    base, pad = min(W, H), int(min(W, H) * 0.075)
    st_, sb = safe(p, H)
    align = brand["style"]["align"]
    info = place_photo(canvas, (0, 0, W, H), sources, spec, tag)
    d = ImageDraw.Draw(canvas)
    sc = brand["colors"]["scrim"]
    pal = palette(brand, "dark")
    if W / H >= 1.5 and align != "center":
        scrim(canvas, (0, 0, int(W * 0.75), H), sc, "left", 0.85)
        tw = int(W * 0.55)
        ops, bh = fit_block(d, brand, v, tw - pad, H - 2 * pad, pal, ALL_PARTS, base, tag)
        draw_block(canvas, ops, pad, (H - bh) // 2, tw - pad, brand, pal)
    elif align == "center":
        darken_all(canvas, (0, 0, W, H), sc, 0.45)
        scrim(canvas, (0, 0, W, H), sc, "bottom", 0.35)
        bw = int(W * 0.78)
        ops, bh = fit_block(d, brand, v, bw, H - 2 * pad - st_ - sb, pal, ALL_PARTS, base, tag)
        draw_block(canvas, ops, (W - bw) // 2, st_ + (H - st_ - sb - bh) // 2, bw, brand, pal, "center")
    else:
        scrim(canvas, (0, 0, W, int(H * 0.72)), sc, "top", 0.82)
        scrim(canvas, (0, int(H * 0.75), W, H), sc, "bottom", 0.6)
        top = max(pad, st_ + pad // 2)
        ops, bh = fit_block(d, brand, v, W - 2 * pad, int(H * 0.5), pal, ALL_PARTS, base, tag)
        draw_block(canvas, ops, pad, top, W - 2 * pad, brand, pal)
    if "dots" in (brand.get("motifs") or []) and align != "center":
        draw_dots(canvas, W - pad, max(pad, st_ + pad // 2) + int(base * 0.02), brand, base)
    footer(canvas, brand, pad, H - max(pad, sb + pad // 2) - int(base * 0.022), pal, base, align, W - 2 * pad)
    return info


def layout_split(canvas, p, sources, spec, brand, v, tag):
    W, H = p["w"], p["h"]
    base, pad = min(W, H), int(min(W, H) * 0.07)
    st_, sb = safe(p, H)
    align = brand["style"]["align"]
    d = ImageDraw.Draw(canvas)
    divider = max(int(base * 0.008), 4)
    pal = bg_palette(brand)
    rule = brand["gradient"] or [brand["colors"]["accent"]]
    if W / H < 0.7:
        ph = int(H * 0.5)
        paint_brand_bg(canvas, (0, 0, W, H - ph), brand)
        top = max(pad, st_ + pad // 2)
        ops, bh = fit_block(d, brand, v, W - 2 * pad, H - ph - top - pad, pal, ALL_PARTS, base, tag)
        draw_block(canvas, ops, pad, top + (H - ph - top - pad - bh) // 2, W - 2 * pad, brand, pal, align)
        info = place_photo(canvas, (0, H - ph, W, H), sources, spec, tag)
        canvas.paste(gradient_image(W, divider, rule), (0, H - ph - divider))
        return info
    panel = int(W * (0.44 if W / H >= 1.2 else 0.5))
    paint_brand_bg(canvas, (0, 0, panel, H), brand)
    info = place_photo(canvas, (panel + divider, 0, W, H), sources, spec, tag)
    canvas.paste(gradient_image(divider, H, rule, horizontal=False), (panel, 0))
    ops, bh = fit_block(d, brand, v, panel - 2 * pad, H - 2 * pad - int(base * 0.06), pal, ALL_PARTS, base, tag)
    draw_block(canvas, ops, pad, max(pad, (H - bh) // 2 - int(base * 0.02)), panel - 2 * pad, brand, pal, align)
    footer(canvas, brand, pad, H - pad - int(base * 0.022), pal, base, align, panel - 2 * pad)
    return info


def layout_band(canvas, p, sources, spec, brand, v, tag):
    W, H = p["w"], p["h"]
    base, pad = min(W, H), int(min(W, H) * 0.06)
    _, sb = safe(p, H)
    align = brand["style"]["align"]
    d = ImageDraw.Draw(canvas)
    band_col = rgb(brand["colors"]["band"])
    pal = palette(brand, "dark") if readable_on(band_col) == (255, 255, 255) else dict(palette(brand, "light"), text=(10, 10, 10))
    parts = ("eyebrow", "headline", "divider", "subhead", "facts", "cta")
    if W / H >= 1.5:
        bw = int(W * 0.42)
        info = place_photo(canvas, (0, 0, W - bw, H), sources, spec, tag)
        canvas.paste(Image.new("RGB", (bw, H), band_col), (W - bw, 0))
        ops, bh = fit_block(d, brand, v, bw - 2 * pad, H - 2 * pad, pal, parts, base, tag)
        draw_block(canvas, ops, W - bw + pad, (H - bh) // 2, bw - 2 * pad, brand, pal, align)
        return info
    ops, bh = fit_block(d, brand, v, W - 2 * pad, int(H * 0.42), pal, parts, base, tag)
    band_h = bh + 2 * pad + sb
    info = place_photo(canvas, (0, 0, W, H - band_h), sources, spec, tag)
    canvas.paste(Image.new("RGB", (W, band_h), band_col), (0, H - band_h))
    if brand["gradient"]:
        canvas.paste(gradient_image(W, max(int(base * 0.008), 4), brand["gradient"]), (0, H - band_h))
    draw_block(canvas, ops, pad, H - band_h + pad, W - 2 * pad, brand, pal, align)
    return info


# ================================================================ layouts that also work without a photo
def layout_card(canvas, p, sources, spec, brand, v, tag):
    """A surface card (paper, white, tinted) floating over the photo or a dark brand background."""
    W, H = p["w"], p["h"]
    base = min(W, H)
    st_, sb = safe(p, H)
    sty = brand["style"]
    c = brand["colors"]
    info = None
    if sources:
        info = place_photo(canvas, (0, 0, W, H), sources, spec, tag)
        darken_all(canvas, (0, 0, W, H), c["scrim"], 0.3)
        scrim(canvas, (0, 0, W, H), c["scrim"], "bottom", 0.6)
    else:
        paint_brand_bg(canvas, (0, 0, W, H), brand, dark=True)
    dark = palette(brand, "dark")
    surf = palette(brand, "surface")
    wide = W / H >= 1.5
    rad = int(min(sty.get("radius", 24), 16) * base / 1080)
    d = ImageDraw.Draw(canvas)
    top_y = max(int(base * 0.06), st_ + int(base * 0.03))
    bottom_m = max(int(base * 0.09), sb + int(base * 0.05))
    if brand.get("name"):
        f = font(brand["fonts"]["wordmark"], int(base * (0.045 if wide else 0.04)))
        if wide:
            draw_text(canvas, (int(base * 0.08), int(base * 0.08)), brand["name"], f, dark["text"])
        else:
            draw_text(canvas, ((W - text_w(d, brand["name"], f)) / 2, top_y), brand["name"], f, dark["text"])
            top_y += line_h(f) + int(base * 0.035)
    cw = int(W * (0.5 if wide else 0.82))
    inner = int(cw * 0.09)
    avail_h = (H - 2 * int(base * 0.08) if wide else H - top_y - bottom_m) - 2 * inner
    parts = ("eyebrow", "headline", "divider", "subhead", "facts", "cta")
    align = "center" if sty["align"] == "center" else "left"
    ops, bh = fit_block(d, brand, v, cw - 2 * inner, avail_h, surf, parts, base, tag, hscale=0.82)
    ch = bh + 2 * inner
    if wide:
        cx, cy = W - cw - int(base * 0.08), (H - ch) // 2
    else:
        cx = (W - cw) // 2
        cy = top_y + max((H - top_y - bottom_m - ch) // 2, 0)
    if sty.get("shadow", True):
        shadow(canvas, (cx, cy, cx + cw, cy + ch), rad, base)
    m = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=rad, fill=255)
    canvas.paste(Image.new("RGB", (cw, ch), rgb(c["surface"])), (cx, cy), m)
    fi = int(base * 0.016)
    draw_frame(canvas, (cx + fi, cy + fi, cx + cw - fi, cy + ch - fi), mix(c["surface_text"], c["surface"], 0.55), sty.get("frame"), base)
    draw_block(canvas, ops, cx + inner, cy + inner, cw - 2 * inner, brand, surf, align)
    if brand.get("domain") and not wide:
        footer(canvas, brand, 0, H - bottom_m + int(base * 0.025), dark, base, "center", W)
    return info or {"source": None, "fit": "no photo"}


def layout_centered(canvas, p, sources, spec, brand, v, tag):
    """Centered stack on the brand background; photo (if any) in the brand's photo shape."""
    W, H = p["w"], p["h"]
    base, pad = min(W, H), int(min(W, H) * 0.08)
    st_, sb = safe(p, H)
    sty = brand["style"]
    pal = bg_palette(brand)
    paint_brand_bg(canvas, (0, 0, W, H), brand)
    d = ImageDraw.Draw(canvas)
    shape = sty["photo_shape"] if sty["photo_shape"] != "rect" else "rounded"
    rad = int(sty.get("radius", 24) * base / 1080)
    info = {"source": None, "fit": "no photo"}
    if W / H >= 1.5:
        tw = W - 2 * pad
        if sources:
            ps = int(H - 2 * pad)
            pw = ps if shape == "circle" else int(ps * 0.8)
            info = place_photo(canvas, (W - pad - pw, pad, W - pad, pad + ps), sources, spec, tag, shape, rad)
            tw = W - pw - 3 * pad
        ops, bh = fit_block(d, brand, v, tw, H - 2 * pad, pal, ALL_PARTS, base, tag)
        draw_block(canvas, ops, pad, (H - bh) // 2, tw, brand, pal, "center")
        return info
    usable = H - st_ - sb - 2 * pad
    o1, h1 = fit_block(d, brand, v, W - 2 * pad, int(usable * (0.36 if sources else 0.6)), pal,
                       ("wordmark", "eyebrow", "headline", "divider"), base, tag)
    o2, h2 = fit_block(d, brand, v, W - 2 * pad, int(usable * (0.28 if sources else 0.4)), pal, ("subhead", "cta") if sources else ("subhead", "facts", "cta"), base, tag)
    gap = int(base * 0.045)
    if sources:
        ph = usable - h1 - h2 - 2 * gap
        pw = min(int(W * 0.72), ph) if shape == "circle" else min(W - 2 * pad, int(ph * (0.82 if shape == "arch" else 1.5)))
        ph = pw if shape == "circle" else ph
        total = h1 + gap + ph + gap + h2
        y = st_ + pad + (usable - total) // 2
        draw_block(canvas, o1, pad, y, W - 2 * pad, brand, pal, "center")
        y += h1 + gap
        info = place_photo(canvas, ((W - pw) // 2, y, (W + pw) // 2, y + ph), sources, spec, tag, shape, rad)
        y += ph + gap
        draw_block(canvas, o2, pad, y, W - 2 * pad, brand, pal, "center")
    else:
        y = st_ + pad + (usable - h1 - h2) // 2
        draw_block(canvas, o1, pad, y, W - 2 * pad, brand, pal, "center")
        draw_block(canvas, o2, pad, y + h1, W - 2 * pad, brand, pal, "center")
    fi = int(base * 0.035)
    draw_frame(canvas, (fi, fi, W - fi, H - fi), pal["line"], sty.get("frame"), base)
    return info


def layout_stats(canvas, p, sources, spec, brand, v, tag):
    """Headline plus 1-4 big-number tiles from the variant's facts. No photo needed."""
    W, H = p["w"], p["h"]
    base, pad = min(W, H), int(min(W, H) * 0.075)
    st_, sb = safe(p, H)
    pal = bg_palette(brand)
    paint_brand_bg(canvas, (0, 0, W, H), brand)
    d = ImageDraw.Draw(canvas)
    facts = (v or {}).get("facts") or []
    if not facts:
        warn(f"{tag}: the stats layout needs 'facts' (value + label) in the variant.")
    tiles = brand.get("tiles") or [{"bg": "#%02x%02x%02x" % lighten(g, 0.9), "fg": g} for g in (brand["gradient"] or [brand["colors"]["accent"]])]
    rad = int(min(brand["style"].get("radius", 24), 28) * base / 1080)
    n = max(min(len(facts), 4), 1)
    gx = int(base * 0.03)
    align = brand["style"]["align"]
    if W / H >= 1.5:
        tw = int(W * 0.48)
        ops, bh = fit_block(d, brand, v, tw - pad, H - 2 * pad, pal, ("wordmark", "eyebrow", "headline", "subhead", "cta"), base, tag)
        draw_block(canvas, ops, pad, (H - bh) // 2, tw - pad, brand, pal)
        cols = 2 if n > 1 else 1
        area = (tw + pad // 2, pad, W - pad, H - pad)
    else:
        top = max(pad, st_ + pad // 2)
        ops, bh = fit_block(d, brand, v, W - 2 * pad, int((H - st_ - sb) * 0.45), pal, ("wordmark", "eyebrow", "headline", "subhead"), base, tag)
        draw_block(canvas, ops, pad, top, W - 2 * pad, brand, pal, align)
        o2, h2 = fit_block(d, brand, v, W - 2 * pad, int(base * 0.2), pal, ("cta",), base, tag)
        bottom = H - max(pad, sb + pad // 2)
        draw_block(canvas, o2, pad, bottom - h2, W - 2 * pad, brand, pal, align)
        cols = n if n <= 2 else 2
        area = (pad, top + bh + int(base * 0.05), W - pad, bottom - h2 - int(base * 0.05))
    rows = (n + cols - 1) // cols
    ax0, ay0, ax1, ay1 = area
    tw_ = (ax1 - ax0 - gx * (cols - 1)) // cols
    th_ = min((ay1 - ay0 - gx * (rows - 1)) // max(rows, 1), int(tw_ * 0.85))
    oy = ay0 + ((ay1 - ay0) - (th_ * rows + gx * (rows - 1))) // 2
    for i, fact in enumerate(facts[:4]):
        r_, c_ = divmod(i, cols)
        in_row = min(cols, n - r_ * cols)
        x0 = ax0 + (cols - in_row) * (tw_ + gx) // 2 + c_ * (tw_ + gx)
        y0 = oy + r_ * (th_ + gx)
        t = tiles[i % len(tiles)]
        ImageDraw.Draw(canvas).rounded_rectangle((x0, y0, x0 + tw_, y0 + th_), radius=rad, fill=rgb(t["bg"]),
                                                 outline=mix(t["bg"], t["fg"], 0.15), width=2)
        vf = font(brand["fonts"]["heading"], int(min(th_ * 0.38, tw_ * 0.3)))
        val = str(fact.get("value", ""))
        while text_w(d, val, vf) > tw_ * 0.86 and vf.size > 14:
            vf = font(brand["fonts"]["heading"], vf.size - 2)
        lf = font(brand["fonts"]["body"], max(int(th_ * 0.12), mp("label")))
        lab = wrap(d, str(fact.get("label", "")), lf, tw_ * 0.84)[:2]
        block_h = line_h(vf) + len(lab) * int(line_h(lf) * 1.1) + int(th_ * 0.04)
        yy = y0 + (th_ - block_h) // 2
        draw_text(canvas, (x0 + (tw_ - text_w(d, val, vf)) / 2, yy), val, vf, rgb(t["fg"]))
        yy += line_h(vf) + int(th_ * 0.04)
        for ln in lab:
            draw_text(canvas, (x0 + (tw_ - text_w(d, ln, lf)) / 2, yy), ln, lf, mix(brand["colors"]["text"], t["bg"], 0.15))
            yy += int(line_h(lf) * 1.1)
    if "dots" in (brand.get("motifs") or []):
        draw_dots(canvas, W - pad, max(pad, st_ + pad // 2) + int(base * 0.02), brand, base)
    return {"source": None, "fit": "no photo"}


def layout_type_only(canvas, p, sources, spec, brand, v, tag):
    """Big headline on the brand background. No photo."""
    W, H = p["w"], p["h"]
    base, pad = min(W, H), int(min(W, H) * 0.09)
    st_, sb = safe(p, H)
    align = brand["style"]["align"]
    pal = bg_palette(brand)
    paint_brand_bg(canvas, (0, 0, W, H), brand)
    d = ImageDraw.Draw(canvas)
    usable = H - st_ - sb - 2 * pad
    ops, bh = fit_block(d, brand, v, W - 2 * pad, usable - int(base * 0.06), pal, ALL_PARTS, base, tag, max_lines=5, hscale=1.35)
    draw_block(canvas, ops, pad, st_ + pad + (usable - bh) // 2, W - 2 * pad, brand, pal, align)
    fi = int(base * 0.035)
    draw_frame(canvas, (fi, fi, W - fi, H - fi), pal["line"], brand["style"].get("frame"), base)
    if "dots" in (brand.get("motifs") or []) and align != "center":
        draw_dots(canvas, W - pad, max(pad, st_ + pad // 2), brand, base)
    footer(canvas, brand, pad, H - max(pad, sb + pad // 2) - int(base * 0.022), pal, base, align, W - 2 * pad)
    return {"source": None, "fit": "no photo"}


LAYOUT_FN = {"editorial": layout_editorial, "full_bleed": layout_full_bleed, "split": layout_split, "band": layout_band,
             "card": layout_card, "centered": layout_centered, "stats": layout_stats, "type_only": layout_type_only}


def render(key, sources, spec, brand, variant, layout, tag):
    if variant and variant.get("facts") and layout in NEEDS_PHOTO and not spec.get("facts_on_photo_layouts"):
        variant = {k: val for k, val in variant.items() if k != "facts"}
    p = PLACEMENTS[key]
    W, H = p["w"], p["h"]
    _boost["k"] = 1.2 if H / W > 1.6 else (1.08 if H / W > 1.4 else 1.0)
    _ctx.update({"W": W, "H": H, "tag": tag, "contrast": spec.get("contrast", "fix")})
    canvas = Image.new("RGB", (W, H), rgb(brand["colors"]["background"]))
    if spec.get("mode", "plain") != "ad":
        info = place_photo(canvas, (0, 0, W, H), sources, spec, tag)
        if brand.get("logo") and spec.get("logo_on_plain", True):
            lg = Image.open(brand["logo"]).convert("RGBA")
            lw = int(min(W, H) * 0.16)
            lg = lg.resize((lw, int(lg.height * lw / lg.width)), Image.LANCZOS)
            m = int(min(W, H) * 0.045)
            canvas.paste(lg, (W - lw - m, max(m, int(H * p["safe_top"]) + m)), lg)
        return canvas, info
    return canvas, LAYOUT_FN[layout](canvas, p, sources, spec, brand, variant, tag)


# ================================================================ output
def utm_link(link, platform, campaign):
    if not link:
        return None
    u = urlparse(link)
    q = dict(parse_qsl(u.query))
    q.update({"utm_source": UTM_SOURCE.get(platform, platform), "utm_medium": "social", "utm_campaign": campaign})
    return urlunparse(u._replace(query=urlencode(q)))


def sheet(items, out_path, title, subtitle="", thumb_h=420):
    pad, label_h, max_w = 32, 64, 2600
    thumbs = []
    for path, label in items:
        im = Image.open(path).convert("RGB")
        thumbs.append((im.resize((round(im.width * thumb_h / im.height), thumb_h), Image.LANCZOS), label))
    rows, row, rw = [], [], pad
    for t, l in thumbs:
        if row and rw + t.width + pad > max_w:
            rows.append(row)
            row, rw = [], pad
        row.append((t, l))
        rw += t.width + pad
    rows.append(row)
    sw = max(sum(t.width + pad for t, _ in r) + pad for r in rows)
    sh = 110 + len(rows) * (thumb_h + label_h + pad) + pad
    s = Image.new("RGB", (sw, sh), (246, 247, 250))
    d = ImageDraw.Draw(s)
    d.text((pad, 26), title, font=ImageFont.truetype(DEFAULT_FONTS["heading"], 30), fill=(17, 17, 17))
    if subtitle:
        d.text((pad, 66), subtitle, font=ImageFont.truetype(DEFAULT_FONTS["body"], 18), fill=(90, 90, 100))
    lf = ImageFont.truetype(DEFAULT_FONTS["label"], 17)
    y = 110
    for r in rows:
        x = pad
        for t, l in r:
            s.paste(t, (x, y))
            d.rectangle((x - 1, y - 1, x + t.width, y + thumb_h), outline=(215, 218, 225))
            for i, part in enumerate(l.split("\n")):
                d.text((x, y + thumb_h + 8 + i * 24), part, font=lf, fill=(50, 50, 60) if i == 0 else (110, 110, 120))
            x += t.width + pad
        y += thumb_h + label_h + pad
    s.save(out_path)


def save(img, path, pil_fmt, quality):
    kw = {"quality": quality} if pil_fmt in ("WEBP", "JPEG") else {"optimize": True}
    if pil_fmt == "WEBP":
        kw["method"] = 6
    img.save(path, pil_fmt, **kw)


def contrast_summary():
    """One line per original color that failed, with the color it was changed to."""
    seen = {}
    for e in contrast_report:
        k = (e["from"], e["to"])
        if k not in seen:
            seen[k] = {"from": e["from"], "to": e["to"], "ratio_before": e["ratio_before"], "ratio_after": e["ratio_after"],
                       "needed": e["needed"], "example_text": e["text"], "where": [e["where"]]}
        elif e["where"] not in seen[k]["where"]:
            seen[k]["where"].append(e["where"])
    return {"standard": "WCAG 2.2 AA: 4.5:1 for text, 3:1 for headline-size text, measured against the pixels behind each line",
            "mode": _ctx.get("contrast", "fix"), "issues": list(seen.values())}


def main(spec_path):
    spec_path = os.path.abspath(spec_path)
    spec_dir = os.path.dirname(spec_path)
    with open(spec_path) as f:
        spec = json.load(f)
    brand = load_brand(spec, spec_dir)
    spec["_brand"] = brand

    name = spec.get("name", "Social").replace(" ", "_")
    out_dir = spec["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    pil_fmt, ext = FORMATS[spec.get("format", "webp").lower()]
    quality = spec.get("quality", 85)

    sources = {}
    for key, val in (spec.get("images") or {}).items():
        e = dict(val) if isinstance(val, dict) else {"path": val}
        pth = e["path"] if os.path.isabs(e["path"]) else os.path.join(spec_dir, e["path"])
        e["img"] = load_photo(pth)
        sources[key] = e

    mode = spec.get("mode", "plain")
    if mode != "ad" and not sources:
        sys.exit("Plain mode needs at least one photo in spec['images'].")
    variants = spec.get("variants") or []
    if mode == "ad" and not variants:
        sys.exit("Ad mode needs at least one variant with a headline.")
    if mode != "ad":
        variants = [None]
    stage = spec.get("stage", "final")

    def check_layouts(lays):
        bad = [l for l in lays if l not in LAYOUTS]
        if bad:
            sys.exit(f"Unknown layouts {bad}. Valid: {LAYOUTS}")
        if not sources:
            need = [l for l in lays if l in NEEDS_PHOTO]
            if need:
                sys.exit(f"Layouts {need} need a photo. Without one, use: {[l for l in LAYOUTS if l not in NEEDS_PHOTO]}")

    if stage == "concepts" and mode == "ad":
        layouts = spec.get("concepts") or (["editorial", "full_bleed", "split"] if sources else ["card", "centered", "type_only"])
        check_layouts(layouts)
        cp = spec.get("concept_placement") or next((k for k in ("meta_portrait", "meta_square", "pinterest") if k in (spec.get("placements") or PLACEMENTS)), "meta_portrait")
        cdir = os.path.join(out_dir, "concepts")
        os.makedirs(cdir, exist_ok=True)
        items, files = [], []
        for i, lay in enumerate(layouts):
            letter = chr(65 + i)
            img, info = render(cp, sources, spec, brand, variants[0], lay, f"concept {letter}")
            path = os.path.join(cdir, f"{name}_concept-{letter}_{lay}.png")
            img.save(path)
            files.append({"concept": letter, "layout": lay, "file": path, **(info or {})})
            items.append((path, f"{letter} · {LAYOUT_LABELS[lay].upper()}\nlayout: {lay}"))
        p = PLACEMENTS[cp]
        sheet_path = os.path.join(out_dir, f"{name}_concepts.png")
        sheet(items, sheet_path, f"{name.replace('_', ' ')}: ad concepts",
              f"{p['label']} · {p['w']}×{p['h']} · pick one direction to apply to every size", thumb_h=560)
        print(json.dumps({"stage": "concepts", "concept_sheet": sheet_path, "concepts": files,
                          "contrast": contrast_summary(), "warnings": warnings}, indent=2))
        return

    layout = spec.get("layout", "editorial" if sources else "card")
    if mode == "ad":
        check_layouts([layout])
    keys = spec.get("placements") or list(PLACEMENTS)
    bad = [k for k in keys if k not in PLACEMENTS]
    if bad:
        sys.exit(f"Unknown placements {bad}. Valid: {list(PLACEMENTS)}")
    only = set(spec.get("only") or [])
    campaign = spec.get("campaign", name.lower())
    manifest = {"name": name, "mode": mode, "layout": layout if mode == "ad" else None, "format": ext,
                "link": spec.get("link"), "brand": brand.get("name"), "images": []}
    items = []
    multi = len(variants) > 1
    for key in keys:
        p = PLACEMENTS[key]
        for v in variants:
            vt = f"_{v['id']}" if v and multi else ""
            tag = f"{key}{vt}"
            if only and tag not in only and key not in only:
                continue
            img, info = render(key, sources, spec, brand, v, layout, tag)
            info = info or {}
            fname = f"{name}_{p['suffix']}{vt}.{ext}"
            save(img, os.path.join(out_dir, fname), pil_fmt, quality)
            entry = {"file": fname, "placement": key, "label": p["label"], "platform": p["platform"],
                     "width": p["w"], "height": p["h"], "variant": v["id"] if v else None,
                     "link": utm_link(spec.get("link"), p["platform"], campaign), **info}
            if v:
                entry.update({k: v.get(k) for k in ("headline", "emphasis", "subhead", "cta", "facts")})
            manifest["images"].append(entry)
            items.append((os.path.join(out_dir, fname), f"{p['suffix']}{vt}\n{p['w']}×{p['h']} · {info.get('fit', '')}"))
    if spec.get("post_content"):
        manifest["post_content"] = spec["post_content"]
    manifest["warnings"] = warnings
    manifest["contrast"] = contrast_summary()
    mpath = os.path.join(out_dir, "manifest.json")
    if only and os.path.exists(mpath):
        with open(mpath) as f:
            old = json.load(f)
        merged = {e["file"]: e for e in old["images"]}
        merged.update({e["file"]: e for e in manifest["images"]})
        old_files = [e["file"] for e in old["images"]]
        order = old_files + [e["file"] for e in manifest["images"] if e["file"] not in old_files]
        old["images"] = [merged[f] for f in order]
        old["warnings"] = warnings
        manifest = old
        items = [(os.path.join(out_dir, e["file"]), f"{e['file'].rsplit('.', 1)[0].replace(name + '_', '')}\n{e['width']}×{e['height']} · {e.get('fit', '')}")
                 for e in manifest["images"] if os.path.exists(os.path.join(out_dir, e["file"]))]
    sheet_path = os.path.join(out_dir, f"{name}_contact-sheet.png")
    if items:
        sheet(items, sheet_path, f"{name.replace('_', ' ')}: {len(items)} images",
              f"Layout: {LAYOUT_LABELS.get(layout, 'plain') if mode == 'ad' else 'plain'}")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps({"stage": "final", "contrast": contrast_summary(), "output_dir": out_dir, "files": [e["file"] for e in manifest["images"]],
                      "contact_sheet": sheet_path if items else None, "warnings": warnings}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
