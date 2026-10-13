"""
Filter WRI Global Power Plant Database for Delhi NCR fossil fuel plants.

Usage:
    python -m src.ingestion.fetch_industrial

Output:
    data/external/industrial.parquet

Columns: name, latitude, longitude, capacity_mw, primary_fuel
"""
import io
import logging
import zipfile
from pathlib import Path

import pandas as pd
import requests

GPPD_URL = "https://wri-dataportal-prod.s3.amazonaws.com/manual/global_power_plant_database_v_1_3.zip"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parents[2]
EXTERNAL_DIR = ROOT / "data" / "external"
GPPD_PATH = EXTERNAL_DIR / "global_power_plant_database.csv"

# Delhi NCR bounding box + 50km buffer (ADR-002)
LAT_MIN, LAT_MAX = 27.5, 29.5
LON_MIN, LON_MAX = 76.0, 78.5

FOSSIL_FUELS = {"Coal", "Oil", "Gas", "Petcoke", "Coke", "Waste"}


def download_gppd():
    logger.info("Downloading WRI Global Power Plant Database...")
    resp = requests.get(GPPD_URL, timeout=120, stream=True)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    chunks = []
    downloaded = 0
    for chunk in resp.iter_content(chunk_size=65536):
        chunks.append(chunk)
        downloaded += len(chunk)
        if total:
            logger.info(f"  {downloaded / 1_000_000:.1f} / {total / 1_000_000:.1f} MB")

    zip_bytes = b"".join(chunks)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
        if not csv_names:
            raise RuntimeError("No CSV found inside the downloaded zip")
        with zf.open(csv_names[0]) as f:
            GPPD_PATH.write_bytes(f.read())
    logger.info(f"  Saved → {GPPD_PATH.name}")


def main():
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    if not GPPD_PATH.exists():
        download_gppd()

    logger.info(f"Reading {GPPD_PATH.name}...")
    df = pd.read_csv(GPPD_PATH, low_memory=False)
    logger.info(f"  Raw: {len(df):,} rows")

    df = df[df["country_long"] == "India"]
    logger.info(f"  India only: {len(df):,} rows")

    df = df[
        (df["latitude"] >= LAT_MIN) & (df["latitude"] <= LAT_MAX) &
        (df["longitude"] >= LON_MIN) & (df["longitude"] <= LON_MAX)
    ]
    logger.info(f"  Delhi NCR bbox: {len(df):,} rows")

    df = df[df["primary_fuel"].isin(FOSSIL_FUELS)]
    logger.info(f"  Fossil fuels only: {len(df):,} rows")

    df = df.dropna(subset=["latitude", "longitude"])
    df = df[df["capacity_mw"] > 0]
    logger.info(f"  Valid coords & capacity: {len(df):,} rows")

    # Fill missing capacity_mw with median per fuel type
    df = df.copy()
    df["capacity_mw"] = df.groupby("primary_fuel")["capacity_mw"].transform(
        lambda x: x.fillna(x.median())
    )

    out = (
        df[["name", "latitude", "longitude", "capacity_mw", "primary_fuel"]]
        .drop_duplicates(subset=["name", "latitude", "longitude"])
        .reset_index(drop=True)
    )

    out_path = EXTERNAL_DIR / "industrial.parquet"
    out.to_parquet(out_path, index=False)
    logger.info(f"✓ {out_path.name}: {len(out)} plants")
    logger.info(f"\n  By fuel:\n{out['primary_fuel'].value_counts().to_string()}")
    logger.info(f"\n  Plant list:\n{out[['name','primary_fuel','capacity_mw']].to_string(index=False)}")


if __name__ == "__main__":
    main()
