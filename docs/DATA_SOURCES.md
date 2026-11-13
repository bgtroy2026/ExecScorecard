# Executive Scorecard — where every number comes from

**Feed** = pulled by a system on a schedule. **Sheet** = typed into the *Leadership Scorecard* Google Sheet
(the "2026 Leadership Scorecard", "VMBG Targets" and "Top Priorities" tabs); it is only as current as its last edit.
The page labels every tile and panel with its source.

| Tier | Measure | Source | Kind | Notes |
|---|---|---|---|---|
| 1 | Taproom revenue (week) | Store Director Portal — Toast net sales | Feed | Nightly. Until the feed is wired here, the sheet's Revenue by Location stands in. |
| 1 | Brewery distro revenue, PY, goal | Sheet — "2026 Leadership Scorecard", Brewery row | **Sheet** | Could become a feed from Ekos invoices (the Sales Portal downloads them; history starts May 2026). |
| 1 | Revenue goals (taprooms, brewery, total) | Sheet — Revenue by Location, goal column | **Sheet** | Store Director Portal's `inputs/targets.csv` (monthly) is the fallback. |
| 1 | Prime cost %, COGS %, food cost %, labor % | Store Director Portal — Toast labor, MarginEdge purchases | Feed | MarginEdge is still provisional (purchases-based proxy). Prime = COGS + labor; when COGS is missing it falls back to food cost + labor, which is how the sheet adds it up. |
| 1 | YTD distribution volume, YoY, brand totals | Sales Portal — VIP *Rolling Scorecard CLAUDE.csv* | Feed | Daily on the Mac. Through Nov 12: 453,769 CEs YTD, +12.6% vs LY. |
| 1 | Brand full-year goals | Sheet — "Top Priorities" | **Sheet** | "Neighborhood" is matched to VIP's "Neighborhood Beer". |
| 1 | Google rating, reviews | Sheet — Google Reviews by Location | **Sheet** | Could become a feed through the Google Business Profile API. |
| 2 | Revenue vs goal by taproom | Toast (feed) + sheet goals | Feed + Sheet | |
| 2 | Revenue mix (food / beer / events / other) | Toast sales categories + Tripleseat events | Feed | Not in the sheet's leadership tab; shown as pending in sheet-only mode. |
| 2 | Efficiency quadrant | Toast labor + MarginEdge food purchases | Feed | |
| 2 | Guests, avg check | Toast guest counts | Feed | |
| 3 | In-Iowa / outside-Iowa YTD case growth | VIP Rolling Scorecard | Feed | The sheet shows +5.33% / +112.21%; VIP today gives +3.96% / +106.92%. Different period or report — confirm which leadership wants. |
| 3 | Growth goals (9.3%, 160%) | Sheet — Total Case Volume Growth | **Sheet** | |
| 3 | POD counts (in / outside Iowa, PY) | Sheet — Pod Count | **Sheet** | VIP "effective placements" (Yearly Distributor Data) is available as a feed but counts differently (28,012 YTD vs the sheet's 17,939). |
| 3 | Holiday pacing — goal and last season | Sheet — "VMBG Targets" (weekly, per taproom) | **Sheet** | |
| 3 | Holiday pacing — this season | Toast guests | Feed | Starts the week of Nov 9. |

## How the data reaches the page

```
Sales Portal (Mac, daily VIP refresh) ──────────────┐
Store Director Portal payload (Actions, nightly) ───┼─ tools/build_local.py ─► site/data/local/*.csv + site/config.local.json
Leadership Scorecard sheet ─────────────────────────┘     (gitignored; preview on this Mac only)
   └ via the Store Director Portal's nightly pull of every tab (payload.scorecard.tabs),
     or CSV downloads of the three tabs in inputs/private/sheet/
```

The leadership tab holds one week at a time, so each run files that week into `inputs/private/sheet_history/`
and the history grows from there.

## Things in the wireframe that the sources disagree with

- **YTD distribution 118,140 CEs, Easy Eddy 65,325, Citrus Surfer 17,097** come from the "Top Priorities" tab, which
  says *YTD thru 4/20/2026*. VIP through Nov 12 has 453,769 CEs, Easy Eddy 229,437, Citrus Surfer 61,215.
- **Holiday location goals.** The wireframe cards show Cedar Rapids 31,796, Iowa City 30,723, Solon 21,993. The VMBG
  Targets tab's weekly rows add up to 35,396, 27,723 and 21,393 (Des Moines 41,092 matches). Both versions total about 125.6k.
- **Direct labor 30.1%** on the wireframe is the company-wide labor line; the per-taproom rows average 22.5% weighted
  by sales. The page uses the per-taproom rows.
