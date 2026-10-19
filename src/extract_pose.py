"""Extract MediaPipe Pose landmarks from MUVIM RGB frames.

The script expects folders named NonFall<id> under --input-root and reads
left-camera PNG frames. Raw images are not redistributed in this repository.
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from common import ensure_dir, parse_trial_spec


def read_image(path: Path):
    """Read an image robustly on Windows paths that may contain non-ASCII text."""
    try:
        data = np.fromfile(path, dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def extract_trial(folder: Path, trial: int, landmarker, output_path: Path) -> dict:
    files = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.name.lower().startswith("left") and p.suffix.lower() == ".png"
    )

    rows = []
    detected_count = 0
    read_errors = 0
    started = time.time()

    for i, path in enumerate(files, start=1):
        match = re.search(r"(\d+)", path.name)
        frame = int(match.group(1)) if match else i
        row = {"video": trial, "filename": path.name, "frame": frame, "detected": 0}

        img = read_image(path)
        if img is None:
            read_errors += 1
            rows.append(row)
            continue

        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)

        if result.pose_landmarks:
            row["detected"] = 1
            detected_count += 1
            for j, lm in enumerate(result.pose_landmarks[0]):
                row[f"x{j}"] = lm.x
                row[f"y{j}"] = lm.y
                row[f"z{j}"] = lm.z
                row[f"visibility{j}"] = getattr(lm, "visibility", np.nan)

        rows.append(row)

    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")
    elapsed = time.time() - started
    total = len(files)
    rate = detected_count / total * 100 if total else 0.0
    return {
        "video": trial,
        "total_frames": total,
        "pose_detected": detected_count,
        "detection_rate": rate,
        "read_errors": read_errors,
        "elapsed_seconds": elapsed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True, help="Root directory containing NonFall<id> folders")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--model", required=True, help="Path to MediaPipe pose_landmarker_lite.task")
    parser.add_argument("--trials", default="2-10", help="e.g. 2-10 or 2-5,8,10")
    args = parser.parse_args()

    input_root = Path(args.input_root)
    output_dir = ensure_dir(args.output_dir)
    trials = parse_trial_spec(args.trials)

    options = vision.PoseLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=args.model),
        output_segmentation_masks=False,
        running_mode=vision.RunningMode.IMAGE,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    summary = []
    try:
        for trial in trials:
            folder = input_root / f"NonFall{trial}"
            if not folder.is_dir():
                print(f"NonFall{trial}: folder not found -> skipped")
                continue
            output_path = output_dir / f"NonFall{trial}_pose.csv"
            result = extract_trial(folder, trial, landmarker, output_path)
            summary.append(result)
            print(
                f"NonFall{trial}: frames={result['total_frames']}, "
                f"pose={result['pose_detected']}, rate={result['detection_rate']:.2f}%"
            )
    finally:
        landmarker.close()

    pd.DataFrame(summary).to_csv(
        output_dir / "pose_extraction_summary.csv", index=False, encoding="utf-8-sig"
    )


if __name__ == "__main__":
    main()
