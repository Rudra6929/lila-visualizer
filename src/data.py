"""Data loading, caching, and filtering helpers.

The parquet file is small (~1.6 MB, 89k rows) so we load the whole thing
once at startup and keep it in a Streamlit cache. Filters run in-memory
against the cached DataFrame.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import streamlit as st

from .config import PARQUET_PATH
from .coords import attach_pixel_coords

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                      r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _is_bot_id(uid: str) -> bool:
    """Bots have short numeric user_ids; humans have UUIDs."""
    return uid.isdigit()


@st.cache_data(show_spinner="Loading LILA event data...")
def load_events(path: str | Path = PARQUET_PATH) -> pd.DataFrame:
    """Load, normalize dtypes, decode event bytes, attach pixel coords.

    The preprocess step already handled most of this, but we defend against
    a raw parquet being uploaded too.
    """
    df = pd.read_parquet(path)

    # Defensive: decode event bytes if the parquet was produced without our
    # preprocessing pass.
    if df["event"].dtype == object:
        sample = df["event"].iloc[0]
        if isinstance(sample, (bytes, bytearray)):
            df["event"] = df["event"].apply(
                lambda v: v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else v
            )

    # Defensive: build is_bot if not present.
    if "is_bot" not in df.columns:
        df["is_bot"] = df["user_id"].astype(str).map(_is_bot_id)

    # Category dtypes reduce memory and speed groupbys.
    for col in ("user_id", "match_id", "map_id", "event"):
        if str(df[col].dtype) != "category":
            df[col] = df[col].astype("category")

    # Extract day from src_file or timestamp if not present.
    if "day" not in df.columns:
        # fall back to a placeholder
        df["day"] = "unknown"
    df["day"] = df["day"].astype("category")

    # Normalize a within-match progress column (0..1). Timestamps in the
    # dataset are compressed (~400ms per match), so absolute time isn't
    # meaningful for the UI - progress is.
    df = df.sort_values(["match_id", "ts"], ignore_index=True)
    grp = df.groupby("match_id", observed=True)["ts"]
    ts_min = grp.transform("min")
    ts_max = grp.transform("max")
    span = (ts_max - ts_min).dt.total_seconds() * 1000  # ms
    elapsed = (df["ts"] - ts_min).dt.total_seconds() * 1000
    # Avoid divide-by-zero for single-event matches
    df["match_progress"] = (elapsed / span.where(span > 0, 1)).fillna(0).astype("float32")

    # Attach pre-computed pixel coordinates for each row.
    df = attach_pixel_coords(df)

    return df


def match_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-match rollup used by the Match Explorer dropdown."""
    agg = df.groupby("match_id", observed=True).agg(
        map_id=("map_id", "first"),
        day=("day", "first"),
        n_events=("event", "size"),
        n_humans=("user_id", lambda s: s[~df.loc[s.index, "is_bot"]].nunique()),
        n_bots=("user_id", lambda s: s[df.loc[s.index, "is_bot"]].nunique()),
        n_loot=("event", lambda s: (s == "Loot").sum()),
        n_bot_kills=("event", lambda s: (s == "BotKill").sum()),
        n_bot_deaths=("event", lambda s: (s == "BotKilled").sum()),
        n_storm_deaths=("event", lambda s: (s == "KilledByStorm").sum()),
    ).reset_index()
    agg["label"] = (
        agg["match_id"].astype(str).str[:8]
        + " | " + agg["map_id"].astype(str)
        + " | " + agg["day"].astype(str)
        + " | " + agg["n_events"].astype(str) + " events"
    )
    return agg.sort_values(["day", "map_id", "match_id"])


def player_summary(df: pd.DataFrame, include_bots: bool = False) -> pd.DataFrame:
    """Per-player rollup used by leaderboards and the sidebar picker.

    By default returns humans only (the specific-player view is only meaningful
    for humans, since bot 'players' don't loot or fight). Set include_bots=True
    for a mixed roster.
    """
    if include_bots:
        pool = df
    else:
        pool = df[~df["is_bot"]]
    agg = pool.groupby("user_id", observed=True).agg(
        n_matches=("match_id", "nunique"),
        n_events=("event", "size"),
        n_loot=("event", lambda s: (s == "Loot").sum()),
        n_bot_kills=("event", lambda s: (s == "BotKill").sum()),
        n_bot_deaths=("event", lambda s: (s == "BotKilled").sum()),
        n_storm_deaths=("event", lambda s: (s == "KilledByStorm").sum()),
        is_bot=("is_bot", "first"),
        maps_played=("map_id", lambda s: ", ".join(sorted(s.unique().astype(str)))),
    ).reset_index()
    # Human/Bot classification made explicit in a "type" column and label.
    agg["type"] = agg["is_bot"].map({True: "🤖 Bot", False: "👤 Human"})
    agg["short_id"] = agg["user_id"].astype(str).str[:8]
    agg["label"] = (
        agg["type"] + " · " + agg["short_id"]
        + " · " + agg["n_matches"].astype(str) + " matches"
        + " · " + agg["n_events"].astype(str) + " events"
    )
    return agg.sort_values("n_events", ascending=False)


def filter_events(
    df: pd.DataFrame,
    *,
    maps: list[str] | None = None,
    days: list[str] | None = None,
    event_types: list[str] | None = None,
    include_humans: bool = True,
    include_bots: bool = True,
    match_id: str | None = None,
    user_id: str | None = None,
    max_progress: float | None = None,
) -> pd.DataFrame:
    """Apply the sidebar filters. Order chosen so cheapest cut runs first."""
    out = df
    if match_id is not None:
        out = out[out["match_id"] == match_id]
    if user_id is not None:
        out = out[out["user_id"] == user_id]
    if maps:
        out = out[out["map_id"].isin(maps)]
    if days:
        out = out[out["day"].isin(days)]
    if event_types:
        out = out[out["event"].isin(event_types)]
    if not include_humans:
        out = out[out["is_bot"]]
    if not include_bots:
        out = out[~out["is_bot"]]
    if max_progress is not None and max_progress < 1.0:
        out = out[out["match_progress"] <= max_progress]
    return out
