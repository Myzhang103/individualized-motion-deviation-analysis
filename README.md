# Individualized Motion Deviation Analysis for Older Adults

大学院研究で作成した、高齢者の日常動作を骨格情報から解析する Python プロジェクトです。
一律の基準だけで評価するのではなく、**本人の日常動作を個人別 Baseline とし、本人の通常状態からの変化を定量化する**ことを目的としています。

> **Note:** 現在の Deviation Score は転倒確率ではなく、本人の通常状態からどの程度変化したかを見るための指標です。転倒リスクとの関係は今後の検証課題です。

このリポジトリは、大学院で進めている研究の中から、就職活動用にコードと結果を整理したものです。MUVIM の原動画・画像およびフレーム単位の骨格座標データは公開していません。データの扱いについては [DATASET.md](DATASET.md) を参照してください。

## Background

前期研究では UR Fall Detection Dataset を用いて、骨格特徴量から Random Forest による転倒・日常動作分類を行いました。5-fold cross-validation の平均精度は **77.1% ± 17.7%** で、SHAP / LIME を用いてモデルの判断根拠も分析し、日本人間工学会で発表しました。

その後、「転倒直前の特徴」だけでなく、高齢者本人の普段の状態からの変化を捉える必要があると考え、MUVIM の高齢者 ADL データを用いた個人別評価へ研究を発展させています。

## What I implemented

- MediaPipe Pose を用いた RGB 映像からの骨格ランドマーク抽出
- Pose 未検出フレームを考慮した連続フレーム処理
- 8 種類の動作特徴量の設計・実装
- Median / MAD による個人別 Baseline の構築
- 標準化逸脱度と Deviation Score の算出
- P95 を用いた探索的な大きな逸脱の抽出
- EWMA による複数試行の逐次評価
- Feature Contribution による特徴量別の逸脱要因確認
- 3 名の高齢者における日常動作特徴量の個人差比較

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

## Example results

Participant A の試作では、NonFall2–5 を Baseline、NonFall6–10 を Evaluation として使用しました。
Baseline の Deviation Score 分布から得た P95 は **5.61** でした。
Evaluation の基準閾値超過フレーム割合は以下の通りでした。

| Trial | Phase | Threshold exceedance rate |
|---|---|---:|
| NonFall6 | Evaluation | 11.10% |
| NonFall7 | Evaluation | 3.26% |
| NonFall8 | Evaluation | 9.38% |
| NonFall9 | Evaluation | 9.72% |
| NonFall10 | Evaluation | 9.98% |

また、3 名の高齢者を比較したところ、特徴量の中心値だけでなく試行間のばらつきにも個人差が確認されました。この結果は「全員に同一の基準を適用するのではなく、本人の通常状態を基準に変化を見る」という研究方針を検討する根拠の一つとして扱っています。

## Visual results

### Participant A: individual-baseline deviation

![Participant A individual-baseline deviation](figure_sequential_deviation.png)

各棒は、各試行において Participant A の個人別 P95 閾値を超えたフレームの割合を示しています。  
この割合は、本人の Baseline から比較的大きく逸脱したフレームの割合を示しています。

### Comparison across three participants

![Comparison of motion features across three participants](figure_participant_comparison.png)

3 名の高齢者について、8 種類の特徴量の試行中央値と IQR をロバスト標準化して比較したものです。  
特徴量の中心値だけでなく、試行間のばらつきにも個人差があることを確認しました。

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

- 個人内の逸脱と実際の転倒リスクとの関係は、今後さらに検証が必要です。
- 加速度は Pose 推定ノイズの影響を受けやすいため、平滑化や特徴量の見直しを検討しています。
- `body_turn_rate` は現在フレーム間の角度差を使っており、今後は一定時間幅での変化量も検討します。
- 足関節間距離などの画像上の特徴量は、カメラ方向や身体の向きの影響を受ける可能性があります。
- Pose の検出成功だけで精度を保証できないため、必要に応じて元映像との照合も行います。

## Technologies

Python / NumPy / pandas / OpenCV / MediaPipe Pose / robust statistics (Median, MAD) / EWMA

## Author

ZHANG MENGYUE (チョウ・ユヅキ)  
Graduate School of Science and Engineering, Hosei University
