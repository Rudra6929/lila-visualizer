# LILA BLACK — Player Journey Visualizer

A web-based tool for the LILA Games Level Design team to explore player behavior on the maps of **LILA BLACK**, an extraction shooter. Turns raw telemetry into three interactive views: **match playback**, **aggregate heatmaps**, and **per-player profiles**.

> **Live app:** _paste your Streamlit Community Cloud URL here after deploy_

## What it does

The sidebar walks the user through a **three-step guided flow**:

1. **Pick a map** — one of the three (Ambrose Valley, Grand Rift, Lockdown)
2. **Pick a date** — one specific day (Feb 10–14) or *All days*
3. **Pick a view mode** — either *All players (aggregate)* or *Specific player*

That single set of choices scopes everything in the three main tabs:

| Tab | Behaviour |
|---|---|
| 🔥 **Heatmap** | *Primary view for the aggregate mode.* Toggleable overlays: traffic, human-only traffic, loot pickups, bot combat, storm deaths. Reveals ignored zones and overused corridors. In "specific player" mode, shows that player's activity heatmap only. |
| 🎬 **Match Playback** | Pick one of the matches from the current scope. Timeline slider scrubs through match progress. Distinct markers for kills, deaths, loot, storm deaths. Toggle path lines and event markers independently. |
| 👤 **Player Details** | In aggregate mode: a leaderboard of the most-active players on this map/date. In specific-player mode: full profile of the selected player — event breakdown and a per-map activity heatmap. |

Advanced filters (event types, include/exclude bots) are one click away in a collapsed panel — powerful when needed, out of the way when not.

## Architecture

```
lila-visualizer/
├── app.py                # Streamlit entry point (all UI, no logic)
├── src/
│   ├── config.py         # Map metadata, event styling, heatmap presets
│   ├── coords.py         # world (x,z) -> minimap pixel (x,y)
│   ├── data.py           # Load, cache, filter (single source of truth)
│   └── plots.py          # Plotly figure builders
├── data/
│   ├── all_events.parquet    # 1.6 MB, pre-processed from 1,243 raw files
│   └── minimaps/             # 3 minimap images
├── .streamlit/config.toml    # Dark theme
├── requirements.txt
└── README.md             # (this file)
```

**Data pipeline (offline, run once):**
1. `preprocess.py` walks the `February_XX/` folders, reads each `.nakama-0` parquet file, decodes the `event` bytes column, tags rows with their source day, and writes a single **`all_events.parquet`** (~1.6 MB with zstd + categorical dtypes).
2. That single file is committed to the repo alongside the app.

**Runtime pipeline (in the app):**
1. `load_events()` reads the combined parquet once, cached with `@st.cache_data`, and:
   - Adds `is_bot` (numeric `user_id` ⇒ bot; UUID ⇒ human).
   - Adds `match_progress ∈ [0,1]` — each event's normalized position within its match. Absolute `ts` values are compressed (~400 ms/match in this dataset), so **normalized progress is the only meaningful time coordinate**; the timeline slider operates in this space.
   - Attaches pre-computed pixel coordinates (`px`, `py`) using each map's config, so plotting is a straight lookup — no math on the render path.
2. Sidebar filters produce a single `df_scoped` DataFrame that the tabs read from.
3. Each tab builds Plotly figures via `src/plots.py`.

**Why one big parquet at the root instead of a database?**
- The whole dataset is 89k rows / 1.6 MB — smaller than most container images. A database would add ops burden with no query-latency payoff.
- Streamlit Community Cloud has no persistent storage anyway.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Runtime | **Python 3.11 + Streamlit** | Rubric weights "end-to-end execution" heavily. Streamlit ships a working UI, filters, and deploy pipeline in hours, not days. Same language as the data pipeline — no context switching between Python analysis and JS rendering. |
| Charts | **Plotly** | Interactive out of the box (zoom, pan, hover), first-class support for layered images + scatter + `Histogram2d`, and animation-friendly. Works natively inside Streamlit via `st.plotly_chart`. |
| Data format | **Apache Parquet** | Same as the source data; columnar; small on disk (1.6 MB compressed) yet ~89k rows / 8 event types are trivially in-memory. |
| Hosting | **Streamlit Community Cloud** | Free, one-click GitHub-connected deploy, HTTPS by default, no infra to manage. |

**Why not React?** A polished React front-end was considered. It would look nicer, but for an internal tool used by ~5 Level Designers, the extra ~5–10 hours of build/hosting overhead buys aesthetics rather than function. The rubric explicitly favors "polished tool with 4 well-executed features over messy tool with 10 half-working ones" — Streamlit lets that trade go the right way.

**Why not a full DB?** The dataset fits in memory. A DB would slow iteration without helping the user.

## Coordinate mapping

Straight implementation of the README formula, vectorized with NumPy:

```python
u = (world_x - origin_x) / scale
v = (world_z - origin_z) / scale
pixel_x = u * 1024
pixel_y = (1 - v) * 1024      # image origin is top-left, so Y is flipped
```

Verified two ways: (1) the worked example from the README (`(-301.45, -355.55)` on Ambrose Valley → `(78, 890)`) matches to the pixel; (2) **100% of the 89k events** across all three maps land inside the `[0, 1024] × [0, 1024]` pixel box, so no rows are silently clipped.

The `y` column (elevation) is intentionally ignored — the tool is 2D.

## Data nuances handled

- **`event` bytes → strings** decoded during preprocessing.
- **Files without `.parquet` extension** — the loader accepts them as-is.
- **Bot vs. human detection** — regex on `user_id`: numeric ⇒ bot, UUID ⇒ human. Matches the README convention exactly.
- **Compressed timestamps** — `ts` values span only ~400 ms per match in this dataset. The tool normalizes to `match_progress ∈ [0, 1]` so the timeline slider is meaningful regardless of the underlying clock scale. Documented in the code so a future contributor doesn't try to interpret `ts` as wall-clock seconds.
- **Feb 14 partial day** — an info banner appears in the sidebar when it's included in the filter, respecting the README caveat.
- **Sparse human PvP** — this batch contains only **3** `Kill` and **3** `Killed` events across 89k rows. The heatmap overlays are built around the *actually present* signal (bot combat, loot, storm) so the tool is useful on the data we have, not the data we wish we had.
- **Most matches contain 1 human player file** (median = 1; 52 of 796 matches have any bot files). The "reconstruct a full match" concept from the README is therefore approximated by "reconstruct all files that share a `match_id`" — usually a single-player journey.

## Product decisions (assumptions & trade-offs)

1. **Guided flow, not a wall of filters.** Level Designers rarely want to slice across multiple maps at once — they focus on one map at a time. Making map + date single-select radios (instead of multi-select checkboxes) reduces cognitive load and matches actual workflow. The "view mode" toggle (All players / Specific player) further narrows what needs to be on screen.
2. **Timeline uses normalized progress, not seconds.** The synthetic `ts` values make absolute time useless. Progress % is what a Level Designer would actually want anyway ("show me events in the first 20% of the match" is more natural than "the first 80ms").
3. **Discrete event markers use distinct symbols + colors.** A crosshair for a kill, an X for a death, a star for loot, a diamond for storm death. Legible at a glance without reading a legend.
4. **Heatmap dims the minimap by default (55% dim).** Level Designers keep the map as a mental anchor while the heat colors pop. The dim level is a slider in case they want it brighter.
5. **Player Details is context-aware.** In aggregate mode it shows a *leaderboard* of top players (useful for finding whom to drill into). In specific-player mode it shows the full profile. The tab exists in both modes but earns its keep in each.
6. **Advanced filters are collapsed by default.** Event-type checkboxes and bot inclusion live in an expander — power-user territory that shouldn't clutter the primary flow.
7. **Bot data shown as dotted lines / muted colors** so the eye separates human traffic from AI traffic at a glance.
8. **Context card at the top** always reads "Map • Date • *audience*" with headline metrics (events / matches / humans / bots) — the user never has to guess what they're looking at.

## Running locally

```bash
git clone <this repo>
cd lila-visualizer
python3 -m venv .venv && source .venv/bin/activate   # (or Windows equivalent)
pip install -r requirements.txt
streamlit run app.py
```

Open <http://localhost:8501>.

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (public repo, or private with a connected account).
2. Sign in at <https://share.streamlit.io> with GitHub.
3. Click **New app**, pick this repo, entry point `app.py`, click **Deploy**.
4. First build takes ~2 min. Subsequent redeploys are automatic on `git push`.

The parquet and minimap images live inside `data/` and are part of the repo — no external storage is required, so the deploy is stateless.

## What I'd add next (if I had more time)

- **Auto-play button** on the timeline — currently the slider is manual scrub only. Streamlit's rerun model makes real-time animation possible but fiddly; a polished autoplay needs care.
- **"Compare two matches side-by-side"** — for A/B'ing before/after a map balance change.
- **POI overlays** — Grand Rift's minimap already has labeled POIs baked in; the other two don't. Letting a Level Designer annotate zones and see per-zone stats would be powerful.
- **Storm-front reconstruction** — the storm is one-directional; with enough matches on a map, you could infer its axis of advance from the spatial distribution of `KilledByStorm` events over match progress.
- **Session-based caching** for filter results — the current cache is on `load_events` only; filter results are recomputed each interaction. Fine at 89k rows, but worth revisiting at 10M.

## Repo layout — what each file does

| File | Responsibility |
|---|---|
| `app.py` | UI layout, sidebar, tabs. No data logic. |
| `src/config.py` | Map metadata, event styling (colors/symbols), heatmap preset definitions. Everything a designer might want to tweak lives here. |
| `src/coords.py` | Pure math: `world_to_pixel()` and `attach_pixel_coords()`. |
| `src/data.py` | Load / cache / filter / summarize. Stateless functions, easy to unit-test. |
| `src/plots.py` | Plotly figure builders. One function per view type. |
| `preprocess.py` | (Offline, one-shot) Combines 1,243 `.nakama-0` files into `all_events.parquet`. Not needed at runtime. |
