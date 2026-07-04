"""Configuration constants for the LILA visualizer.

Keeping styling and map metadata in one place so a Level Designer's tweaks
(colors, marker sizes, adding a new map) only touch a single file.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PARQUET_PATH = DATA_DIR / "all_events.parquet"
MINIMAP_DIR = DATA_DIR / "minimaps"

# ---------------------------------------------------------------------------
# Map configuration (from README)
# world_x, world_z -> pixel_x, pixel_y on a 1024x1024 minimap image
# ---------------------------------------------------------------------------
IMAGE_SIZE = 1024

MAP_CONFIG = {
    "AmbroseValley": {
        "scale": 900,
        "origin_x": -370,
        "origin_z": -473,
        "image": "AmbroseValley_Minimap.png",
        "display_name": "Ambrose Valley",
        "blurb": "Primary map. River-split town with dense POIs.",
    },
    "GrandRift": {
        "scale": 581,
        "origin_x": -290,
        "origin_z": -290,
        "image": "GrandRift_Minimap.png",
        "display_name": "Grand Rift",
        "blurb": "Desert/canyon map with labeled quarters and mine pit.",
    },
    "Lockdown": {
        "scale": 1000,
        "origin_x": -500,
        "origin_z": -500,
        "image": "Lockdown_Minimap.jpg",
        "display_name": "Lockdown",
        "blurb": "Coastal/industrial map. Tighter, close-quarters flow.",
    },
}

# ---------------------------------------------------------------------------
# Event styling
# Colors chosen for legibility on dark minimaps; symbols are Plotly built-ins.
# ---------------------------------------------------------------------------
EVENT_STYLES = {
    # Movement — small, low-emphasis, drawn under everything else
    "Position": {
        "color": "#4FC3F7",  # cyan
        "symbol": "circle",
        "size": 5,
        "opacity": 0.75,
        "category": "movement",
        "label": "Human position",
    },
    "BotPosition": {
        "color": "#9E9E9E",  # gray
        "symbol": "circle",
        "size": 4,
        "opacity": 0.55,
        "category": "movement",
        "label": "Bot position",
    },
    # Combat — bright, prominent
    "Kill": {
        "color": "#FF1744",
        "symbol": "cross",
        "size": 16,
        "opacity": 1.0,
        "category": "combat",
        "label": "Killed a player",
    },
    "Killed": {
        "color": "#B71C1C",
        "symbol": "x",
        "size": 16,
        "opacity": 1.0,
        "category": "combat",
        "label": "Killed by a player",
    },
    "BotKill": {
        "color": "#FFC400",
        "symbol": "cross-thin-open",
        "size": 14,
        "opacity": 1.0,
        "category": "combat",
        "label": "Killed a bot",
    },
    "BotKilled": {
        "color": "#FF6D00",
        "symbol": "x-thin-open",
        "size": 14,
        "opacity": 1.0,
        "category": "combat",
        "label": "Killed by a bot",
    },
    # Environment
    "KilledByStorm": {
        "color": "#B388FF",
        "symbol": "diamond",
        "size": 16,
        "opacity": 1.0,
        "category": "environment",
        "label": "Killed by storm",
    },
    # Loot
    "Loot": {
        "color": "#69F0AE",
        "symbol": "star",
        "size": 11,
        "opacity": 0.95,
        "category": "loot",
        "label": "Loot pickup",
    },
}

# Convenient groupings used by the UI
MOVEMENT_EVENTS = [k for k, v in EVENT_STYLES.items() if v["category"] == "movement"]
COMBAT_EVENTS = [k for k, v in EVENT_STYLES.items() if v["category"] == "combat"]
DISCRETE_EVENTS = [k for k, v in EVENT_STYLES.items() if v["category"] != "movement"]

# Heatmap layer options presented to the user
HEATMAP_LAYERS = {
    "Traffic (all positions)": {"events": ["Position", "BotPosition"], "colorscale": "Viridis"},
    "Human traffic only":      {"events": ["Position"],                "colorscale": "Cividis"},
    "Loot pickups":            {"events": ["Loot"],                    "colorscale": "Greens"},
    "Bot combat (kills+deaths)": {"events": ["BotKill", "BotKilled"],  "colorscale": "YlOrRd"},
    "Bot kills by players":    {"events": ["BotKill"],                 "colorscale": "YlOrRd"},
    "Players killed by bots":  {"events": ["BotKilled"],               "colorscale": "OrRd"},
    "Storm deaths":            {"events": ["KilledByStorm"],           "colorscale": "Purples"},
}
