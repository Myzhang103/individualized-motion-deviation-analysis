"""Build an individual baseline and quantify within-person motion deviation.

This script measures deviation from a participant's own ADL baseline. The output
is an exploratory state-change score, not a probability of falling.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from common import ensure_dir, parse_trial_spec

FEATURES = [
    "velocity",
    "acceleration",
    "body_turn_rate",
    "symmetry",
    "foot_offset",
    "ankle_distance",
    "shoulder_hip_angle",
    "movement_variability",
]
EPS = 1e-9


def load_feature_data(feature_dir: Path, trials: list[int]) -> dict[int, pd.DataFrame]:
    data = {}
    for trial in trials:
        path = feature_dir / f"NonFall{trial}_features8.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_csv(path)
        missing = [f for f in FEATURES if f not in df.columns]
        if missing:
            raise ValueError(f"NonFall{trial}: missing columns {missing}")
        data[trial] = df
    return data


def build_baseline(data: dict[int, pd.DataFrame], baseline_trials: list[int]) -> pd.DataFrame:
    rows = []
    for feature in FEATURES:
        values = pd.concat(
            [pd.to_numeric(data[t][feature], errors="coerce") for t in baseline_trials],
            ignore_index=True,
        ).dropna().to_numpy(float)
        median = np.median(values)
        mad = np.median(np.abs(values - median))
        robust_sigma = max(1.4826 * mad, EPS)
        rows.append(
            {
                "feature": feature,
                "n": len(values),
                "median": median,
                "MAD": mad,
                "robust_sigma": robust_sigma,
            }
        )
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--baseline", default="2-5")
    parser.add_argument("--evaluation", default="6-10")
    parser.add_argument("--percentile", type=float, default=95.0)
    parser.add_argument("--alpha", type=float, default=0.4)
    args = parser.parse_args()

    feature_dir = Path(args.feature_dir)
    output_dir = ensure_dir(args.output_dir)
    baseline_trials = parse_trial_spec(args.baseline)
    evaluation_trials = parse_trial_spec(args.evaluation)
    trials = baseline_trials + evaluation_trials
    data = load_feature_data(feature_dir, trials)

    baseline_df = build_baseline(data, baseline_trials)
    baseline_df.to_csv(output_dir / "individual_baseline.csv", index=False, encoding="utf-8-sig")
    baseline = baseline_df.set_index("feature").to_dict("index")

    deviation_data = {}
    for trial in trials:
        df = data[trial].copy()
        z_cols = []
        for feature in FEATURES:
            x = pd.to_numeric(df[feature], errors="coerce")
            z_name = f"z_{feature}"
            df[z_name] = np.abs(x - baseline[feature]["median"]) / baseline[feature]["robust_sigma"]
            z_cols.append(z_name)
        df["available_feature_n"] = df[z_cols].notna().sum(axis=1)
        df["deviation_score"] = df[z_cols].mean(axis=1, skipna=True)
        df.loc[df["available_feature_n"] == 0, "deviation_score"] = np.nan
        deviation_data[trial] = df

    pooled_baseline = pd.concat(
        [deviation_data[t]["deviation_score"] for t in baseline_trials],
        ignore_index=True,
    ).dropna()
    threshold = float(np.percentile(pooled_baseline, args.percentile))

    summary_rows = []
    for trial in trials:
        d = deviation_data[trial]["deviation_score"].dropna()
        n_valid = len(d)
        n_large = int((d > threshold).sum()) if n_valid else 0
        summary_rows.append(
            {
                "video": trial,
                "phase": "Baseline" if trial in baseline_trials else "Evaluation",
                "valid_frames": n_valid,
                "median_deviation": d.median() if n_valid else np.nan,
                "mean_deviation": d.mean() if n_valid else np.nan,
                "large_deviation_frames": n_large,
                "large_deviation_rate": n_large / n_valid * 100 if n_valid else np.nan,
            }
        )
    summary = pd.DataFrame(summary_rows)

    ewma = None
    for trial in evaluation_trials:
        idx = summary.index[summary["video"] == trial][0]
        current = summary.loc[idx, "large_deviation_rate"]
        if pd.isna(current):
            summary.loc[idx, "long_term_trend"] = np.nan
            continue
        ewma = current if ewma is None else args.alpha * current + (1 - args.alpha) * ewma
        summary.loc[idx, "long_term_trend"] = ewma

    contribution_rows = []
    for trial in evaluation_trials:
        df = deviation_data[trial]
        mean_z = {f: df[f"z_{f}"].mean(skipna=True) for f in FEATURES}
        total = np.nansum(list(mean_z.values()))
        row = {"video": trial}
        for feature in FEATURES:
            row[feature] = mean_z[feature] / total * 100 if total > 0 else np.nan
        contribution_rows.append(row)

    summary.to_csv(output_dir / "deviation_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(contribution_rows).to_csv(
        output_dir / "feature_contribution.csv", index=False, encoding="utf-8-sig"
    )
    (output_dir / "analysis_settings.txt").write_text(
        f"baseline_trials={baseline_trials}\n"
        f"evaluation_trials={evaluation_trials}\n"
        f"percentile={args.percentile}\n"
        f"threshold={threshold:.10f}\n"
        f"ewma_alpha={args.alpha}\n",
        encoding="utf-8",
    )

    print(f"Individual threshold (P{args.percentile:g}): {threshold:.6f}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
