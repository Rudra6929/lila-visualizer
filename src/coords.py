"""World-to-minimap coordinate conversion.

Implements the formula from the README:

    u = (x - origin_x) / scale
    v = (z - origin_z) / scale
    pixel_x = u * IMAGE_SIZE
    pixel_y = (1 - v) * IMAGE_SIZE   # Y flipped: image origin is top-left

Verified numerically against the README's worked example (world=(-301.45,
-355.55) on AmbroseValley -> pixel=(78, 890)) and against the full dataset
(100% of points fall inside the 0-1024 box on all three maps).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import IMAGE_SIZE, MAP_CONFIG


def world_to_pixel(
    x: np.ndarray | pd.Series | float,
    z: np.ndarray | pd.Series | float,
    map_id: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert world (x, z) to minimap (pixel_x, pixel_y). Vectorized."""
    cfg = MAP_CONFIG[map_id]
    u = (np.asarray(x, dtype=np.float64) - cfg["origin_x"]) / cfg["scale"]
    v = (np.asarray(z, dtype=np.float64) - cfg["origin_z"]) / cfg["scale"]
    pixel_x = u * IMAGE_SIZE
    pixel_y = (1.0 - v) * IMAGE_SIZE
    return pixel_x, pixel_y


def attach_pixel_coords(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with `px` and `py` columns added.

    Handles heterogeneous map_ids in one pass by grouping.
    """
    out = df.copy()
    out["px"] = np.nan
    out["py"] = np.nan
    for m, sub in out.groupby("map_id", observed=True):
        if m not in MAP_CONFIG:
            continue
        px, py = world_to_pixel(sub["x"].to_numpy(), sub["z"].to_numpy(), m)
        out.loc[sub.index, "px"] = px
        out.loc[sub.index, "py"] = py
    return out
