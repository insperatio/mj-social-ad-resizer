#!/usr/bin/env python3
"""
Download a Google Font by family name for use in the brand profile.

Usage:
    python3 fetch_font.py "Playfair Display" OUT_DIR

Tries the google/fonts GitHub repo (ofl/, apache/, ufl/ folders), static
or variable files. Prints JSON: {"ok": true, "path": ..., "variable": bool,
"weights": [...]} or {"ok": false, "reason": ...}. If it fails (no network,
or the font isn't a Google Font), use the bundled Inter or ask the user to
upload the font files.
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


def main(family, out_dir):
    slug = family.lower().replace(" ", "")
    camel = family.replace(" ", "")
    os.makedirs(out_dir, exist_ok=True)
    candidates = []
    for lic in ("ofl", "apache", "ufl"):
        # 1) ask the GitHub API for the folder listing (may be rate limited)
        try:
            listing = json.loads(get(API.format(lic=lic, slug=slug)))
            names = [i["name"] for i in listing if i["name"].endswith(".ttf")]
            names.sort(key=lambda n: ("Italic" in n, "[" not in n))
            candidates += [(lic, n) for n in names]
            if names:
                break
        except Exception:
            pass
        # 2) guess common file names
        for n in (f"{camel}[wght].ttf", f"{camel}[opsz,wght].ttf", f"{camel}[wdth,wght].ttf",
                  f"{camel}-Bold.ttf", f"{camel}-Regular.ttf"):
            candidates.append((lic, n))
    for lic, name in candidates:
        try:
            data = get(RAW.format(lic=lic, slug=slug, file=quote(name)), binary=True)
        except Exception:
            continue
        if len(data) < 1000:
            continue
        path = os.path.join(out_dir, name.replace("[", "_").replace("]", "").replace(",", "_"))
        with open(path, "wb") as f:
            f.write(data)
        weights = []
        try:
            from PIL import ImageFont
            weights = [n.decode() if isinstance(n, bytes) else n for n in ImageFont.truetype(path, 20).get_variation_names()]
        except Exception:
            pass
        print(json.dumps({"ok": True, "family": family, "path": path, "variable": "[" in name,
                          "weights": weights, "license": lic.upper()}))
        return
    print(json.dumps({"ok": False, "family": family,
                      "reason": "Not found on Google Fonts or no network access. Use the bundled Inter or ask the user for the font files."}))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
