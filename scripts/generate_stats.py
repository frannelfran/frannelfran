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
OUT_TROPHIES = os.environ.get("OUT_TROPHIES", "assets/trofeos.svg")
FONTS = {400: "assets/jetbrains-mono-latin-400-normal.woff2", 700: "assets/jetbrains-mono-latin-700-normal.woff2"}
MOCK = os.environ.get("MOCK_JSON")

QUERY = """
query($login:String!){ user(login:$login){
  createdAt followers{totalCount}
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


def streaks(days):
    days = sorted(days, key=lambda d: d["date"])
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] > 0 else 0
        best = max(best, run)
    cur = 0
    rev = list(reversed(days))
    if rev and rev[0]["contributionCount"] == 0:
        rev = rev[1:]  # hoy aún sin actividad no rompe la racha
    for d in rev:
        if d["contributionCount"] > 0:
            cur += 1
        else:
            break
    return cur, best


def smooth(pts):
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        mx = (x0 + x1) / 2
        d += f" C{mx:.1f},{y0:.1f} {mx:.1f},{y1:.1f} {x1:.1f},{y1:.1f}"
    return d


def build(u):
    import math
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    cur, best = streaks(days)
    weeks = cal["weeks"][-52:]
    totals = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    langs = defaultdict(lambda: [0, "#8B9BB4"])
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]][0] += e["size"]
            langs[e["node"]["name"]][1] = e["node"]["color"] or "#8B9BB4"
    total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:5]

    kpis = [
        (f"{cal['totalContributions']:,}".replace(",", "."), "contribuciones · año", "#4C8FE0"),
        (f"{cc['totalCommitContributions']:,}".replace(",", "."), "commits", "#5DA9C9"),
        (f"{cc['totalPullRequestContributions']:,}".replace(",", "."), "pull requests", "#8B7FD8"),
        (f"{cur} d", "racha actual", "#34B3A0"),
        (f"{best} d", "mejor racha", "#E0B341"),
    ]
    W, H = 900, 430
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Actividad de {escape(USER)} en GitHub">',
         "<defs><linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#0B1F3A'/><stop offset='1' stop-color='#0D1117'/></linearGradient>"
         "<linearGradient id='ar' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='#4C8FE0' stop-opacity='.45'/><stop offset='1' stop-color='#4C8FE0' stop-opacity='0'/></linearGradient><style>", font_css(),
         """text{font-family:'JB','JetBrains Mono',ui-monospace,Menlo,Consolas,monospace}
.t{fill:#fff;font-size:18px;font-weight:700}.s{fill:#8B9BB4;font-size:12px}.pt{fill:#C9D6E8;font-size:12px;font-weight:700}
.kv{font-size:22px;font-weight:700}.kl{fill:#8B9BB4;font-size:10.5px}.l{fill:#C9D6E8;font-size:11.5px}.ax{fill:#5F7391;font-size:10px}
.up{opacity:0;transform:translateY(8px);animation:up .7s ease forwards}
.ln{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 2s ease .5s forwards}
.fadein{opacity:0;animation:fi 1.2s ease 1.2s forwards}
.seg{opacity:0;animation:fi .8s ease forwards}
@keyframes up{to{opacity:1;transform:none}}@keyframes draw{to{stroke-dashoffset:0}}@keyframes fi{to{opacity:1}}
@media (prefers-reduced-motion:reduce){.up,.fadein,.seg{animation:none;opacity:1;transform:none}.ln{animation:none;stroke-dashoffset:0}}
</style></defs>"""]
    o.append(f"<rect width='{W}' height='{H}' rx='10' fill='url(#bg)' stroke='#1F3350'/>")
    o.append(f"<text x='40' y='44' class='t'>Actividad en GitHub</text><text x='40' y='64' class='s'>@{escape(USER)} · {u['repositories']['totalCount']} repositorios · {u['followers']['totalCount']} seguidores</text>")
    # KPIs
    kw, kg = 156, 10
    for i, (v, lab, c) in enumerate(kpis):
        x = 40 + i * (kw + kg)
        o.append(f"<g class='up' style='animation-delay:{.1*i:.1f}s'><rect x='{x}' y='84' width='{kw}' height='62' rx='8' fill='#0B1F3A' stroke='#1F3350'/>"
                 f"<rect x='{x}' y='84' width='3' height='62' rx='1.5' fill='{c}'/>"
                 f"<text x='{x+16}' y='114' class='kv' fill='{c}'>{v}</text><text x='{x+16}' y='134' class='kl'>{lab}</text></g>")
    # panel izquierdo: área semanal
    px, py, pw, ph = 40, 164, 540, 244
    o.append(f"<g class='up' style='animation-delay:.5s'><rect x='{px}' y='{py}' width='{pw}' height='{ph}' rx='8' fill='#0B1F3A' stroke='#1F3350'/>"
             f"<text x='{px+16}' y='{py+24}' class='pt'>Contribuciones por semana</text></g>")
    cx0, cx1, cy0, cy1 = px + 44, px + pw - 18, py + 48, py + ph - 34
    mx = max(totals + [1])
    top_v = math.ceil(mx / 5) * 5 or 5
    for k in range(4):
        gy = cy1 - (cy1 - cy0) * k / 3
        o.append(f"<line x1='{cx0}' y1='{gy:.1f}' x2='{cx1}' y2='{gy:.1f}' stroke='#1F3350' stroke-dasharray='3 4'/><text x='{cx0-8}' y='{gy+3:.1f}' text-anchor='end' class='ax'>{round(top_v*k/3)}</text>")
    pts = [(cx0 + (cx1 - cx0) * i / max(1, len(totals) - 1), cy1 - (cy1 - cy0) * v / top_v) for i, v in enumerate(totals)]
    line = smooth(pts)
    o.append(f"<path class='fadein' d='{line} L{pts[-1][0]:.1f},{cy1} L{pts[0][0]:.1f},{cy1} Z' fill='url(#ar)'/>")
    o.append(f"<path class='ln' pathLength='1' d='{line}' fill='none' stroke='#79B8FF' stroke-width='2.2' stroke-linecap='round'/>")
    im = totals.index(mx)
    o.append(f"<g class='fadein'><circle cx='{pts[im][0]:.1f}' cy='{pts[im][1]:.1f}' r='4.5' fill='#0D1117' stroke='#E0B341' stroke-width='2'/>"
             f"<text x='{min(max(pts[im][0], cx0+30), cx1-30):.1f}' y='{pts[im][1]-12:.1f}' text-anchor='middle' class='pt' fill='#E0B341' style='fill:#E0B341'>{mx}</text></g>")
    for idx in (0, len(weeks) // 2, len(weeks) - 1):
        o.append(f"<text x='{pts[idx][0]:.1f}' y='{cy1+20}' text-anchor='{'start' if idx == 0 else 'end' if idx == len(weeks)-1 else 'middle'}' class='ax'>{weeks[idx]['contributionDays'][0]['date'][:7]}</text>")
    # panel derecho: donut
    qx, qw = 600, 260
    o.append(f"<g class='up' style='animation-delay:.6s'><rect x='{qx}' y='{py}' width='{qw}' height='{ph}' rx='8' fill='#0B1F3A' stroke='#1F3350'/>"
             f"<text x='{qx+16}' y='{py+24}' class='pt'>Lenguajes</text></g>")
    dcx, dcy, r = qx + 66, py + 128, 44
    circ = 2 * math.pi * r
    stot = sum(v[0] for _, v in top)
    off = 0.0
    for i, (name, (sz, col)) in enumerate(top):
        seg = circ * sz / stot
        o.append(f"<circle class='seg' style='animation-delay:{.8+.15*i:.2f}s' cx='{dcx}' cy='{dcy}' r='{r}' fill='none' stroke='{col}' stroke-width='14' stroke-dasharray='{max(seg-2,0.5):.1f} {circ-max(seg-2,0.5):.1f}' stroke-dashoffset='{-off:.1f}' transform='rotate(-90 {dcx} {dcy})'/>")
        off += seg
    o.append(f"<text x='{dcx}' y='{dcy+5}' text-anchor='middle' class='pt'>{len(langs)}</text><text x='{dcx}' y='{dcy+19}' text-anchor='middle' class='ax'>lenguajes</text>")
    for i, (name, (sz, col)) in enumerate(top):
        ly = py + 76 + i * 30
        o.append(f"<g class='up' style='animation-delay:{1+.1*i:.1f}s'><circle cx='{qx+132}' cy='{ly}' r='4.5' fill='{col}'/>"
                 f"<text x='{qx+144}' y='{ly-2}' class='l'>{escape(name[:16])}</text><text x='{qx+144}' y='{ly+11}' class='ax'>{100*sz/total:.1f}%</text></g>")
    o.append("</svg>")
    return "\n".join(o)


TIERS = ["-", "C", "B", "A", "S", "SS"]
TCOL = ["#2A3D57", "#3B6EA5", "#4C8FE0", "#79B8FF", "#B6D4FF", "#E3B341"]


def tier(v, th):
    return sum(1 for t in th if v >= t)


ICONS = {
    "commit": '<circle cx="12" cy="12" r="4"/><path d="M2 12h6M16 12h6"/>',
    "pr": '<circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M6 8.5v7M18 15.5V10a4 4 0 0 0-4-4h-3M13 3l-3 3 3 3"/>',
    "star": '<polygon points="12,3 14.8,9 21,9.7 16.3,14 17.7,20.5 12,17.2 6.3,20.5 7.7,14 3,9.7 9.2,9"/>',
    "users": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M16 14.2c3 0 5 2 5 5"/>',
    "book": '<path d="M5 4h12a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2z"/><path d="M9 8h6M9 12h6"/>',
    "issue": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5" fill="currentColor"/>',
    "cal": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M8 3v4M16 3v4"/>',
}


def build_trophies(u):
    import datetime
    import math
    cc = u["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in u["repositories"]["nodes"])
    now = datetime.datetime.now(datetime.timezone.utc)
    years = max(0, (now - datetime.datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00"))).days // 365)
    items = [
        ("Commits", cc["totalCommitContributions"], [1, 50, 200, 500, 1000], "commit", "#4C8FE0"),
        ("Pull requests", cc["totalPullRequestContributions"], [1, 10, 30, 100, 300], "pr", "#8B7FD8"),
        ("Estrellas", stars, [1, 5, 20, 50, 200], "star", "#E0B341"),
        ("Seguidores", u["followers"]["totalCount"], [1, 10, 30, 100, 300], "users", "#34B3A0"),
        ("Repositorios", u["repositories"]["totalCount"], [1, 5, 15, 30, 60], "book", "#5DA9C9"),
        ("Issues", cc["totalIssueContributions"], [1, 5, 15, 40, 100], "issue", "#D9825B"),
        ("Años en GitHub", years, [1, 2, 3, 5, 8], "cal", "#9AA9C0"),
    ]
    W, H, cw, gap = 900, 210, 116, 8
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Trofeos de GitHub">', "<defs><style>", font_css(),
         """text{font-family:'JB','JetBrains Mono',ui-monospace,Menlo,Consolas,monospace;text-anchor:middle}
.v{fill:#fff;font-size:20px;font-weight:700}.k{fill:#8B9BB4;font-size:11px}.tl{font-size:13px;font-weight:700}
.card{opacity:0;transform:translateY(10px);animation:up .7s ease forwards}
.hex{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.3s ease .3s forwards}
.pg{transform-box:fill-box;transform-origin:left center;transform:scaleX(0);animation:gr 1.1s cubic-bezier(.22,.9,.3,1) .8s forwards}
@keyframes up{to{opacity:1;transform:none}}@keyframes draw{to{stroke-dashoffset:0}}@keyframes gr{to{transform:scaleX(1)}}
@media (prefers-reduced-motion:reduce){.card{animation:none;opacity:1;transform:none}.hex{animation:none;stroke-dashoffset:0}.pg{animation:none;transform:none}}
</style>"""]
    for i, (_, _, _, _, c) in enumerate(items):
        o.append(f"<linearGradient id='g{i}' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='{c}' stop-opacity='.40'/><stop offset='1' stop-color='#0D1117' stop-opacity='.95'/></linearGradient>")
    o.append("</defs>")
    o.append(f"<rect width='{W}' height='{H}' rx='10' fill='#0D1117' stroke='#1F3350'/>")
    for i, (name, val, th, icon, col) in enumerate(items):
        x = 20 + i * (cw + gap)
        cx, cy, r = x + cw / 2, 68, 34
        t = tier(val, th)
        tc = TCOL[t]
        pts = " ".join(f"{cx + r * math.cos(math.radians(-90 + 60 * k)):.1f},{cy + r * math.sin(math.radians(-90 + 60 * k)):.1f}" for k in range(6))
        frac = 1.0 if t >= len(th) else (val - (th[t - 1] if t else 0)) / (th[t] - (th[t - 1] if t else 0))
        frac = max(0.04, min(1.0, frac))
        o.append(
            f"<g class='card' style='animation-delay:{.12*i:.2f}s'>"
            f"<rect x='{x}' y='18' width='{cw}' height='176' rx='9' fill='#0B1F3A' stroke='#1F3350'/>"
            f"<rect x='{x}' y='18' width='{cw}' height='3' rx='1.5' fill='{col}' opacity='.8'/>"
            f"<polygon points='{pts}' fill='url(#g{i})' stroke='#16283F' stroke-width='2'/>"
            f"<polygon class='hex' pathLength='1' points='{pts}' fill='none' stroke='{col}' stroke-width='2.2' stroke-linejoin='round'/>"
            f"<g transform='translate({cx-13},{cy-13}) scale(1.08)' fill='none' stroke='#E6EEF9' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' color='#E6EEF9'>{ICONS[icon]}</g>"
            f"<rect x='{cx-16}' y='96' width='32' height='18' rx='9' fill='#0D1117' stroke='{tc}' stroke-width='1.5'/>"
            f"<text x='{cx}' y='109' class='tl' fill='{tc}'>{TIERS[t]}</text>"
            + f"<text x='{cx}' y='141' class='v'>{val:,}</text>".replace(",", ".")
            + f"<text x='{cx}' y='159' class='k'>{escape(name)}</text>"
            f"<rect x='{cx-38}' y='172' width='76' height='4' rx='2' fill='#16283F'/>"
            f"<rect class='pg' x='{cx-38}' y='172' width='{76*frac:.1f}' height='4' rx='2' fill='{col}'/></g>"
        )
    o.append("</svg>")
    return "\n".join(o)


def main():
    try:
        user = fetch()
        svg = build(user)
        tro = build_trophies(user)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if svg != old:
        open(OUT, "w", encoding="utf-8").write(svg)
        print("actividad.svg actualizado")
    old = open(OUT_TROPHIES, encoding="utf-8").read() if os.path.exists(OUT_TROPHIES) else ""
    if tro != old:
        open(OUT_TROPHIES, "w", encoding="utf-8").write(tro)
        print("trofeos.svg actualizado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
