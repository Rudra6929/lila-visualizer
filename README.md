# LILA BLACK — Player Journey Visualizer

# IMP Note:-On the free tier of Streamlit Community Cloud, apps go to sleep after a period of inactivity to save resources.
# Here's what happens:
  # inactive app → After some time with no visitors, the app goes to sleep.
  # (click-on:yes get this backup when opening app link its it went to sleep) First visitor afterward → The app wakes up automatically, but it can take 10–60 seconds (sometimes longer if dependencies are large).
  
# A web-based tool for the LILA Games Level Design team to explore player behavior on the maps of **LILA BLACK**, an extraction shooter. Turns raw telemetry into three interactive views: **match playback**, **aggregate heatmaps**, and **per-player profiles**.

> **Live app:** https://lila-visualizer-sk44ahuzqbbeogow5nfakd.streamlit.app/?map=AmbroseValley&date=All&mode=All+players

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
---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Runtime | **Python 3.11+** | Same language as the data pipeline |
| App framework | **Streamlit 1.42+** | Ships working UI + deploy in minutes |
| Charts | **Plotly 5.20+** | Interactive canvas, `Histogram2d`, native animation frames |
| Data | **Pandas 2.0+ / PyArrow 14+** | Fast in-memory columnar ops on Parquet |
| Images | **Pillow 10+** | Minimap thumbnail generation |
| Numerics | **NumPy 1.24+** | Vectorized coord conversion |
| Hosting | **Streamlit Community Cloud** | Free, GitHub-connected, HTTPS by default |

Full dependency list in [`requirements.txt`](./requirements.txt).

---

## Features

- **🔥 Heatmap** — 7 preset overlays (traffic, loot, bot combat, storm deaths, etc.) with adjustable grid + map dim
- **🗺️ Coverage** — grid-based dead-zone finder with `coverage %` stat
- **🎬 Match Playback** — animated timeline with ▶ Play / ⏸ Pause / ⏮ Reset (native Plotly frames, smooth client-side)
- **👤 Players** — ranked leaderboard in aggregate mode, full profile in specific-player mode
- **🧑 Humans vs 🤖 Bots** — visually distinct paths + text labels everywhere
- **🔗 Shareable URLs** — filter state encoded in query params, send a link → recipient sees the same view

Details in [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## Prerequisites

- Python 3.11 or newer
- pip
- ~50 MB free disk space (mostly the minimap images)

That's it. No database, no Node, no Docker.

---

## Local setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/lila-visualizer.git
cd lila-visualizer

# 2. (Recommended) create a virtual environment
python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app opens at **http://localhost:8501**. First load takes ~2 seconds while the parquet is cached.

### Windows without a virtual env

If you're on Windows and the `streamlit` command isn't found after install (common with Microsoft Store Python):

```powershell
python -m streamlit run app.py
```

Works identically.

---

## Environment variables

**None required for the base app.** The tool reads from a local Parquet file and needs no external services.

Optional variables that Streamlit itself respects:

| Variable | Purpose | Default |
|---|---|---|
| `STREAMLIT_SERVER_PORT` | Local port for `streamlit run` | `8501` |
| `STREAMLIT_SERVER_HEADLESS` | Skip opening browser on start | `false` |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | Anonymous telemetry to Streamlit | `false` (already off) |

Nothing sensitive. No API keys. No database URLs. Nothing you need to hide.

---

## Project structure

```
lila-visualizer/
├── app.py                   # Streamlit entry point — UI only, no data logic
├── src/
│   ├── __init__.py
│   ├── config.py            # Map coords, event styles, heatmap presets
│   ├── coords.py            # World (x,z) → pixel (x,y) math
│   ├── data.py              # Load / cache / filter / summarize
│   └── plots.py             # Plotly figure builders
├── data/
│   ├── all_events.parquet   # 1.6 MB, 89k rows — pre-combined
│   └── minimaps/            # 3 minimap images
├── preprocess.py            # Offline: 1,243 raw files → all_events.parquet
├── requirements.txt
├── .streamlit/
│   └── config.toml          # Dark theme
├── .gitignore
├── README.md                # ← you are here
├── ARCHITECTURE.md          # One-page architecture doc
├── INSIGHTS.md              # 5 data-backed findings
└── PRD.md                   # Product requirements (RICE + MoSCoW + wireframes)
```

---

## Regenerating the dataset (optional)

If you have access to the raw `.nakama-0` files from the game server, you can regenerate the bundled Parquet:

```bash
# Place your February_10/ ... February_14/ folders anywhere, then edit
# preprocess.py to point at that directory, and:
python preprocess.py
```

Output: `all_events.parquet` in the current directory, plus a `summary.csv` with per-day counts for sanity-checking.

**Not required for normal use** — the repo ships with a pre-generated Parquet.

---

## Deployment (Streamlit Community Cloud)

1. Push this repo to **GitHub** (public repo for free tier)
2. Go to https://share.streamlit.io → sign in with GitHub
3. Click **Create app**
   - Repository: `YOUR_USERNAME/lila-visualizer`
   - Branch: `main`
   - Main file path: `app.py`
4. Click **Deploy**

First build takes ~2 min. Subsequent `git push` triggers auto-redeploy in ~30 sec.

The parquet and minimaps are bundled in the repo, so no external storage setup is needed.

### Deploying elsewhere

Any Streamlit-compatible host works. For **Render** or **Fly.io**:

```bash
# Start command:
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

For **Docker**:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

---

## Data schema

Each row in `all_events.parquet`:

| Column | Type | Description |
|---|---|---|
| `user_id` | string | UUID = human, numeric = bot |
| `match_id` | string | Unique game session ID |
| `map_id` | category | `AmbroseValley` / `GrandRift` / `Lockdown` |
| `x, y, z` | float32 | World coordinates (`y` = elevation, ignored in 2D views) |
| `ts` | timestamp(ms) | Compressed within-match time — see `ARCHITECTURE.md` |
| `event` | category | One of 8 event types (see [`src/config.py`](./src/config.py)) |
| `is_bot` | bool | Added at load time — `user_id.isdigit()` |
| `day` | category | Source folder — `February_10` … `February_14` |

Derived columns added at runtime (in `src/data.py::load_events`):

- `match_progress` — normalized 0..1 within-match time
- `px, py` — pre-computed pixel coordinates on the 1024×1024 minimap

---

## Development

### Making changes

1. Edit files locally
2. Restart Streamlit (or just save — auto-reload is on by default in dev mode)
3. Browser refreshes automatically

### Adding a new map

Edit `src/config.py::MAP_CONFIG`:

```python
MAP_CONFIG["YourNewMap"] = {
    "scale": 800,
    "origin_x": -400,
    "origin_z": -400,
    "image": "YourNewMap_Minimap.png",
    "display_name": "Your New Map",
    "blurb": "One-line description.",
}
```

Drop the minimap image into `data/minimaps/`. Done. Every tab picks it up automatically.

### Adding a new event type

Edit `src/config.py::EVENT_STYLES`:

```python
EVENT_STYLES["NewEventType"] = {
    "color": "#123456",
    "symbol": "star",
    "size": 12,
    "opacity": 1.0,
    "category": "combat",  # or "loot", "movement", "environment"
    "label": "Human-readable label",
}
```

The event appears in filters, legends, and heatmap presets automatically.

### Running tests

There aren't any yet. Adding smoke tests for `world_to_pixel()` and `filter_events()` is the top v2 priority — see [`PRD.md`](./PRD.md).

---

## Troubleshooting

**"streamlit: command not found"** on Windows with Microsoft Store Python
→ Use `python -m streamlit run app.py` instead.

**App boots but sidebar is empty / no maps show up**
→ Check that `data/all_events.parquet` is present. If missing, the parquet didn't get committed to Git — check `.gitignore`.

**Deployment fails on Streamlit Cloud with "ModuleNotFoundError"**
→ Something's missing from `requirements.txt`. Add it, `git push`, wait for redeploy.

**Coordinates look off — points spilling outside the minimap**
→ The `MAP_CONFIG` origin/scale for that map is wrong. Verify against the game engine's world bounds.

**Match Playback animation is jerky**
→ On very old browsers, Plotly's client-side animation can lag. Chrome / Edge / Firefox on any machine from the last 5 years should be smooth.

---

## License

Internal / assignment submission — no license attached. Contact the repo owner for reuse permissions.

---

## Credits

- **Built by:** Assignment submission for LILA Games' Product Engineer role
- **Data:** LILA BLACK production telemetry (Feb 10–14, 2026)
- **Minimap images:** LILA Games
- **Frameworks:** Streamlit, Plotly, pandas, PyArrow
