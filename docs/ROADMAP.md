# Executive Scorecard — roadmap

## Phase 0 — framework (done, Nov 2026)
- Scorecard tiles: net sales, labor %, COGS %, prime cost %, avg check, depletions — with target status.
- Taprooms: monthly trend vs LY, location table. Wholesale: monthly trend vs LY, brand change, state table.
- Period picker: year to date, last 3 months, single month; "through" month.
- Sample data, GitHub repo + Pages, double-click deploy.

## Phase 0.5 — wireframe layout (done, Nov 13)
- Rebuilt the page in the Google Site wireframe's three tiers, in the portal's tokens; every tile labelled Feed or Sheet.
- `tools/build_local.py`: VIP (Sales Portal), Store Director Portal payload, Leadership Scorecard sheet → local preview.
- Sample data regenerated so nothing committed matches a real figure.

## Phase 1 — outline session (Friday)
- [ ] Confirm the KPI list for leadership (what's on the scorecard vs. left in the detail portals).
- [ ] Confirm targets (labor, COGS, sales growth, depletion growth) → `site/config.json`.
- [ ] Decide refresh cadence: daily, weekly, or month-end close.
- [ ] User/admin access: who views, who edits, and which account/license the portals sit under.

## Phase 2 — real data
- **Store Director Portal → exec bundle (recommended).** Add an `exec` label to StorePortal's `build_site.py` that runs
  the same weekly roll-up as `tools/build_local.py` (`taprooms_from_sdp` + sheet parsing of `scorecard.tabs`) and
  encrypts it like the `scorecard` bundle (leadership-only). The ExecScorecard page fetches and decrypts it after sign-in.
- **VIP roll-up.** The Mac's daily Sales Portal refresh uploads the Rolling Scorecard roll-up (state × brand × premise,
  no accounts) to the Apps Script, the way `tools/push_depletions.py` already does for StorePortal; the nightly build
  includes it in the exec bundle.
- **Taprooms:** reuse the StorePortal pipeline (`sdp` metrics) to emit the taproom CSV/JSON in the
  data contract (README). Toast covers 5 of 6 locations today (Solon credentials missing);
  MarginEdge COGS waits on API access from MarginEdge support.
- **Depletions:** monthly VIP export (state × brand × cases, with LY) from the Depletion Dashboard / Sales Portal refresh.
- Add a scheduled GitHub Action that builds the data files nightly, like StorePortal's `refresh.yml`.

## Phase 3 — access
- [x] Nov 13: Google sign-in on the page. Uses the Store Director Portal's Apps Script + roster; allowed: Troy, Matt Swift,
  Mike Wehr, Sarah Heinrich, Bryan Farrell, Rachel Hart (`EXEC` list in `site/index.html`, must also be Admin/Leadership on the roster).
  This gates the page only — the data files are still public, so only sample data until the encrypted exec bundle lands.
- Google sign-in + AES-encrypted data bundle, same approach as the Sales Portal and StorePortal
  (Apps Script roster → bundle keys). Until then, only sample data is published.
