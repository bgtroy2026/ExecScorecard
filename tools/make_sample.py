#!/usr/bin/env python3
"""Regenerate the sample data in site/data/sample/ (placeholders only, safe to commit).

    python3 tools/make_sample.py

Week 45 (Nov 2-8, 2026) is shaped like the leadership wireframe, but every figure is moved by a random 5-15%
so that nothing committed here matches a real result: the wireframe was filled from the Leadership Scorecard
workbook, and this repository is public. Every other week is generated around those figures with a fixed seed.
"""
from __future__ import annotations

import csv
import os
import random
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site", "data", "sample")
rnd = random.Random(2026)

# ---- week 45 figures from the wireframe ----------------------------------------------------------------
W45 = date(2026, 11, 2)  # ISO week 45, Monday
LOCS = {  # revenue, goal, food/beer/events mix %, food cost %, labor %, guests, rating, reviews
    "Prairie Village": (142711, 113866, (52, 25, 23), 25.3, 22.1, None, 4.8, 412),
    "Iowa City": (135907, 102223, (52, 22, 26), 20.0, 19.7, 5100, 5.0, 1606),
    "Des Moines": (110941, 106527, (55, 23, 22), 24.5, 23.2, 4068, 4.7, 1290),
    "Cedar Rapids": (89320, 82717, (57, 18, 25), 25.8, 20.6, 3071, 4.7, 945),
    "Omaha": (83794, 100333, (49, 20, 31), 26.3, 25.3, 3355, 4.6, 530),
    "Solon": (48845, 46129, (68, 17, 15), 24.2, 28.2, 2150, 4.3, 1120),
}
DISTRO_W45, DISTRO_GOAL_W45 = 106808, 251705


def _fuzz(v, lo=0.85, hi=1.15):
    return v if v is None else type(v)(round(v * _f.uniform(lo, hi), 1 if isinstance(v, float) else 0))


_f = random.Random(7)
LOCS = {k: (_fuzz(a), _fuzz(b), m, round(fc * _f.uniform(0.92, 1.08), 1), round(lb * _f.uniform(0.92, 1.08), 1), _fuzz(g),
            round(min(5.0, r - _f.choice((0, 0, 0.1))), 1), _fuzz(n)) for k, (a, b, m, fc, lb, g, r, n) in LOCS.items()}
DISTRO_W45, DISTRO_GOAL_W45 = _fuzz(DISTRO_W45), _fuzz(DISTRO_GOAL_W45)


def season(d: date) -> float:
    """Rough taproom seasonality: summer and December peaks, a January trough."""
    m = d.month + d.day / 31
    return 0.86 + 0.12 * max(0, 1 - abs(m - 7) / 3) + 0.10 * max(0, 1 - abs(m - 12.3) / 1.2) - 0.06 * max(0, 1 - abs(m - 1.5) / 1.5)


def write(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


def main():
    os.makedirs(OUT, exist_ok=True)
    weeks = [W45 - timedelta(weeks=k) for k in range(44, -1, -1)]  # ISO weeks 1..45 of 2026
    s45 = season(W45)

    tap, comp, rep = [], [], []
    for wk in weeks:
        pinned = wk == W45
        f = season(wk) / s45
        for loc, (rev, goal, mix, fc, lab, guests, rating, reviews) in LOCS.items():
            if loc == "Prairie Village" and wk < date(2026, 3, 2):
                continue  # opened in 2026: no history before March
            g = round(goal * f)
            net = rev if pinned else round(rev * f * rnd.uniform(0.86, 1.08))
            ly = None if loc == "Prairie Village" else round(net / rnd.uniform(1.02, 1.14))
            fm, bm, em = mix if pinned else (mix[0] + rnd.randint(-3, 3), mix[1] + rnd.randint(-2, 2), 0)
            em = em or 100 - fm - bm
            food, beer, events = (round(net * p / 100) for p in (fm, bm, em))
            other = max(0, net - food - beer - events)
            fcp = fc if pinned else round(fc + rnd.uniform(-1.6, 1.6), 1)
            lp = lab if pinned else round(lab + rnd.uniform(-2.0, 2.4), 1)
            cogs = round(fcp * 0.62 + 9.5 + rnd.uniform(-0.4, 0.4), 1)  # all-category cost runs a little above food alone
            gu = None if guests is None else (guests if pinned else round(guests * f * rnd.uniform(0.9, 1.08)))
            tap.append([wk.isoformat(), loc, net, ly if ly is not None else "", g, food, beer, events, other, fcp, cogs, lp,
                        gu if gu is not None else ""])
            r = rating if pinned else round(min(5.0, max(3.9, rating + rnd.uniform(-0.25, 0.15))), 1)
            new = rnd.randint(2, 25)
            rep.append([wk.isoformat(), loc, r, round(min(5.0, rating - 0.1 + rnd.uniform(-0.05, 0.05)), 1), new,
                        reviews - (45 - weeks.index(wk) - 1) * rnd.randint(2, 9)])
        dg = round(DISTRO_GOAL_W45 * rnd.uniform(0.85, 1.15)) if not pinned else DISTRO_GOAL_W45
        dv = DISTRO_W45 if pinned else round(dg * rnd.uniform(0.45, 1.1))
        comp.append([wk.isoformat(), dv, dg])

    write("taproom_weekly.csv", ["week_start", "location", "net_sales", "net_sales_ly", "sales_goal", "food_sales", "beer_sales",
                                 "event_sales", "other_sales", "food_cost_pct", "cogs_pct", "labor_pct", "guests"], tap)
    write("company_weekly.csv", ["week_start", "brewery_distro_revenue", "brewery_distro_goal"], comp)
    write("reputation_weekly.csv", ["week_start", "location", "rating_week", "rating", "new_reviews", "reviews"], rep)

    # ---- wholesale: VIP weeks run Sunday-Saturday ------------------------------------------------------
    states = {"IA": 0.80, "IL": 0.06, "NE": 0.045, "KS": 0.035, "WI": 0.03, "MN": 0.015, "MO": 0.01, "SD": 0.003, "ND": 0.002}
    growth = {"IA": 0.0533, "IL": 0.55, "NE": 0.45, "KS": 3.2, "WI": 4.0, "MN": 2.0, "MO": 1.5, "SD": 9.0, "ND": 9.0}
    brands = {"Easy Eddy": 61800, "Citrus Surfer": 18350, "Tigerhawk": 9800, "Neighborhood Beer": 6900, "Wild Eddy": 5400,
              "Royal Eddy": 4300, "Zero Eddy": 3900, "Seasonals": 5418}  # sums to 118,140 YTD
    as_of = date(2026, 11, 12)
    vip_weeks = [date(2025, 12, 28) + timedelta(weeks=k) for k in range(46)]
    wk_rows, ytd_rows = [], []
    for st, share in states.items():
        for br, ytd in brands.items():
            for prem, ps in (("OFF", 0.62), ("ON", 0.38)):
                total = ytd * share * ps
                wts = [season(w) * rnd.uniform(0.85, 1.15) * (5 / 7 if w == vip_weeks[-1] else 1) for w in vip_weeks]
                k = total / sum(wts)
                for w, x in zip(vip_weeks, wts):
                    wk_rows.append([w.isoformat(), st, br, prem, round(x * k, 1)])
                ly = total / (1 + growth[st]) if growth[st] < 8 else 0
                ytd_rows.append([as_of.isoformat(), st, br, prem, round(total, 1), round(ly, 1)])
    write("distribution_weekly.csv", ["week_start", "state", "brand", "premise", "ce"], wk_rows)
    write("distribution_ytd.csv", ["as_of", "state", "brand", "premise", "ce_ytd", "ce_ytd_ly"], ytd_rows)

    # Effective placements: 17,939 total (+23.5%), 4,038 outside Iowa (+62.8%)
    pods = [[as_of.isoformat(), "IA", 12850, round(12850 / 1.14)],
            [as_of.isoformat(), "IL", 1310, round(1310 / 1.45)], [as_of.isoformat(), "NE", 980, round(980 / 1.35)],
            [as_of.isoformat(), "WI", 760, 0 + 180], [as_of.isoformat(), "KS", 420, round(420 / 2.4)],
            [as_of.isoformat(), "MN", 250, 120], [as_of.isoformat(), "MO", 128, 40], [as_of.isoformat(), "SD", 40, 0],
            [as_of.isoformat(), "ND", 20, 0]]
    write("placements.csv", ["as_of", "state", "placements", "placements_ly"], pods)

    # ---- holiday pacing: weekly guest goal and last season's actual for the pop-up taprooms --------------
    # (shaped like the workbook's VMBG Targets tab, numbers moved; real ones come from the workbook)
    shape = {"Des Moines": [4.3, 3.4, 2.0, 3.2, 3.1, 4.0, 2.9, 4.4], "Cedar Rapids": [3.5, 2.7, 1.8, 2.5, 2.5, 3.4, 3.6, 3.8],
             "Solon": [0, 1.8, 1.5, 1.8, 1.8, 2.6, 1.9, 2.8], "Iowa City": [0, 0, 1.9, 2.9, 2.5, 3.7, 3.0, 4.5]}
    v_rows = []
    for loc, ks in shape.items():
        for i, k in enumerate(ks):
            if not k:
                continue
            ly = round(k * 1000 * rnd.uniform(0.85, 1.1))
            v_rows.append([(date(2026, 11, 9) + timedelta(weeks=i)).isoformat(), loc, round(ly * rnd.uniform(1.35, 1.6)), ly])
    write("vmbg_targets.csv", ["week_start", "location", "guests_goal", "guests_ly"], v_rows)
    write("guests_daily.csv", ["date", "location", "guests"], [])  # the holiday window has not started in the sample week

if __name__ == "__main__":
    main()
