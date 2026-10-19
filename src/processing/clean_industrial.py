"""
Clean WRI industrial data per ADR-005.

Pipeline:
    1. Confirm fossil fuels only (safety re-check)
    2. Drop missing coordinates or zero capacity
    3. Fill missing capacity_mw with median per fuel type
    4. Deduplicate: plants ≤ 1km apart → keep higher capacity

Usage:
    python -m src.processing.clean_industrial

Input/Output: data/external/industrial.parquet  (overwrite in-place)
"""
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parents[2]
INDUSTRIAL_PATH = ROOT / "data" / "external" / "industrial.parquet"

FOSSIL_FUELS = {"Coal", "Oil", "Gas", "Petcoke", "Coke", "Waste"}
DEDUP_DISTANCE_KM = 1.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    )
    return float(2 * R * np.arcsin(np.sqrt(a)))


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Drop plants ≤ 1km apart, keeping the one with higher capacity."""
    df = df.sort_values("capacity_mw", ascending=False).reset_index(drop=True)
    drop_idx: set[int] = set()
    for i in range(len(df)):
        if i in drop_idx:
            continue
        for j in range(i + 1, len(df)):
            if j in drop_idx:
                continue
            d = haversine_km(
                df.at[i, "latitude"], df.at[i, "longitude"],
                df.at[j, "latitude"], df.at[j, "longitude"],
            )
            if d <= DEDUP_DISTANCE_KM:
                drop_idx.add(j)
    return df.drop(index=list(drop_idx)).reset_index(drop=True)


def main():
    if not INDUSTRIAL_PATH.exists():
        raise FileNotFoundError(f"{INDUSTRIAL_PATH} — run fetch_industrial.py first")

    df = pd.read_parquet(INDUSTRIAL_PATH)
    logger.info(f"Loaded {len(df)} plants")

    # 1. Confirm fossil fuels only
    n_before = len(df)
    df = df[df["primary_fuel"].isin(FOSSIL_FUELS)].copy()
    logger.info(f"  Fossil fuels only: {n_before} → {len(df)}")

    # 2. Drop missing coords or zero/null capacity
    df = df.dropna(subset=["latitude", "longitude", "capacity_mw"])
    df = df[df["capacity_mw"] > 0].copy()
    logger.info(f"  Valid coords & capacity: {len(df)}")

    # 3. Fill missing capacity_mw with median per fuel type
    df["capacity_mw"] = df.groupby("primary_fuel")["capacity_mw"].transform(
        lambda x: x.fillna(x.median())
    )

    # 4. Deduplicate by proximity
    n_before = len(df)
    df = deduplicate(df)
    logger.info(f"  Deduplicated (≤{DEDUP_DISTANCE_KM}km): {n_before} → {len(df)}")

    df.to_parquet(INDUSTRIAL_PATH, index=False)
    logger.info(f"\n✓ {INDUSTRIAL_PATH.name}: {len(df)} plants")
    logger.info(f"\n  By fuel:\n{df['primary_fuel'].value_counts().to_string()}")
    logger.info(f"\n  Plants:\n{df[['name','primary_fuel','capacity_mw']].to_string(index=False)}")


if __name__ == "__main__":
    main()
