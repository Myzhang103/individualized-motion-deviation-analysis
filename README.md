# Individualized Motion Deviation Analysis for Older Adults

[日本語版 / Japanese](README_JA.md)

A research-oriented Python project for analyzing **within-person changes in daily motion** from RGB video and pose landmarks.

The project explores how a person's own usual motion patterns can be used as an individualized reference rather than applying one fixed threshold to everyone.

> **Research status:** This repository contains an exploratory prototype. Its deviation scores are **not fall probabilities**, and the code is **not a clinical fall-risk prediction system**.

## Overview

My earlier work used the UR Fall Detection Dataset to classify fall / non-fall video segments from pose-derived features with a Random Forest model. In 5-fold cross-validation, the mean accuracy was **77.1% ± 17.7%**. I also used SHAP and LIME to inspect model behavior and presented this work at the 67th Annual Meeting of the Japan Ergonomics Society.

The research then shifted from short-term fall-event classification toward a different question:

**Can changes in a person's own daily motion be quantified before interpreting them as fall risk?**

For this purpose, I developed a prototype pipeline using MUVIM RGB daily-activity data, MediaPipe Pose, image-space motion features, robust statistics, and sequential deviation analysis.

## What this repository contains

- RGB-frame pose extraction with **MediaPipe Pose**
- Handling of missing pose frames while preserving original frame numbers
- Eight image-space motion features
- Individualized baselines using **Median / MAD**
- Standardized deviation and a combined Deviation Score
- Exploratory percentile-based deviation screening
- EWMA-based sequential aggregation across trials
- Feature-level contribution summaries
- Exploratory comparison across provisional trial groups
- Small aggregate result files and figures

### Repository scope

This public repository reflects an **early prototype stage** of the research.

Later research work has included additional checks of pose availability, landmark visibility, frame continuity, feature definitions, reference-trial selection, threshold sensitivity, EWMA settings, and correspondence with original RGB frames. Not all of those later validation scripts or research data are included here.

The labels **A / B / C** used in the prototype are provisional trial-group labels. Their mapping to formal participant IDs has not been confirmed, so this repository does not treat them as verified individual identities.

## Technical workflow

1. RGB frames
2. MediaPipe Pose landmark extraction
3. Frame-continuity checks
4. Image-space motion feature calculation
5. Individualized baseline construction with Median / MAD
6. Standardized deviation calculation
7. Exploratory combined Deviation Score
8. Sequential aggregation with EWMA
9. Feature-level and trial-group comparisons

## Motion feature definitions

The source code keeps the original variable names for reproducibility, but several names should **not** be interpreted as physical measurements.

| Code variable | What the current code actually calculates |
|---|---|
| `velocity` | Frame-to-frame 2D displacement of the midpoint of the two hip landmarks in normalized image coordinates. **Not physical walking speed (m/s).** |
| `acceleration` | Difference between consecutive displacement values when three consecutive pose frames are available. **Not acceleration in m/s².** |
| `body_turn_rate` | Absolute frame-to-frame change in shoulder-line orientation. **Not angular velocity.** |
| `symmetry` | Absolute difference between the image y-coordinates of the left and right ankle landmarks. |
| `foot_offset` | Mean absolute x-offset of both ankle landmarks from the hip-center proxy. |
| `ankle_distance` | 2D distance between the two ankle landmarks in normalized image coordinates. |
| `shoulder_hip_angle` | Absolute angular difference between the shoulder line and hip line in the same frame. |
| `movement_variability` | Rolling standard deviation of the displacement feature within continuous pose-detection segments (window up to 15 frames, minimum 5 valid values). |

Because these features are derived from image coordinates, they can be affected by camera viewpoint, projection, pose-estimation errors, and missing landmarks.

## Prototype individualized baseline

The prototype baseline uses robust statistics:

```text
robust_sigma = 1.4826 × MAD
standardized_deviation = |x - median| / robust_sigma
```

The code then averages available feature-level deviations into a frame-level Deviation Score.

A percentile threshold and EWMA are included as **exploratory analysis mechanisms**, not as validated clinical thresholds.

## Prototype example

The current public example uses:

- `NonFall2–5` as baseline trials
- `NonFall6–10` as evaluation trials

This split was chosen for prototype analysis. It **does not represent verified chronological progression from past to future**, and the trial numbers should not be interpreted as dates or risk levels.

![Prototype sequential deviation analysis](figure_sequential_deviation.png)

The figure shows the proportion of frames exceeding an exploratory individual-reference threshold in each evaluation trial. It should be interpreted only as deviation from the prototype reference distribution.

### Provisional trial-group comparison

![Exploratory comparison across provisional trial groups](figure_participant_comparison.png)

The figure compares trial-level feature distributions across provisional groups A / B / C. These labels are retained from the prototype code for reproducibility and should not be treated as confirmed participant identities.

## Data-quality and validation lessons

Subsequent research checks highlighted several points that are important when interpreting pose-derived motion features:

- A successful Pose output does not guarantee accurate landmark localization.
- Missing detections should not be treated as zero motion.
- Frame continuity matters when calculating displacement-based features.
- Extreme shoulder-line changes can sometimes be associated with temporary landmark correspondence changes or nearly coincident shoulder points in selected image sequences.
- Image-space feature values depend on viewpoint and scale and should not be relabeled as physical gait measurements without time and spatial calibration.
- Mixing different daily activities can change feature distributions even if underlying ability is unchanged, so like-for-like activity comparison is important.
- Baseline choice, percentile threshold, EWMA parameters, and observation order can affect exploratory results.
- The relationship between within-person deviation and future fall risk remains a separate validation question.

These findings shifted the research emphasis from simply producing a risk score toward first verifying **what is actually being measured and how reliably it can be interpreted**.

## What this project demonstrates

- Python-based data processing and analysis
- Computer-vision / pose-estimation workflows
- Feature engineering from time-ordered landmark data
- Robust statistics using Median / MAD
- Machine-learning evaluation experience
- Data-quality inspection and technical debugging
- Reproducible analysis pipelines
- Careful interpretation of model-derived measurements

## Repository structure

```text
.
├── README.md
├── README_JA.md
├── DATASET.md
├── requirements.txt
├── figure_sequential_deviation.png
├── figure_participant_comparison.png
├── src/
│   ├── common.py
│   ├── extract_pose.py
│   ├── extract_features.py
│   ├── analyze_individual_deviation.py
│   └── compare_participants.py
└── results/
    ├── participant_a_deviation_summary.csv
    ├── participant_a_feature_contribution.csv
    └── participant_abc_comparison.csv
```

## How to run

**Environment:** Python 3.10+

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Extract pose landmarks

```bash
python src/extract_pose.py \
  --input-root /path/to/ZED_RGB_ADL_COM \
  --output-dir work/pose \
  --model /path/to/pose_landmarker_lite.task \
  --trials 2-10
```

### 3. Extract motion features

```bash
python src/extract_features.py \
  --pose-dir work/pose \
  --output-dir work/features \
  --trials 2-10
```

### 4. Build a prototype individual baseline and evaluate deviation

```bash
python src/analyze_individual_deviation.py \
  --feature-dir work/features \
  --output-dir work/analysis \
  --baseline 2-5 \
  --evaluation 6-10 \
  --percentile 95 \
  --alpha 0.4
```

### 5. Compare provisional trial groups

```bash
python src/compare_participants.py \
  --feature-dir work/features \
  --output-dir work/comparison \
  --group A:2-10 \
  --group B:71-80 \
  --group C:81-90
```

## Data and privacy

This project uses the **MUVIM (Multi Visual Modality Fall Detection Dataset)** for research.

The original videos, RGB frames, and frame-level pose-coordinate files are **not redistributed** in this repository. See [DATASET.md](DATASET.md) for details.

## Technologies

Python / NumPy / pandas / OpenCV / MediaPipe Pose / scikit-learn / Matplotlib / SHAP / LIME / robust statistics (Median, MAD) / EWMA

## Presentation

**Japan Ergonomics Society, 67th Annual Meeting (May 2026)**  
Presentation: *Proposal of a Fall-Risk Evaluation Method for Older Adults Using Skeletal Information and Explainable AI*  
https://pub.confit.atlas.jp/ja/event/jes67/presentation/1B2-03

## Author

**ZHANG MENGYUE (チョウ・ユヅキ)**  
M.S. Candidate, Graduate School of Science and Engineering, Hosei University
