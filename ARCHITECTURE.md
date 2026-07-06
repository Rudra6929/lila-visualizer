# Architecture

## What I built with and why

- **Streamlit + Plotly** for UI + charts. Same language as the data pipeline (Python), zero context switching, deploys in under 5 minutes. Plotly gives me layered images, scatter, `Histogram2d`, and native animation frames out of the box.
- **Pandas + PyArrow** for data. 89k rows is trivially in-memory; a database would add ops burden with no latency payoff.
- **Streamlit Community Cloud** for hosting. Free, GitHub-connected, auto-redeploys on `git push`. No infrastructure to manage.

## How data flows to screen

Two-stage pipeline: preprocess **offline once**, serve at **runtime**.

```
─── OFFLINE (preprocess.py) ────────────────────────────────
   1,243 .nakama-0 files (5 daily folders)
      │  decode `event` bytes → strings
      │  tag row with source day
      │  cast to categorical, zstd compress
      ▼
   all_events.parquet   1.6 MB, 89,104 rows

─── RUNTIME (Streamlit app) ────────────────────────────────
   all_events.parquet
      │  @st.cache_data (loaded once per session)
      │  add derived columns:
      │    - is_bot           (user_id.isdigit)
      │    - match_progress   (0..1 within match)
      │    - px, py           (pre-computed pixel coords)
      ▼
   Sidebar widgets  →  filter_events()   ← one function, all filters
      ▼
   src/plots.py figure builders (heatmap, coverage, match anim, player)
      ▼
   st.plotly_chart  →  browser (Plotly.js renders interactively)
```

Everything downstream of the DataFrame is a column read. No math on the render path — that's why the app feels instant.

## Coordinate mapping (the tricky part)

World coords `(x, z)` → minimap pixel coords `(px, py)`. Each map has its own scale + origin.

**The formula** (from the dataset README):

```
u = (world_x - origin_x) / scale
v = (world_z - origin_z) / scale
pixel_x = u * 1024
pixel_y = (1 - v) * 1024        # Y flipped: image origin is top-left
```

Per-map constants live in `src/config.py::MAP_CONFIG` — adding a new map is a one-line change.

**My approach:**

1. Wrote `world_to_pixel(x, z, map_id)` in `src/coords.py`, **vectorized with NumPy** so it operates on whole columns at once, not row-by-row.
2. **Verified twice before trusting it:**
   - README's worked example: world `(-301.45, -355.55)` → pixel `(78, 890)`. My function returns exactly `(78, 890)`.
   - Across all 89,104 events on all three maps, **100% fall inside `[0,1024] × [0,1024]`**. Nothing spills off the image.
3. **Ran the conversion once at load time** and stored `px, py` as DataFrame columns. Every plot is a column read — no per-request coord math.
4. The `y` column (elevation) is intentionally ignored — the tool is 2D. Every figure anchors to a 1024×1024 canvas with the minimap drawn as a Plotly background image and axes locked to pixel space.

## Assumptions I made where the data was ambiguous

| What I ran into | How I handled it |
|---|---|
| `event` column stored as bytes, not strings | Decoded during preprocessing; defensive re-decode at load time too |
| Timestamps compressed — matches span ~400 ms in the raw values instead of minutes | Absolute time is meaningless. Derived `match_progress ∈ [0,1]` — normalized within-match time. Timeline slider and playback operate in this space. |
| README says matches have "10 humans + 40 bots" but 99% of matches in this dataset contain only one human's file | Didn't pretend otherwise. "Match reconstruction" in the tool = combining all files sharing a `match_id`, usually a single-player journey. Called this out so a reviewer doesn't wonder why paths look sparse. |
| Only 6 human PvP kills across 89k events | Built heatmap presets around actually present signal (bot combat, loot, storm), not what's hypothetically possible |
| 39 storm-death events across all 5 days | Too sparse for storm-front reconstruction. Explicit non-goal. Storm deaths still appear as markers and a heatmap preset — just no dedicated storm-analysis view. |
| Feb 14 is a partial day | Warning chip auto-appears in sidebar when that day is selected |
| Files have no `.parquet` extension | Parquet readers care about contents, not extensions. Ignored. |
| Bot vs human detection | `user_id.isdigit()` — matches the README convention exactly |

## Major tradeoffs

| Decision | Alternative considered | Why this way |
|---|---|---|
| **Streamlit + Plotly** | React + FastAPI + custom charts | Streamlit ships working UI + deploy pipeline in hours, not days. React would look nicer but adds 5–10 hrs of build/hosting overhead for a tool used by ~5 designers. |
| **One combined parquet, not a DB** | DuckDB / SQLite / Postgres | 89k rows fits in memory; groupby is µs-scale. A DB adds ops burden with zero latency payoff. Worth revisiting past ~10M rows. |
| **Preprocess offline, not per-request** | Read 1,243 raw files at each app boot | Tiny files take ~30 sec to read; one merged file loads in ~500 ms. |
| **Bake parquet into the repo** | Fetch from S3/GCS at startup | 1.6 MB fits in Git. Streamlit Cloud has no persistent storage anyway; external fetching adds infra and latency. |
| **Native Plotly animation frames** | `time.sleep()` + `st.rerun()` loop | Rerun loop causes flicker, blocks the app, can't be cleanly paused. Plotly frames animate client-side — smooth, no server round-trips. |
| **Guided sidebar (single-select map/date)** | Multi-select checkboxes across everything | Level Designers focus on one map at a time. Segmented controls match iOS/macOS conventions users already know. |
| **Normalized `match_progress`, not raw seconds** | Show real timestamps | The ~400 ms compressed values make absolute time useless. Progress % is what a designer wants anyway. |
| **URL query params for shared state** | Server-side saved views + auth | Stateless, no backend, and designers already share links via Slack. Auth would be over-engineered for an internal tool. |
