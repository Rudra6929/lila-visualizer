"""
LILA BLACK preprocessor
-----------------------
Reads all .nakama-0 parquet files under player_data/February_XX/ folders,
combines them into a single parquet, and writes a small summary CSV.

Usage:
    Put this script in the same folder that contains February_11/,
    February_12/, February_13/, February_14/ (and optionally February_10/).
    Then run:
        python preprocess.py

Outputs (created next to this script):
    all_events.parquet   - one combined table, ready to upload
    summary.csv          - quick per-day / per-map / per-event breakdown
"""

import os
import sys
from pathlib import Path
import pyarrow.parquet as pq
import pandas as pd

HERE = Path(__file__).resolve().parent
DAYS = ["February_10", "February_11", "February_12", "February_13", "February_14"]

def load_file(path: Path) -> pd.DataFrame | None:
    try:
        df = pq.read_table(str(path)).to_pandas()
    except Exception as e:
        print(f"  ! skipped {path.name}: {e}")
        return None
    # decode event column from bytes to string
    df["event"] = df["event"].apply(
        lambda v: v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else v
    )
    # tag origin (small strings, cheap)
    df["day"] = path.parent.name
    df["src_file"] = path.name
    return df

def main() -> None:
    frames: list[pd.DataFrame] = []
    total_files = 0
    for day in DAYS:
        day_dir = HERE / day
        if not day_dir.is_dir():
            print(f"[skip] {day}/ not found next to script")
            continue
        files = sorted(day_dir.iterdir())
        print(f"[{day}] {len(files)} files")
        for i, f in enumerate(files, 1):
            df = load_file(f)
            if df is not None:
                frames.append(df)
            total_files += 1
            if i % 100 == 0:
                print(f"  ... {i}/{len(files)}")

    if not frames:
        print("No data loaded. Are the February_XX folders next to this script?")
        sys.exit(1)

    print(f"\nCombining {len(frames)} DataFrames from {total_files} files...")
    df = pd.concat(frames, ignore_index=True)
    df["is_bot"] = df["user_id"].str.match(r"^\d+$")

    # Reasonable dtypes to keep the output small
    for col in ("user_id", "match_id", "map_id", "event", "day", "src_file"):
        df[col] = df[col].astype("category")

    out_parquet = HERE / "all_events.parquet"
    df.to_parquet(out_parquet, compression="zstd", index=False)
    print(f"Wrote {out_parquet} ({out_parquet.stat().st_size/1e6:.2f} MB, {len(df):,} rows)")

    # Small summary CSV - useful sanity check + quick share
    summary = (
        df.groupby(["day", "map_id", "event"], observed=True)
        .size()
        .rename("count")
        .reset_index()
    )
    out_csv = HERE / "summary.csv"
    summary.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv}")

    print("\nHigh-level stats:")
    print(f"  Rows:            {len(df):,}")
    print(f"  Matches:         {df['match_id'].nunique():,}")
    print(f"  Unique players:  {df.loc[~df['is_bot'], 'user_id'].nunique():,}")
    print(f"  Unique bots:     {df.loc[df['is_bot'], 'user_id'].nunique():,}")
    print(f"  Days covered:    {sorted(df['day'].unique().tolist())}")
    print(f"  Maps:            {df['map_id'].value_counts().to_dict()}")

if __name__ == "__main__":
    main()
