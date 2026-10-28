"""
Phase 5 — Evaluation: chi tiết metrics theo mùa, theo trạm, theo mức ô nhiễm.

Output:
    reports/evaluation_report.csv   — bảng metrics đầy đủ
    reports/figures/eval_by_season.png
    reports/figures/eval_by_station.png
    reports/figures/eval_by_level.png
    reports/figures/error_heatmap.png
"""
import logging
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ROOT         = Path(__file__).parents[2]
FEATURES_DIR = ROOT / "data" / "features"
MODELS_DIR   = ROOT / "models"
FIGURES_DIR  = ROOT / "reports" / "figures"
REPORTS_DIR  = ROOT / "reports"

plt.rcParams.update({
    "figure.dpi": 120,
    "font.size":  11,
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

TEMPORAL = [
    "pm25_lag1", "pm25_lag2", "pm25_lag3", "pm25_lag7",
    "pm25_roll7_mean", "pm25_roll14_mean", "pm25_roll30_mean",
    "pm25_roll7_std",  "pm25_roll14_std",
    "month_sin", "month_cos", "dow_sin", "dow_cos",
    "season_winter", "season_spring", "season_monsoon",
]
WEATHER    = ["temperature", "wind_speed", "wind_direction", "precipitation", "humidity", "et0"]
INDUSTRIAL = ["dist_nearest_plant_km", "capacity_weighted_dist", "n_plants_50km"]
ALL_FEATS  = TEMPORAL + WEATHER + INDUSTRIAL

WHO_PM25 = 15.0

SEASON_MAP = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Spring",  4: "Spring", 5: "Spring",
    6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Autumn", 11: "Autumn",
}
SEASON_ORDER  = ["Winter", "Spring", "Monsoon", "Autumn"]
SEASON_COLORS = {"Winter": "#4a90d9", "Spring": "#5ab26e", "Monsoon": "#e6ac2a", "Autumn": "#d6604d"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_model(name: str):
    with open(MODELS_DIR / f"{name}.pkl", "rb") as f:
        return pickle.load(f)


def metrics(y_true, y_pred) -> dict:
    return {
        "MAE":  round(mean_absolute_error(y_true, y_pred), 3),
        "RMSE": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3),
        "R2":   round(r2_score(y_true, y_pred), 4),
        "N":    len(y_true),
    }


def add_season(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["season"] = df["date"].dt.month.map(SEASON_MAP)
    return df


def add_pm25_level(df: pd.DataFrame) -> pd.DataFrame:
    """WHO-based pollution levels."""
    df = df.copy()
    bins   = [0, WHO_PM25, 35, 75, 150, float("inf")]
    labels = ["Good", "Moderate", "Unhealthy", "Very Unhealthy", "Hazardous"]
    df["pm25_level"] = pd.cut(df["pm25_target"], bins=bins, labels=labels)
    return df


# ── 1. Overall metrics ─────────────────────────────────────────────────────────

def evaluate_overall(val: pd.DataFrame, test: pd.DataFrame, model) -> list[dict]:
    rows = []
    for split_name, df in [("val", val), ("test", test)]:
        y_true = df["pm25_target"].values
        y_pred = model.predict(df[ALL_FEATS])
        m = metrics(y_true, y_pred)
        rows.append({"split": split_name, "group": "overall", "subgroup": "all", **m})
        logger.info(f"  {split_name} overall — MAE={m['MAE']}  RMSE={m['RMSE']}  R²={m['R2']}")
    return rows


# ── 2. By season ───────────────────────────────────────────────────────────────

def evaluate_by_season(val: pd.DataFrame, test: pd.DataFrame, model) -> list[dict]:
    rows = []
    for split_name, df in [("val", val), ("test", test)]:
        df = add_season(df)
        y_pred_all = model.predict(df[ALL_FEATS])
        df = df.copy()
        df["y_pred"] = y_pred_all
        for season in SEASON_ORDER:
            sub = df[df["season"] == season]
            if len(sub) < 5:
                continue
            m = metrics(sub["pm25_target"].values, sub["y_pred"].values)
            rows.append({"split": split_name, "group": "season", "subgroup": season, **m})
    return rows


def plot_by_season(rows: list[dict]):
    df = pd.DataFrame(rows)
    df = df[df["group"] == "season"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Metrics theo mùa — LightGBM Exp3", fontweight="bold")

    for ax, split_name in zip(axes, ["val", "test"]):
        sub = df[df["split"] == split_name]
        sub = sub.set_index("subgroup").reindex(SEASON_ORDER).dropna()
        colors = [SEASON_COLORS[s] for s in sub.index]

        bars = ax.bar(sub.index, sub["MAE"], color=colors, width=0.5)

        ax.set_title(f"{split_name.capitalize()} set")
        ax.set_ylabel("MAE (µg/m³)")
        ax.set_xlabel("Season")

        # Ghi số N lên trên MAE label
        for i, (season, row) in enumerate(sub.iterrows()):
            ax.text(i, row["MAE"] + 0.3,
                    f"{row['MAE']:.1f}\n(n={int(row['N'])})",
                    ha="center", va="bottom", fontweight="bold", fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "eval_by_season.png", bbox_inches="tight")
    plt.close()
    logger.info("  ✓ eval_by_season.png")


# ── 3. By pollution level ──────────────────────────────────────────────────────

LEVEL_ORDER = ["Good", "Moderate", "Unhealthy", "Very Unhealthy", "Hazardous"]


def evaluate_by_level(val: pd.DataFrame, test: pd.DataFrame, model) -> list[dict]:
    rows = []
    for split_name, df in [("val", val), ("test", test)]:
        df = add_pm25_level(df)
        y_pred_all = model.predict(df[ALL_FEATS])
        df = df.copy()
        df["y_pred"] = y_pred_all
        for level in LEVEL_ORDER:
            sub = df[df["pm25_level"] == level]
            if len(sub) < 5:
                continue
            m = metrics(sub["pm25_target"].values, sub["y_pred"].values)
            rows.append({"split": split_name, "group": "level", "subgroup": level, **m})
    return rows


def plot_by_level(rows: list[dict]):
    df = pd.DataFrame(rows)
    df = df[df["group"] == "level"]
    level_colors = ["#1a9641", "#a6d96a", "#fdae61", "#d7191c", "#7b0000"]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Metrics theo mức ô nhiễm — LightGBM Exp3", fontweight="bold")

    for ax, split_name in zip(axes, ["val", "test"]):
        sub = df[df["split"] == split_name]
        sub = sub.set_index("subgroup").reindex(LEVEL_ORDER).dropna()
        colors = [level_colors[LEVEL_ORDER.index(s)] for s in sub.index]

        x_pos = np.arange(len(sub))
        bars = ax.bar(x_pos, sub["MAE"], color=colors, width=0.5)
        for bar, row in zip(bars, sub.itertuples()):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f"{row.MAE:.1f}\nn={row.N}", ha="center", va="bottom", fontsize=8)

        ax.set_title(f"{split_name.capitalize()} set")
        ax.set_ylabel("MAE (µg/m³)")
        ax.set_xticks(x_pos)
        ax.set_xticklabels(list(sub.index), rotation=15, ha="right")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "eval_by_level.png", bbox_inches="tight")
    plt.close()
    logger.info("  ✓ eval_by_level.png")


# ── 4. By station ──────────────────────────────────────────────────────────────

def evaluate_by_station(test: pd.DataFrame, model) -> list[dict]:
    rows = []
    y_pred_all = model.predict(test[ALL_FEATS])
    df = test.copy()
    df["y_pred"] = y_pred_all
    for station, grp in df.groupby("location_name"):
        if len(grp) < 10:
            continue
        m = metrics(grp["pm25_target"].values, grp["y_pred"].values)
        rows.append({"station": station, **m})
    return rows


def plot_by_station(rows: list[dict]):
    df = pd.DataFrame(rows).sort_values("MAE", ascending=True)

    fig, ax = plt.subplots(figsize=(8, max(5, len(df) * 0.35)))
    colors = ["#d6604d" if mae > 20 else "#4a90d9" for mae in df["MAE"]]
    bars = ax.barh(df["station"], df["MAE"], color=colors)

    for bar, mae in zip(bars, df["MAE"]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f"{mae:.1f}", va="center", fontsize=8)

    ax.axvline(df["MAE"].mean(), color="gray", linewidth=1.2, linestyle="--",
               label=f"Mean MAE = {df['MAE'].mean():.1f}")
    ax.set_xlabel("MAE (µg/m³)")
    ax.set_title("MAE theo từng trạm — Test set", fontweight="bold")
    ax.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "eval_by_station.png", bbox_inches="tight")
    plt.close()
    logger.info("  ✓ eval_by_station.png")


# ── 5. Error heatmap theo tháng × giờ ─────────────────────────────────────────

def plot_error_heatmap(test: pd.DataFrame, model):
    df = test.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.month
    df["y_pred"] = model.predict(df[ALL_FEATS])
    df["abs_error"] = (df["y_pred"] - df["pm25_target"]).abs()

    monthly_mae = df.groupby("month")["abs_error"].mean().reindex(range(1, 13))

    fig, ax = plt.subplots(figsize=(10, 4))
    month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
                    "Jul","Aug","Sep","Oct","Nov","Dec"]
    colors = []
    for m in range(1, 13):
        season = SEASON_MAP[m]
        colors.append(SEASON_COLORS[season])

    bars = ax.bar(range(1, 13), monthly_mae.values, color=colors, width=0.7)
    for bar, val in zip(bars, monthly_mae.values):
        if not np.isnan(val):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                    f"{val:.0f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(month_labels)
    ax.set_ylabel("MAE trung bình (µg/m³)")
    ax.set_title("MAE theo tháng — Test set", fontweight="bold")

    # Legend mùa
    from matplotlib.patches import Patch
    legend_items = [Patch(color=c, label=s) for s, c in SEASON_COLORS.items()]
    ax.legend(handles=legend_items, fontsize=9)

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "error_heatmap.png", bbox_inches="tight")
    plt.close()
    logger.info("  ✓ error_heatmap.png")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    val  = pd.read_parquet(FEATURES_DIR / "val.parquet")
    test = pd.read_parquet(FEATURES_DIR / "test.parquet")
    model = load_model("lgbm_exp3_best")
    logger.info(f"Val {len(val):,} | Test {len(test):,}")

    all_rows = []

    logger.info("\n── Overall ─────────────────────────────────────────────")
    all_rows += evaluate_overall(val, test, model)

    logger.info("\n── By season ───────────────────────────────────────────")
    season_rows = evaluate_by_season(val, test, model)
    all_rows += season_rows
    plot_by_season(season_rows)

    logger.info("\n── By pollution level ──────────────────────────────────")
    level_rows = evaluate_by_level(val, test, model)
    all_rows += level_rows
    plot_by_level(level_rows)

    logger.info("\n── By station (test only) ──────────────────────────────")
    station_rows = evaluate_by_station(test, model)
    plot_by_station(station_rows)

    logger.info("\n── Error by month ──────────────────────────────────────")
    plot_error_heatmap(test, model)

    # Save full report
    df_report = pd.DataFrame(all_rows)
    out = REPORTS_DIR / "evaluation_report.csv"
    df_report.to_csv(out, index=False)
    logger.info(f"\n✓ Saved {out.name}")

    # Print summary
    logger.info("\n── Season MAE summary (test) ───────────────────────────")
    for row in season_rows:
        if row["split"] == "test":
            logger.info(f"  {row['subgroup']:10s}  MAE={row['MAE']:.2f}  N={row['N']}")


if __name__ == "__main__":
    main()
