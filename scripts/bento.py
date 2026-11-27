#!/usr/bin/env python3
"""Génère la grille « bento » du profil GitHub (dist/bento.svg).

Données réelles via l'API GraphQL de GitHub (variable GITHUB_TOKEN).
`python scripts/bento.py --sample` produit un aperçu avec des données fictives.
"""
import base64
import datetime as dt
import json
import math
import os
import sys
import urllib.request
from html import escape

LOGIN = os.environ.get("PROFILE_LOGIN", "Armandodino")
OUT = os.environ.get("BENTO_OUT", "dist/bento.svg")

# ── Contenu éditable ──────────────────────────────────────────────
DISPLAY_NAME = "Armandodino"
ROLE = "Développeur Full-Stack"
TAGLINE = "Je conçois des produits web modernes, rapides et utiles."
STATUS = "Disponible pour de nouveaux projets"
FOCUS_TITLE = "En ce moment"
FOCUS_LINES = ["Plateformes e-commerce,", "outils de gestion &", "applications éducatives."]
LANGUAGES = ["Python", "TypeScript", "JavaScript", "Java", "PHP", "SQL"]
STACK = ["React", "Next.js", "Node.js", "Express", "Tailwind CSS",
         "PostgreSQL", "MySQL", "Git", "Vercel"]

# ── Design ────────────────────────────────────────────────────────
W = 1200
GAP = 16
SANS = "'Inter','Segoe UI Variable Display','Segoe UI',system-ui,-apple-system,Roboto,Helvetica,Arial,sans-serif"
MONO = "'JetBrains Mono','Cascadia Code',Consolas,'SFMono-Regular',Menlo,monospace"
ACCENT = "#8B5CF6"
LANG_COLORS = ["#8B5CF6", "#22D3EE", "#F472B6", "#FBBF24", "#34D399", "#64748B"]
HEAT = ["#16161D", "#2E1065", "#5B21B6", "#7C3AED", "#A78BFA"]


def gql(query, variables):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "bento-profile"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if payload.get("errors"):
        raise SystemExit(f"GraphQL: {payload['errors']}")
    return payload["data"]


QUERY = """
query($login:String!){
  user(login:$login){
    avatarUrl(size:320)
    followers{totalCount}
    repositories(ownerAffiliations:OWNER, privacy:PUBLIC, isFork:false, first:100){
      totalCount
      nodes{ stargazerCount
        languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } }
    }
    contributionsCollection{ contributionCalendar{ totalContributions
      weeks{ contributionDays{ date contributionCount } } } }
  }
}"""


def fetch_real():
    u = gql(QUERY, {"login": LOGIN})["user"]
    langs = {}
    stars = 0
    for repo in u["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    req = urllib.request.Request(u["avatarUrl"], headers={"User-Agent": "bento-profile"})
    with urllib.request.urlopen(req, timeout=30) as r:
        mime = r.headers.get_content_type() or "image/png"
        avatar = f"data:{mime};base64," + base64.b64encode(r.read()).decode()
    return {"repos": u["repositories"]["totalCount"], "followers": u["followers"]["totalCount"],
            "stars": stars, "langs": langs, "days": days, "total": cal["totalContributions"],
            "avatar": avatar}


def fetch_sample():
    import random
    random.seed(7)
    start = dt.date.today() - dt.timedelta(days=370)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    days = []
    d = start
    while d <= dt.date.today():
        days.append((d.isoformat(), random.choice([0, 0, 0, 1, 2, 3, 5, 8, 12])))
        d += dt.timedelta(days=1)
    return {"repos": 16, "followers": 0, "stars": 0, "days": days,
            "total": sum(c for _, c in days), "avatar": None,
            "langs": {"TypeScript": 900, "JavaScript": 300, "HTML": 150, "CSS": 120, "Shell": 20, "PLpgSQL": 10}}


def streaks(days):
    today = dt.date.today().isoformat()
    longest = cur = 0
    for _, c in days:
        cur = cur + 1 if c else 0
        longest = max(longest, cur)
    current = 0
    for date, c in reversed(days):
        if date > today:
            continue
        if c:
            current += 1
        elif date == today:
            continue  # la journée n'est pas finie
        else:
            break
    return current, longest


# ── Primitives SVG ────────────────────────────────────────────────
def tile(x, y, w, h, extra=""):
    return (f'<g transform="translate({x} {y})">'
            f'<rect width="{w}" height="{h}" rx="22" fill="url(#tileBg)"/>'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="21.5" fill="none" stroke="url(#tileStroke)"/>'
            f'{extra}</g>')


def label(x, y, text, color="#71717A"):
    return (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="11.5" font-weight="600" '
            f'letter-spacing="2.2" fill="{color}">{escape(text.upper())}</text>')


def wrap(text, width):
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + ([cur] if cur else [])


def fmt(n):
    return f"{n:,}".replace(",", " ")


def kpi(x, y, w, h, title, value, caption, spark=None, accent="#A78BFA"):
    inner = label(26, 38, title)
    inner += (f'<text x="24" y="{h-48}" font-family="{SANS}" font-size="50" font-weight="700" '
              f'letter-spacing="-1.5" fill="#FAFAFA">{escape(value)}</text>')
    inner += (f'<text x="26" y="{h-22}" font-family="{SANS}" font-size="14" fill="#A1A1AA">'
              f'{escape(caption)}</text>')
    inner += f'<circle cx="{w-30}" cy="34" r="4" fill="{accent}"/><circle cx="{w-30}" cy="34" r="9" fill="{accent}" opacity=".18"/>'
    if spark:
        sw, sh = w * 0.46, 46
        ox, oy = w - sw - 24, h - 34 - sh
        mx = max(spark) or 1
        pts = [(ox + i * sw / (len(spark) - 1), oy + sh - v / mx * sh) for i, v in enumerate(spark)]
        line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        area = f"M{pts[0][0]:.1f},{oy+sh} L" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + f" L{pts[-1][0]:.1f},{oy+sh} Z"
        inner += f'<path d="{area}" fill="url(#sparkFill)"/>'
        inner += f'<polyline points="{line}" fill="none" stroke="{accent}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        inner += f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3.5" fill="#FAFAFA"/>'
    return tile(x, y, w, h, inner)


def build(data):
    cur_streak, best_streak = streaks(data["days"])
    weekly = []
    for i in range(0, len(data["days"]), 7):
        weekly.append(sum(c for _, c in data["days"][i:i + 7]))
    langs = sorted(data["langs"].items(), key=lambda kv: -kv[1])
    total_bytes = sum(v for _, v in langs) or 1
    top = langs[:5]
    other = total_bytes - sum(v for _, v in top)
    if other > 0:
        top.append(("Autres", other))

    col_l = 584
    col_r = W - col_l - GAP
    out = []
    y = 0

    # ── Rangée 1 : profil + KPI ────────────────────────────────
    h1 = 312
    av = (f'<image href="{data["avatar"]}" x="34" y="44" width="132" height="132" '
          f'clip-path="url(#avClip)" preserveAspectRatio="xMidYMid slice"/>'
          if data["avatar"] else '<circle cx="100" cy="110" r="66" fill="#27272A"/>')
    prof = (
        '<rect width="584" height="312" rx="22" fill="url(#glow)" opacity=".9"/>'
        '<g transform="translate(100 110)"><circle r="74" fill="none" stroke="url(#ring)" stroke-width="2.5" '
        'stroke-dasharray="300 165" stroke-linecap="round">'
        '<animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="14s" repeatCount="indefinite"/>'
        '</circle></g>'
        f'{av}'
        f'<text x="200" y="96" font-family="{SANS}" font-size="38" font-weight="700" letter-spacing="-1" fill="#FAFAFA">{escape(DISPLAY_NAME)}</text>'
        f'<text x="201" y="128" font-family="{SANS}" font-size="18" font-weight="500" fill="url(#roleGrad)">{escape(ROLE)}</text>'
        + "".join(f'<text x="201" y="{160 + i*21}" font-family="{SANS}" font-size="14.5" fill="#A1A1AA">{escape(l)}</text>' for i, l in enumerate(wrap(TAGLINE, 42))) +
        '<g transform="translate(34 226)">'
        '<rect width="330" height="40" rx="20" fill="#052E1B" fill-opacity=".55" stroke="#22C55E" stroke-opacity=".35"/>'
        '<circle cx="22" cy="20" r="4.5" fill="#22C55E"/>'
        '<circle cx="22" cy="20" r="4.5" fill="#22C55E"><animate attributeName="r" values="4.5;11;4.5" dur="2.2s" repeatCount="indefinite"/>'
        '<animate attributeName="opacity" values=".6;0;.6" dur="2.2s" repeatCount="indefinite"/></circle>'
        f'<text x="40" y="25.5" font-family="{SANS}" font-size="14" font-weight="500" fill="#BBF7D0">{escape(STATUS)}</text></g>'
        f'<text x="550" y="282" text-anchor="end" font-family="{MONO}" font-size="12" fill="#52525B">github.com/{LOGIN}</text>'
    )
    out.append(tile(0, y, col_l, h1, prof))

    kw = (col_r - GAP) / 2
    kh = (h1 - GAP) / 2
    x0 = col_l + GAP
    out.append(kpi(x0, y, col_r, kh, "Contributions · 12 mois", fmt(data["total"]),
                   "sur la dernière année", spark=weekly[-26:]))
    out.append(kpi(x0, y + kh + GAP, kw, kh, "Série actuelle", f"{cur_streak} j",
                   f"record : {best_streak} jours", accent="#F472B6"))
    out.append(kpi(x0 + kw + GAP, y + kh + GAP, kw, kh, "Dépôts publics", str(data["repos"]),
                   f"{data['stars']} étoiles · {data['followers']} abonnés", accent="#22D3EE"))
    y += h1 + GAP

    # ── Rangée 2 : calendrier + langages ───────────────────────
    h2 = 214
    hw = 776
    days = data["days"][-53 * 7:]
    cell, gap = 10.5, 3
    grid_w = 53 * (cell + gap)
    gx = (hw - grid_w) / 2
    gy = 88
    mx = max((c for _, c in days), default=0) or 1
    cells = []
    months = []
    last_month = None
    for i, (date, c) in enumerate(days):
        col, row = divmod(i, 7)
        lvl = 0 if c == 0 else min(4, 1 + int(3 * c / mx + 0.0001))
        cells.append(f'<rect x="{gx + col*(cell+gap):.1f}" y="{gy + row*(cell+gap):.1f}" width="{cell}" height="{cell}" rx="2.6" fill="{HEAT[lvl]}"/>')
        m = date[5:7]
        if row == 0 and m != last_month:
            last_month = m
            if col < 51:
                name = ["janv", "févr", "mars", "avr", "mai", "juin", "juil", "août", "sept", "oct", "nov", "déc"][int(m) - 1]
                months.append(f'<text x="{gx + col*(cell+gap):.1f}" y="{gy-12}" font-family="{SANS}" font-size="11.5" fill="#71717A">{name}</text>')
    lx = hw - 28 - 34 - 5 * 14
    legend = "".join(f'<rect x="{lx+i*14}" y="34" width="10.5" height="10.5" rx="2.6" fill="{c}"/>' for i, c in enumerate(HEAT))
    heat = (label(28, 44, "Activité") +
            f'<text x="{lx-8}" y="43" text-anchor="end" font-family="{SANS}" font-size="12" fill="#71717A">moins</text>'
            + legend +
            f'<text x="{hw-28}" y="43" text-anchor="end" font-family="{SANS}" font-size="12" fill="#71717A">plus</text>'
            + "".join(months) + "".join(cells))
    out.append(tile(0, y, hw, h2, heat))

    lw = W - hw - GAP
    pw = (lw - 56 - 12) / 2
    chips = []
    for i, name in enumerate(LANGUAGES[:6]):
        cx = 28 + (i % 2) * (pw + 12)
        cy = 70 + (i // 2) * 44
        c = LANG_COLORS[i]
        chips.append(f'<g transform="translate({cx:.1f} {cy})">'
                     f'<rect width="{pw:.1f}" height="36" rx="11" fill="{c}" fill-opacity=".07" stroke="{c}" stroke-opacity=".35"/>'
                     f'<circle cx="20" cy="18" r="5" fill="{c}"/>'
                     f'<text x="36" y="23.5" font-family="{SANS}" font-size="15.5" font-weight="600" fill="#F4F4F5">{escape(name)}</text></g>')
    out.append(tile(hw + GAP, y, lw, h2, label(28, 44, "Langages") + "".join(chips)))
    y += h2 + GAP

    # ── Rangée 3 : stack + focus ───────────────────────────────
    h3 = 176
    sw = 776
    px, py = 28, 76
    pills = []
    for t in STACK:
        tw = len(t) * 8.4 + 34
        if px + tw > sw - 28:
            px, py = 28, py + 44
        pills.append(f'<g transform="translate({px:.1f} {py})"><rect width="{tw:.1f}" height="34" rx="10" fill="#FFFFFF" fill-opacity=".035" stroke="#FFFFFF" stroke-opacity=".09"/>'
                     f'<text x="{tw/2:.1f}" y="22" text-anchor="middle" font-family="{SANS}" font-size="14" font-weight="500" fill="#D4D4D8">{escape(t)}</text></g>')
        px += tw + 10
    out.append(tile(0, y, sw, h3, label(28, 44, "Stack") + "".join(pills)))

    fw = W - sw - GAP
    focus = label(28, 44, FOCUS_TITLE)
    for i, line in enumerate(FOCUS_LINES):
        focus += (f'<text x="28" y="{86 + i*30}" font-family="{SANS}" font-size="22" font-weight="600" '
                  f'letter-spacing="-.4" fill="{"url(#roleGrad)" if i == len(FOCUS_LINES)-1 else "#FAFAFA"}">{escape(line)}</text>')
    out.append(tile(sw + GAP, y, fw, h3, focus))
    y += h3

    updated = dt.date.today().strftime("%d/%m/%Y")
    foot = (f'<text x="{W/2}" y="{y+34}" text-anchor="middle" font-family="{MONO}" font-size="11.5" '
            f'letter-spacing="1.5" fill="#71717A">MIS À JOUR AUTOMATIQUEMENT · {updated}</text>')
    H = y + 48

    defs = f'''<defs>
<linearGradient id="tileBg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#141418"/><stop offset="1" stop-color="#0C0C0F"/></linearGradient>
<linearGradient id="tileStroke" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".14"/><stop offset="1" stop-color="#FFFFFF" stop-opacity=".04"/></linearGradient>
<radialGradient id="glow" cx="0.12" cy="0.1" r="0.9"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".30"/><stop offset=".55" stop-color="{ACCENT}" stop-opacity=".04"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>
<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22D3EE"/><stop offset=".5" stop-color="#8B5CF6"/><stop offset="1" stop-color="#F472B6"/></linearGradient>
<linearGradient id="roleGrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#C4B5FD"/><stop offset="1" stop-color="#F9A8D4"/></linearGradient>
<linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#A78BFA" stop-opacity=".35"/><stop offset="1" stop-color="#A78BFA" stop-opacity="0"/></linearGradient>
<clipPath id="avClip"><circle cx="100" cy="110" r="66"/></clipPath>
</defs>'''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'role="img" aria-label="Profil de {escape(DISPLAY_NAME)}">{defs}{"".join(out)}{foot}</svg>')


def main():
    data = fetch_sample() if "--sample" in sys.argv else fetch_real()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(data))
    print(f"OK → {OUT}")


if __name__ == "__main__":
    main()
