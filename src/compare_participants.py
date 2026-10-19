"""Compare trial-level feature distributions across multiple participants."""
from __future__ import annotations

import argparse
from pathlib import Path

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


def parse_group(text: str) -> tuple[str, list[int]]:
    if ":" not in text:
        raise ValueError("Use NAME:TRIALS, e.g. A:2-10")
    name, spec = text.split(":", 1)
    return name.strip(), parse_trial_spec(spec)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--group",
        action="append",
        required=True,
        help="Participant label and trials, e.g. --group A:2-10 --group B:71-80",
    )
    args = parser.parse_args()

    feature_dir = Path(args.feature_dir)
    output_dir = ensure_dir(args.output_dir)
    groups = [parse_group(x) for x in args.group]

    trial_rows = []
    for participant, trials in groups:
        for trial in trials:
            path = feature_dir / f"NonFall{trial}_features8.csv"
            if not path.exists():
                print(f"NonFall{trial}: feature CSV not found -> skipped")
                continue
            df = pd.read_csv(path)
            row = {"participant": participant, "video": trial}
            for feature in FEATURES:
                row[feature] = pd.to_numeric(df[feature], errors="coerce").median()
            trial_rows.append(row)

    trial_df = pd.DataFrame(trial_rows)
    trial_df.to_csv(output_dir / "participant_trial_medians.csv", index=False, encoding="utf-8-sig")

    summary_rows = []
    for participant, _ in groups:
        d = trial_df[trial_df["participant"] == participant]
        row = {"participant": participant, "n_trials": len(d)}
        for feature in FEATURES:
            values = d[feature].dropna()
            row[f"{feature}_median"] = values.median()
            row[f"{feature}_iqr"] = values.quantile(0.75) - values.quantile(0.25)
        summary_rows.append(row)

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(output_dir / "participant_comparison.csv", index=False, encoding="utf-8-sig")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
