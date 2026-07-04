"""LILA BLACK — Player Journey Visualizer.

Level-designer tool for exploring player behavior on LILA BLACK's maps.

UX design principles applied here:
    - Progressive disclosure: primary controls up front, power features tucked away
    - Guided flow: MAP -> DATE -> MODE, in that order, always visible
    - Show, don't tell: map thumbnails, colored metric cards, distinctive event glyphs
    - Contextual UI: the same tab reshapes based on the selected view mode
    - Game-adjacent aesthetic: cyan/violet accents on charcoal, chip-based navigation
"""

from __future__ import annotations

import streamlit as st

from src.config import EVENT_STYLES, HEATMAP_LAYERS, MAP_CONFIG, MOVEMENT_EVENTS
from src.data import (
    filter_events,
    load_events,
    match_summary,
    player_summary,
)
from src.plots import (
    make_coverage_figure,
    make_heatmap_figure,
    make_match_figure,
    make_match_animation_figure,
    make_player_activity_chart,
    minimap_thumbnail_uri,
)

# =============================================================================
# Page setup
# =============================================================================
st.set_page_config(
    page_title="LILA BLACK — Level Design Explorer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# URL state sync
# Reads ?map=&date=&mode=&user= on first load and seeds session_state, so
# a shared link opens with the sender's exact filters. On widget change,
# session_state values are written back to the URL at the end of the script.
# =============================================================================
_URL_KEYS = {
    "map":  "ui_map",
    "date": "ui_date",
    "mode": "ui_mode",
    "user": "ui_user",
}
# One-shot: URL → session_state (only if the widget hasn't rendered yet).
for url_key, state_key in _URL_KEYS.items():
    if state_key not in st.session_state and url_key in st.query_params:
        st.session_state[state_key] = st.query_params[url_key]


def _sync_url(**updates: str | None) -> None:
    """Write current filter state back to the browser URL (no rerun)."""
    for k, v in updates.items():
        if v is None or v == "":
            if k in st.query_params:
                del st.query_params[k]
        else:
            st.query_params[k] = str(v)

# =============================================================================
# Design system — one big stylesheet so the UI has a consistent feel.
# =============================================================================
st.markdown("""
<style>
/* ---------- root layout ---------- */
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 3rem !important;
    max-width: 1400px;
}
section[data-testid="stSidebar"] {
    min-width: 320px !important;
    background: #0a0d13 !important;
    border-right: 1px solid rgba(255,255,255,0.05);
}
section[data-testid="stSidebar"] > div {padding-top: 1rem;}

/* ---------- typography ---------- */
h1, h2, h3, h4 {
    font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
    letter-spacing: -0.015em;
}
h1 {font-size: 1.55rem !important; font-weight: 700 !important;}
h2 {font-size: 1.15rem !important; font-weight: 600 !important;}
h3 {font-size: 1.0rem !important; font-weight: 600 !important;}
.section-label {
    text-transform: uppercase;
    letter-spacing: 0.09em;
    font-size: 0.7rem;
    font-weight: 700;
    color: rgba(255,255,255,0.45);
    margin: 1rem 0 0.4rem 0;
}

/* ---------- brand header ---------- */
.brand {
    display: flex; align-items: center; gap: 0.65rem;
    padding-bottom: 0.4rem; margin-bottom: 0.2rem;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}
.brand .logo {
    width: 34px; height: 34px; border-radius: 8px;
    background: linear-gradient(135deg, #4FC3F7 0%, #B388FF 100%);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; color: #0a0d13; font-size: 1.1rem;
}
.brand .wordmark {font-weight: 700; font-size: 1.05rem; letter-spacing: -0.01em;}
.brand .tag {
    font-size: 0.65rem; color: rgba(255,255,255,0.4);
    text-transform: uppercase; letter-spacing: 0.12em;
}

/* ---------- hero context bar (main content) ---------- */
.hero {
    display: flex; align-items: center; gap: 1rem;
    margin-bottom: 0.75rem;
}
.hero .hero-thumb {
    width: 46px; height: 46px; border-radius: 8px; object-fit: cover;
    border: 1px solid rgba(255,255,255,0.1);
}
.hero .hero-title {
    font-size: 1.35rem; font-weight: 700; letter-spacing: -0.015em;
    margin: 0; line-height: 1.1;
}
.hero .hero-sub {
    font-size: 0.82rem; color: rgba(255,255,255,0.55); margin-top: 0.15rem;
}
.chip-row {display: flex; gap: 0.4rem; margin-top: 0.35rem; flex-wrap: wrap;}
.chip {
    display: inline-flex; align-items: center; gap: 0.35rem;
    padding: 0.2rem 0.6rem; border-radius: 999px;
    font-size: 0.72rem; font-weight: 500;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.75);
}
.chip.accent {
    background: rgba(79,195,247,0.1);
    border-color: rgba(79,195,247,0.3);
    color: #4FC3F7;
}
.chip.warn {
    background: rgba(255,193,7,0.1);
    border-color: rgba(255,193,7,0.35);
    color: #FFC107;
}

/* ---------- metric strip ---------- */
.metric-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.6rem;
    margin: 0.5rem 0 1rem 0;
}
.metric-card {
    padding: 0.7rem 0.9rem; border-radius: 10px;
    background: linear-gradient(135deg, rgba(255,255,255,0.035) 0%, rgba(255,255,255,0.008) 100%);
    border: 1px solid rgba(255,255,255,0.06);
    border-left: 3px solid var(--acc, #4FC3F7);
    transition: transform .15s ease, border-color .15s ease;
}
.metric-card:hover {transform: translateY(-1px);}
.metric-card .label {
    font-size: 0.66rem; letter-spacing: 0.09em; text-transform: uppercase;
    color: rgba(255,255,255,0.55); font-weight: 600;
}
.metric-card .value {
    font-size: 1.55rem; font-weight: 700; margin-top: 0.15rem; line-height: 1.1;
}
.metric-card .foot {
    font-size: 0.7rem; color: rgba(255,255,255,0.45); margin-top: 0.1rem;
}

/* ---------- tab bar restyled as pills ---------- */
div[data-baseweb="tab-list"] {
    gap: 0.35rem !important;
    border-bottom: none !important;
    padding: 0.3rem;
    background: rgba(255,255,255,0.03);
    border-radius: 10px;
    width: fit-content;
    margin-bottom: 1rem;
}
button[data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 7px !important;
    padding: 0.4rem 1rem !important;
    height: auto !important;
    color: rgba(255,255,255,0.7) !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    border: none !important;
}
button[data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.04) !important;
    color: #fafafa !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background: rgba(79,195,247,0.15) !important;
    color: #4FC3F7 !important;
}
div[data-baseweb="tab-panel"] {padding-top: 0.5rem !important;}
div[data-baseweb="tab-highlight"] {display: none !important;}
div[data-baseweb="tab-border"] {display: none !important;}

/* ---------- segmented control custom accent ---------- */
div[data-testid="stSegmentedControl"] label {
    background: transparent !important;
}

/* ---------- widget label refinement ---------- */
div[data-testid="stWidgetLabel"] > label > div > p {
    font-size: 0.72rem !important;
    color: rgba(255,255,255,0.55) !important;
    text-transform: uppercase; letter-spacing: 0.08em;
    font-weight: 600;
}

/* ---------- expander polish ---------- */
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 8px !important;
}

/* ---------- empty state card ---------- */
.empty-state {
    padding: 2rem; border-radius: 10px;
    background: rgba(255,255,255,0.02);
    border: 1px dashed rgba(255,255,255,0.1);
    text-align: center; color: rgba(255,255,255,0.55);
}
.empty-state .icon {font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.4;}
.empty-state .title {font-weight: 600; color: rgba(255,255,255,0.75); margin-bottom: 0.3rem;}

/* ---------- Streamlit chrome cleanup ---------- */
header[data-testid="stHeader"] {background: transparent !important;}
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Data
# =============================================================================
df = load_events()

# =============================================================================
# Sidebar — brand + guided flow
# =============================================================================
with st.sidebar:
    # Brand
    st.markdown(
        """
        <div class="brand">
            <div class="logo">L</div>
            <div>
                <div class="wordmark">LILA BLACK</div>
                <div class="tag">Level Design Explorer</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Map ---
    st.markdown('<div class="section-label">Map</div>', unsafe_allow_html=True)
    map_options = list(MAP_CONFIG.keys())
    map_id = st.segmented_control(
        label="Map",
        options=map_options,
        format_func=lambda m: MAP_CONFIG[m]["display_name"],
        default=map_options[0],
        selection_mode="single",
        label_visibility="collapsed",
        key="ui_map",
    )
    if not map_id:  # segmented_control can return None on deselect - defensive
        map_id = map_options[0]

    # Thumbnail preview of the currently selected map
    st.markdown(
        f"""
        <div style="margin-top:0.5rem; margin-bottom:0.3rem;">
            <img src="{minimap_thumbnail_uri(map_id, 300)}"
                 style="width:100%; border-radius:8px;
                        border:1px solid rgba(255,255,255,0.08);"/>
            <div style="font-size:0.72rem; color:rgba(255,255,255,0.55);
                        margin-top:0.4rem; line-height:1.3;">
                {MAP_CONFIG[map_id]["blurb"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Date ---
    st.markdown('<div class="section-label">Date</div>', unsafe_allow_html=True)
    ALL_DAYS_LABEL = "All"
    all_days = sorted(df["day"].cat.categories.tolist())
    day_display = {ALL_DAYS_LABEL: "All"}
    for d in all_days:
        day_display[d] = d.replace("February_", "Feb ")
    day_choice = st.segmented_control(
        label="Date",
        options=[ALL_DAYS_LABEL] + all_days,
        format_func=lambda d: day_display[d],
        default=ALL_DAYS_LABEL,
        selection_mode="single",
        label_visibility="collapsed",
        key="ui_date",
    )
    if not day_choice:
        day_choice = ALL_DAYS_LABEL
    if day_choice == "February_14":
        st.markdown(
            '<div class="chip warn" style="margin-top:0.3rem;">⚠ Partial day '
            '— collection was still ongoing</div>',
            unsafe_allow_html=True,
        )
    selected_days = all_days if day_choice == ALL_DAYS_LABEL else [day_choice]

    # --- View mode ---
    st.markdown('<div class="section-label">View mode</div>', unsafe_allow_html=True)
    view_options = ["All players", "Specific player"]
    view_mode = st.segmented_control(
        label="View mode",
        options=view_options,
        format_func=lambda v: "👥  " + v if v.startswith("All") else "👤  " + v,
        default=view_options[0],
        selection_mode="single",
        label_visibility="collapsed",
        key="ui_mode",
    )
    if not view_mode:
        view_mode = view_options[0]
    is_specific_player = view_mode.startswith("Specific")

    # Player picker only when needed
    selected_user_id: str | None = None
    if is_specific_player:
        # Sub-toggle: humans (the default) vs bots
        who_kind = st.segmented_control(
            label="Type",
            options=["Humans", "Bots"],
            format_func=lambda k: "🧑 Humans" if k == "Humans" else "🤖 Bots",
            default="Humans",
            selection_mode="single",
            label_visibility="collapsed",
            key="ui_who_kind",
        )
        if not who_kind:
            who_kind = "Humans"

        want_humans = who_kind == "Humans"
        scope = filter_events(df, maps=[map_id], days=selected_days,
                              include_humans=want_humans,
                              include_bots=not want_humans)
        eligible = player_summary(scope, include_bots=not want_humans)
        if eligible.empty:
            _kind_word = "players" if want_humans else "bots"
            st.markdown(
                f'<div class="empty-state" style="padding:1rem; margin-top:0.5rem;">'
                f'<div class="title">No {_kind_word} here</div>'
                f'<div style="font-size:0.75rem;">Nobody played '
                f'{MAP_CONFIG[map_id]["display_name"]} on the selected date.</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            _kind_word = "players" if want_humans else "bots"
            player_label = st.selectbox(
                f"Pick a {_kind_word.rstrip('s')} ({len(eligible)} available)",
                options=eligible["label"].tolist(),
                help="Sorted by activity (event count).",
            )
            selected_user_id = eligible.loc[
                eligible["label"] == player_label, "user_id"
            ].iloc[0]

    # --- Advanced (collapsed by default) ---
    with st.expander("⚙︎  Advanced filters"):
        include_bots = st.toggle("Include bots in views", value=True,
                                 help="Show bot movement lines and combat markers "
                                      "in Match Playback.")
        st.markdown('<div class="section-label" style="margin-top:0.8rem;">'
                    'Event types</div>', unsafe_allow_html=True)
        selected_events: list[str] = []
        cats: dict[str, list[str]] = {}
        for evt, style in EVENT_STYLES.items():
            cats.setdefault(style["category"], []).append(evt)
        for cat, evts in cats.items():
            st.markdown(
                f'<div style="font-size:0.72rem; color:rgba(255,255,255,0.5); '
                f'margin: 0.4rem 0 0.2rem 0;">{cat.title()}</div>',
                unsafe_allow_html=True,
            )
            for evt in evts:
                if st.checkbox(EVENT_STYLES[evt]["label"], value=True,
                               key=f"evt_{evt}"):
                    selected_events.append(evt)

    st.markdown(
        """
        <div style="margin-top:1rem; padding: 0.6rem 0.75rem;
                    background: rgba(79,195,247,0.06);
                    border: 1px solid rgba(79,195,247,0.18);
                    border-radius: 8px;
                    font-size: 0.72rem; color: rgba(255,255,255,0.7);
                    line-height: 1.45;">
            <div style="color:#4FC3F7; font-weight:600; margin-bottom:0.15rem;">
                🔗 Shareable view
            </div>
            Your current selections are saved in the URL. Copy the browser
            address bar to share this exact view with a teammate.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style="margin-top:1rem; padding-top:0.8rem;
                    border-top:1px solid rgba(255,255,255,0.06);
                    font-size:0.7rem; color:rgba(255,255,255,0.4);
                    line-height:1.5;">
            <strong style="color:rgba(255,255,255,0.6);">Dataset</strong><br/>
            {len(df):,} events • {df['match_id'].nunique():,} matches<br/>
            {df.loc[~df['is_bot'], 'user_id'].nunique():,} humans • {df.loc[df['is_bot'], 'user_id'].nunique():,} bots<br/>
            Feb 10–14, 2026
        </div>
        """,
        unsafe_allow_html=True,
    )

# =============================================================================
# Apply filters
# =============================================================================
scoped = filter_events(
    df,
    maps=[map_id],
    days=selected_days,
    event_types=selected_events,
    include_humans=True,
    include_bots=include_bots,
    user_id=selected_user_id,
)

n_events = len(scoped)
n_matches = scoped["match_id"].nunique()
n_humans = scoped.loc[~scoped["is_bot"], "user_id"].nunique()
n_bots = scoped.loc[scoped["is_bot"], "user_id"].nunique()

# =============================================================================
# Hero
# =============================================================================
who_label = "All players"
if is_specific_player:
    if selected_user_id:
        _is_bot = str(selected_user_id).isdigit()
        _kind = "🤖 Bot" if _is_bot else "🧑 Player"
        who_label = f"{_kind} {str(selected_user_id)[:8]}"
    else:
        who_label = "No player selected"
when_label = "All days" if day_choice == ALL_DAYS_LABEL else day_choice.replace("February_", "Feb ")

st.markdown(
    f"""
    <div class="hero">
        <img class="hero-thumb" src="{minimap_thumbnail_uri(map_id, 120)}"/>
        <div>
            <div class="hero-title">{MAP_CONFIG[map_id]["display_name"]}</div>
            <div class="hero-sub">Exploring {who_label.lower()} • {when_label}</div>
            <div class="chip-row">
                <span class="chip accent">{MAP_CONFIG[map_id]["display_name"]}</span>
                <span class="chip">{when_label}</span>
                <span class="chip">{who_label}</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Metric cards
st.markdown(
    f"""
    <div class="metric-grid">
        <div class="metric-card" style="--acc:#4FC3F7;">
            <div class="label">Events</div>
            <div class="value">{n_events:,}</div>
            <div class="foot">telemetry points in scope</div>
        </div>
        <div class="metric-card" style="--acc:#B388FF;">
            <div class="label">Matches</div>
            <div class="value">{n_matches:,}</div>
            <div class="foot">game sessions</div>
        </div>
        <div class="metric-card" style="--acc:#69F0AE;">
            <div class="label">Humans</div>
            <div class="value">{n_humans:,}</div>
            <div class="foot">unique players</div>
        </div>
        <div class="metric-card" style="--acc:#FFB74D;">
            <div class="label">Bots</div>
            <div class="value">{n_bots:,}</div>
            <div class="foot">AI opponents</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# Tabs
# =============================================================================
tab_heat, tab_coverage, tab_match, tab_player = st.tabs([
    "🔥  Heatmap",
    "🗺️  Coverage",
    "🎬  Match Playback",
    "👤  Players",
])

# -----------------------------------------------------------------------------
# TAB 1 — Heatmap
# -----------------------------------------------------------------------------
with tab_heat:
    heading = ("Where does the action happen?" if not is_specific_player
               else "This player's activity heatmap")
    sub = ("Aggregated across every match on this map for the selected date."
           if not is_specific_player else
           "Aggregated across every match this player took on this map.")
    st.markdown(f"### {heading}")
    st.caption(sub)

    c1, c2, c3 = st.columns([2.5, 1, 1])
    with c1:
        layer_name = st.selectbox(
            "Overlay",
            options=list(HEATMAP_LAYERS.keys()),
            help="What events to bin into the heat.",
        )
    with c2:
        bins = st.number_input(
            "Grid", min_value=20, max_value=120, value=60, step=10,
            help="Higher = finer detail, lower = smoother.",
        )
    with c3:
        map_op = st.slider(
            "Map dim", 0.0, 1.0, 0.45, 0.05,
            help="Fade the minimap so heat colors pop.",
        )

    layer = HEATMAP_LAYERS[layer_name]
    heat_df = filter_events(
        df, maps=[map_id], days=selected_days,
        event_types=layer["events"],
        include_humans=True, include_bots=include_bots,
        user_id=selected_user_id,
    )

    if heat_df.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="icon">🗺️</div>'
            '<div class="title">Nothing to heat up yet</div>'
            '<div>No events of this type match the current selection. '
            'Try a different overlay or loosen the filters in the sidebar.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="font-size:0.8rem; color:rgba(255,255,255,0.6); '
            f'margin-bottom:0.4rem;">Showing <strong>{len(heat_df):,}</strong> '
            f'events in this overlay.</div>',
            unsafe_allow_html=True,
        )
        fig = make_heatmap_figure(
            heat_df, map_id=map_id,
            events_to_bin=layer["events"],
            colorscale=layer["colorscale"],
            bins=int(bins), map_opacity=map_op,
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displaylogo": False})

    with st.expander("Event breakdown for this scope"):
        if not scoped.empty:
            by_event = (scoped["event"].value_counts()
                        .rename("count").rename_axis("event").reset_index())
            st.dataframe(by_event, use_container_width=True, hide_index=True)
        else:
            st.caption("Empty selection.")

# -----------------------------------------------------------------------------
# TAB 1.5 — Coverage / dead zones
# -----------------------------------------------------------------------------
with tab_coverage:
    st.markdown("### Which parts of the map does nobody use?")
    st.caption(
        "Splits the map into a grid and counts player visits per cell. "
        "**Red cells = dead zones** with zero (or near-zero) activity — "
        "areas the level design might be failing to draw players into."
    )

    cvg_c1, cvg_c2, cvg_c3, cvg_c4 = st.columns([1, 1, 1, 1])
    with cvg_c1:
        grid_size = st.select_slider(
            "Grid size",
            options=[10, 15, 20, 25, 30, 40, 50],
            value=20,
            help="Coarser grids find big dead regions; finer grids find small ones.",
        )
    with cvg_c2:
        dead_threshold = st.number_input(
            "Dead if ≤", min_value=0, max_value=50, value=0, step=1,
            help="A cell counts as 'dead' when it has this many visits or fewer.",
        )
    with cvg_c3:
        only_dead = st.toggle(
            "Only show dead zones", value=False,
            help="Hide the activity heat and highlight only the empty cells.",
        )
    with cvg_c4:
        cvg_map_op = st.slider(
            "Map dim", 0.0, 1.0, 0.55, 0.05,
            help="Fade the minimap so cell colors read clearly.",
            key="cvg_map_dim",
        )

    # Coverage is computed from Position events across the current sidebar scope.
    cvg_df = filter_events(
        df, maps=[map_id], days=selected_days,
        event_types=list(MOVEMENT_EVENTS),
        include_humans=True, include_bots=include_bots,
        user_id=selected_user_id,
    )
    cvg_fig, cvg_stats = make_coverage_figure(
        cvg_df, map_id=map_id, grid_size=int(grid_size),
        dead_threshold=int(dead_threshold),
        show_only_dead=only_dead, map_opacity=cvg_map_op,
    )

    # Stat cards
    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card" style="--acc:#69F0AE;">
                <div class="label">Coverage</div>
                <div class="value">{cvg_stats['coverage_pct']:.0f}%</div>
                <div class="foot">of the map has activity</div>
            </div>
            <div class="metric-card" style="--acc:#FF3D47;">
                <div class="label">Dead cells</div>
                <div class="value">{cvg_stats['dead_cells']}</div>
                <div class="foot">of {cvg_stats['total_cells']} total</div>
            </div>
            <div class="metric-card" style="--acc:#4FC3F7;">
                <div class="label">Peak activity</div>
                <div class="value">{cvg_stats['max_activity']:,}</div>
                <div class="foot">visits in the hottest cell</div>
            </div>
            <div class="metric-card" style="--acc:#B388FF;">
                <div class="label">Positions</div>
                <div class="value">{cvg_stats['total_positions']:,}</div>
                <div class="foot">total movement pings in scope</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.plotly_chart(cvg_fig, use_container_width=True,
                    config={"displaylogo": False})

    with st.expander("How to read this"):
        st.markdown("""
- **Red cells** are dead zones — no one (in the current filter) has been there.
- **Bright yellow/green cells** are hot spots — heavy player traffic.
- A high coverage % on a small grid (e.g. 20×20) means players spread out well.
- A low coverage % with big red patches often points to unused corners, unclear
  navigation, or content that isn't drawing players in.
- Increase **Dead if ≤** to find not just empty cells but *rarely-visited* ones
  (e.g. treat any cell with ≤ 3 visits as effectively unused).
        """)

# -----------------------------------------------------------------------------
# TAB 2 — Match Playback
# -----------------------------------------------------------------------------
with tab_match:
    st.markdown("### Watch one match unfold")
    st.caption("Scrub the timeline to reveal events over match progress. "
               "Path lines and event markers are toggleable.")

    match_scope = filter_events(
        df, maps=[map_id], days=selected_days,
        include_humans=True, include_bots=include_bots,
        user_id=selected_user_id,
    )
    ms = match_summary(match_scope)

    if ms.empty:
        st.markdown(
            '<div class="empty-state">'
            '<div class="icon">🎬</div>'
            '<div class="title">No matches to replay</div>'
            '<div>Nothing matches the current sidebar selection. '
            'Try "All days" or switch to "All players" mode.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        col_pick, col_stats = st.columns([2, 1])
        with col_pick:
            match_label = st.selectbox(
                f"Match ({len(ms)} available)",
                options=ms["label"].tolist(), index=0,
                help="Format: short_id | map | day | event count",
            )
            match_row = ms[ms["label"] == match_label].iloc[0]
            match_id = match_row["match_id"]
            match_map = match_row["map_id"]
        with col_stats:
            st.markdown(
                f"""
                <div style="display:grid; grid-template-columns: repeat(2, 1fr);
                            gap:0.4rem; margin-top:1.6rem;">
                    <div class="metric-card" style="--acc:#4FC3F7; padding:0.5rem 0.7rem;">
                        <div class="label">Events</div>
                        <div class="value" style="font-size:1.15rem;">{int(match_row['n_events'])}</div>
                    </div>
                    <div class="metric-card" style="--acc:#69F0AE; padding:0.5rem 0.7rem;">
                        <div class="label">Loot</div>
                        <div class="value" style="font-size:1.15rem;">{int(match_row['n_loot'])}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown('<div class="section-label" style="margin-top:1rem;">'
                    'Playback</div>', unsafe_allow_html=True)
        ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1, 1])
        with ctrl_col1:
            speed = st.select_slider(
                "Playback speed",
                options=["Slow", "Normal", "Fast", "Very fast"],
                value="Normal",
                label_visibility="collapsed",
            )
        with ctrl_col2:
            show_paths = st.toggle("Paths", value=True,
                                   help="Draw movement paths as lines.")
        with ctrl_col3:
            show_events = st.toggle("Events", value=True,
                                    help="Show discrete markers (loot, kills, deaths).")

        st.caption(
            "▶ **Play** to watch the match unfold  •  ⏸ **Pause** anywhere  •  "
            "⏮ **Reset** to start over  •  Drag the slider to jump to any moment"
        )

        speed_ms = {"Slow": 250, "Normal": 120, "Fast": 60, "Very fast": 30}[speed]

        match_df = filter_events(
            df, match_id=match_id, event_types=selected_events,
            include_humans=True, include_bots=include_bots,
        )
        fig = make_match_animation_figure(
            match_df, map_id=match_map,
            show_paths=show_paths, show_events=show_events,
            n_frames=40, frame_ms=speed_ms,
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={"displaylogo": False})

        with st.expander("Match metadata"):
            st.write({
                "match_id": match_id,
                "map_id": match_map,
                "day": str(match_row["day"]),
                "humans": int(match_row["n_humans"]),
                "bots": int(match_row["n_bots"]),
                "loot_pickups": int(match_row["n_loot"]),
                "bot_kills_by_player": int(match_row["n_bot_kills"]),
                "player_deaths_by_bot": int(match_row["n_bot_deaths"]),
                "storm_deaths": int(match_row["n_storm_deaths"]),
            })

# -----------------------------------------------------------------------------
# TAB 3 — Players (leaderboard OR profile)
# -----------------------------------------------------------------------------
with tab_player:
    if not is_specific_player:
        st.markdown("### Top players on this map + date")
        st.caption("Ranked by activity, showing both humans and bots. "
                   "Switch to **Specific player** in the sidebar to drill into any one of them.")
        ps = player_summary(
            filter_events(df, maps=[map_id], days=selected_days,
                          include_humans=True, include_bots=include_bots),
            include_bots=include_bots,
        )
        if ps.empty:
            st.markdown(
                '<div class="empty-state">'
                '<div class="icon">👥</div>'
                '<div class="title">No players in scope</div>'
                '<div>Try a different map/date combination.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            total_players = len(ps)
            n_humans_in_ps = int((~ps["is_bot"]).sum())
            n_bots_in_ps = int(ps["is_bot"].sum())
            # Top-N control - defaults to "All" so nothing is hidden by default
            col_info, col_topn = st.columns([3, 1])
            with col_info:
                bots_txt = f" + <strong>{n_bots_in_ps}</strong> bots" if n_bots_in_ps else ""
                st.markdown(
                    f'<div style="font-size:0.85rem; color:rgba(255,255,255,0.75); '
                    f'margin-top:0.4rem;"><strong>{n_humans_in_ps}</strong> humans'
                    f'{bots_txt} in this scope</div>',
                    unsafe_allow_html=True,
                )
            with col_topn:
                topn_options = ["All"]
                for cap in (10, 25, 50, 100):
                    if cap < total_players:
                        topn_options.append(str(cap))
                topn = st.selectbox(
                    "Show", options=topn_options, index=0,
                    label_visibility="collapsed",
                )
            top = ps.drop(columns=["label", "maps_played", "is_bot", "short_id"],
                          errors="ignore").reset_index(drop=True)
            if topn != "All":
                top = top.head(int(topn))
            top.insert(0, "Rank", range(1, len(top) + 1))
            top["user_id"] = top["user_id"].astype(str).str[:8]
            # Put the Type column right after Rank so classification is the first thing you see.
            type_col = top.pop("type")
            top.insert(1, "Type", type_col)
            top = top.rename(columns={
                "user_id": "Player",
                "n_matches": "Matches",
                "n_events": "Events",
                "n_loot": "Loot",
                "n_bot_kills": "Bot kills",
                "n_bot_deaths": "Bot deaths",
                "n_storm_deaths": "Storm deaths",
            })
            st.dataframe(
                top, use_container_width=True, hide_index=True, height=500,
                column_config={
                    "Events": st.column_config.ProgressColumn(
                        "Events", format="%d",
                        min_value=0, max_value=int(top["Events"].max()),
                    ),
                },
            )
    else:
        if selected_user_id is None:
            st.markdown(
                '<div class="empty-state">'
                '<div class="icon">👤</div>'
                '<div class="title">Pick a player from the sidebar</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            player_all = filter_events(df, user_id=selected_user_id, days=selected_days)
            _is_bot = str(selected_user_id).isdigit()
            _kind = "🤖 Bot" if _is_bot else "🧑 Human player"

            st.markdown(f"### {_kind} · `{str(selected_user_id)[:8]}`")
            st.caption(f"Maps played: **"
                       f"{', '.join(sorted(player_all['map_id'].unique().astype(str)))}**")

            n_m = int(player_all["match_id"].nunique())
            n_bk = int((player_all["event"] == "BotKill").sum())
            n_bd = int((player_all["event"] == "BotKilled").sum())
            n_sd = int((player_all["event"] == "KilledByStorm").sum())
            st.markdown(
                f"""
                <div class="metric-grid">
                    <div class="metric-card" style="--acc:#4FC3F7;">
                        <div class="label">Matches</div>
                        <div class="value">{n_m}</div>
                        <div class="foot">total played</div>
                    </div>
                    <div class="metric-card" style="--acc:#FFC400;">
                        <div class="label">Bot kills</div>
                        <div class="value">{n_bk}</div>
                        <div class="foot">by this player</div>
                    </div>
                    <div class="metric-card" style="--acc:#FF6D00;">
                        <div class="label">Bot deaths</div>
                        <div class="value">{n_bd}</div>
                        <div class="foot">by bots</div>
                    </div>
                    <div class="metric-card" style="--acc:#B388FF;">
                        <div class="label">Storm deaths</div>
                        <div class="value">{n_sd}</div>
                        <div class="foot">caught by zone</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            left, right = st.columns([1, 2])
            with left:
                st.markdown("**Event breakdown**")
                st.plotly_chart(make_player_activity_chart(player_all),
                                use_container_width=True,
                                config={"displaylogo": False})
            with right:
                st.markdown(
                    f"**Activity on {MAP_CONFIG[map_id]['display_name']}**"
                )
                on_map = player_all[player_all["map_id"] == map_id]
                if on_map.empty:
                    st.markdown(
                        '<div class="empty-state" style="padding:1.5rem;">'
                        '<div>This player has no events on the current map + date.</div>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    fig = make_heatmap_figure(
                        on_map, map_id=map_id,
                        events_to_bin=list(EVENT_STYLES.keys()),
                        colorscale="Plasma", bins=50, map_opacity=0.5,
                    )
                    st.plotly_chart(fig, use_container_width=True,
                                    config={"displaylogo": False})

# =============================================================================
# URL sync back — write current sidebar state to browser URL so it's shareable.
# Do this AFTER all widgets have rendered so session_state values are final.
# =============================================================================
_sync_url(
    map=st.session_state.get("ui_map"),
    date=st.session_state.get("ui_date"),
    mode=st.session_state.get("ui_mode"),
    user=selected_user_id,
)

# =============================================================================
# Footer
# =============================================================================
st.markdown(
    """
    <div style="margin-top: 2rem; padding-top: 1rem;
                border-top: 1px solid rgba(255,255,255,0.05);
                font-size: 0.7rem; color: rgba(255,255,255,0.35);
                text-align: center;">
        Built for LILA Games' Level Design team •
        Data: 5 days of production telemetry (Feb 10–14, 2026) •
        Bookmark the URL to save this view • See README.md for architecture &amp; assumptions
    </div>
    """,
    unsafe_allow_html=True,
)
