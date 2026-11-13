# Big Grove Brewery — Executive Scorecard

A leadership roll-up of the **Store Director Portal** (taprooms: Toast + MarginEdge) and the
**Depletion Dashboard** (wholesale: VIP). It's a static site on GitHub Pages, deployed the same way as the
StorePortal and Sales Portal.

- Repo: https://github.com/bgtroy2026/ExecScorecard
- Site: https://bgtroy2026.github.io/ExecScorecard/

> **Status: three-tier layout with sample data on the public site; real numbers in the local preview only.**

## Everyday use

| Do this | How |
|---|---|
| Preview on this Mac | Double-click **Preview locally.command** → opens http://localhost:8010 |
| Publish changes | Double-click **Deploy ExecScorecard.command** (commits, pushes; Pages updates in ~1 min) |
| See real numbers (this Mac only) | `python3 tools/build_local.py`, then Preview locally |
| Change placeholder targets | Edit `targets` in `site/config.json` (real goals come from the sheet into `config.local.json`) |

The first deploy creates the GitHub repo, turns on Pages and initializes git in this folder, using the
token already in your Keychain (`BigGrovePortalDeploy`). That token needs the `repo` and `workflow` scopes.

## Layout

| Path | What it is |
|---|---|
| `site/index.html` | The scorecard (single file; Chart.js and Jost font vendored, same brand tokens as StorePortal) |
| `site/config.json` | Data source label, file paths, targets |
| `site/data/sample/*.csv` | Sample inputs (the only data allowed in git) |
| `tools/build_local.py` | Real sources → `site/data/local/` + `site/config.local.json` (gitignored) |
| `tools/make_sample.py` | Regenerates the sample |
| `inputs/private/` | Sheet tab CSVs and sheet history (gitignored) |
| `docs/DATA_SOURCES.md` | Every measure, its source, Feed vs Sheet |
| `.github/workflows/pages.yml` | Publishes `site/` to GitHub Pages on every push to `main` |
| `_deploy/deploy.sh` | What the Deploy .command runs |
| `docs/ROADMAP.md` | What's next: live feeds, access, refresh |

## Layout of the page

Three tiers, laid out like the leadership wireframe on the Google Site, in the portal's own look:

1. **Executive Pulse** — total weekly revenue (taprooms + brewery vs goal), taproom prime cost %, YTD distribution
   volume with brand goals, Google reputation. Each tile has a 12-week sparkline.
2. **Location Performance Matrix** — revenue vs goal, revenue mix, prime-cost quadrant, guest traffic & avg check.
   The Location picker highlights one taproom across all four.
3. **Growth Engines & Q4 Initiatives** — in/outside-Iowa case growth vs goal, POD counts, holiday (VMBG) guest pacing.

Every tile and panel is labelled **Feed** or **Sheet**. See `docs/DATA_SOURCES.md` for the full map.

## Data contract (site/data/sample/ shows the shape)

| File | Grain | Columns |
|---|---|---|
| `taproom_weekly.csv` | ISO week (Mon) × taproom | week_start, location, net_sales, net_sales_ly, sales_goal, food_sales, beer_sales, event_sales, other_sales, food_cost_pct, cogs_pct, labor_pct, guests |
| `company_weekly.csv` | week | week_start, brewery_distro_revenue, brewery_distro_goal (, brewery_distro_py) |
| `reputation_weekly.csv` | week × taproom | week_start, location, rating_week, rating, new_reviews, reviews |
| `distribution_weekly.csv` | VIP week (Sun) × state × brand × premise | week_start, state, brand, premise, ce |
| `distribution_ytd.csv` | state × brand × premise | as_of, state, brand, premise, ce_ytd, ce_ytd_ly |
| `placements.csv` | state (or group) | as_of, state, placements, placements_ly |
| `vmbg_targets.csv` | holiday week × taproom | week_start, location, guests_goal, guests_ly |
| `guests_daily.csv` | day × taproom | date, location, guests |

Blank cells are fine: the page shows that panel as pending rather than as zero.

## Real numbers on this Mac (local preview)

```bash
python3 tools/build_local.py                    # VIP from the Sales Portal + the sheet tabs in inputs/private/sheet/
python3 tools/build_local.py --sdp-json PATH    # add taprooms from a Store Director Portal payload (dev.json)
```

It writes `site/data/local/` and `site/config.local.json`; the page reads `config.local.json` first, so
**Preview locally.command** shows real numbers here while GitHub Pages keeps the sample. Both are gitignored, and the
deploy script refuses to push them (checked before and after staging). `tools/make_sample.py` regenerates the
sample, with every figure moved 5–15% off the real week so nothing real is committed.

## Before real numbers go in

The repo is public (GitHub Pages on the free plan requires it), so **real data must not be committed in
plaintext.** `.gitignore` and the deploy script both refuse anything in `site/data/` outside `sample/`.
The plan is the same gate the other portals use — Google sign-in + encrypted bundles. See `docs/ROADMAP.md`.
