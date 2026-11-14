#!/usr/bin/env python3
"""Build the scorecard's data files from the real sources, for a LOCAL preview only.

Writes site/data/local/*.csv and site/config.local.json. Both are gitignored, and the deploy script refuses to
push them: this repository is public. The page reads config.local.json first when it exists, so
"Preview locally.command" shows real numbers on this Mac while GitHub Pages keeps showing the sample.

    python3 tools/build_local.py                       # defaults below: the sibling project folders
    python3 tools/build_local.py --sdp-json PATH       # add taprooms from a Store Director Portal payload

Sources, and what each one supplies
-----------------------------------
FEEDS (pulled by a system on a schedule)
  Sales Portal (VIP, refreshed daily on the Mac)
    Rolling Scorecard/Rolling Scorecard CLAUDE.csv   -> distribution_weekly.csv, distribution_ytd.csv
  Store Director Portal payload (Toast, MarginEdge, Tripleseat; nightly in GitHub Actions)
    `python -m sdp build --no-encrypt --dev-json` writes _site/data/dev.json; a decrypted "all" bundle has the
    same shape.                                       -> taproom_weekly.csv, guests_daily.csv

SPREADSHEET (typed into the Leadership Scorecard workbook; NOT a feed)
  Read from the Store Director Portal payload's `scorecard.tabs` when it carries them (the nightly pipeline
  already pulls every tab of the workbook), otherwise from CSV downloads of the tabs placed in
  inputs/private/sheet/ (File > Download > CSV, one file per tab, named after the tab):
    "2026 Leadership Scorecard"  -> reviews, brewery revenue + goal, weekly location goals, POD counts, growth goals
    "VMBG Targets"               -> holiday weekly goals and last season
    "Top Priorities"             -> full-year brand CE goals
  The leadership tab holds ONE week at a time, so each run files that week into
  inputs/private/sheet_history/*.csv and the page's history grows week by week from there.
  When no Store Director Portal payload is given, the sheet's revenue / food cost / labor rows stand in for the
  taproom feed (marked as sheet values in config.local.json -> "taproomSource").
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS = os.path.dirname(ROOT)
OUT = os.path.join(ROOT, "site", "data", "local")
PRIVATE = os.path.join(ROOT, "inputs", "private")
LOCATIONS = ["Solon", "Iowa City", "Des Moines", "Cedar Rapids", "Omaha", "Prairie Village"]


# ------------------------------------------------------------------------------------------------ helpers
def num(s):
    """'$(16,539)' -> -16539.0, '24.24%' -> 24.24, '(0.17)%' -> -0.17, '' -> None."""
    if s is None:
        return None
    t = str(s).strip().replace("$", "").replace(",", "").replace("%", "").strip()
    if not t or t in ("-", "—"):
        return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def write(name, header, rows):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name}: {len(rows)} rows")


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_from_label(label: str, today: date) -> date | None:
    """'11/2-11/8' -> the most recent date with that month/day that is not in the future."""
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})", label or "")
    if not m:
        return None
    mo, dy = int(m.group(1)), int(m.group(2))
    for y in (today.year, today.year - 1):
        d = date(y, mo, dy)
        if d <= today + timedelta(days=1):
            return d
    return None


# ------------------------------------------------------------------------------------------------ VIP (feed)
def vip(sales_portal: str, home="IA"):
    """Rolling Scorecard export: one row per distributor x brand x premise, a column per VIP week (Sun-Sat),
    then this-year-to-date, last-year-to-date, diff, pct."""
    path = os.path.join(sales_portal, "Rolling Scorecard", "Rolling Scorecard CLAUDE.csv")
    rows = [r for r in csv.reader(open(path, encoding="utf-8-sig")) if r and any(c.strip() for c in r)]
    head = rows[0]
    wk_cols, ty_col, ly_col, as_of = [], None, None, None
    for i, h in enumerate(head):
        m = re.match(r"\s*1 Week (\d+/\d+/\d{4}) thru (\d+/\d+/\d{4})", h)
        if m:
            wk_cols.append((i, datetime.strptime(m.group(1), "%m/%d/%Y").date(), datetime.strptime(m.group(2), "%m/%d/%Y").date()))
            continue
        m = re.match(r"\s*\d+ Weeks (\d+/\d+/\d{4}) thru (\d+/\d+/\d{4})", h)
        if m:
            end = datetime.strptime(m.group(2), "%m/%d/%Y").date()
            if ty_col is None:
                ty_col, as_of = i, end
            else:
                ly_col = i
    if ty_col is None or ly_col is None or not wk_cols:
        sys.exit(f"Rolling Scorecard header not recognised: {head[:4]} ... {head[-4:]}")
    weekly, ytd = defaultdict(float), defaultdict(lambda: [0.0, 0.0])
    for r in rows[1:]:
        dist, brand, prem = r[0].strip(), r[1].strip(), r[2].strip() or "NA"
        st = dist.rsplit(",", 1)[-1].strip().upper() if "," in dist else ""
        if not re.fullmatch(r"[A-Z]{2}", st):
            continue
        for i, ws, _ in wk_cols:
            v = num(r[i]) if i < len(r) else None
            if v:
                weekly[(ws.isoformat(), st, brand, prem)] += v
        ytd[(st, brand, prem)][0] += num(r[ty_col]) or 0
        ytd[(st, brand, prem)][1] += num(r[ly_col]) or 0
    # A partial final week is kept; the page leaves it out of the sparkline.
    write("distribution_weekly.csv", ["week_start", "state", "brand", "premise", "ce"],
          [[*k, round(v, 1)] for k, v in sorted(weekly.items()) if abs(v) >= 0.05])
    write("distribution_ytd.csv", ["as_of", "state", "brand", "premise", "ce_ytd", "ce_ytd_ly"],
          [[as_of.isoformat(), *k, round(a, 1), round(b, 1)] for k, (a, b) in sorted(ytd.items()) if a or b])
    ty = sum(a for a, _ in ytd.values()); ly = sum(b for _, b in ytd.values())
    ia = [v for k, v in ytd.items() if k[0] == home]; oth = [v for k, v in ytd.items() if k[0] != home]
    g = lambda vs: (sum(a for a, _ in vs) / sum(b for _, b in vs) - 1) * 100 if sum(b for _, b in vs) else float("nan")
    print(f"  VIP through {as_of}: {ty:,.0f} CEs YTD ({(ty / ly - 1) * 100:+.1f}% vs LY); {home} {g(ia):+.2f}%, outside {g(oth):+.2f}%")
    return as_of


# ------------------------------------------------------------------------------------------------ sheet (spreadsheet values)
def load_tabs(sdp_payload: dict | None) -> dict:
    tabs = {}
    for t in ((sdp_payload or {}).get("scorecard") or {}).get("tabs") or []:
        tabs[t["name"]] = t["grid"]
    d = os.path.join(PRIVATE, "sheet")
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if fn.lower().endswith(".csv"):
                name = re.sub(r"^.*? - ", "", fn[:-4]) if " - " in fn else fn[:-4]  # "Leadership Scorecard - VMBG Targets.csv"
                tabs.setdefault(name, list(csv.reader(open(os.path.join(d, fn), encoding="utf-8-sig"))))
    return tabs


def section(grid, title, labels):
    """Rows under the section whose first cell starts with `title`, keyed by first-cell label, until the next
    section title. Values are the row's cells (display strings), positions kept."""
    start = next((i for i, r in enumerate(grid) if r and str(r[0]).strip().lower().startswith(title.lower())), None)
    if start is None:
        return {}
    out = {}
    for r in grid[start + 1:]:
        first = str(r[0]).strip() if r else ""
        if first in labels:
            out[first] = [str(c) for c in r]
        elif first and first != "Location" and out:
            break
    return out


def cell(row, i):
    return num(row[i]) if row and i < len(row) else None


def leadership(grid, today):
    wk = week_from_label(str(grid[0][0]) if grid and grid[0] else "", today)
    if not wk:
        print("  ! 2026 Leadership Scorecard: no week label in A1 — skipped")
        return None
    ws = monday(wk).isoformat()
    rev = section(grid, "Revenue by Location", LOCATIONS + ["Brewery"])
    food = section(grid, "Food Cost by Location", LOCATIONS)
    lab = section(grid, "Direct Labor Cost by Location", LOCATIONS)
    rvw = section(grid, "Google Reviews by Location", LOCATIONS)
    grow = section(grid, "Total Case Volume Growth", ["In Iowa", "Outside of Iowa", "Total"])
    pods = section(grid, "Pod Count", ["In Iowa", "Outside of Iowa", "Total"])
    return {
        "week_start": ws,
        "taprooms": {l: {"net": cell(r, 1), "py": cell(r, 2), "goal": cell(r, 3), "food": cell(food.get(l), 1), "labor": cell(lab.get(l), 1)}
                     for l, r in rev.items() if l != "Brewery"},
        "brewery": {"net": cell(rev.get("Brewery"), 1), "py": cell(rev.get("Brewery"), 2), "goal": cell(rev.get("Brewery"), 3)},
        # Columns as the tab lays them out: score for the week, overall average, new reviews, last week's count, count.
        "reviews": {l: {"week": cell(r, 1), "overall": cell(r, 2), "new": cell(r, 3), "count": cell(r, 7)} for l, r in rvw.items()},
        "growth_goal": {k: cell(r, 3) for k, r in grow.items()},
        "growth_sheet": {k: cell(r, 2) for k, r in grow.items()},
        "pods": {k: (cell(r, 1), cell(r, 2)) for k, r in pods.items()},
    }


def vmbg(grid, season_start: date):
    """VMBG Targets: a 'week of' header row, then 2025 rows (last season) and 2026 rows (goal) per taproom. Each
    taproom's values are right-aligned to the season's last week (Solon and Iowa City start later)."""
    block, out = None, {}
    for r in grid:
        cells = [str(c).strip() for c in r]
        while cells and not cells[0]:
            cells = cells[1:]  # the year sits in column A of its block's first row only
        if not cells:
            continue
        if cells[0] in ("2025", "2026"):
            block = cells[0]
            cells = cells[1:]
        if cells and cells[0].lower().startswith("cumulative"):
            break
        if block and cells and cells[0] in LOCATIONS:
            vals = [num(c) for c in cells[1:] if num(c) is not None]
            out.setdefault(cells[0], {})[block] = vals
    res = []
    for loc, d in out.items():
        goal, ly = d.get("2026", []), d.get("2025", [])
        n = max(len(goal), len(ly))
        for k in range(n):
            wk = season_start + timedelta(weeks=8 - n + k)
            g = goal[k] if k < len(goal) else None
            l = ly[k] if k < len(ly) else None
            res.append([wk.isoformat(), loc, g if g is not None else "", l if l is not None else ""])
    return res


def brand_goals(grid):
    goals = []
    for r in grid:
        cells = [str(c).strip() for c in r]
        # "... | Citrus Surfer | 17,097 | (4.9)% | 91,250" — a brand name followed by YTD, growth, FY goal
        for i, c in enumerate(cells):
            if c and not num(c) and i + 3 < len(cells) and num(cells[i + 1]) and "%" in cells[i + 2] and (num(cells[i + 3]) or 0) > 1000:
                if c not in ("Total", "Iowa", "Outside Iowa"):
                    goals.append({"brand": c, "goal": num(cells[i + 3])})
    return goals


def file_history(name, header, key_cols, new_rows):
    """Merge this week's sheet rows into inputs/private/sheet_history/<name>, newest value wins per key."""
    d = os.path.join(PRIVATE, "sheet_history"); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    have = {}
    if os.path.exists(p):
        for r in list(csv.reader(open(p)))[1:]:
            have[tuple(r[i] for i in key_cols)] = r
    for r in new_rows:
        have[tuple(str(r[i]) for i in key_cols)] = [str(x) if x is not None else "" for x in r]
    rows = sorted(have.values())
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    return rows


# ------------------------------------------------------------------------------------------------ Store Director Portal (feed)
def taprooms_from_sdp(payload: dict, sheet_goals: dict):
    keys = payload["meta"]["daily_keys"]
    names = {l["id"]: l["name"] for l in payload["locations"]}
    weekly = defaultdict(lambda: defaultdict(float))
    guests_daily = []
    for lid, rows in payload["daily"].items():
        for row in rows:
            d = dict(zip(keys, row))
            day = date.fromisoformat(d["d"])
            w = weekly[(monday(day).isoformat(), lid)]
            for k in ("net", "f", "b", "lc", "p", "pf", "guests"):
                w[k] += d.get(k) or 0
            w["days"] += 1
            guests_daily.append([d["d"], names[lid], int(d.get("guests") or 0)])
    # events (Tripleseat): actual if settled, else booked total; lost/cancelled left out
    ev = defaultdict(float)
    for lid, rows in (payload.get("events") or {}).items():
        for e in rows:
            status = str(e[3] or "").lower()
            if any(s in status for s in ("lost", "cancel", "turned")):
                continue
            ev[(monday(date.fromisoformat(e[2][:10])).isoformat(), lid)] += float(e[6] or e[5] or 0)
    targets = payload.get("targets") or {}

    def goal_for(ws, lid):
        g = sheet_goals.get((ws, names[lid]))
        if g:
            return g
        tot = 0.0
        for i in range(7):  # monthly target spread evenly over the days of the month
            d = date.fromisoformat(ws) + timedelta(days=i)
            t = (targets.get(lid) or {}).get(d.strftime("%Y-%m"))
            if t and t[0]:
                nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
                tot += t[0] / (nxt - d.replace(day=1)).days
        return round(tot) or ""

    out = []
    for (ws, lid), w in sorted(weekly.items()):
        if w["days"] < 7 or not w["net"]:
            continue  # partial weeks at either end of the window
        ly = weekly.get(((date.fromisoformat(ws) - timedelta(days=364)).isoformat(), lid))
        net, food, beer, events = w["net"], w["f"], w["b"], ev.get((ws, lid), 0.0)
        out.append([ws, names[lid], round(net), round(ly["net"]) if ly and ly["days"] >= 7 else "", goal_for(ws, lid),
                    round(food), round(beer), round(events), round(max(0.0, net - food - beer - events)),
                    round(w["pf"] / food * 100, 1) if food and w["pf"] else "",
                    round(w["p"] / net * 100, 1) if w["p"] else "",
                    round(w["lc"] / net * 100, 1) if w["lc"] else "",
                    int(w["guests"]) if w["guests"] else ""])
    return out, guests_daily


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sales-portal", default=os.path.join(PROJECTS, "Big Grove Sales Portal"))
    ap.add_argument("--sdp-json", help="Store Director Portal payload (dev.json or a decrypted 'all' bundle)")
    ap.add_argument("--today", default=date.today().isoformat())
    a = ap.parse_args()
    today = date.fromisoformat(a.today)
    base = json.load(open(os.path.join(ROOT, "site", "config.json")))
    cfg = json.loads(json.dumps(base))
    if not a.sdp_json and os.path.exists(os.path.join(PRIVATE, "sdp_payload.json")):
        a.sdp_json = os.path.join(PRIVATE, "sdp_payload.json")   # written by tools/fetch_sdp.py
    payload = json.load(open(a.sdp_json)) if a.sdp_json else None
    print("Executive Scorecard — local build")

    # ---- VIP feed
    vip_asof = vip(a.sales_portal, cfg["targets"].get("homeState", "IA"))

    # ---- spreadsheet values
    tabs = load_tabs(payload)
    print(f"  sheet tabs found: {', '.join(sorted(tabs)) or 'none'}")
    L = leadership(tabs["2026 Leadership Scorecard"], today) if "2026 Leadership Scorecard" in tabs else None
    sheet_goals = {}
    if L:
        ws = L["week_start"]
        comp = file_history("company_weekly.csv", ["week_start", "brewery_distro_revenue", "brewery_distro_goal", "brewery_distro_py"], [0],
                            [[ws, L["brewery"]["net"], L["brewery"]["goal"], L["brewery"]["py"]]])
        rep = file_history("reputation_weekly.csv", ["week_start", "location", "rating_week", "rating", "new_reviews", "reviews"], [0, 1],
                           [[ws, l, v["week"], v["overall"], v["new"], v["count"]] for l, v in L["reviews"].items()])
        tsh = file_history("taproom_sheet.csv", ["week_start", "location", "net_sales", "net_sales_ly", "sales_goal", "food_cost_pct", "labor_pct"], [0, 1],
                           [[ws, l, v["net"], v["py"], v["goal"], v["food"], v["labor"]] for l, v in L["taprooms"].items()])
        sheet_goals = {(r[0], r[1]): num(r[4]) for r in tsh}
        write("company_weekly.csv", ["week_start", "brewery_distro_revenue", "brewery_distro_goal", "brewery_distro_py"], comp)
        write("reputation_weekly.csv", ["week_start", "location", "rating_week", "rating", "new_reviews", "reviews"], rep)
        pods = L["pods"]
        if pods.get("In Iowa") and pods.get("Outside of Iowa"):
            write("placements.csv", ["as_of", "state", "placements", "placements_ly"],
                  [[ws, "IA", *pods["In Iowa"]], [ws, "Outside IA", *pods["Outside of Iowa"]]])
        gg = L["growth_goal"]
        if gg.get("In Iowa") is not None: cfg["targets"]["inIowaGrowthPct"] = gg["In Iowa"]
        if gg.get("Outside of Iowa") is not None: cfg["targets"]["outsideIowaGrowthPct"] = gg["Outside of Iowa"]
        if L["growth_sheet"].get("In Iowa") is not None:
            print(f"  sheet growth (for comparison): In Iowa {L['growth_sheet']['In Iowa']}%, outside {L['growth_sheet'].get('Outside of Iowa')}%")
        # total weekly goal on the sheet = taprooms + brewery; prime-cost goal is not on the sheet, so it stays as configured
    else:
        print("  ! no '2026 Leadership Scorecard' tab — reviews, brewery revenue, goals and PODs left out")
    if "VMBG Targets" in tabs:
        vt = vmbg(tabs["VMBG Targets"], date.fromisoformat(cfg["holiday"]["start"]))
        write("vmbg_targets.csv", ["week_start", "location", "guests_goal", "guests_ly"], vt)
    if "Top Priorities" in tabs:
        bg = brand_goals(tabs["Top Priorities"])
        if bg:
            # The sheet says "Neighborhood"; VIP says "Neighborhood Beer". When a goal's name is not a VIP brand,
            # count the VIP brands that start with it, and list them so the match can be checked.
            vip_brands = {r[2] for r in csv.reader(open(os.path.join(OUT, "distribution_ytd.csv")))}
            for g in bg:
                if g["brand"] not in vip_brands:
                    g["match"] = sorted(v for v in vip_brands if v.lower().startswith(g["brand"].lower()))
                    print(f"  brand goal '{g['brand']}' counts VIP brands {g['match']}")
            cfg["brandGoals"] = bg

    # ---- taprooms: Store Director Portal feed, else the sheet's rows
    if payload:
        tap, gd = taprooms_from_sdp(payload, sheet_goals)
        cfg["taproomSource"] = "feed"
        write("guests_daily.csv", ["date", "location", "guests"], gd)
    else:
        tap = [[r[0], r[1], r[2], r[3], r[4], "", "", "", "", r[5], "", r[6], ""] for r in
               (list(csv.reader(open(os.path.join(PRIVATE, "sheet_history", "taproom_sheet.csv"))))[1:] if L else [])]
        cfg["taproomSource"] = "sheet"
        write("guests_daily.csv", ["date", "location", "guests"], [])
        print("  ! no Store Director Portal payload: taproom revenue, goal, food cost and labor come from the sheet;"
              " mix, COGS and guests stay empty")
    write("taproom_weekly.csv", ["week_start", "location", "net_sales", "net_sales_ly", "sales_goal", "food_sales", "beer_sales",
                                 "event_sales", "other_sales", "food_cost_pct", "cogs_pct", "labor_pct", "guests"], tap)

    cfg["dataSource"] = "local"
    cfg["dataLabel"] = (f"Local preview — VIP through {vip_asof:%b %-d}; taprooms from the "
                        f"{'Store Director Portal' if payload else 'Leadership Scorecard sheet'}; sheet items as last entered")
    cfg["updated"] = f"{today:%b %-d, %Y}"
    cfg["placementsLabel"] = "POD count (Leadership Scorecard sheet)"
    cfg["files"] = {k: v.replace("data/sample/", "data/local/") for k, v in base["files"].items()}
    for k, f in list(cfg["files"].items()):
        if not os.path.exists(os.path.join(ROOT, "site", f)):
            cfg["files"][k] = ""  # not built this run: the page shows that panel as pending
    json.dump(cfg, open(os.path.join(ROOT, "site", "config.local.json"), "w"), indent=2)
    print("  wrote site/config.local.json — double-click 'Preview locally.command' to view")


if __name__ == "__main__":
    main()
