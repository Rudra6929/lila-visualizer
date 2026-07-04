"""Plotly figure builders.

Every figure is anchored to a 1024x1024 minimap image drawn as the plot
background. All coordinates use pixel space (0..1024 for x, 1024..0 for y
so the image origin is top-left, matching the README convention).
"""

from __future__ import annotations

import base64
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image

from .config import (
    EVENT_STYLES,
    IMAGE_SIZE,
    MAP_CONFIG,
    MINIMAP_DIR,
    MOVEMENT_EVENTS,
)


# ---------------------------------------------------------------------------
# Minimap image handling
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _minimap_data_uri(map_id: str) -> str:
    """Return a base64 data URI for the minimap image.

    Plotly's `layout.images.source` accepts URLs or data URIs. We use a data
    URI so the deployed app doesn't need to serve static files separately.
    """
    path = MINIMAP_DIR / MAP_CONFIG[map_id]["image"]
    img = Image.open(path).convert("RGB")
    # Downsize slightly if huge - the minimaps in this dataset are already 1024.
    if max(img.size) > 1024:
        img.thumbnail((1024, 1024))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


@st.cache_data(show_spinner=False)
def minimap_thumbnail_uri(map_id: str, size: int = 280) -> str:
    """Small thumbnail data URI for use in HTML preview cards in the UI."""
    path = MINIMAP_DIR / MAP_CONFIG[map_id]["image"]
    img = Image.open(path).convert("RGB")
    img.thumbnail((size, size))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=82)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _base_figure(map_id: str, title: str | None = None, height: int = 720) -> go.Figure:
    """Empty figure with the minimap as background and axes locked to pixel space."""
    fig = go.Figure()
    fig.add_layout_image(
        dict(
            source=_minimap_data_uri(map_id),
            xref="x",
            yref="y",
            x=0,
            y=0,
            sizex=IMAGE_SIZE,
            sizey=IMAGE_SIZE,
            sizing="stretch",
            layer="below",
            opacity=1.0,
        )
    )
    fig.update_xaxes(
        range=[0, IMAGE_SIZE],
        showgrid=False,
        zeroline=False,
        visible=False,
        constrain="domain",
    )
    fig.update_yaxes(
        range=[IMAGE_SIZE, 0],  # flipped
        showgrid=False,
        zeroline=False,
        visible=False,
        scaleanchor="x",
        scaleratio=1,
    )
    fig.update_layout(
        title=title,
        height=height,
        margin=dict(l=0, r=0, t=40 if title else 10, b=0),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
        legend=dict(
            bgcolor="rgba(20,20,20,0.6)",
            bordercolor="rgba(255,255,255,0.15)",
            borderwidth=1,
            font=dict(size=11),
            itemsizing="constant",
        ),
        hoverlabel=dict(bgcolor="#1e1e1e", font_size=12),
    )
    return fig


# ---------------------------------------------------------------------------
# Match view — paths and event markers
# ---------------------------------------------------------------------------
def make_match_figure(
    match_df: pd.DataFrame,
    map_id: str,
    show_paths: bool = True,
    show_events: bool = True,
    max_progress: float = 1.0,
) -> go.Figure:
    """Build a figure showing player+bot paths and discrete events for a match.

    Filters to events with match_progress <= max_progress so the timeline
    slider can 'reveal' the match over time.
    """
    fig = _base_figure(map_id, height=720)
    if match_df.empty:
        fig.add_annotation(text="No events for this selection",
                           showarrow=False, font=dict(color="#fafafa", size=14))
        return fig

    df = match_df[match_df["match_progress"] <= max_progress]
    if df.empty:
        return fig

    # ------- Path lines (one per user) -------
    if show_paths:
        # Order matters for path continuity
        for uid, sub in df[df["event"].isin(MOVEMENT_EVENTS)].groupby("user_id", observed=True):
            if sub.empty:
                continue
            sub = sub.sort_values("ts")
            is_bot = bool(sub["is_bot"].iloc[0])
            style = EVENT_STYLES["BotPosition" if is_bot else "Position"]
            fig.add_trace(
                go.Scatter(
                    x=sub["px"],
                    y=sub["py"],
                    mode="lines",
                    line=dict(
                        color=style["color"],
                        width=1.6 if is_bot else 2.0,
                        dash="dot" if is_bot else "solid",
                    ),
                    opacity=0.55 if is_bot else 0.75,
                    name=f"{'🤖 Bot' if is_bot else '🧑 Player'} {str(uid)[:8]}",
                    legendgroup="paths",
                    legendgrouptitle_text="Paths",
                    hovertemplate=(f"<b>{'🤖 Bot' if is_bot else '🧑 Player'}</b>: {str(uid)[:8]}"
                                   "<extra></extra>"),
                )
            )

    # ------- Discrete event markers -------
    if show_events:
        for evt_name, style in EVENT_STYLES.items():
            if style["category"] == "movement":
                continue
            sub = df[df["event"] == evt_name]
            if sub.empty:
                continue
            fig.add_trace(
                go.Scatter(
                    x=sub["px"],
                    y=sub["py"],
                    mode="markers",
                    marker=dict(
                        color=style["color"],
                        symbol=style["symbol"],
                        size=style["size"],
                        opacity=style["opacity"],
                        line=dict(color="rgba(0,0,0,0.6)", width=1),
                    ),
                    name=style["label"],
                    legendgroup="events",
                    legendgrouptitle_text="Events",
                    customdata=np.column_stack([
                        sub["user_id"].astype(str),
                        sub["match_progress"] * 100,
                    ]),
                    hovertemplate=(
                        f"<b>{style['label']}</b><br>"
                        "User: %{customdata[0]}<br>"
                        "Progress: %{customdata[1]:.1f}%<br>"
                        "World: (%{x:.0f}, %{y:.0f})"
                        "<extra></extra>"
                    ),
                )
            )
    return fig


# ---------------------------------------------------------------------------
# Animated match view — proper Plotly frames with play/pause controls
# ---------------------------------------------------------------------------
def make_match_animation_figure(
    match_df: pd.DataFrame,
    map_id: str,
    show_paths: bool = True,
    show_events: bool = True,
    n_frames: int = 40,
    frame_ms: int = 120,
) -> go.Figure:
    """Animated match figure. Play/Pause/Reset buttons + progress slider.

    Uses native Plotly frames (client-side animation) rather than a Streamlit
    rerun loop, so playback is smooth. Each frame reveals cumulative events
    up to that progress %.
    """
    fig = _base_figure(map_id, height=720)

    if match_df.empty:
        fig.add_annotation(
            text="No events for this match",
            showarrow=False, font=dict(color="#fafafa", size=14),
        )
        return fig

    df = match_df.sort_values("ts").reset_index(drop=True)

    # Discover trace slots: one per user's path + one per event type present.
    # Each frame updates these slots with cumulative data <= progress.
    trace_specs: list[tuple] = []  # (kind, key, style, is_bot)
    if show_paths:
        for uid, sub in df[df["event"].isin(MOVEMENT_EVENTS)].groupby(
            "user_id", observed=True
        ):
            if sub.empty:
                continue
            is_bot = bool(sub["is_bot"].iloc[0])
            style = EVENT_STYLES["BotPosition" if is_bot else "Position"]
            trace_specs.append(("path", uid, style, is_bot))
    if show_events:
        for evt_name, style in EVENT_STYLES.items():
            if style["category"] == "movement":
                continue
            if (df["event"] == evt_name).any():
                trace_specs.append(("event", evt_name, style, None))

    if not trace_specs:
        return fig

    # Base traces (empty; frames will fill them in)
    for kind, key, style, is_bot in trace_specs:
        if kind == "path":
            fig.add_trace(go.Scatter(
                x=[], y=[], mode="lines",
                line=dict(
                    color=style["color"],
                    width=2.0 if not is_bot else 1.6,
                    dash="solid" if not is_bot else "dot",
                ),
                opacity=0.75 if not is_bot else 0.55,
                name=f"{'🤖 Bot' if is_bot else '🧑 Player'} {str(key)[:8]}",
                legendgroup="paths",
                legendgrouptitle_text="Paths",
                hovertemplate=(
                    f"<b>{'🤖 Bot' if is_bot else '🧑 Player'}</b>: {str(key)[:8]}"
                    "<extra></extra>"
                ),
            ))
        else:  # event
            fig.add_trace(go.Scatter(
                x=[], y=[], mode="markers",
                marker=dict(
                    color=style["color"], symbol=style["symbol"],
                    size=style["size"], opacity=style["opacity"],
                    line=dict(color="rgba(0,0,0,0.6)", width=1),
                ),
                name=style["label"],
                legendgroup="events",
                legendgrouptitle_text="Events",
                hovertemplate=(
                    f"<b>{style['label']}</b><br>"
                    "World: (%{x:.0f}, %{y:.0f})<extra></extra>"
                ),
            ))

    # Precompute grouped data for speed inside the frame loop.
    by_user_path = {
        uid: sub.sort_values("ts")
        for uid, sub in df[df["event"].isin(MOVEMENT_EVENTS)].groupby(
            "user_id", observed=True
        )
    }
    by_event = {evt: df[df["event"] == evt] for evt, style in EVENT_STYLES.items()
                if style["category"] != "movement"}

    # Build frames
    progress_steps = np.linspace(0.0, 1.0, n_frames + 1)
    frames: list[go.Frame] = []
    for progress in progress_steps:
        frame_traces: list[dict] = []
        for kind, key, style, is_bot in trace_specs:
            if kind == "path":
                sub = by_user_path.get(key)
                if sub is None or sub.empty:
                    frame_traces.append(dict(x=[], y=[]))
                    continue
                mask = sub["match_progress"] <= progress
                frame_traces.append(dict(
                    x=sub.loc[mask, "px"].tolist(),
                    y=sub.loc[mask, "py"].tolist(),
                ))
            else:  # event
                sub = by_event.get(key)
                if sub is None or sub.empty:
                    frame_traces.append(dict(x=[], y=[]))
                    continue
                mask = sub["match_progress"] <= progress
                frame_traces.append(dict(
                    x=sub.loc[mask, "px"].tolist(),
                    y=sub.loc[mask, "py"].tolist(),
                ))
        frames.append(go.Frame(data=frame_traces, name=f"{int(round(progress * 100))}"))

    fig.frames = frames

    # Play / Pause / Reset controls above the plot
    fig.update_layout(
        updatemenus=[dict(
            type="buttons",
            direction="left",
            x=0.0, y=1.08,
            xanchor="left", yanchor="top",
            pad=dict(t=4, r=8, l=4, b=4),
            showactive=False,
            bgcolor="rgba(255,255,255,0.06)",
            bordercolor="rgba(255,255,255,0.15)",
            font=dict(color="#fafafa", size=12),
            buttons=[
                dict(
                    label="▶  Play",
                    method="animate",
                    args=[None, dict(
                        frame=dict(duration=frame_ms, redraw=True),
                        fromcurrent=True,
                        transition=dict(duration=40, easing="linear"),
                    )],
                ),
                dict(
                    label="⏸  Pause",
                    method="animate",
                    args=[[None], dict(
                        frame=dict(duration=0, redraw=False),
                        mode="immediate",
                        transition=dict(duration=0),
                    )],
                ),
                dict(
                    label="⏮  Reset",
                    method="animate",
                    args=[[frames[0].name], dict(
                        frame=dict(duration=0, redraw=True),
                        mode="immediate",
                        transition=dict(duration=0),
                    )],
                ),
            ],
        )],
        sliders=[dict(
            active=0,  # start empty; user hits Play
            x=0.20, y=1.06, len=0.78,
            xanchor="left", yanchor="top",
            pad=dict(t=0, b=0),
            currentvalue=dict(
                prefix="Progress: ", suffix="%",
                font=dict(color="#4FC3F7", size=12),
                xanchor="right", offset=6,
            ),
            transition=dict(duration=40),
            font=dict(color="rgba(255,255,255,0.55)", size=10),
            bgcolor="rgba(255,255,255,0.08)",
            activebgcolor="#4FC3F7",
            tickcolor="rgba(255,255,255,0.2)",
            ticklen=3,
            steps=[
                dict(
                    method="animate",
                    args=[[f.name], dict(
                        mode="immediate",
                        frame=dict(duration=0, redraw=True),
                        transition=dict(duration=0),
                    )],
                    label="" if i % 5 else f.name + "%",
                )
                for i, f in enumerate(frames)
            ],
        )],
        margin=dict(t=80),  # room for buttons + slider
    )
    return fig
def make_heatmap_figure(
    df: pd.DataFrame,
    map_id: str,
    events_to_bin: list[str],
    colorscale: str = "Viridis",
    bins: int = 60,
    map_opacity: float = 0.45,
) -> go.Figure:
    """2D histogram of event locations, overlaid on a dimmed minimap.

    Dimming the minimap makes the heat colors readable while keeping the
    map geography as a mental anchor for the Level Designer.
    """
    sub = df[df["event"].isin(events_to_bin)]
    fig = _base_figure(map_id, height=720)
    # Dim the map so heat colors pop
    fig.layout.images[0].opacity = map_opacity

    if sub.empty:
        fig.add_annotation(text="No events match the current filters",
                           showarrow=False, font=dict(color="#fafafa", size=14))
        return fig

    fig.add_trace(
        go.Histogram2d(
            x=sub["px"],
            y=sub["py"],
            xbins=dict(start=0, end=IMAGE_SIZE, size=IMAGE_SIZE / bins),
            ybins=dict(start=0, end=IMAGE_SIZE, size=IMAGE_SIZE / bins),
            colorscale=colorscale,
            opacity=0.75,
            zsmooth="best",
            hovertemplate="Events here: %{z}<extra></extra>",
            colorbar=dict(title="events", thickness=12, len=0.55, x=1.02),
            showscale=True,
        )
    )
    return fig


# ---------------------------------------------------------------------------
# Coverage / dead-zone view
# ---------------------------------------------------------------------------
def make_coverage_figure(
    df: pd.DataFrame,
    map_id: str,
    grid_size: int = 20,
    dead_threshold: int = 0,
    show_only_dead: bool = False,
    map_opacity: float = 0.5,
) -> tuple[go.Figure, dict]:
    """Grid-based coverage map for finding under-utilized regions.

    Splits the 1024x1024 minimap into `grid_size x grid_size` cells and counts
    Position events per cell. Cells at or below `dead_threshold` are painted
    red (dead zones). Active cells show a heat overlay of visit counts.

    Returns (figure, stats_dict) so the caller can render a summary alongside.
    """
    fig = _base_figure(map_id, height=720)
    fig.layout.images[0].opacity = map_opacity

    pos = df[df["event"].isin(MOVEMENT_EVENTS)]
    default_stats = {
        "total_cells": grid_size * grid_size, "dead_cells": 0,
        "active_cells": 0, "coverage_pct": 0.0,
        "max_activity": 0, "total_positions": 0,
    }
    if pos.empty:
        fig.add_annotation(
            text="No movement data for this scope",
            showarrow=False, font=dict(color="#fafafa", size=14),
        )
        return fig, default_stats

    # Bin into grid using pre-computed pixel coords.
    cell = IMAGE_SIZE / grid_size
    x_edges = np.linspace(0, IMAGE_SIZE, grid_size + 1)
    y_edges = np.linspace(0, IMAGE_SIZE, grid_size + 1)
    counts, _, _ = np.histogram2d(
        pos["px"].to_numpy(), pos["py"].to_numpy(),
        bins=[x_edges, y_edges],
    )
    # histogram2d returns (nx, ny); Plotly Heatmap wants z[y][x], hence .T
    counts = counts.T

    total_cells = grid_size * grid_size
    dead_mask = counts <= dead_threshold
    dead_cells = int(dead_mask.sum())
    active_cells = total_cells - dead_cells
    coverage_pct = (active_cells / total_cells) * 100.0

    x_centers = x_edges[:-1] + cell / 2
    y_centers = y_edges[:-1] + cell / 2

    # Trace 1: dead cells rendered as opaque red overlay.
    dead_z = np.where(dead_mask, 1.0, np.nan)
    fig.add_trace(go.Heatmap(
        z=dead_z, x=x_centers, y=y_centers,
        colorscale=[[0, "rgba(255, 60, 70, 0.70)"],
                    [1, "rgba(255, 60, 70, 0.70)"]],
        showscale=False,
        hovertemplate=(
            "<b>Dead zone</b><br>"
            f"≤ {dead_threshold} visit{'s' if dead_threshold != 1 else ''}"
            "<extra></extra>"
        ),
        name="Dead zones",
    ))

    if not show_only_dead:
        # Trace 2: activity heat for non-dead cells.
        active_z = np.where(dead_mask, np.nan, counts)
        fig.add_trace(go.Heatmap(
            z=active_z, x=x_centers, y=y_centers,
            colorscale="Viridis",
            opacity=0.72,
            zmin=max(1, dead_threshold + 1),
            colorbar=dict(
                title="visits", thickness=10, len=0.5, x=1.02,
                tickfont=dict(color="#fafafa"),
                title_font=dict(color="#fafafa"),
            ),
            hovertemplate="Visits: %{z:.0f}<extra></extra>",
            name="Activity",
        ))

    stats = {
        "total_cells": total_cells,
        "dead_cells": dead_cells,
        "active_cells": active_cells,
        "coverage_pct": coverage_pct,
        "max_activity": int(counts.max()),
        "total_positions": int(counts.sum()),
    }
    return fig, stats


# ---------------------------------------------------------------------------
# Player profile - small activity chart per map
# ---------------------------------------------------------------------------
def make_player_activity_chart(player_df: pd.DataFrame) -> go.Figure:
    """Horizontal bar of event counts per event type for one player."""
    counts = player_df["event"].value_counts()
    counts = counts.reindex(list(EVENT_STYLES.keys())).dropna()
    colors = [EVENT_STYLES[e]["color"] for e in counts.index]
    fig = go.Figure(
        go.Bar(
            x=counts.values,
            y=[EVENT_STYLES[e]["label"] for e in counts.index],
            orientation="h",
            marker=dict(color=colors),
            hovertemplate="%{x} events<extra></extra>",
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", title="count"),
        yaxis=dict(autorange="reversed"),
    )
    return fig
