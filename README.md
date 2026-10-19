# Individualized Motion Deviation Analysis for Older Adults

大学院研究で作成した、高齢者の日常動作を骨格情報から解析する Python プロジェクトです。
一律の基準だけで評価するのではなく、**本人の日常動作を個人別 Baseline とし、本人の通常状態からの変化を定量化する**ことを目的としています。

> **Important:** 現在の Deviation Score は「転倒確率」を表すものではありません。本人の通常状態からの個人内変化を表す探索的な指標であり、転倒リスクとの関係は現在検証中です。

## Background

前期研究では UR Fall Detection Dataset を用いて、骨格特徴量から Random Forest による転倒・日常動作分類を行いました。5-fold cross-validation の平均精度は **77.1% ± 17.7%** で、SHAP / LIME を用いてモデルの判断根拠も分析し、日本人間工学会で発表しました。

その後、「転倒直前の特徴」だけでなく、高齢者本人の普段の状態からの変化を捉える必要があると考え、MUVIM の高齢者 ADL データを用いた個人別評価へ研究を発展させています。

## Pipeline

1. RGB frames → MediaPipe Pose による 33 点の骨格ランドマーク抽出
2. フレーム番号を保持し、Pose 未検出区間をまたがないよう連続性を確認
3. 8 種類の骨格特徴量を算出
4. Median / MAD を用いて個人別 Baseline を構築
5. 各特徴量の標準化逸脱度を計算
6. 複数特徴量を Deviation Score として統合
7. Baseline 分布から探索的閾値（P95）を設定
8. 複数試行の変化を EWMA で逐次的に確認
9. 特徴量別寄与率と複数 Participant の個人差を分析

## Motion features

- `velocity`: 腰部中心のフレーム間 2D 移動量
- `acceleration`: 連続フレーム間の速度変化
- `body_turn_rate`: 肩線方向角のフレーム間変化量
- `symmetry`: 左右足関節の画像 y 座標差
- `foot_offset`: 腰部中心に対する左右足関節の x 方向偏差
- `ankle_distance`: 左右足関節間の 2D 距離
- `shoulder_hip_angle`: 肩線と腰線の方向差
- `movement_variability`: 連続区間内の移動速度の局所的な標準偏差

各距離は MediaPipe の正規化画像座標に基づくため、実空間の cm 単位ではありません。

## Repository structure

```text
.
├── README.md
├── DATASET.md
├── requirements.txt
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

## Example results

Participant A の試作では、NonFall2–5 を Baseline、NonFall6–10 を Evaluation として使用しました。
Baseline の Deviation Score 分布から得た P95 は **5.61** でした。
Evaluation の基準閾値超過フレーム割合は、NonFall6–10 でそれぞれ **11.10%, 3.26%, 9.38%, 9.72%, 9.98%** でした。

また、3 名の高齢者を比較したところ、特徴量の中心値だけでなく試行間のばらつきにも個人差が確認されました。この結果は「全員に同一の基準を適用するのではなく、本人の通常状態を基準に変化を見る」という研究方針を検討する根拠の一つとして扱っています。

## How to run

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

### 4. Build an individual baseline and evaluate deviation

```bash
python src/analyze_individual_deviation.py \
  --feature-dir work/features \
  --output-dir work/analysis \
  --baseline 2-5 \
  --evaluation 6-10 \
  --percentile 95 \
  --alpha 0.4
```

### 5. Compare multiple participants

```bash
python src/compare_participants.py \
  --feature-dir work/features \
  --output-dir work/comparison \
  --group A:2-10 \
  --group B:71-80 \
  --group C:81-90
```

## Current limitations and next steps

- Deviation from an individual baseline is **not yet a validated fall-risk threshold**.
- Acceleration can amplify pose-estimation noise; smoothing and feature validity need further evaluation.
- `body_turn_rate` is currently a frame-to-frame angular change and will be reconsidered using a fixed time window / angular velocity.
- Image-plane ankle distance can be affected by camera/body orientation.
- Pose detection success does not guarantee landmark accuracy; high-deviation frames should be checked against the source video.
- The relationship between these within-person changes and established fall-risk indicators is an ongoing research question.

## Technologies

Python / NumPy / pandas / OpenCV / MediaPipe Pose / robust statistics (Median, MAD) / EWMA

## Author

ZHANG MENGYUE (チョウ・ユヅキ)  
Graduate School of Science and Engineering, Hosei University
