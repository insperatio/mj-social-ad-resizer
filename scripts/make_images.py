#!/usr/bin/env python3
"""
Social image kit: turn a supplied photo into sized social images.

Usage:
    python3 make_images.py spec.json

Reads a JSON spec (see references/spec.md), writes one image per
placement (and per A/B variant), a contact sheet and manifest.json
into spec["output_dir"]. Prints a JSON summary with warnings.
"""
import json
import os
import sys
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")
DEFAULT_HEADING = os.path.join(FONT_DIR, "Inter-Bold.otf")
DEFAULT_BODY = os.path.join(FONT_DIR, "Inter-Regular.otf")
DEFAULT_CTA = os.path.join(FONT_DIR, "Inter-SemiBold.otf")

# Placement presets. safe = fraction of height to keep clear of text
# at top/bottom (platform UI overlays).
PLACEMENTS = {
    "meta_square":   {"w": 1080, "h": 1080, "platform": "meta",      "suffix": "IG-1x1",  "label": "Meta feed 1:1",         "safe_top": 0.0,  "safe_bottom": 0.0},
    "meta_portrait": {"w": 1080, "h": 1350, "platform": "meta",      "suffix": "IG-4x5",  "label": "Meta feed 4:5",         "safe_top": 0.0,  "safe_bottom": 0.0},
    "meta_story":    {"w": 1080, "h": 1920, "platform": "meta",      "suffix": "STORY",   "label": "Meta Stories/Reels 9:16","safe_top": 0.14, "safe_bottom": 0.20},
    "pinterest":     {"w": 1000, "h": 1500, "platform": "pinterest", "suffix": "PT",      "label": "Pinterest pin 2:3",     "safe_top": 0.0,  "safe_bottom": 0.0},
    "link_preview":  {"w": 1200, "h": 630,  "platform": "link",      "suffix": "FB",      "label": "Link preview 1.91:1 (Facebook, X, LinkedIn)", "safe_top": 0.0, "safe_bottom": 0.0},
    "linkedin_square": {"w": 1200, "h": 1200, "platform": "linkedin", "suffix": "LI-1x1", "label": "LinkedIn feed 1:1",     "safe_top": 0.0,  "safe_bottom": 0.0},
    "x_post":        {"w": 1600, "h": 900,  "platform": "x",         "suffix": "X",       "label": "X in-feed image 16:9",  "safe_top": 0.0,  "safe_bottom": 0.0},
}

UTM_SOURCE = {"meta": "facebook", "pinterest": "pinterest", "link": "social",
              "linkedin": "linkedin", "x": "x"}

FORMATS = {"webp": ("WEBP", "webp"), "png": ("PNG", "png"),
           "jpg": ("JPEG", "jpg"), "jpeg": ("JPEG", "jpg")}

warnings = []


# ---------- color helpers ----------
def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rel_lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = rel_lum(a), rel_lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def best_text_on(bg):
    return (255, 255, 255) if contrast((255, 255, 255), bg) >= contrast((17, 17, 17), bg) else (17, 17, 17)


# ---------- image helpers ----------
def load_image(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def pick_source(sources, target_ratio):
    """Pick the supplied photo whose aspect ratio is closest to the target."""
    best, best_d = None, None
    for key, s in sources.items():
        r = s["img"].width / s["img"].height
        d = abs((r / target_ratio) - 1) if r >= target_ratio else abs((target_ratio / r) - 1)
        if best_d is None or d < best_d:
            best, best_d = key, d
    return best


def cover_crop(img, w, h, focus):
    """Scale to cover w x h and crop around focus (fx, fy in 0..1)."""
    scale = max(w / img.width, h / img.height)
    nw, nh = round(img.width * scale), round(img.height * scale)
    resized = img.resize((nw, nh), Image.LANCZOS)
    fx, fy = focus
    left = min(max(round(fx * nw - w / 2), 0), nw - w)
    top = min(max(round(fy * nh - h / 2), 0), nh - h)
    return resized.crop((left, top, left + w, top + h)), scale


def contain_on_fill(img, w, h, fill, color):
    """Fit whole image inside w x h over a blurred copy or a solid color."""
    if fill == "blur":
        bg, _ = cover_crop(img, w, h, (0.5, 0.5))
        bg = bg.filter(ImageFilter.GaussianBlur(radius=max(w, h) // 30))
        bg = Image.blend(bg, Image.new("RGB", (w, h), (0, 0, 0)), 0.25)
    else:
        bg = Image.new("RGB", (w, h), color)
    scale = min(w / img.width, h / img.height)
    nw, nh = round(img.width * scale), round(img.height * scale)
    fg = img.resize((nw, nh), Image.LANCZOS)
    bg.paste(fg, ((w - nw) // 2, (h - nh) // 2))
    return bg, scale


def fill_photo(img, w, h, focus, fill_mode, fill_color, max_loss):
    """Choose cover crop unless it would cut away too much of the photo."""
    src_r, tgt_r = img.width / img.height, w / h
    kept = min(src_r, tgt_r) / max(src_r, tgt_r)  # fraction of photo kept by cover crop
    if fill_mode == "crop" or (fill_mode == "auto" and (1 - kept) <= max_loss):
        return cover_crop(img, w, h, focus), "crop", kept
    style = "blur" if fill_mode in ("auto", "blur") else "color"
    return contain_on_fill(img, w, h, style, fill_color), style, kept


# ---------- text helpers ----------
def font(path, size):
    return ImageFont.truetype(path, size)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def fit_text(draw, text, font_path, max_w, max_lines, start, minimum):
    size = start
    while size >= minimum:
        f = font(font_path, size)
        lines = wrap(draw, text, f, max_w)
        if len(lines) <= max_lines and all(draw.textlength(l, font=f) <= max_w for l in lines):
            return f, lines, size
        size -= 2
    f = font(font_path, minimum)
    return f, wrap(draw, text, f, max_w)[:max_lines], minimum


def text_block_height(fnt, lines, spacing):
    asc, desc = fnt.getmetrics()
    return len(lines) * (asc + desc) + max(0, len(lines) - 1) * spacing


def draw_lines(draw, x, y, lines, fnt, fill, spacing, align, box_w):
    asc, desc = fnt.getmetrics()
    for line in lines:
        lw = draw.textlength(line, font=fnt)
        lx = x + (box_w - lw) / 2 if align == "center" else x
        draw.text((lx, y), line, font=fnt, fill=fill)
        y += asc + desc + spacing
    return y


# ---------- layout ----------
def band_ratio(p, mode):
    if mode != "ad":
        return 0.0
    w, h = p["w"], p["h"]
    r = w / h
    if r >= 1.5:
        return 0.42   # wide: band on the right side (handled as side layout)
    if r <= 0.6:
        return 0.26   # stories (band grows upward past the safe zone)
    if r <= 0.7:
        return 0.32   # pins
    if r <= 0.85:
        return 0.34   # 4:5
    return 0.38       # square


def render(placement_key, p, sources, spec, variant):
    W, H = p["w"], p["h"]
    brand = spec.get("brand", {})
    primary = hex_to_rgb(brand.get("primary", "#111111"))
    text_color = hex_to_rgb(brand["on_primary"]) if brand.get("on_primary") else best_text_on(primary)
    heading_font = brand.get("font_heading") or DEFAULT_HEADING
    body_font = brand.get("font_body") or DEFAULT_BODY
    cta_font = brand.get("font_cta") or brand.get("font_heading") or DEFAULT_CTA
    mode = spec.get("mode", "plain")
    fill_mode = spec.get("fill", "auto")
    max_loss = spec.get("max_crop_loss", 0.45)
    fill_color = primary

    canvas = Image.new("RGB", (W, H), primary)
    br = band_ratio(p, mode)
    side = mode == "ad" and W / H >= 1.5

    if side:
        band_w = round(W * br)
        photo_box = (0, 0, W - band_w, H)
    else:
        band_h = round(H * br)
        photo_box = (0, 0, W, H - band_h)

    pw, ph = photo_box[2] - photo_box[0], photo_box[3] - photo_box[1]
    src_key = pick_source(sources, pw / ph)  # match the photo area, not the whole canvas
    src = sources[src_key]
    focus = (src.get("focus", {}).get("x", 0.5), src.get("focus", {}).get("y", 0.5))
    (photo, scale), how, kept = fill_photo(src["img"], pw, ph, focus, fill_mode, fill_color, max_loss)
    canvas.paste(photo, (photo_box[0], photo_box[1]))

    info = {"source": src_key, "fit": how, "photo_kept_pct": round(kept * 100)}
    if scale > 1.05:
        warnings.append(f"{placement_key}{'_' + variant['id'] if variant else ''}: photo '{src_key}' upscaled {scale:.2f}x; supply a larger photo for a sharper result.")
        info["upscaled"] = round(scale, 2)

    draw = ImageDraw.Draw(canvas)

    if mode == "ad" and variant:
        pad = round(min(W, H) * 0.05)
        if side:
            bx0, by0, bx1, by1 = W - band_w, 0, W, H
        else:
            bx0, by0, bx1, by1 = 0, H - band_h, W, H
            # keep text out of platform UI zones (stories)
            safe_bottom = round(H * p["safe_bottom"])
            if safe_bottom:
                by1 = H - safe_bottom
                # extend band upward so text area keeps its height
                extra = safe_bottom
                by0 = max(H - band_h - extra, round(H * p["safe_top"]))
                draw.rectangle((0, by0, W, H), fill=primary)
                # repaint photo above band
                canvas.paste(photo.crop((0, 0, W, by0)), (0, 0))
                draw = ImageDraw.Draw(canvas)
        draw.rectangle((bx0, by0, bx1, H if not side else by1), fill=primary)

        box_x, box_y = bx0 + pad, by0 + pad
        box_w, box_h = (bx1 - bx0) - 2 * pad, (by1 - by0) - 2 * pad
        align = "left"

        hl = variant.get("headline", "")
        sub = variant.get("subhead", "")
        cta = variant.get("cta", "")
        base = min(W, H)

        hf, hlines, hsize = fit_text(draw, hl, heading_font, box_w, 3, round(base * 0.075), round(base * 0.04))
        sf, slines = (None, [])
        if sub:
            sf, slines, _ = fit_text(draw, sub, body_font, box_w, 2, max(round(hsize * 0.5), round(base * 0.03)), round(base * 0.026))
        cf = font(cta_font, max(round(hsize * 0.42), round(base * 0.03))) if cta else None

        gap = round(base * 0.02)
        cta_h = 0
        if cta:
            asc, desc = cf.getmetrics()
            cta_h = asc + desc + round(base * 0.03)
        total = text_block_height(hf, hlines, round(hsize * 0.15))
        if slines:
            total += gap + text_block_height(sf, slines, 4)
        if cta:
            total += gap * 2 + cta_h

        # shrink everything if it overflows the band
        tries = 0
        while total > box_h and tries < 10:
            hsize = max(round(hsize * 0.9), 16)
            hf = font(heading_font, hsize)
            hlines = wrap(draw, hl, hf, box_w)[:3]
            if sub:
                sf = font(body_font, max(round(hsize * 0.5), round(base * 0.026)))
                slines = wrap(draw, sub, sf, box_w)[:2]
            if cta:
                cf = font(cta_font, max(round(hsize * 0.42), round(base * 0.026)))
                asc, desc = cf.getmetrics()
                cta_h = asc + desc + round(base * 0.03)
            total = text_block_height(hf, hlines, round(hsize * 0.15))
            if slines:
                total += gap + text_block_height(sf, slines, 4)
            if cta:
                total += gap * 2 + cta_h
            tries += 1
        cut = " ".join(hlines) != " ".join(hl.split()) or (sub and " ".join(slines) != " ".join(sub.split()))
        if total > box_h or cut:
            warnings.append(f"{placement_key}_{variant['id']}: text is too long for this size; shorten the headline or subhead.")

        y = box_y + max(0, (box_h - total) // 2)
        y = draw_lines(draw, box_x, y, hlines, hf, text_color, round(hsize * 0.15), align, box_w)
        if slines:
            y += gap
            y = draw_lines(draw, box_x, y, slines, sf, text_color, 4, align, box_w)
        if cta:
            y += gap * 2
            pill_bg = hex_to_rgb(brand["accent"]) if brand.get("accent") else text_color
            pill_fg = hex_to_rgb(brand["on_accent"]) if brand.get("on_accent") else best_text_on(pill_bg)
            tw = draw.textlength(cta, font=cf)
            px, py = round(base * 0.03), round(base * 0.015)
            asc, desc = cf.getmetrics()
            draw.rounded_rectangle((box_x, y, box_x + tw + 2 * px, y + asc + desc + 2 * py),
                                   radius=(asc + desc + 2 * py) // 2, fill=pill_bg)
            draw.text((box_x + px, y + py), cta, font=cf, fill=pill_fg)
            c = contrast(pill_bg, pill_fg)
            if c < 4.5:
                warnings.append(f"CTA button contrast is {c:.1f}:1 (WCAG AA needs 4.5:1). Adjust accent/on_accent.")
            info["cta_contrast"] = round(c, 2)
            if contrast(pill_bg, primary) < 1.5:
                warnings.append("CTA button blends into the text band; pick an accent color that stands out from the primary color.")

        c = contrast(text_color, primary)
        info["text_contrast"] = round(c, 2)
        if c < 4.5:
            warnings.append(f"Text contrast is {c:.1f}:1 on the brand band (WCAG AA needs 4.5:1). Adjust primary/on_primary.")

    # logo
    logo_path = brand.get("logo")
    if logo_path:
        logo = Image.open(logo_path).convert("RGBA")
        lw = round(min(W, H) * brand.get("logo_scale", 0.16))
        lh = round(logo.height * lw / logo.width)
        logo = logo.resize((lw, lh), Image.LANCZOS)
        m = round(min(W, H) * 0.04)
        top = max(m, round(H * p["safe_top"]) + m) if p["safe_top"] else m
        pos = brand.get("logo_position", "top-left")
        x = m if "left" in pos else W - lw - m
        y = top if "top" in pos else H - lh - m - round(H * p["safe_bottom"])
        canvas.paste(logo, (x, y), logo)

    return canvas, info


def utm_link(link, platform, campaign):
    if not link:
        return None
    u = urlparse(link)
    q = dict(parse_qsl(u.query))
    q.update({"utm_source": UTM_SOURCE.get(platform, platform), "utm_medium": "social",
              "utm_campaign": campaign})
    return urlunparse(u._replace(query=urlencode(q)))


def contact_sheet(items, out_path, title):
    thumb_h = 360
    thumbs = []
    for path, label in items:
        im = Image.open(path).convert("RGB")
        tw = round(im.width * thumb_h / im.height)
        thumbs.append((im.resize((tw, thumb_h), Image.LANCZOS), label))
    pad, label_h, max_w = 24, 56, 2400
    rows, row, row_w = [], [], pad
    for t, l in thumbs:
        if row and row_w + t.width + pad > max_w:
            rows.append(row)
            row, row_w = [], pad
        row.append((t, l))
        row_w += t.width + pad
    if row:
        rows.append(row)
    sheet_w = max(sum(t.width + pad for t, _ in r) + pad for r in rows)
    sheet_h = 70 + len(rows) * (thumb_h + label_h + pad) + pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 245, 245))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 20), title, font=font(DEFAULT_HEADING, 28), fill=(20, 20, 20))
    lf = font(DEFAULT_BODY, 16)
    y = 70
    for r in rows:
        x = pad
        for t, l in r:
            sheet.paste(t, (x, y))
            d.rectangle((x - 1, y - 1, x + t.width, y + thumb_h), outline=(200, 200, 200))
            for i, part in enumerate(l.split("\n")):
                d.text((x, y + thumb_h + 6 + i * 22), part, font=lf, fill=(60, 60, 60))
            x += t.width + pad
        y += thumb_h + label_h + pad
    sheet.save(out_path)


def main(spec_path):
    with open(spec_path) as f:
        spec = json.load(f)

    name = spec.get("name", "Social").replace(" ", "_")
    out_dir = spec["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    fmt_key = spec.get("format", "webp").lower()
    pil_fmt, ext = FORMATS[fmt_key]
    quality = spec.get("quality", 85)

    sources = {}
    for key, val in spec["images"].items():
        entry = val if isinstance(val, dict) else {"path": val}
        entry["img"] = load_image(entry["path"])
        sources[key] = entry
    if not sources:
        sys.exit("At least one image is required.")

    keys = spec.get("placements") or list(PLACEMENTS)
    unknown = [k for k in keys if k not in PLACEMENTS]
    if unknown:
        sys.exit(f"Unknown placements: {unknown}. Valid: {list(PLACEMENTS)}")

    mode = spec.get("mode", "plain")
    variants = spec.get("variants") or []
    if mode == "ad" and not variants:
        sys.exit("Ad mode needs at least one variant with a headline.")
    if mode != "ad":
        variants = [None]

    only = set(spec.get("only", []))  # e.g. ["pinterest_B"] to redo a single file
    manifest = {"name": name, "mode": mode, "format": ext, "link": spec.get("link"), "images": []}
    sheet_items = []
    campaign = spec.get("campaign", name.lower())

    for key in keys:
        p = PLACEMENTS[key]
        for v in variants:
            tag = f"{key}_{v['id']}" if v and len(variants) > 1 else key
            if only and tag not in only and key not in only:
                continue
            img, info = render(key, p, sources, spec, v)
            suffix = p["suffix"] + (f"_{v['id']}" if v and len(variants) > 1 else "")
            fname = f"{name}_{suffix}.{ext}"
            path = os.path.join(out_dir, fname)
            save_kwargs = {"quality": quality} if pil_fmt in ("WEBP", "JPEG") else {"optimize": True}
            if pil_fmt == "WEBP":
                save_kwargs["method"] = 6
            img.save(path, pil_fmt, **save_kwargs)
            entry = {"file": fname, "placement": key, "label": p["label"], "platform": p["platform"],
                     "width": p["w"], "height": p["h"], "variant": v["id"] if v else None,
                     "link": utm_link(spec.get("link"), p["platform"], campaign), **info}
            if v:
                entry.update({k: v.get(k) for k in ("headline", "subhead", "cta")})
            manifest["images"].append(entry)
            sheet_items.append((path, f"{suffix}\n{p['w']}x{p['h']} · {info['fit']}"))

    if spec.get("post_content"):
        manifest["post_content"] = spec["post_content"]
    deduped = list(dict.fromkeys(warnings))
    warnings[:] = deduped
    manifest["warnings"] = warnings

    sheet_path = os.path.join(out_dir, f"{name}_contact-sheet.png")
    if sheet_items:
        contact_sheet(sheet_items, sheet_path, f"{name} — {len(sheet_items)} images")
    with open(os.path.join(out_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    print(json.dumps({"output_dir": out_dir, "files": [i["file"] for i in manifest["images"]],
                      "contact_sheet": sheet_path, "warnings": warnings}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
