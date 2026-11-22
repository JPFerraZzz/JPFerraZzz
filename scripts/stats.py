"""Generate profile stat cards (SVG) from the GitHub API. Stdlib only.
Usage: GH_TOKEN=... python scripts/stats.py <login>"""
import json, math, os, sys, urllib.request, urllib.parse
from collections import Counter
from datetime import datetime

USER = sys.argv[1] if len(sys.argv) > 1 else "JPFerraZzz"
TOKEN = os.environ["GH_TOKEN"]
BG, BORDER, INK, INK2, AC = "#0e1314", "#1f2a26", "#eef3ef", "#aab6af", "#00ff9c"
F = "Helvetica,Arial,Liberation Sans,sans-serif"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets")


def api(path, data=None):
    req = urllib.request.Request("https://api.github.com" + path, data=data,
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json", "User-Agent": "profile-stats"})
    return json.load(urllib.request.urlopen(req))


def gql(q):
    return api("/graphql", json.dumps({"query": q}).encode())["data"]["user"]


u = gql('query{user(login:"%s"){pullRequests{totalCount} issues{totalCount} followers{totalCount}'
        ' contributionsCollection{totalCommitContributions contributionCalendar{totalContributions weeks{contributionDays{contributionCount date weekday}}}}}}' % USER) if False else None
data = api("/graphql", json.dumps({"query": 'query{user(login:"%s"){pullRequests{totalCount} issues{totalCount} followers{totalCount} contributionsCollection{totalCommitContributions contributionCalendar{totalContributions weeks{contributionDays{contributionCount date weekday}}}}}}' % USER}).encode())["data"]["user"]
repos = []
page = 1
while True:
    chunk = api(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
    repos += chunk
    if len(chunk) < 100: break
    page += 1
repos = [r for r in repos if not r["fork"]]
stars = sum(r["stargazers_count"] for r in repos)
merged = api("/search/issues?q=" + urllib.parse.quote(f"author:{USER} type:pr is:merged"))["total_count"]
langs = Counter()
for r in repos:
    for k, v in api(f"/repos/{USER}/{r['name']}/languages").items(): langs[k] += v
days = [d for w in data["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"]]


def svg(w, h, body): return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{F}"><rect width="{w}" height="{h}" rx="14" fill="{BG}" stroke="{BORDER}"/>{body}</svg>'
def title(t): return f'<text x="22" y="34" font-size="18" font-weight="700" fill="{AC}">{t}</text>'
def save(name, s): open(os.path.join(OUT, name), "w").write(s)

# 1 overview
items = [("Stars earned", stars), ("Commits (12 months)", data["contributionsCollection"]["totalCommitContributions"]),
         ("Pull requests", data["pullRequests"]["totalCount"]), ("PRs merged", merged),
         ("Issues", data["issues"]["totalCount"]), ("Public repos", len(repos))]
b = title("Overview")
for i, (lab, val) in enumerate(items):
    x = 22 + (i % 2) * 210; y = 74 + (i // 2) * 44
    b += f'<text x="{x}" y="{y}" font-size="28" font-weight="800" fill="{INK}">{val}</text><text x="{x}" y="{y+17}" font-size="13" fill="{INK2}">{lab}</text>'
save("stats-overview.svg", svg(440, 200, b))

# 2 languages
tot = sum(langs.values()) or 1
top = langs.most_common(6)
cols = ["#00ff9c", "#6df2b0", "#00b36b", "#0a7a4a", "#aab6af", "#5c6b63"]
cx, cy, r, sw = 108, 122, 50, 24
b = title("Most Used Languages"); a = -math.pi / 2; gap = math.radians(1.6)
shown = sum(v for _, v in top)
for i, (n, v) in enumerate(top):
    span = 2 * math.pi * v / shown; a1, a2 = a + gap / 2, a + span - gap / 2
    x1, y1, x2, y2 = cx + r * math.cos(a1), cy + r * math.sin(a1), cx + r * math.cos(a2), cy + r * math.sin(a2)
    b += f'<path d="M{x1:.2f} {y1:.2f} A{r} {r} 0 {1 if a2-a1>math.pi else 0} 1 {x2:.2f} {y2:.2f}" fill="none" stroke="{cols[i]}" stroke-width="{sw}"/>'
    a += span
for i, (n, v) in enumerate(top):
    y = 68 + i * 21.5
    b += f'<circle cx="214" cy="{y-5}" r="5.5" fill="{cols[i]}"/><text x="228" y="{y}" font-size="15" font-weight="600" fill="{INK}">{n}</text><text x="358" y="{y}" font-size="15" fill="{INK2}" text-anchor="end">{v/tot*100:.1f}%</text>'
save("languages-auto.svg", svg(380, 195, b))

# 3 weekday
names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
wd = [0] * 7
for d in days: wd[d["weekday"]] += d["contributionCount"]
mx = max(wd) or 1
b = title("Contributions by weekday")
for i, v in enumerate(wd):
    bw = 38; x = 24 + i * 58; hh = max(3, 100 * v / mx); y = 160 - hh
    b += f'<rect x="{x}" y="{y:.1f}" width="{bw}" height="{hh:.1f}" rx="6" fill="{AC if v==mx else "#0a7a4a"}"/><text x="{x+bw/2}" y="{y-6:.1f}" font-size="12" fill="{INK}" text-anchor="middle">{v}</text><text x="{x+bw/2}" y="182" font-size="13" fill="{INK2}" text-anchor="middle">{names[i]}</text>'
save("stats-weekday.svg", svg(440, 200, b))

# 4 months
m = Counter()
for d in days: m[d["date"][:7]] += d["contributionCount"]
keys = sorted(m)[-12:]; vals = [m[k] for k in keys]; mx = max(vals) or 1
b = title(f"Contributions per month · {sum(vals)} in the last year")
for i, (k, v) in enumerate(zip(keys, vals)):
    bw = 46; x = 22 + i * 70.5; hh = max(3, 100 * v / mx); y = 160 - hh
    b += f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="{hh:.1f}" rx="6" fill="{AC if v==mx else "#0a7a4a"}"/><text x="{x+bw/2:.1f}" y="{y-6:.1f}" font-size="12" fill="{INK}" text-anchor="middle">{v}</text><text x="{x+bw/2:.1f}" y="182" font-size="12" fill="{INK2}" text-anchor="middle">{datetime.strptime(k, "%Y-%m").strftime("%b")}</text>'
save("stats-months.svg", svg(900, 200, b))
print("ok", items, top[:3], wd)
