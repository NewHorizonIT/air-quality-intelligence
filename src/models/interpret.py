"""
Phase 5 — Interpretation: SHAP feature importance + dependence plots.

SHAP (SHapley Additive exPlanations) giải thích TẠI SAO model đưa ra từng
dự đoán — mỗi feature đóng góp bao nhiêu vào kết quả.

Output:
    reports/figures/shap_summary.png        — tổng quan tầm quan trọng
    reports/figures/shap_beeswarm.png       — phân phối đóng góp từng feature
    reports/figures/shap_dependence_top3.png — quan hệ feature-value vs SHAP
    reports/shap_importance.csv             — bảng feature importance
"""
import logging
import pickle
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

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

GROUP_COLOR = {}
for f in TEMPORAL:    GROUP_COLOR[f] = "#2166ac"
for f in WEATHER:     GROUP_COLOR[f] = "#35978f"
for f in INDUSTRIAL:  GROUP_COLOR[f] = "#d6604d"


def load_model(name: str):
    with open(MODELS_DIR / f"{name}.pkl", "rb") as f:
        return pickle.load(f)


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    val  = pd.read_parquet(FEATURES_DIR / "val.parquet")
    test = pd.read_parquet(FEATURES_DIR / "test.parquet")
    model = load_model("lgbm_exp3_best")

    # Dùng val + test để SHAP có đủ coverage
    df_eval = pd.concat([val, test], ignore_index=True)
    X = df_eval[ALL_FEATS]
    logger.info(f"SHAP input: {X.shape[0]:,} rows × {X.shape[1]} features")

    # ── Tính SHAP values ──────────────────────────────────────────────────────
    logger.info("Computing SHAP values (TreeExplainer)...")
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    logger.info("  ✓ SHAP computed")

    # ── 1. Feature importance (mean |SHAP|) ───────────────────────────────────
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance_df = (
        pd.DataFrame({"feature": ALL_FEATS, "mean_abs_shap": mean_abs_shap})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )
    importance_df.to_csv(REPORTS_DIR / "shap_importance.csv", index=False)
    logger.info("  ✓ Saved shap_importance.csv")

    logger.info("\n── Top 10 features by mean |SHAP| ──")
    for _, row in importance_df.head(10).iterrows():
        logger.info(f"  {row['feature']:30s}  {row['mean_abs_shap']:.3f}")

    # ── 2. Bar chart — mean |SHAP| theo nhóm ─────────────────────────────────
    imp_sorted = importance_df.sort_values("mean_abs_shap", ascending=True)
    bar_colors = [GROUP_COLOR[f] for f in imp_sorted["feature"]]

    fig, ax = plt.subplots(figsize=(8, 9))
    ax.barh(imp_sorted["feature"], imp_sorted["mean_abs_shap"], color=bar_colors)
    ax.set_xlabel("Mean |SHAP value| (µg/m³ impact)")
    ax.set_title("Feature Importance — SHAP\n(Tầm quan trọng trung bình)", fontweight="bold")

    from matplotlib.patches import Patch
    legend_items = [
        Patch(color="#2166ac", label="Temporal"),
        Patch(color="#35978f", label="Weather"),
        Patch(color="#d6604d", label="Industrial"),
    ]
    ax.legend(handles=legend_items, fontsize=9)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "shap_summary.png", bbox_inches="tight")
    plt.close()
    logger.info("  ✓ shap_summary.png")

    # ── 3. Beeswarm plot ──────────────────────────────────────────────────────
    # Lấy top 15 feature để plot không bị chật
    top15 = importance_df.head(15)["feature"].tolist()
    top15_idx = [ALL_FEATS.index(f) for f in top15]

    # plt.figure trước để shap.summary_plot dùng đúng figsize (plot_size=None = reuse current fig)
    plt.figure(figsize=(10, 8))
    shap.summary_plot(
        shap_values[:, top15_idx],
        X[top15],
        feature_names=top15,
        show=False,
        plot_size=None,
        color_bar_label="Feature value (normalized)",
    )
    plt.gca().set_title("SHAP Beeswarm — Top 15 features\n(đỏ = giá trị cao, xanh = giá trị thấp)",
                        fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "shap_beeswarm.png", bbox_inches="tight")
    plt.close()
    logger.info("  ✓ shap_beeswarm.png")

    # ── 4. Dependence plots — top 3 features ─────────────────────────────────
    top3 = importance_df.head(3)["feature"].tolist()
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("SHAP Dependence Plots — Top 3 features\n"
                 "(mỗi điểm = 1 ngày/trạm, trục Y = đóng góp vào dự đoán)",
                 fontweight="bold")

    for ax, feat in zip(axes, top3):
        feat_idx  = ALL_FEATS.index(feat)
        feat_vals = X[feat].values
        shap_vals = shap_values[:, feat_idx]

        sc = ax.scatter(feat_vals, shap_vals, alpha=0.2, s=5,
                        c=feat_vals, cmap="RdYlBu_r")
        ax.axhline(0, color="gray", linewidth=0.8, linestyle="--")
        ax.set_xlabel(feat)
        ax.set_ylabel("SHAP value (µg/m³)")
        ax.set_title(f"{feat}\nmean|SHAP|={importance_df.loc[importance_df['feature']==feat,'mean_abs_shap'].values[0]:.2f}")
        plt.colorbar(sc, ax=ax, label="Feature value")

    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "shap_dependence_top3.png", bbox_inches="tight")
    plt.close()
    logger.info("  ✓ shap_dependence_top3.png")

    # ── 5. Group contribution ─────────────────────────────────────────────────
    # mean(axis=0) → mean |SHAP| per feature, then sum → total group contribution
    # (không dùng .mean() thẳng vì sẽ penalize nhóm nhiều feature hơn)
    group_contrib = {
        "Temporal":   np.abs(shap_values[:, [ALL_FEATS.index(f) for f in TEMPORAL]]).mean(axis=0).sum(),
        "Weather":    np.abs(shap_values[:, [ALL_FEATS.index(f) for f in WEATHER]]).mean(axis=0).sum(),
        "Industrial": np.abs(shap_values[:, [ALL_FEATS.index(f) for f in INDUSTRIAL]]).mean(axis=0).sum(),
    }
    total = sum(group_contrib.values())

    fig, ax = plt.subplots(figsize=(6, 5))
    groups = list(group_contrib.keys())
    vals   = [group_contrib[g] for g in groups]
    colors = ["#2166ac", "#35978f", "#d6604d"]

    bars = ax.bar(groups, vals, color=colors, width=0.5)
    for bar, val in zip(bars, vals):
        pct = val / total * 100
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f"{val:.2f}\n({pct:.1f}%)", ha="center", va="bottom", fontweight="bold")

    ax.set_ylabel("Mean |SHAP value| (µg/m³)")
    ax.set_title("Đóng góp của từng nhóm feature\n(SHAP group contribution)", fontweight="bold")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "shap_group_contribution.png", bbox_inches="tight")
    plt.close()
    logger.info("  ✓ shap_group_contribution.png")

    logger.info("\n── Group contribution ──────────────────────────────────")
    for g, v in group_contrib.items():
        logger.info(f"  {g:12s}  mean|SHAP|={v:.3f}  ({v/total*100:.1f}%)")


if __name__ == "__main__":
    main()
