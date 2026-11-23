#!/usr/bin/env python3
"""
Find and prepare a logo for the ads.

Usage:
    python3 prepare_logo.py from-url https://example.com OUT_DIR
        Look for the logo in the site's HTML (header/nav images and inline SVGs
        named or classed "logo", JSON-LD "logo", apple-touch-icon as a last
        resort), download the best candidate and prepare it.

    python3 prepare_logo.py prepare LOGO_FILE OUT_DIR [--bg auto|none|#RRGGBB]
        Prepare a logo the user uploaded, an SVG saved from the page, or a
        browser screenshot of the logo: converts SVG to PNG, removes a solid
        background (auto-detected from the corners) when there's no
        transparency, trims empty space, and makes a light version for dark
        backgrounds (or a dark one for light backgrounds) when the logo is a
        single color.

Prints JSON with the prepared files and how to use them in brand.json:
    "logo": the version for light backgrounds, "logo_on_dark": the version for dark ones.
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin

from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (mj-social-ad-resizer)"}


# ---------------------------------------------------------------- SVG
def svg_to_png(svg_path, png_path, width=1600):
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=width)
        return True
    except Exception:
        pass
    for cmd in (["rsvg-convert", "-w", str(width), "-o", png_path, svg_path],
                ["convert", "-background", "none", "-density", "300", svg_path, "-resize", f"{width}x", png_path],
                ["magick", "-background", "none", "-density", "300", svg_path, "-resize", f"{width}x", png_path]):
        try:
            if subprocess.run(cmd, capture_output=True, timeout=60).returncode == 0 and os.path.exists(png_path):
                return True
        except Exception:
            continue
    return False


# ---------------------------------------------------------------- image prep
def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def key_out_background(img, bg="auto", tol=28):
    """Make a solid background transparent. bg: 'auto' (from corners), 'none', or '#RRGGBB'."""
    img = img.convert("RGBA")
    if bg == "none":
        return img, None
    alpha = img.getchannel("A")
    if alpha.getextrema()[0] < 250 and bg == "auto":
        return img, None  # already has transparency
    if bg == "auto":
        w, h = img.size
        corners = [img.getpixel(p)[:3] for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
        # corners must agree, or it isn't a solid background
        ref = corners[0]
        if any(sum(abs(a - b) for a, b in zip(ref, c)) > tol * 2 for c in corners):
            return img, None
        key = ref
    else:
        h_ = bg.lstrip("#")
        key = tuple(int(h_[i:i + 2], 16) for i in (0, 2, 4))
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            d = abs(r - key[0]) + abs(g - key[1]) + abs(b - key[2])
            if d <= tol:
                px[x, y] = (r, g, b, 0)
            elif d <= tol * 3:  # soften anti-aliased edges
                px[x, y] = (r, g, b, int(a * (d - tol) / (tol * 2)))
    return img, "#%02X%02X%02X" % key


def trim(img, pad_ratio=0.02):
    bbox = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if not bbox:
        return img
    img = img.crop(bbox)
    pad = int(max(img.size) * pad_ratio)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.paste(img, (pad, pad))
    return out


def analyze(img):
    """Average color and luminance of the solid pixels; whether the logo is (nearly) one color."""
    import numpy as np
    small = img.copy()
    small.thumbnail((240, 240))
    arr = np.array(small.convert("RGBA")).reshape(-1, 4)
    solid = arr[arr[:, 3] > 230][:, :3].astype(int)
    if not len(solid):
        return None
    med = np.median(solid, axis=0)
    dist = np.abs(solid - med).sum(axis=1)
    single = float(np.percentile(dist, 90)) < 60
    avg = tuple(int(v) for v in solid.mean(axis=0))
    return {"avg": "#%02X%02X%02X" % avg, "luminance": round(lum(avg), 3), "single_color": single}


def recolor(img, color):
    out = Image.new("RGBA", img.size, color + (0,))
    out.putalpha(img.getchannel("A"))
    solid = Image.new("RGBA", img.size, color + (255,))
    solid.putalpha(img.getchannel("A"))
    return solid


def prepare(path, out_dir, bg="auto", source=None):
    os.makedirs(out_dir, exist_ok=True)
    work = path
    if path.lower().endswith(".svg") or open(path, "rb").read(200).lstrip().startswith((b"<svg", b"<?xml")):
        png = os.path.join(out_dir, "logo_source.png")
        if not svg_to_png(path, png):
            return {"ok": False, "reason": "Couldn't convert the SVG (no cairosvg, rsvg-convert or ImageMagick). "
                                           "Run `pip install cairosvg`, or ask the user for a PNG."}
        work = png
    img = Image.open(work)
    img.load()
    keyed, removed = key_out_background(img, bg)
    img = trim(keyed)
    if min(img.size) < 40:
        return {"ok": False, "reason": f"The logo is only {img.size[0]}×{img.size[1]} px after trimming. Ask the user for a larger file (SVG or a PNG at least 600 px wide)."}
    info = analyze(img)
    main = os.path.join(out_dir, "logo.png")
    img.save(main)
    result = {"ok": True, "source": source or path, "background_removed": removed, "size": list(img.size),
              "tone": info, "files": {}, "notes": []}
    if img.width < 400:
        result["notes"].append("Low resolution: the logo may look soft on large sizes. An SVG or larger PNG is better.")
    dark_logo = info and info["luminance"] < 0.35
    if dark_logo:
        result["files"]["logo"] = main
        if info["single_color"]:
            light = os.path.join(out_dir, "logo_on_dark.png")
            recolor(img, (255, 255, 255)).save(light)
            result["files"]["logo_on_dark"] = light
            result["notes"].append("Made a white version for dark backgrounds (single-color logo). Confirm the brand allows a reversed logo.")
        else:
            result["notes"].append("Multi-color dark logo: no automatic white version. Ask the user for a reversed logo for dark backgrounds, or keep the logo on light areas.")
    else:
        result["files"]["logo_on_dark"] = main
        if info and info["single_color"]:
            darkp = os.path.join(out_dir, "logo_on_light.png")
            recolor(img, (17, 17, 17)).save(darkp)
            result["files"]["logo"] = darkp
            result["notes"].append("Light logo: made a dark version for light backgrounds. Confirm the brand allows it.")
        else:
            result["notes"].append("Light, multi-color logo: works on dark backgrounds. Ask for a dark version for light backgrounds.")
    result["brand_json"] = {k: os.path.abspath(v) for k, v in result["files"].items()}
    return result


# ---------------------------------------------------------------- find on a site
class LogoFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cands = []      # (score, kind, value)
        self.depth_header = 0
        self.in_logo_link = 0
        self.svg_stack = None
        self.svg_score = 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        blob = " ".join([a.get("class", ""), a.get("id", ""), a.get("alt", ""), a.get("src", ""),
                         a.get("aria-label", ""), a.get("title", "")]).lower()
        if tag in ("header", "nav"):
            self.depth_header += 1
        if tag == "a" and ("logo" in blob or "brand" in blob or a.get("href") in ("/", "./", "#")):
            self.in_logo_link += 1
        if tag == "img":
            src = a.get("src") or a.get("data-src")
            if src:
                score = (5 if "logo" in blob else 0) + (2 if self.depth_header else 0) + (2 if self.in_logo_link else 0)
                if score:
                    self.cands.append((score, "url", src))
        if tag == "svg" and self.svg_stack is None:
            score = (5 if "logo" in blob else 0) + (2 if self.depth_header else 0) + (3 if self.in_logo_link else 0)
            if score >= 3:
                self.svg_stack = [self.get_starttag_text()]
                self.svg_score = score
                return
        if self.svg_stack is not None:
            self.svg_stack.append(self.get_starttag_text())
        if tag == "link" and "icon" in a.get("rel", "") and a.get("href"):
            self.cands.append((1 if "apple-touch" in a.get("rel", "") else 0, "url", a["href"]))
        if tag == "meta" and a.get("property") == "og:logo" and a.get("content"):
            self.cands.append((6, "url", a["content"]))

    def handle_startendtag(self, tag, attrs):
        if self.svg_stack is not None:
            self.svg_stack.append(self.get_starttag_text())
        else:
            self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self.svg_stack is not None:
            self.svg_stack.append(data)
        m = re.search(r'"logo"\s*:\s*(?:\{[^}]*"url"\s*:\s*)?"([^"]+)"', data)
        if m:
            self.cands.append((7, "url", m.group(1)))

    def handle_endtag(self, tag):
        if self.svg_stack is not None:
            self.svg_stack.append(f"</{tag}>")
            if tag == "svg":
                svg = "".join(self.svg_stack)
                if "xmlns" not in svg:
                    svg = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
                self.cands.append((self.svg_score, "svg", svg))
                self.svg_stack = None
            return
        if tag in ("header", "nav") and self.depth_header:
            self.depth_header -= 1
        if tag == "a" and self.in_logo_link:
            self.in_logo_link -= 1


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def from_url(url, out_dir):
    try:
        html = get(url)
    except Exception as e:
        return {"ok": False, "reason": f"Couldn't load {url} from here ({e.__class__.__name__}). Use the browser steps in "
                                       "SKILL.md to find the logo, or ask the user to upload it."}
    f = LogoFinder()
    f.feed(html)
    if not f.cands:
        return {"ok": False, "reason": "No logo found in the page HTML (it may be added by JavaScript). Use the browser steps, or ask the user to upload it."}
    os.makedirs(out_dir, exist_ok=True)
    for score, kind, val in sorted(f.cands, key=lambda c: -c[0]):
        try:
            if kind == "svg":
                path = os.path.join(out_dir, "logo_download.svg")
                with open(path, "w") as fh:
                    fh.write(val)
                src = "inline SVG"
            else:
                full = urljoin(url, val)
                data = get(full, binary=True)
                ext = ".svg" if full.lower().split("?")[0].endswith(".svg") or data.lstrip()[:5] in (b"<svg ", b"<?xml") else ".img"
                path = os.path.join(out_dir, "logo_download" + ext)
                with open(path, "wb") as fh:
                    fh.write(data)
                src = full
            res = prepare(path, out_dir, source=src)
            if res.get("ok"):
                res["confidence"] = "high" if score >= 5 else ("medium" if score >= 2 else "low (site icon)")
                return res
        except Exception:
            continue
    return {"ok": False, "reason": "Logo candidates were found but none could be downloaded or prepared. Ask the user to upload it."}


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 3 and args[0] == "from-url":
        print(json.dumps(from_url(args[1], args[2]), indent=1))
    elif len(args) >= 3 and args[0] == "prepare":
        bg = args[args.index("--bg") + 1] if "--bg" in args else "auto"
        print(json.dumps(prepare(args[1], args[2], bg), indent=1))
    else:
        sys.exit(__doc__)
