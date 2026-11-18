#!/usr/bin/env python3
"""
mj-social-ad-resizer renderer.

Usage:
    python3 make_images.py spec.json

Two stages (spec["stage"]):
  concepts  Render each layout in spec["concepts"] at one placement and
            write a concept sheet for the user to pick a direction.
  final     Render every placement (and A/B variant) in spec["layout"],
            plus a contact sheet and manifest.json.

See references/spec.md and references/brand.md for every field.
"""
import json
import os
import sys
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.normpath(os.path.join(HERE, "..", "assets", "fonts"))
DEFAULT_FONTS = {
    "heading": os.path.join(FONT_DIR, "Inter-Bold.otf"),
    "body": os.path.join(FONT_DIR, "Inter-Regular.otf"),
    "label": os.path.join(FONT_DIR, "Inter-SemiBold.otf"),
}

PLACEMENTS = {
    "meta_square":     {"w": 1080, "h": 1080, "platform": "meta",      "suffix": "IG-1x1", "label": "Meta feed 1:1",          "safe_top": 0.0,  "safe_bottom": 0.0},
    "meta_portrait":   {"w": 1080, "h": 1350, "platform": "meta",      "suffix": "IG-4x5", "label": "Meta feed 4:5",          "safe_top": 0.0,  "safe_bottom": 0.0},
    "meta_story":      {"w": 1080, "h": 1920, "platform": "meta",      "suffix": "STORY",  "label": "Meta Stories/Reels 9:16","safe_top": 0.14, "safe_bottom": 0.20},
    "pinterest":       {"w": 1000, "h": 1500, "platform": "pinterest", "suffix": "PT",     "label": "Pinterest pin 2:3",      "safe_top": 0.0,  "safe_bottom": 0.0},
    "link_preview":    {"w": 1200, "h": 630,  "platform": "link",      "suffix": "FB",     "label": "Link preview 1.91:1",    "safe_top": 0.0,  "safe_bottom": 0.0},
    "linkedin_square": {"w": 1200, "h": 1200, "platform": "linkedin",  "suffix": "LI-1x1", "label": "LinkedIn feed 1:1",      "safe_top": 0.0,  "safe_bottom": 0.0},
    "x_post":          {"w": 1600, "h": 900,  "platform": "x",         "suffix": "X",      "label": "X in-feed 16:9",         "safe_top": 0.0,  "safe_bottom": 0.0},
}
LAYOUTS = ["editorial", "full_bleed", "split", "band"]
LAYOUT_LABELS = {"editorial": "Editorial", "full_bleed": "Full bleed", "split": "Split panel", "band": "Color band"}
UTM_SOURCE = {"meta": "facebook", "pinterest": "pinterest", "link": "social", "linkedin": "linkedin", "x": "x"}
FORMATS = {"webp": ("WEBP", "webp"), "png": ("PNG", "png"), "jpg": ("JPEG", "jpg"), "jpeg": ("JPEG", "jpg")}

warnings = []


def warn(msg):
    if msg not in warnings:
        warnings.append(msg)


# ---------------------------------------------------------------- color
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
    r, g, b = (ch(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def readable_on(bg):
    return (255, 255, 255) if contrast((255, 255, 255), bg) >= contrast((10, 10, 10), bg) else (10, 10, 10)


def gradient_image(w, h, colors, horizontal=True):
    """Multi-stop linear gradient."""
    colors = [rgb(c) for c in colors] or [(0, 0, 0)]
    if len(colors) == 1:
        return Image.new("RGB", (w, h), colors[0])
    n = w if horizontal else h
    strip = Image.new("RGB", (max(n, 2), 1))
    px = strip.load()
    segs = len(colors) - 1
    for i in range(strip.width):
        t = i / (strip.width - 1) * segs
        k = min(int(t), segs - 1)
        f = t - k
        a, b = colors[k], colors[k + 1]
        px[i, 0] = tuple(round(a[j] + (b[j] - a[j]) * f) for j in range(3))
    if horizontal:
        return strip.resize((w, h), Image.BILINEAR)
    return strip.resize((h, w), Image.BILINEAR).rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)


# ---------------------------------------------------------------- brand
BRAND_DEFAULTS = {
    "name": "",
    "domain": "",
    "colors": {
        "background": "#FFFFFF", "background_2": None, "text": "#111111", "muted": "#555555",
        "primary": "#111111", "on_primary": None, "accent": None, "border": "#E5E7EB",
        "scrim": "#0A0A0A", "band": None,
    },
    "gradient": [],
    "glows": [],
    "grid": None,
    "fonts": {},
    "headline_tracking": -0.02,
    "headline_case": "none",
    "button": {"style": "solid", "radius": "pill"},
    "motifs": [],
    "eyebrow": "",
    "logo": None,
    "logo_on_dark": None,
    "corner_radius": 0,
}


def load_brand(spec, spec_dir):
    raw = spec.get("brand") or {}
    base = spec_dir
    if isinstance(raw, str):
        path = raw if os.path.isabs(raw) else os.path.join(spec_dir, raw)
        base = os.path.dirname(path)
        if not os.path.exists(path):
            sys.exit(f"Brand profile not found: {path}. Paths in the spec are relative to the spec file.")
        with open(path) as f:
            raw = json.load(f)
    # legacy flat format from v1 (primary/accent/logo/font_heading at top level)
    if "colors" not in raw and any(k in raw for k in ("primary", "accent", "on_primary")):
        raw = {"colors": {k: raw[k] for k in ("primary", "on_primary", "accent") if k in raw},
               "logo": raw.get("logo"),
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

    def resolve(p):
        if not p:
            return None
        p = p if os.path.isabs(p) else os.path.join(base, p)
        if not os.path.exists(p):
            warn(f"Brand file not found: {p}. Using the default instead.")
            return None
        return p

    fonts = {}
    for role in ("heading", "body", "label"):
        entry = b["fonts"].get(role)
        if isinstance(entry, dict):
            fonts[role] = {"path": resolve(entry.get("path")) or DEFAULT_FONTS[role], "variation": entry.get("variation")}
        else:
            fonts[role] = {"path": resolve(entry) or DEFAULT_FONTS[role], "variation": None}
    if not b["fonts"].get("label") and b["fonts"].get("heading"):
        fonts["label"] = fonts["heading"]
    b["fonts"] = fonts
    b["logo"] = resolve(b.get("logo"))
    b["logo_on_dark"] = resolve(b.get("logo_on_dark"))
    return b


_font_cache = {}


def font(role_or_spec, size):
    spec = role_or_spec
    key = (spec["path"], spec.get("variation"), size)
    if key not in _font_cache:
        f = ImageFont.truetype(spec["path"], size)
        if spec.get("variation"):
            try:
                f.set_variation_by_name(spec["variation"])
            except Exception:
                pass
        _font_cache[key] = f
    return _font_cache[key]


# ---------------------------------------------------------------- photo
def load_photo(path):
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def pick_source(sources, ratio):
    def dist(r):
        return r / ratio if r >= ratio else ratio / r
    return min(sources, key=lambda k: dist(sources[k]["img"].width / sources[k]["img"].height))


def place_photo(canvas, box, sources, spec, tag, radius=0):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
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
            bg = bg.crop(((bg.width - w) // 2, (bg.height - h) // 2, (bg.width - w) // 2 + w, (bg.height - h) // 2 + h))
            tile = Image.blend(bg.filter(ImageFilter.GaussianBlur(max(w, h) // 30)), Image.new("RGB", (w, h), 0), 0.2)
        else:
            tile = Image.new("RGB", (w, h), rgb(spec["_brand"]["colors"]["primary"]))
        fg = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        tile.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
    if scale > 1.05:
        where = tag.rsplit("_", 1)[0] if len(tag.rsplit("_", 1)[-1]) == 1 else tag
        warn(f"{where}: photo '{key}' was enlarged {scale:.1f}x and may look soft. A larger photo will be sharper.")
    if radius:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
        canvas.paste(tile, (x0, y0), mask)
    else:
        canvas.paste(tile, (x0, y0))
    return {"source": key, "fit": how, "photo_kept_pct": round(kept * 100), "scale": round(scale, 2)}


# ---------------------------------------------------------------- backgrounds and motifs
def paint_brand_bg(canvas, box, brand):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    c = brand["colors"]
    bg = gradient_image(w, h, [c["background"], c["background_2"]], horizontal=False)
    base = min(w, h)
    for g in brand.get("glows") or []:
        rad = max(int(base * g.get("r", 0.45)), 4)
        mask = Image.radial_gradient("L").resize((rad * 2, rad * 2), Image.BILINEAR)
        mask = ImageOps.invert(mask).point(lambda v: int(v * g.get("strength", 0.9)))
        layer = Image.new("RGB", (rad * 2, rad * 2), rgb(g["color"]))
        bg.paste(layer, (int(g.get("x", 0.2) * w) - rad, int(g.get("y", 0.1) * h) - rad), mask)
    grid = brand.get("grid")
    if grid:
        step = max(int(grid.get("size", 64) * base / 1080), 12)
        col = rgb(grid.get("color", "#000000"))
        a = grid.get("opacity", 0.06)
        overlay = Image.new("RGB", (w, h), col)
        m = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(m)
        for gx in range(0, w, step):
            d.line((gx, 0, gx, h), fill=int(255 * a), width=max(1, base // 1080))
        for gy in range(0, h, step):
            d.line((0, gy, w, gy), fill=int(255 * a), width=max(1, base // 1080))
        bg.paste(overlay, (0, 0), m)
    canvas.paste(bg, (x0, y0))


def scrim(canvas, box, color, direction, strength=0.78, reach=1.0):
    """Darken part of the canvas with a gradient. direction: 'top','bottom','left','right' = where it's darkest."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    horiz = direction in ("left", "right")
    n = w if horiz else h
    strip = Image.new("L", (n, 1))
    for i in range(n):
        t = i / max(n - 1, 1)
        t = t if direction in ("right", "bottom") else 1 - t
        t = max(0.0, (t - (1 - reach)) / reach) if reach < 1 else t
        strip.putpixel((i, 0), int(255 * strength * (t ** 1.4)))
    m = strip.resize((w, h)) if horiz else strip.resize((h, w)).rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
    region = canvas.crop(box)
    region.paste(Image.new("RGB", (w, h), rgb(color)), (0, 0), m)
    canvas.paste(region, (x0, y0))


def draw_dots(draw, x_right, y, brand, base):
    cols = brand["gradient"] or [brand["colors"]["accent"]]
    r = max(int(base * 0.007), 3)
    gap = r * 3
    cols = (cols * 4)[:4]
    x = x_right - (len(cols) - 1) * gap - r
    for c in cols:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=rgb(c))
        x += gap


# ---------------------------------------------------------------- text
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
    return lines


def text_w(draw, s, f, tracking=0):
    return draw.textlength(s, font=f) + tracking * f.size * max(len(s) - 1, 0)


def line_h(f, leading=1.0):
    a, d = f.getmetrics()
    return int((a + d) * leading)


def draw_text(canvas, xy, s, f, fill, tracking=0, gradient=None):
    """Draw a line of text; tracking in em; gradient = list of colors (fills glyphs)."""
    x, y = xy
    w = int(text_w(ImageDraw.Draw(canvas), s, f, tracking)) + 4
    h = line_h(f) + 4
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    if tracking:
        cx = 0
        for ch in s:
            md.text((cx, 0), ch, font=f, fill=255)
            cx += md.textlength(ch, font=f) + tracking * f.size
    else:
        md.text((0, 0), s, font=f, fill=255)
    fill_img = gradient_image(w, h, gradient) if gradient else Image.new("RGB", (w, h), fill)
    canvas.paste(fill_img, (int(x), int(y)), mask)
    return w


def split_emphasis(headline, emphasis):
    if emphasis and headline.rstrip().endswith(emphasis.strip()):
        lead = headline.rstrip()[: -len(emphasis.strip())].rstrip()
        return lead, emphasis.strip()
    return headline, ""


# ---------------------------------------------------------------- text block
def build_block(draw, brand, variant, width, scale, theme, parts, base):
    """Measure the text block; returns list of draw ops and total height."""
    c = brand["colors"]
    F = brand["fonts"]
    motifs = set(brand.get("motifs") or [])
    dark = theme == "dark"
    text_col = (255, 255, 255) if dark else rgb(c["text"])
    muted = (225, 225, 230) if dark else rgb(c["muted"])
    ops, y = [], 0
    track = brand.get("headline_tracking", 0)

    if "wordmark" in parts and (brand.get("name") or brand.get("logo")):
        logo = brand.get("logo_on_dark") if dark and brand.get("logo_on_dark") else brand.get("logo")
        if logo:
            lg = Image.open(logo).convert("RGBA")
            lh = int(base * 0.05 * scale)
            lw = int(lg.width * lh / lg.height)
            ops.append(("logo", y, lg.resize((lw, lh), Image.LANCZOS)))
            y += lh + int(base * 0.03 * scale)
        else:
            f = font(F["label"], max(int(base * 0.03 * scale), 14))
            ops.append(("text", y, brand["name"], f, text_col, 0, None))
            y += line_h(f) + int(base * 0.028 * scale)

    eyebrow = variant.get("eyebrow", brand.get("eyebrow")) if variant else brand.get("eyebrow")
    if "eyebrow" in parts and eyebrow and "eyebrow_pill" in motifs:
        f = font(F["label"], max(int(base * 0.019 * scale), 12))
        s = eyebrow.upper()
        tw = text_w(draw, s, f, 0.06)
        px, py = int(f.size * 0.9), int(f.size * 0.55)
        ops.append(("pill", y, s, f, tw, px, py, dark))
        y += line_h(f) + 2 * py + int(base * 0.035 * scale)

    hl = (variant or {}).get("headline", "")
    if brand.get("headline_case") == "upper":
        hl = hl.upper()
    emph = (variant or {}).get("emphasis")
    if emph is None and "gradient_text" in motifs and brand["gradient"] and len(hl.split()) > 1:
        emph = hl.split()[-1]
    lead, emph = split_emphasis(hl, emph or "")
    hsize = int(base * 0.092 * scale)
    hf = font(F["heading"], max(hsize, 18))
    lead_lines = wrap(draw, lead, hf, width, track) if lead else []
    emph_lines = wrap(draw, emph, hf, width, track) if emph else []
    lh = int(hf.size * brand.get("headline_leading", 1.08))
    for ln in lead_lines:
        ops.append(("text", y, ln, hf, text_col, track, None))
        y += lh
    grad = brand["gradient"] if (brand["gradient"] and "gradient_text" in motifs) else None
    if grad and dark:
        grad = [lighten(g, 0.35) for g in grad]
    for ln in emph_lines:
        ops.append(("text", y, ln, hf, text_col, track, grad))
        y += lh
    last = (emph_lines or lead_lines or [""])[-1]
    if "gradient_underline" in motifs and brand["gradient"]:
        uw = int(text_w(draw, last, hf, track))
        bottom = (y - lh) + hf.getbbox(last)[3]  # true glyph bottom of the last line
        bar_y = bottom + int(hsize * 0.12)
        ops.append(("bar", bar_y, uw, max(int(hsize * 0.09), 4)))
        y = max(y, bar_y + max(int(hsize * 0.09), 4) + int(hsize * 0.1))
    headline_lines = len(lead_lines) + len(emph_lines)

    sub = (variant or {}).get("subhead")
    if sub:
        y += int(base * 0.025 * scale)
        sf = font(F["body"], max(int(base * 0.032 * scale), 14))
        for ln in wrap(draw, sub, sf, width)[:3]:
            ops.append(("text", y, ln, sf, muted, 0, None))
            y += int(line_h(sf) * 1.15)

    cta = (variant or {}).get("cta")
    if cta and "cta" in parts:
        y += int(base * 0.045 * scale)
        cf = font(F["label"], max(int(base * 0.03 * scale), 14))
        tw = text_w(draw, cta, cf)
        px, py = int(cf.size * 1.25), int(cf.size * 0.75)
        ops.append(("button", y, cta, cf, tw, px, py, dark))
        y += line_h(cf) + 2 * py
    return ops, y, headline_lines, hl, emph


def lighten(c, t):
    r = rgb(c)
    return tuple(int(v + (255 - v) * t) for v in r)


def draw_block(canvas, ops, x, y, width, brand, align="left"):
    draw = ImageDraw.Draw(canvas)
    c = brand["colors"]
    btn = brand.get("button") or {}
    for op in ops:
        kind, oy = op[0], y + op[1]
        if kind == "text":
            _, _, s, f, col, track, grad = op
            tw = text_w(draw, s, f, track)
            ox = x + (width - tw) / 2 if align == "center" else x
            draw_text(canvas, (ox, oy), s, f, col, track, grad)
        elif kind == "logo":
            lg = op[2]
            ox = x + (width - lg.width) // 2 if align == "center" else x
            canvas.paste(lg, (int(ox), int(oy)), lg)
        elif kind == "bar":
            _, _, uw, bh = op
            ox = x + (width - uw) / 2 if align == "center" else x
            bar = gradient_image(uw, bh, brand["gradient"])
            m = Image.new("L", (uw, bh), 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, uw - 1, bh - 1), radius=bh // 2, fill=255)
            canvas.paste(bar, (int(ox), int(oy)), m)
        elif kind == "pill":
            _, _, s, f, tw, px, py, dark = op
            w, h = int(tw + 2 * px), line_h(f) + 2 * py
            ox = x + (width - w) / 2 if align == "center" else x
            fill = (255, 255, 255) if not dark else None
            outline = rgb(c["border"]) if not dark else (255, 255, 255)
            draw.rounded_rectangle((ox, oy, ox + w, oy + h), radius=h // 2, fill=fill, outline=outline, width=max(2, f.size // 10))
            draw_text(canvas, (ox + px, oy + py - 1), s, f, rgb(c["text"]) if not dark else (255, 255, 255), 0.06)
            draw = ImageDraw.Draw(canvas)
        elif kind == "button":
            _, _, s, f, tw, px, py, dark = op
            w, h = int(tw + 2 * px), line_h(f) + 2 * py
            ox = x + (width - w) / 2 if align == "center" else x
            style = btn.get("style", "solid")
            rad = h // 2 if btn.get("radius", "pill") == "pill" else int(btn.get("radius", 8))
            m = Image.new("L", (w, h), 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=rad, fill=255)
            if style == "gradient" and brand["gradient"]:
                face, fg = gradient_image(w, h, brand["gradient"]), (255, 255, 255)
                worst = min(contrast(fg, rgb(g)) for g in brand["gradient"])
                if worst < 4.5:
                    warn(f"Button text contrast drops to {worst:.1f}:1 on the gradient (WCAG AA needs 4.5:1). Consider a darker gradient or the solid button style.")
            elif dark:
                face, fg = Image.new("RGB", (w, h), (255, 255, 255)), (10, 10, 10)
            else:
                face, fg = Image.new("RGB", (w, h), rgb(c["primary"])), rgb(c["on_primary"])
            canvas.paste(face, (int(ox), int(oy)), m)
            draw_text(canvas, (ox + px, oy + py - 1), s, f, fg)
            draw = ImageDraw.Draw(canvas)
            if style == "solid" and not dark:
                ratio = contrast(rgb(c["primary"]), rgb(c["on_primary"]))
                if ratio < 4.5:
                    warn(f"Button text contrast is {ratio:.1f}:1 (WCAG AA needs 4.5:1).")


def fit_block(draw, brand, variant, width, max_h, theme, parts, base, tag):
    scale = 1.0
    while True:
        ops, h, n, hl, emph = build_block(draw, brand, variant, width, scale, theme, parts, base)
        if (h <= max_h and n <= 4) or scale <= 0.5:
            break
        scale -= 0.05
    if h > max_h or n > 4:
        warn(f"{tag}: the text is too long for this size. Shorten the headline or subhead.")
    return ops, h


def footer(canvas, brand, x, y, theme, base, align_right_w=None):
    if not brand.get("domain"):
        return
    f = font(brand["fonts"]["label"], max(int(base * 0.022), 12))
    col = (255, 255, 255) if theme == "dark" else rgb(brand["colors"]["muted"])
    draw_text(canvas, (x, y), brand["domain"], f, col)


# ---------------------------------------------------------------- layouts
def layout_editorial(canvas, p, sources, spec, brand, variant, tag):
    W, H = p["w"], p["h"]
    base = min(W, H)
    pad = int(base * 0.075)
    st, sb = int(H * p["safe_top"]), int(H * p["safe_bottom"])
    d = ImageDraw.Draw(canvas)
    wide = W / H >= 1.5
    paint_brand_bg(canvas, (0, 0, W, H), brand)
    if wide:
        tw = int(W * 0.5)
        ops, bh = fit_block(d, brand, variant, tw - 2 * pad, H - 2 * pad, "light", {"wordmark", "eyebrow", "cta"}, base, tag)
        draw_block(canvas, ops, pad, (H - bh) // 2, tw - 2 * pad, brand)
        info = place_photo(canvas, (tw, pad, W - pad, H - pad), sources, spec, tag, radius=int(base * 0.03))
        return info
    ops, bh = fit_block(d, brand, variant, W - 2 * pad, int(H * 0.5), "light", {"wordmark", "eyebrow", "cta"}, base, tag)
    top = max(pad, st + pad // 2)
    draw_block(canvas, ops, pad, top, W - 2 * pad, brand)
    py0 = top + bh + int(pad * 0.8)
    info = place_photo(canvas, (0, py0, W, H), sources, spec, tag)
    if "dots" in (brand.get("motifs") or []):
        draw_dots(ImageDraw.Draw(canvas), W - pad, top + int(base * 0.02), brand, base)
    if brand.get("domain") and not sb:
        scrim(canvas, (0, max(py0, H - int(H * 0.18)), W, H), brand["colors"]["scrim"], "bottom", 0.55)
        footer(canvas, brand, pad, H - pad - int(base * 0.022), "dark", base)
    return info


def layout_full_bleed(canvas, p, sources, spec, brand, variant, tag):
    W, H = p["w"], p["h"]
    base = min(W, H)
    pad = int(base * 0.075)
    st, sb = int(H * p["safe_top"]), int(H * p["safe_bottom"])
    info = place_photo(canvas, (0, 0, W, H), sources, spec, tag)
    d = ImageDraw.Draw(canvas)
    wide = W / H >= 1.5
    sc = brand["colors"]["scrim"]
    if wide:
        scrim(canvas, (0, 0, int(W * 0.75), H), sc, "left", 0.85)
        tw = int(W * 0.55)
        ops, bh = fit_block(d, brand, variant, tw - pad, H - 2 * pad, "dark", {"wordmark", "eyebrow", "cta"}, base, tag)
        draw_block(canvas, ops, pad, (H - bh) // 2, tw - pad, brand)
    else:
        scrim(canvas, (0, 0, W, int(H * 0.72)), sc, "top", 0.82)
        scrim(canvas, (0, int(H * 0.75), W, H), sc, "bottom", 0.6)
        top = max(pad, st + pad // 2)
        ops, bh = fit_block(d, brand, variant, W - 2 * pad, int(H * 0.5), "dark", {"wordmark", "eyebrow", "cta"}, base, tag)
        draw_block(canvas, ops, pad, top, W - 2 * pad, brand)
    if "dots" in (brand.get("motifs") or []):
        draw_dots(ImageDraw.Draw(canvas), W - pad, max(pad, st + pad // 2) + int(base * 0.02), brand, base)
    footer(canvas, brand, pad, H - max(pad, sb + pad // 2) - int(base * 0.022), "dark", base)
    return info


def layout_split(canvas, p, sources, spec, brand, variant, tag):
    W, H = p["w"], p["h"]
    base = min(W, H)
    pad = int(base * 0.07)
    st, sb = int(H * p["safe_top"]), int(H * p["safe_bottom"])
    d = ImageDraw.Draw(canvas)
    divider = max(int(base * 0.008), 4)
    tall = W / H < 0.7
    if tall:  # stories: text panel on top, photo below
        ph = int(H * 0.5)
        paint_brand_bg(canvas, (0, 0, W, H - ph), brand)
        top = max(pad, st + pad // 2)
        ops, bh = fit_block(d, brand, variant, W - 2 * pad, H - ph - top - pad, "light", {"wordmark", "eyebrow", "cta"}, base, tag)
        draw_block(canvas, ops, pad, top + (H - ph - top - pad - bh) // 2, W - 2 * pad, brand)
        info = place_photo(canvas, (0, H - ph, W, H), sources, spec, tag)
        if brand["gradient"]:
            canvas.paste(gradient_image(W, divider, brand["gradient"]), (0, H - ph - divider))
        return info
    panel = int(W * (0.44 if W / H >= 1.2 else 0.5))
    paint_brand_bg(canvas, (0, 0, panel, H), brand)
    info = place_photo(canvas, (panel + divider, 0, W, H), sources, spec, tag)
    if brand["gradient"]:
        canvas.paste(gradient_image(divider, H, brand["gradient"], horizontal=False), (panel, 0))
    ops, bh = fit_block(d, brand, variant, panel - 2 * pad, H - 2 * pad - int(base * 0.06), "light", {"wordmark", "eyebrow", "cta"}, base, tag)
    draw_block(canvas, ops, pad, max(pad, (H - bh) // 2 - int(base * 0.02)), panel - 2 * pad, brand)
    footer(canvas, brand, pad, H - pad - int(base * 0.022), "light", base)
    return info


def layout_band(canvas, p, sources, spec, brand, variant, tag):
    W, H = p["w"], p["h"]
    base = min(W, H)
    pad = int(base * 0.06)
    sb = int(H * p["safe_bottom"])
    d = ImageDraw.Draw(canvas)
    band_col = rgb(brand["colors"]["band"])
    b2 = dict(brand, colors=dict(brand["colors"], text="#%02x%02x%02x" % readable_on(band_col)))
    theme = "dark" if readable_on(band_col) == (255, 255, 255) else "light"
    if W / H >= 1.5:
        bw = int(W * 0.42)
        info = place_photo(canvas, (0, 0, W - bw, H), sources, spec, tag)
        canvas.paste(Image.new("RGB", (bw, H), band_col), (W - bw, 0))
        ops, bh = fit_block(d, b2, variant, bw - 2 * pad, H - 2 * pad, theme, {"eyebrow", "cta"}, base, tag)
        draw_block(canvas, ops, W - bw + pad, (H - bh) // 2, bw - 2 * pad, b2)
        return info
    ops, bh = fit_block(d, b2, variant, W - 2 * pad, int(H * 0.42), theme, {"eyebrow", "cta"}, base, tag)
    band_h = bh + 2 * pad + sb
    info = place_photo(canvas, (0, 0, W, H - band_h), sources, spec, tag)
    canvas.paste(Image.new("RGB", (W, band_h), band_col), (0, H - band_h))
    if brand["gradient"]:
        canvas.paste(gradient_image(W, max(int(base * 0.008), 4), brand["gradient"]), (0, H - band_h))
    draw_block(canvas, ops, pad, H - band_h + pad, W - 2 * pad, b2)
    return info


LAYOUT_FN = {"editorial": layout_editorial, "full_bleed": layout_full_bleed, "split": layout_split, "band": layout_band}


def render(key, sources, spec, brand, variant, layout, tag):
    p = PLACEMENTS[key]
    W, H = p["w"], p["h"]
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
    info = LAYOUT_FN[layout](canvas, p, sources, spec, brand, variant, tag)
    return canvas, info


# ---------------------------------------------------------------- output helpers
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


# ---------------------------------------------------------------- main
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
        p = e["path"] if os.path.isabs(e["path"]) else os.path.join(spec_dir, e["path"])
        e["img"] = load_photo(p)
        sources[key] = e
    if not sources:
        sys.exit("At least one photo is required in spec['images'].")

    mode = spec.get("mode", "plain")
    variants = spec.get("variants") or []
    if mode == "ad" and not variants:
        sys.exit("Ad mode needs at least one variant with a headline.")
    if mode != "ad":
        variants = [None]
    stage = spec.get("stage", "final")

    # ---- concept stage
    if stage == "concepts" and mode == "ad":
        layouts = spec.get("concepts") or ["editorial", "full_bleed", "split"]
        bad = [l for l in layouts if l not in LAYOUTS]
        if bad:
            sys.exit(f"Unknown layouts {bad}. Valid: {LAYOUTS}")
        cp = spec.get("concept_placement") or next((k for k in ("meta_portrait", "meta_square", "pinterest") if k in (spec.get("placements") or PLACEMENTS)), "meta_portrait")
        cdir = os.path.join(out_dir, "concepts")
        os.makedirs(cdir, exist_ok=True)
        items, files = [], []
        for i, lay in enumerate(layouts):
            letter = chr(65 + i)
            img, info = render(cp, sources, spec, brand, variants[0], lay, f"concept {letter}")
            path = os.path.join(cdir, f"{name}_concept-{letter}_{lay}.png")
            img.save(path)
            files.append({"concept": letter, "layout": lay, "file": path, **info})
            items.append((path, f"{letter} · {LAYOUT_LABELS[lay].upper()}\nlayout: {lay}"))
        p = PLACEMENTS[cp]
        sheet_path = os.path.join(out_dir, f"{name}_concepts.png")
        sheet(items, sheet_path, f"{name.replace('_', ' ')}: ad concepts",
              f"{p['label']} · {p['w']}×{p['h']} · pick one direction to apply to every size", thumb_h=560)
        print(json.dumps({"stage": "concepts", "concept_sheet": sheet_path, "concepts": files, "warnings": warnings}, indent=2))
        return

    # ---- final stage
    layout = spec.get("layout", "editorial")
    if mode == "ad" and layout not in LAYOUTS:
        sys.exit(f"Unknown layout '{layout}'. Valid: {LAYOUTS}")
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
            fname = f"{name}_{p['suffix']}{vt}.{ext}"
            save(img, os.path.join(out_dir, fname), pil_fmt, quality)
            entry = {"file": fname, "placement": key, "label": p["label"], "platform": p["platform"],
                     "width": p["w"], "height": p["h"], "variant": v["id"] if v else None,
                     "link": utm_link(spec.get("link"), p["platform"], campaign), **(info or {})}
            if v:
                entry.update({k: v.get(k) for k in ("headline", "emphasis", "subhead", "cta")})
            manifest["images"].append(entry)
            items.append((os.path.join(out_dir, fname), f"{p['suffix']}{vt}\n{p['w']}×{p['h']} · {info['fit'] if info else ''}"))
    if spec.get("post_content"):
        manifest["post_content"] = spec["post_content"]
    manifest["warnings"] = warnings
    mpath = os.path.join(out_dir, "manifest.json")
    if only and os.path.exists(mpath):  # merge re-rendered entries into the existing manifest
        with open(mpath) as f:
            old = json.load(f)
        done = {e["file"] for e in manifest["images"]}
        merged = {e["file"]: e for e in old["images"]}
        merged.update({e["file"]: e for e in manifest["images"]})
        order = [e["file"] for e in old["images"]] + [f for f in done if f not in {e["file"] for e in old["images"]}]
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
    print(json.dumps({"stage": "final", "output_dir": out_dir, "files": [e["file"] for e in manifest["images"]],
                      "contact_sheet": sheet_path if items else None, "warnings": warnings}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
