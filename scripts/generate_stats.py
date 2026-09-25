#!/usr/bin/env python3
"""Genera assets/actividad.svg (panel de actividad animado) con la API GraphQL de GitHub."""
import base64
import json
import os
import sys
import urllib.request
from collections import defaultdict
from html import escape

USER = os.environ.get("GH_USER", "frannelfran")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT_PATH", "assets/actividad.svg")
FONTS = {400: "assets/jetbrains-mono-latin-400-normal.woff2", 700: "assets/jetbrains-mono-latin-700-normal.woff2"}
MOCK = os.environ.get("MOCK_JSON")

QUERY = """
query($login:String!){ user(login:$login){
  followers{totalCount}
  contributionsCollection{
    totalCommitContributions totalPullRequestContributions totalIssueContributions
    contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount date } } }
  }
  repositories(ownerAffiliations:OWNER,isFork:false,first:100){
    totalCount
    nodes{ stargazerCount languages(first:6,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name color } } } }
  }
}}"""


def fetch():
    if MOCK:
        return json.load(open(MOCK))["data"]["user"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-readme"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]["user"]


def font_css():
    css = []
    for w, path in FONTS.items():
        if os.path.exists(path):
            b64 = base64.b64encode(open(path, "rb").read()).decode()
            css.append(f"@font-face{{font-family:'JB';font-weight:{w};src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    return "\n".join(css)


def level(n, mx):
    if n == 0:
        return "#16283F"
    r = n / mx
    return "#1F4E79" if r < .25 else "#2F6DB5" if r < .5 else "#4C8FE0" if r < .75 else "#79B8FF"


def build(u):
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    langs = defaultdict(lambda: [0, "#8B9BB4"])
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]][0] += e["size"]
            langs[e["node"]["name"]][1] = e["node"]["color"] or "#8B9BB4"
    total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]

    tiles = [
        (cal["totalContributions"], "contribuciones · último año"),
        (cc["totalCommitContributions"], "commits"),
        (cc["totalPullRequestContributions"], "pull requests"),
        (stars, "estrellas recibidas"),
    ]
    W, H = 900, 412
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Actividad de {escape(USER)} en GitHub">']
    o.append("<defs><linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#0B1F3A'/><stop offset='1' stop-color='#0D1117'/></linearGradient>"
             "<clipPath id='lc'><rect x='40' y='196' width='820' height='14' rx='7'/></clipPath><style>")
    o.append(font_css())
    o.append("""
text{font-family:'JB','JetBrains Mono',ui-monospace,Menlo,Consolas,monospace}
.t{fill:#fff;font-size:18px;font-weight:700}.s{fill:#8B9BB4;font-size:12px}.n{fill:#79B8FF;font-size:30px;font-weight:700}
.l{fill:#C9D6E8;font-size:12px}
.up{opacity:0;transform:translateY(8px);animation:up .7s ease forwards}
.seg{transform-box:fill-box;transform-origin:left center;transform:scaleX(0);animation:gr 1.2s cubic-bezier(.22,.9,.3,1) .5s forwards}
.c{opacity:0;animation:up .5s ease forwards}
@keyframes up{to{opacity:1;transform:none}}@keyframes gr{to{transform:scaleX(1)}}
@media (prefers-reduced-motion:reduce){.up,.c{animation:none;opacity:1;transform:none}.seg{animation:none;transform:none}}
""")
    o.append("</style></defs>")
    o.append(f"<rect width='{W}' height='{H}' rx='10' fill='url(#bg)' stroke='#1F3350'/>")
    o.append(f"<text x='40' y='44' class='t'>Actividad en GitHub</text><text x='40' y='64' class='s'>@{escape(USER)} · {u['repositories']['totalCount']} repositorios · {u['followers']['totalCount']} seguidores</text>")
    # tiles
    for i, (v, lab) in enumerate(tiles):
        x = 40 + i * 205
        o.append(f"<g class='up' style='animation-delay:{.1*i:.1f}s'><text x='{x}' y='112' class='n'>{v:,}</text><text x='{x}' y='132' class='s'>{lab}</text></g>".replace(",", "."))
    # languages
    o.append("<text x='40' y='182' class='l'>Lenguajes</text>")
    o.append("<g clip-path='url(#lc)'>")
    x = 40.0
    for name, (sz, col) in top:
        w = 820 * sz / sum(v[0] for _, v in top)
        o.append(f"<rect class='seg' x='{x:.1f}' y='196' width='{w:.1f}' height='14' fill='{col}'/>")
        x += w
    o.append("</g>")
    x = 40
    for name, (sz, col) in top:
        pct = 100 * sz / total
        o.append(f"<g class='up' style='animation-delay:.9s'><circle cx='{x+5}' cy='230' r='5' fill='{col}'/><text x='{x+16}' y='234' class='l'>{escape(name)} {pct:.1f}%</text></g>")
        x += 170
    # heatmap (últimas 26 semanas)
    weeks = cal["weeks"][-26:]
    mx = max([d["contributionCount"] for w in weeks for d in w["contributionDays"]] + [1])
    o.append("<text x='40' y='274' class='l'>Contribuciones · últimas 26 semanas</text>")
    for wi, w in enumerate(weeks):
        for di, d in enumerate(w["contributionDays"]):
            o.append(f"<rect class='c' style='animation-delay:{1.0+wi*.03:.2f}s' x='{40+wi*31.5:.1f}' y='{288+di*15}' width='26' height='11' rx='3' fill='{level(d['contributionCount'], mx)}'><title>{d['date']}: {d['contributionCount']}</title></rect>")
    o.append("</svg>")
    return "\n".join(o)


def main():
    try:
        svg = build(fetch())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if svg != old:
        open(OUT, "w", encoding="utf-8").write(svg)
        print("actividad.svg actualizado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
