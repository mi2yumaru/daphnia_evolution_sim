# Daphnia Evolution Simulation

ミジンコをモチーフにしたエージェントベース進化シミュレーションです。2Dグリッド上で、個体の移動・摂食・繁殖・死亡と、食料の増減・系譜追跡・戦略変化をステップ単位でシミュレートします。

## プロジェクト概要

このリポジトリは、単一 seed の実行と複数 seed の反復実験の両方を扱えるように設計されています。現在の実装では、食料再生成率の時系列、食料増減のステップログ、共有食料に関する派生指標、静的グラフ、ライブ可視化を提供しています。

## 研究目的

本プロジェクトの最終的な関心は、個体群における「遺伝子交換能力の進化」です。完成した有性生殖が突然出現するモデルを仮定するのではなく、まずは無性生殖集団を基盤として解析を進めています。

現段階では、以下を土台として構築・検証しています。

- 2D グリッド上の個体・食料・環境変動を扱う個体ベース進化シミュレーション
- 個体の移動・摂食・繁殖・死亡・系譜追跡
- 季節的食料補給を含む環境入力と、実際の食料動態の記録

将来的には、稀な遺伝子交換を導入し、環境条件に応じて遺伝子交換を行う割合・頻度がどのように進化するかを検証したいと考えています。現在のコードでは遺伝子交換そのものは未実装であり、今後導入予定の機能です。

## シミュレーション時間

このシステムの基本単位は step です。時間単位は設定によって次のように対応付けられます。

- `simulation.steps_per_day`: 1日あたりの step 数
- `simulation.days_per_year`: 1年あたりの日数
- `simulation.duration_mode`: `steps` または `years`

デフォルト設定では、1日 = 10 step、1年 = 365 日です。`duration_mode: years` の場合、総 step 数は

```
duration_years × days_per_year × steps_per_day
```

で計算されます。現在のデフォルトでは `duration_years: 3` のため、3年間の実行は 10,950 step になります。

実行中は `simulation_year` / `day_of_year` / `month` / `day_of_month` をログに記録し、ライブ可視化でも年・日情報を利用します。現在は閏年を扱わず、各年を固定の 365 日として扱います。

## 季節的な食料供給

`seasonal_food.enabled` が `true` の場合、`seasonal_food.csv_path` から 1～365 日の `day_of_year` と `food_respawn_rate` を読み込みます。デフォルトの CSV は `data/kasumigaura_sta9_food_respawn_365_v3.csv` です。

- `food_respawn_rate` は固定値だけでなく、CSV から 365 日分の季節曲線を読み込むことができます。
- 365 日分の固定曲線は、複数年シミュレーションでも年ごとに繰り返して利用されます。
- 1日の値は、その日のすべての step で同じ `food_respawn_rate` として使われます。

この曲線は、霞ヶ浦 Sta.9 の一次生産量の季節性を参照し、長期の月次観測値をもとにシミュレーション用の滑らかな 365 日固定曲線として構成したものです。一次生産量の季節性を、シミュレーション上の餌供給強度へ対応付けたモデル化であり、物理単位の直接変換ではありません。

`seasonal_food.enabled` が `false` の場合は、`environment.food_respawn_rate` の固定値を使用します。

## 現在の実装内容

- 2D グリッド環境
  - 幅・高さを設定可能
  - 食料は `random` モードまたは `patch` モードで配置
  - `patch` モードでは `patch_layout`（`random` / `radial` / `spread`）と密度・半径を設定可能
- 個体の行動
  - 移動（`moore` 8方向または `von_neumann` 4方向）
  - 摂食
  - 無性生殖（エネルギー閾値を超えると子を生成）
  - 死亡（エネルギー枯渇または寿命による死亡）
- ゲノムから戦略へ
  - 20 ビットゲノムを 4 つの 6 ビットセグメントに分割
  - 各セグメントを 0..63 から 0.0..1.0 に正規化し、以下の表現型（phenotype）を生成
    - `exploration_tendency`
    - `site_fidelity`
    - `risk_tolerance`
    - `reproduction_timing`
- 系譜追跡
  - 各個体に `organism_id`, `parent_id`, `founder_id`, `generation`, `birth_step`, `death_step`, `death_cause` を持たせる
  - 単一 seed 実行ごとに `lineage.csv` と `lineage_strategy_summary.csv` を出力
- 食料ダイナミクスの追跡
  - 各ステップで `food_respawn_count`, `food_consumed_count`, `food_count`, `food_respawn_rate` を記録
  - 1 step で実際に追加された餌マス数を `food_respawn_count[t]`、実際に削除された餌マス数を `food_consumed_count[t]` として扱う
  - step 終了時点の `food_count[t]` は、前 step の在庫にその step の補給と消費を反映した値です

    初期状態を除く各 step では、他に食料を増減させる処理がない場合、次の食料収支が成り立ちます。

    ```text
    food_count[t]
      = food_count[t-1]
      + food_respawn_count[t]
      - food_consumed_count[t]
    ```

  - 同じ餌マスを複数個体が共有する場合、`eat_count` は摂食した個体数を数え、`food_consumed_count` は実際に削除された餌マス数を数えます
- 詳細ログ
  - `move_rate` / `total_eat_rate` / `eat_after_move_rate` / `eat_without_move_rate`
  - `shared_food_cell_count` / `shared_food_consumer_count` / `mean_consumers_per_shared_food`
  - `birth_count` / `death_count` / `age_death_count` / `energy_death_count`
  - `active_lineage_count` / `largest_lineage_share` / `average_generation` / `max_generation`
- 可視化
  - 単一 seed では、個体数・平均エネルギー・平均年齢・出生/死亡・戦略平均・戦略内部のばらつき・戦略範囲・共有食料指標・系統構造・食料ダイナミクスなどを描画
  - 複数 seed では、seed 間平均と標準偏差を含む集計グラフを生成
  - `behavior_trait_std` や各 trait の min/max range は、単一試行内の個体群内部のばらつきを示します
  - 一方、複数 seed の mean±std は seed 間の試行結果のばらつきを示します
  - `food_respawn_rate.png` は環境入力としての補給条件を示し、`food_dynamics.png` はその環境条件下で実際に供給・消費・蓄積された餌を示します

## 今後の拡張

現在までに、個体ベースモデルの基盤構築、random / patch 環境の実装・基礎比較、季節的食料供給の導入までを進めています。

今後は以下を予定しています。

- 季節変動環境下での基礎挙動・行動戦略進化の検証
- random / patch 環境と季節変動を組み合わせた比較
- 遺伝子交換機構の導入
- 固定した遺伝子交換率による比較実験
- 遺伝子交換率を進化可能な形質として導入
- 遺伝子交換コストや環境条件に対する感度分析

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
cd daphnia_evolution_sim
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

`results/single_runs/seed_{seed}/` 以下に出力されます。

- `log.csv`: ステップごとの統計ログ
- `lineage.csv`: 全個体の系譜記録
- `lineage_strategy_summary.csv`: founder 系統ごとの戦略・存続状況まとめ
- `population.png`
- `average_energy.png`
- `average_age.png`
- `movement_and_eating_rates.png`
- `eating_breakdown_rates.png`
- `behavior_traits.png`
- `behavior_trait_std.png`
- `exploration_tendency_range.png`
- `site_fidelity_range.png`
- `risk_tolerance_range.png`
- `reproduction_timing_range.png`
- `birth_count.png`
- `death_count.png`
- `birth_death_rates.png`
- `birth_death_counts.png`
- `food_sharing_ratios.png`
- `consumers_per_shared_food.png`
- `active_lineage_count.png`
- `largest_lineage_share.png`
- `generation.png`
- `food_respawn_rate.png`
- `food_dynamics.png`

### 複数 seed 実験

`results/experiments/{experiment_name}/` 以下に出力されます。

- `aggregate.csv`: 各 step の seed 間平均と標準偏差
- `summary.csv`: 各 seed の最終値と後半 100 step 平均の要約
- `lineage_strategy_all_seeds.csv`: すべての seed の founder 系統サマリを結合
- `population_mean_std.png`
- `average_energy_mean_std.png`
- `average_age_mean_std.png`
- `movement_eating_mean_std.png`
- `eating_breakdown_rates_mean_std.png`
- `behavior_traits_mean_std.png`
- `birth_death_mean_std.png`
- `birth_death_counts_mean_std.png`
- `food_sharing_ratios_mean_std.png`
- `consumers_per_shared_food_mean_std.png`
- `active_lineage_count_mean_std.png`
- `largest_lineage_share_mean_std.png`
- `generation_mean_std.png`
- `food_dynamics_mean_std.png`
- `food_respawn_rate.png`

複数 seed 実験では、`food_respawn_rate.png` は全 seed で共通の固定 365 日季節曲線を表す環境入力プロットとして扱われます。個体群や集団指標の多くは seed 間平均 ± 標準偏差で表示されます。

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
- `food_respawn_rate` による環境側の餌供給条件
- `food_respawn_count`, `food_consumed_count`, `food_count` による食料収支・餌動態

## プロジェクト構造

```text
daphnia_evolution_sim/
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
