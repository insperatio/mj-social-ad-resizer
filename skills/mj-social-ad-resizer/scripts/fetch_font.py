#!/usr/bin/env python3
"""
Download a Google Font family (upright and italic) for the brand profile.

Usage:
    python3 fetch_font.py "Vollkorn" OUT_DIR

Looks in the google/fonts GitHub repo (ofl/, apache/, ufl/). Prints JSON:
{"ok": true, "files": [{"path", "italic", "variable", "weights"}]}
or {"ok": false, "reason": ...}. Variable fonts are used in brand.json as
{"path": ..., "variation": "Bold"}. If this fails (no network, or not a
Google Font), use the bundled Inter or ask the user for the font files.
"""
import json
import os
import sys
import urllib.request
from urllib.parse import quote

RAW = "https://raw.githubusercontent.com/google/fonts/main/{lic}/{slug}/{file}"
API = "https://api.github.com/repos/google/fonts/contents/{lic}/{slug}"


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "mj-social-ad-resizer"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read()
    return data if binary else data.decode()


def describe(path, name):
    weights = []
    try:
        from PIL import ImageFont
        weights = [n.decode() if isinstance(n, bytes) else n
                   for n in ImageFont.truetype(path, 20).get_variation_names()]
    except Exception:
        pass
    return {"path": path, "italic": "Italic" in name, "variable": "[" in name, "weights": weights}


def main(family, out_dir):
    slug = family.lower().replace(" ", "")
    camel = family.replace(" ", "")
    os.makedirs(out_dir, exist_ok=True)
    guesses = []
    for axes in ("wght", "opsz,wght", "wdth,wght"):
        guesses += [f"{camel}[{axes}].ttf", f"{camel}-Italic[{axes}].ttf"]
    guesses += [f"{camel}-Regular.ttf", f"{camel}-Bold.ttf", f"{camel}-Italic.ttf"]
    for lic in ("ofl", "apache", "ufl"):
        names = []
        try:
            listing = json.loads(get(API.format(lic=lic, slug=slug)))
            ttf = [i["name"] for i in listing if i["name"].endswith(".ttf")]
            var = [n for n in ttf if "[" in n]
            names = var or [n for n in ttf if any(w in n for w in ("Regular", "Bold", "Italic", "SemiBold"))][:6]
        except Exception:
            names = guesses
        files = []
        for name in names:
            try:
                data = get(RAW.format(lic=lic, slug=slug, file=quote(name)), binary=True)
            except Exception:
                continue
            if len(data) < 1000:
                continue
            path = os.path.join(out_dir, name.replace("[", "_").replace("]", "").replace(",", "_"))
            with open(path, "wb") as f:
                f.write(data)
            files.append(describe(path, name))
        if files:
            print(json.dumps({"ok": True, "family": family, "license": lic.upper(), "files": files}, indent=1))
            return
    print(json.dumps({"ok": False, "family": family,
                      "reason": "Not found on Google Fonts or no network access. Use the bundled Inter or ask the user for the font files."}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
