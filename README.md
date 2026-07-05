# Daphnia Evolution Simulation

ミジンコをモチーフにしたエージェントベース進化シミュレーション

## プロジェクト概要

このリポジトリは、2Dグリッド上で個体と食料が相互作用する進化シミュレーション基盤です。
現在は無性生殖と行動戦略に着目し、個体の移動・摂食・繁殖・死亡、系譜追跡、行動戦略の変化を記録・可視化します。

## 現在の実装内容

- **2Dグリッド環境**
  - 幅/高さを設定できるグリッド
  - 食料はランダム配置またはパッチ環境配置
- **個体の行動**
  - 移動（デフォルトは Moore 8方向、`move_type` で von_neumann 4方向も選択可能）
  - 摂食
  - 無性生殖（エネルギー閾値を超えると子を生成）
  - 死亡（エネルギー枯渇または寿命による死亡）
- **ゲノム→戦略マッピング**
  - 20ビットゲノムを 5ビットずつ 4 つに分割
  - 各5ビットを 0..31 から 0.0..1.0 へ正規化して phenotype を生成
  - phenotype:
    - `exploration_tendency`
    - `site_fidelity`
    - `risk_tolerance`
    - `reproduction_timing`
- **系譜追跡**
  - 各個体に `organism_id`, `parent_id`, `founder_id`, `generation`, `birth_step`, `death_step`, `death_cause` を付与
  - 1つの seed 実行ごとに `lineage.csv` と `lineage_strategy_summary.csv` を出力
- **詳細ログ**
  - 移動率、摂食率、年齢死亡率、エネルギー死亡率
  - 共有食料の発生状況（共有食料マス数、共有食料消費者数、共有食料1マスあたりの平均消費者数）
  - 系統数、最大系統シェア、平均世代、最大世代
- **可視化**
  - 個体数、平均エネルギー、平均年齢、出生/死亡、行動戦略の平均値、個体戦略の分布幅などをグラフ化
  - リアルタイム可視化では、全個体を `blue`、食料を `green` で描画

## 依存パッケージ

- numpy
- pandas
- matplotlib
- imageio
- pillow
- PyYAML

`requirements.txt` に必要なバージョンが記載されています。

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

macOS/Linux:

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

以下のオプションが使えます:

- `--seed <n>`: 使用する乱数 seed を指定
- `--live`: リアルタイム可視化を有効にする
- `--no-csv`: 詳細ログ CSV を保存しない
- `--no-plots`: 静的グラフを保存しない

例:

```bash
python src/main.py --seed 0 --live
```

### 複数 seed の実行

`src/run_experiments.py` を使うと複数 seed を連続して実行し、集計結果を保存できます。

```bash
python src/run_experiments.py --seeds 0 1 2 3 4 --experiment-name multi_seed_test --save-run-plots
```

- `--seeds`: 実行する seed の一覧（例: `0 1 2`）
- `--experiment-name`: 出力ディレクトリ名
- `--save-run-plots`: 各 seed の個別グラフも保存

### ヘルプ

```bash
python src/main.py --help
python src/run_experiments.py --help
```

## 出力構成

### 単一 seed 実行

`results/single_runs/seed_{seed}/` に以下のファイルを出力します:

- `log.csv` - ステップごとの統計ログ
- `lineage.csv` - 全個体の系譜記録
- `lineage_strategy_summary.csv` - founder 系統ごとの最終戦略・存続状況まとめ
- `population.png`
- `average_energy.png`
- `average_age.png`
- `birth_count.png`
- `death_count.png`
- `behavior_traits.png`
- `behavior_trait_std.png`
- `exploration_tendency_range.png`
- `site_fidelity_range.png`
- `risk_tolerance_range.png`
- `reproduction_timing_range.png`
- `movement_and_eating_rates.png`
- `eating_breakdown_rates.png`
- `birth_death_rates.png`

### 複数 seed 実験

`results/multi_seed/{experiment_name}/` に以下の集計ファイルを出力します:

- `aggregate.csv` - seed 間の平均と標準偏差を含む集計データ
- `lineage_strategy_all_seeds.csv` - すべての seed の founder 系統戦略サマリ結合
- `population_mean_std.png`
- `movement_eating_mean_std.png`
- `eating_breakdown_rates_mean_std.png`
- `food_sharing_ratios_mean_std.png`
- `consumers_per_shared_food_mean_std.png`
- `birth_death_mean_std.png`
- `behavior_traits_mean_std.png`
- `average_energy_mean_std.png`
- `average_age_mean_std.png`
- `birth_death_counts_mean_std.png`
- `active_lineage_count_mean_std.png`
- `largest_lineage_share_mean_std.png`
- `generation_mean_std.png`

## 主要パラメータ

`configs/default.yaml` で次のような設定を調整できます:

- `simulation.steps`
- `simulation.random_seed`
- `environment.width`, `environment.height`
- `environment.mode` (`random` / `patch`)
- `environment.patch_layout` (`random` / `radial` / `spread`)
- `environment.initial_food_count`
- `environment.food_respawn_rate`
- `organism.initial_population`
- `organism.initial_energy`
- `organism.move_cost`
- `organism.living_cost`
- `organism.reproduction_threshold`
- `organism.reproduction_cost`
- `organism.offspring_energy`
- `organism.randomize_initial_age`
- `organism.randomize_lifespan`
- `organism.lifespan_min`, `organism.lifespan_max`
- `organism.max_age`
- `genetics.genome_length`
- `genetics.mutation_rate`
- `visualization.save_video`
- `visualization.save_animation`

## 主要な記録項目

- `move_rate` と `total_eat_rate` による個体の行動傾向
- `eat_after_move_rate` と `eat_without_move_rate` による摂食成功内訳
- `shared_food_cell_ratio` と `shared_food_consumer_ratio` による共有食料指標
- `age_death_rate` と `energy_death_rate` による死因分析
- `active_lineage_count` と `largest_lineage_share` による系統構造
- `average_generation` と `max_generation` による世代進行

## プロジェクト構造

```
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

- `src/main.py` - 単一 seed 実行のエントリーポイント
- `src/runner.py` - 単一シミュレーション実行と結果保存の共通処理
- `src/run_experiments.py` - 複数 seed の独立反復実験と集計出力
- `src/simulation.py` - シミュレーションの主制御ロジック
- `src/environment.py` - 2D 環境と食料配置の管理
- `src/organism.py` - 個体の振る舞いと系譜管理
- `src/logger.py` - step ごとの統計記録
- `src/visualizer.py` - ログから静的グラフを生成
- `src/live_visualizer.py` - matplotlib を使ったリアルタイム可視化

## 注意点

- 現在、リアルタイム可視化ではすべての個体を青色で描画します。
- `lineage_strategy_summary.csv` が生成されるには、`lineage.csv` に系譜データが含まれている必要があります。
- `run_experiments.py` は各 seed の `lineage_strategy_summary.csv` を読み込み、`lineage_strategy_all_seeds.csv` を作成します。
