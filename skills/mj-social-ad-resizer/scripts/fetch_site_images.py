#!/usr/bin/env python3
"""
Download candidate photos from the user's own website (when they have no photo).

Usage:
    python3 fetch_site_images.py https://example.com OUT_DIR [--max 6]

Collects og:image / twitter:image and the largest <img> / srcset images on the
page, downloads up to --max of them, and prints JSON with each file's path and
pixel size, largest first. Only use this on the user's own site.

If the page can't be reached from here (sandbox network limits, or a site built
with JavaScript), it prints {"ok": false, ...}. Then use a browser tool to open
the image URLs and capture them, or ask the user to download and attach photos.
"""
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

UA = {"User-Agent": "Mozilla/5.0 (mj-social-ad-resizer)"}


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []  # (url, hint_width, kind)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("property") in ("og:image", "og:image:url") or a.get("name") in ("twitter:image",)):
            if a.get("content"):
                self.found.append((a["content"], 2000, "og"))
        if tag in ("img", "source"):
            srcset = a.get("srcset") or a.get("data-srcset")
            if srcset:
                best = None
                for part in srcset.split(","):
                    bits = part.strip().split()
                    if not bits:
                        continue
                    w = int(re.sub(r"\D", "", bits[1]) or 0) if len(bits) > 1 and bits[1].endswith("w") else 0
                    if not best or w > best[1]:
                        best = (bits[0], w)
                if best:
                    self.found.append((best[0], best[1], "srcset"))
            src = a.get("src") or a.get("data-src")
            if src and not src.startswith("data:"):
                w = int(re.sub(r"\D", "", a.get("width", "") or "0") or 0)
                self.found.append((src, w, "img"))


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def main(url, out_dir, max_n=6):
    try:
        html = get(url)
    except Exception as e:
        print(json.dumps({"ok": False, "reason": f"Could not load {url} from here ({e.__class__.__name__}). "
                          "Open the page in a browser tool and capture its images, or ask the user to attach photos."}))
        return
    c = Collector()
    c.feed(html)
    seen, cands = set(), []
    for u, w, kind in c.found:
        full = urljoin(url, u)
        if full in seen or re.search(r"\.(svg|gif)(\?|$)", full, re.I) or re.search(r"(logo|icon|sprite|favicon|avatar)", full, re.I):
            continue
        seen.add(full)
        cands.append((full, w, kind))
    if not cands:
        print(json.dumps({"ok": False, "reason": "No images found in the page HTML (the site may load them with JavaScript). "
                          "Use a browser tool to list and capture the images, or ask the user for photos."}))
        return
    cands.sort(key=lambda c_: (c_[2] != "og", -c_[1]))
    os.makedirs(out_dir, exist_ok=True)
    files = []
    from PIL import Image
    for i, (u, _, kind) in enumerate(cands[: max_n * 2]):
        if len(files) >= max_n:
            break
        try:
            data = get(u, binary=True)
        except Exception:
            continue
        name = f"site_{i + 1:02d}_" + os.path.basename(urlparse(u).path)[-60:]
        path = os.path.join(out_dir, name)
        with open(path, "wb") as f:
            f.write(data)
        try:
            with Image.open(path) as im:
                w, h = im.size
        except Exception:
            os.remove(path)
            continue
        if min(w, h) < 300:
            os.remove(path)
            continue
        files.append({"path": path, "url": u, "width": w, "height": h, "source": kind})
    files.sort(key=lambda f_: -(f_["width"] * f_["height"]))
    print(json.dumps({"ok": bool(files), "files": files,
                      "reason": None if files else "Images were found but none could be downloaded at a usable size."}, indent=1))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n = 6
    if "--max" in sys.argv:
        n = int(sys.argv[sys.argv.index("--max") + 1])
        args = [a for a in args if a != str(n)]
    if len(args) != 2:
        sys.exit(__doc__)
    main(args[0], args[1], n)
