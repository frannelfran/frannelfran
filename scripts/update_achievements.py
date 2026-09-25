#!/usr/bin/env python3
"""Actualiza la sección de logros de GitHub del README leyendo el perfil público."""
import html
import os
import re
import sys
import urllib.request

USER = os.environ.get("GH_USER", "frannelfran")
README = os.environ.get("README_PATH", "README.md")
START, END = "<!--ACHIEVEMENTS:START-->", "<!--ACHIEVEMENTS:END-->"
URLS = [
    f"https://github.com/{USER}?tab=achievements",
    f"https://github.com/{USER}",
]
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
TIER_RE = re.compile(r"achievement-tier-label[^>]*>\s*(x\d+)", re.I)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (profile-readme-updater)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def attr(tag, name):
    m = re.search(rf'\b{name}="([^"]*)"', tag, re.I)
    return html.unescape(m.group(1)) if m else ""


def parse(page):
    found, seen = [], set()
    for m in IMG_RE.finditer(page):
        tag = m.group(0)
        alt = attr(tag, "alt")
        src = attr(tag, "src")
        is_badge = alt.lower().startswith("achievement:") or "achievement-badge" in attr(tag, "class")
        if not is_badge or not src:
            continue
        name = alt.split(":", 1)[1].strip() if ":" in alt else alt.strip()
        if src.startswith("/"):
            src = "https://github.com" + src
        if name in seen:
            continue
        seen.add(name)
        tier = TIER_RE.search(page[m.end(): m.end() + 800])
        found.append((name, src, tier.group(1) if tier else ""))
    return found


def render(items):
    cells = []
    for name, src, tier in items:
        label = f"{name} {tier}".strip()
        cells.append(
            f'<td align="center" width="130"><a href="https://github.com/{USER}?tab=achievements">'
            f'<img src="{src}" width="80" height="80" alt="{label}" title="{label}"/></a><br/>'
            f"<sub><b>{label}</b></sub></td>"
        )
    rows = [cells[i:i + 6] for i in range(0, len(cells), 6)]
    body = "\n".join("<tr>" + "".join(r) + "</tr>" for r in rows)
    return f'<div align="center">\n<table>\n{body}\n</table>\n</div>'


def main():
    items = []
    for url in URLS:
        try:
            items = parse(fetch(url))
        except Exception as exc:  # noqa: BLE001
            print(f"aviso: no se pudo leer {url}: {exc}", file=sys.stderr)
        if items:
            break
    if not items:
        print("No se encontraron logros; README sin cambios.")
        return 0

    text = open(README, encoding="utf-8").read()
    if START not in text or END not in text:
        print("Faltan los marcadores en el README.", file=sys.stderr)
        return 1
    pre, rest = text.split(START, 1)
    _, post = rest.split(END, 1)
    new = f"{pre}{START}\n{render(items)}\n{END}{post}"
    if new != text:
        open(README, "w", encoding="utf-8").write(new)
        print(f"README actualizado con {len(items)} logros.")
    else:
        print("Sin cambios.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
