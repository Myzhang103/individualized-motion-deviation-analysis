"""Extract eight interpretable motion features from pose landmark CSV files."""
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


def calculate_features(df: pd.DataFrame, window: int = 15) -> pd.DataFrame:
    d = df[df["detected"] == 1].copy().sort_values("frame").reset_index(drop=True)

    d["hip_x"] = (d["x23"] + d["x24"]) / 2
    d["hip_y"] = (d["y23"] + d["y24"]) / 2

    shoulder_dx = d["x12"] - d["x11"]
    shoulder_dy = d["y12"] - d["y11"]
    hip_dx = d["x24"] - d["x23"]
    hip_dy = d["y24"] - d["y23"]
    d["shoulder_angle"] = np.arctan2(shoulder_dy, shoulder_dx)
    d["hip_angle"] = np.arctan2(hip_dy, hip_dx)

    # Preserve original frame numbers so missing pose frames are not treated as adjacent.
    d["frame_gap"] = d["frame"].diff()
    continuous = d["frame_gap"] == 1

    dx = d["hip_x"].diff()
    dy = d["hip_y"].diff()
    raw_velocity = np.sqrt(dx**2 + dy**2)
    d["velocity"] = np.where(continuous, raw_velocity, np.nan)

    velocity_diff = d["velocity"].diff()
    valid_acc = continuous & continuous.shift(1, fill_value=False)
    d["acceleration"] = np.where(valid_acc, velocity_diff, np.nan)

    angle_diff = np.arctan2(
        np.sin(d["shoulder_angle"].diff()),
        np.cos(d["shoulder_angle"].diff()),
    )
    d["body_turn_rate"] = np.where(continuous, np.abs(angle_diff), np.nan)

    # Image-coordinate features (not physical centimeters).
    d["symmetry"] = np.abs(d["y27"] - d["y28"])
    d["foot_offset"] = (
        np.abs(d["x27"] - d["hip_x"]) + np.abs(d["x28"] - d["hip_x"])
    ) / 2
    d["ankle_distance"] = np.sqrt(
        (d["x27"] - d["x28"]) ** 2 + (d["y27"] - d["y28"]) ** 2
    )

    orientation_diff = np.arctan2(
        np.sin(d["shoulder_angle"] - d["hip_angle"]),
        np.cos(d["shoulder_angle"] - d["hip_angle"]),
    )
    d["shoulder_hip_angle"] = np.abs(orientation_diff)

    # Rolling variability is calculated only within continuous pose-detection segments.
    segment_id = (d["frame_gap"].fillna(1) != 1).cumsum()
    d["movement_variability"] = d.groupby(segment_id)["velocity"].transform(
        lambda x: x.rolling(window, min_periods=5).std()
    )

    return d[["frame", "frame_gap"] + FEATURES].copy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pose-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--trials", default="2-10")
    parser.add_argument("--window", type=int, default=15)
    args = parser.parse_args()

    pose_dir = Path(args.pose_dir)
    output_dir = ensure_dir(args.output_dir)
    summary = []

    for trial in parse_trial_spec(args.trials):
        input_path = pose_dir / f"NonFall{trial}_pose.csv"
        if not input_path.exists():
            print(f"NonFall{trial}: pose CSV not found -> skipped")
            continue

        result = calculate_features(pd.read_csv(input_path), args.window)
        result.to_csv(
            output_dir / f"NonFall{trial}_features8.csv",
            index=False,
            encoding="utf-8-sig",
        )

        row = {"video": trial, "pose_frames": len(result)}
        for feature in FEATURES:
            values = result[feature].dropna()
            row[f"{feature}_n"] = len(values)
            row[f"{feature}_median"] = values.median()
            row[f"{feature}_mean"] = values.mean()
            row[f"{feature}_std"] = values.std()
        summary.append(row)
        print(f"NonFall{trial}: {len(result)} pose frames")

    pd.DataFrame(summary).to_csv(
        output_dir / "feature_summary.csv", index=False, encoding="utf-8-sig"
    )


if __name__ == "__main__":
    main()
