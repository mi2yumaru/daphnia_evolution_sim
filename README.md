# Daphnia Evolution Simulation

ミジンコをモチーフにしたエージェントベース進化シミュレーションです。2Dグリッド上で、個体の移動・摂食・繁殖・死亡と、食料の増減・系譜追跡・戦略変化をステップ単位でシミュレートします。

## プロジェクト概要

このリポジトリは、単一 seed の実行と複数 seed の反復実験の両方を扱えるように設計されています。現在の実装では、食料再生成率の時系列・食料増減のステップログ・共有食料に関する派生指標・静的グラフ・ライブ可視化を揃えて提供しています。

## 現在の実装内容

- 2D グリッド環境
  - 幅・高さを設定可能
  - 食料は random モードまたは patch モードで配置
  - patch モードでは patch layout（random / radial / spread）と密度・半径を設定可能
- 個体の行動
  - 移動（Moore 8方向または von Neumann 4方向）
  - 摂食
  - 無性生殖（エネルギー閾値を超えると子を生成）
  - 死亡（エネルギー枯渇または寿命による死亡）
- ゲノムから戦略へ
  - 20ビットゲノムを 4つの 5ビットセグメントに分割
  - 各セグメントを 0..31 から 0.0..1.0 へ正規化し、以下の phenotype を生成
    - exploration_tendency
    - site_fidelity
    - risk_tolerance
    - reproduction_timing
- 系譜追跡
  - 各個体に organism_id, parent_id, founder_id, generation, birth_step, death_step, death_cause を持たせます
  - 単一 seed 実行ごとに lineage.csv と lineage_strategy_summary.csv を出力します
- 食料ダイナミクスの追跡
  - 各ステップで food_respawn_count, food_consumed_count, food_count を記録します
  - これにより、food_count(t+1) = food_count(t) + food_respawn_count - food_consumed_count が成立しているかを確認できます
- 詳細ログ
  - 移動率・摂食率・出生・死亡・年齢死亡・エネルギー死亡
  - 共有食料の発生状況（共有食料セル数、共有食料消費者数、1セルあたりの平均消費者数）
  - 系統数、最大系統シェア、平均世代、最大世代
- 可視化
  - 単一 seed の実行では、個体数・平均エネルギー・平均年齢・出生/死亡・戦略平均・戦略分散・戦略範囲などを描画します
  - 複数 seed 実験では、seed 間平均と標準偏差を含む集計グラフを生成します
  - ライブ可視化では、全個体を青色、食料を緑色で表示します

## 依存パッケージ

- numpy
- pandas
- matplotlib
- imageio
- imageio-ffmpeg
- PyYAML

依存関係は requirements.txt に記載されています。

## セットアップ

```bash
cd daphnia_simulation
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows cmd:

```cmd
.venv\Scripts\activate.bat
```

macOS / Linux:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## 実行方法

### 単一 seed の実行

```bash
python src/main.py
```

利用できるオプション:

- --seed <n>: 使用する乱数 seed を指定
- --live: リアルタイム可視化を有効化
- --no-csv: 詳細ログ CSV を保存しない
- --no-plots: 静的グラフを保存しない

例:

```bash
python src/main.py --seed 0 --live
```

### 複数 seed の実行

```bash
python src/run_experiments.py --seeds 0 1 2 3 4 --experiment-name multi_seed_test --save-run-plots
```

- --seeds: 実行する seed の一覧
- --experiment-name: 実験結果ディレクトリ名
- --save-run-plots: 各 seed の個別グラフも保存

### ヘルプ

```bash
python src/main.py --help
python src/run_experiments.py --help
```

## 出力構成

### 単一 seed 実行

results/single_runs/seed_{seed}/ 以下に以下を出力します。

- log.csv: ステップごとの統計ログ
- lineage.csv: 全個体の系譜記録
- lineage_strategy_summary.csv: founder 系統ごとの戦略・存続状況まとめ
- population.png
- average_energy.png
- average_age.png
- birth_count.png
- death_count.png
- behavior_traits.png
- behavior_trait_std.png
- exploration_tendency_range.png
- site_fidelity_range.png
- risk_tolerance_range.png
- reproduction_timing_range.png
- movement_and_eating_rates.png
- eating_breakdown_rates.png
- birth_death_rates.png
- food_respawn_rate.png
- food_dynamics.png

### 複数 seed 実験

results/experiments/{experiment_name}/ 以下に以下を出力します。

- aggregate.csv: 各 step の seed 間平均と標準偏差
- summary.csv: 各 seed の最終値と後半 100 step 平均の要約
- lineage_strategy_all_seeds.csv: すべての seed の founder 系統サマリを結合
- population_mean_std.png
- average_energy_mean_std.png
- average_age_mean_std.png
- movement_eating_mean_std.png
- eating_breakdown_rates_mean_std.png
- food_sharing_ratios_mean_std.png
- consumers_per_shared_food_mean_std.png
- birth_death_mean_std.png
- behavior_traits_mean_std.png
- birth_death_counts_mean_std.png
- active_lineage_count_mean_std.png
- largest_lineage_share_mean_std.png
- generation_mean_std.png
- food_dynamics_mean_std.png
- food_respawn_rate_mean_std.png

## 主要設定

configs/default.yaml で主な挙動を調整できます。

- simulation.duration_mode: steps または years
- simulation.steps / simulation.duration_years / simulation.days_per_year / simulation.steps_per_day
- simulation.random_seed
- environment.width / environment.height
- environment.mode: random / patch
- environment.patch_layout: random / radial / spread
- environment.initial_food_count
- environment.food_respawn_rate
- seasonal_food.enabled と seasonal_food.csv_path
- organism.initial_population / initial_energy / move_cost / living_cost / reproduction_threshold / reproduction_cost / offspring_energy
- organism.randomize_initial_age / randomize_lifespan / lifespan_min / lifespan_max / max_age
- genetics.genome_length / mutation_rate
- visualization.interval_ms / save_animation / save_video

## 主要な記録項目

- move_rate と total_eat_rate による行動傾向
- eat_after_move_rate と eat_without_move_rate による摂食成功内訳
- shared_food_cell_ratio と shared_food_consumer_ratio による共有食料指標
- age_death_rate と energy_death_rate による死因分析
- active_lineage_count と largest_lineage_share による系統構造
- average_generation と max_generation による世代進行

## プロジェクト構造

```text
daphnia_simulation/
├─ README.md
├─ requirements.txt
├─ configs/
│  └─ default.yaml
├─ data/
├─ results/
└─ src/
   ├─ main.py
   ├─ runner.py
   ├─ run_experiments.py
   ├─ simulation.py
   ├─ environment.py
   ├─ organism.py
   ├─ food.py
   ├─ logger.py
   ├─ visualizer.py
   └─ live_visualizer.py
```

## モジュール概要

- src/main.py: 単一 seed 実行のエントリーポイント
- src/runner.py: 単一シミュレーション実行と結果保存の共通処理
- src/run_experiments.py: 複数 seed の反復実験と集計出力
- src/simulation.py: シミュレーションの主制御ロジック
- src/environment.py: 2D 環境と食料配置の管理
- src/organism.py: 個体の振る舞いと系譜管理
- src/logger.py: step ごとの統計記録
- src/visualizer.py: 静的グラフ生成
- src/live_visualizer.py: リアルタイム可視化

## 補足

- ライブ可視化はインタラクティブなウィンドウで表示され、必要に応じて GIF / MP4 へ保存できます。
- ライブ可視化の保存先は configs/default.yaml の visualization.animation_path / video_path で変更できます。
- 単一 seed 実行では共通グラフに加え、戦略範囲や birth/death count の単独プロットも保存されます。
