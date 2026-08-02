# Daphnia Evolution Simulation

ミジンコをモチーフにした、エージェントベース進化シミュレーションです。

2Dグリッド上で、個体の移動・摂食・繁殖・死亡、食料の供給・消費、環境の季節変動、系譜構造、行動戦略および遺伝子交換能力の進化をステップ単位でシミュレートします。

## プロジェクト概要

本プロジェクトでは、環境変動下において、個体の行動戦略や遺伝子交換能力がどのように進化するかを検証するための個体ベースモデルを構築しています。

単一seedの実行と、複数seedによる反復実験の両方に対応しています。シミュレーション結果として、個体数、行動、摂食、繁殖、死亡、食料動態、系譜構造、遺伝子交換イベント、各遺伝形質の変化などをCSVおよびグラフとして出力します。

現在は、以下の要素まで実装しています。

- 2Dグリッド上の個体・食料・環境
- 個体の移動・摂食・無性生殖・死亡
- random環境およびpatch環境
- 季節的に変動する食料再生成率
- 120 lociの二値ゲノム
- 4種類の行動形質
- 遺伝子交換確率と遺伝子交換割合
- 固定値または進化可能な遺伝子交換機構
- 系譜および遺伝子交換履歴の追跡
- 単一seed・複数seedのログ集計と可視化

## 研究目的

本プロジェクトの最終的な関心は、個体群における**遺伝子交換能力の進化**です。

完成した有性生殖が突然出現するモデルを仮定するのではなく、無性生殖集団を基盤として、個体間で部分的な遺伝情報の交換が発生するモデルを構築しています。

現在のモデルでは、子個体は基本的に親個体のゲノムを継承します。ただし、繁殖時に周辺個体を遺伝子提供個体として選び、ゲノムの一部を置換することで、局所的な遺伝子交換を表現します。

この遺伝子交換について、個体ごとに次の2つの能力を持たせています。

- 遺伝子交換を行う確率
- 1回の交換で置換するゲノムの割合

これらを進化可能な遺伝形質として扱うことで、環境条件、空間構造、資源分布、交換コストなどに応じて、遺伝子交換能力がどのように変化するかを検証することを目的としています。

なお、現在実装している遺伝子交換は、二倍体、オス・メス、配偶子、減数分裂などを含む完全な有性生殖ではありません。無性生殖を基盤として、周辺個体から部分的に遺伝情報を取り込む中間的な機構としてモデル化しています。

## 現在の研究進捗

現在までに、次の実装と基礎実験を行っています。

1. 個体ベースモデルの基盤構築
2. random環境とpatch環境の実装
3. 個体の行動形質と突然変異の導入
4. 系譜追跡と複数seed実験への対応
5. 季節的な食料供給曲線の導入
6. 食料の供給・消費・蓄積量の詳細記録
7. 遺伝子交換機構の実装
8. 遺伝子交換確率・交換割合の進化可能化
9. ゲノムの120 loci化
10. 3年間・10 seedによるベースライン実験の実行

現在は、遺伝子交換を実装する前段階ではなく、**遺伝子交換能力を進化可能な形質として導入し、比較実験を開始できる段階**です。

今後は、遺伝子交換なし、固定された遺伝子交換、進化可能な遺伝子交換の比較を中心に、環境条件やコストを変化させた実験を進めます。

## シミュレーション時間

本システムの基本時間単位は `step` です。

時間設定には、次のパラメータを使用します。

- `simulation.steps_per_day`: 1日あたりのstep数
- `simulation.days_per_year`: 1年あたりの日数
- `simulation.duration_mode`: 実行期間の指定方法
- `simulation.steps`: step数を直接指定する場合の実行期間
- `simulation.duration_years`: 年単位で指定する場合の実行期間

`simulation.duration_mode` には、次のいずれかを指定します。

- `steps`
- `years`

`duration_mode: years` の場合、総step数は次の式で計算されます。

```text
総step数
  = duration_years
  × days_per_year
  × steps_per_day
```

現在のデフォルト設定は次のとおりです。

```yaml
simulation:
  duration_mode: "years"
  duration_years: 3
  days_per_year: 365
  steps_per_day: 10
```

したがって、3年間のシミュレーションは次のstep数になります。

```text
3 × 365 × 10 = 10,950 step
```

実行中は、以下の時間情報をログに記録します。

- `simulation_year`
- `day_of_year`
- `month`
- `day_of_month`

ライブ可視化でも、現在の年・日情報を表示します。

現在は閏年を扱わず、すべての年を固定の365日として扱います。

## 環境

### 2Dグリッド

個体と食料は、設定された幅と高さを持つ2Dグリッド上に配置されます。

```yaml
environment:
  width: 100
  height: 100
```

グリッドの境界は周期境界ではありません。

### 食料配置

食料の配置方法として、次の2種類を利用できます。

- `random`
- `patch`

```yaml
environment:
  mode: "random"
```

#### randomモード

グリッド全体に食料をランダムに配置します。

#### patchモード

食料を複数のパッチ領域に集中して配置します。

パッチの配置方法として、次のレイアウトを指定できます。

- `random`
- `radial`
- `spread`

```yaml
environment:
  mode: "patch"
  patch_layout: "spread"
```

パッチ数、半径、密度なども設定ファイルから変更できます。

## 季節的な食料供給

`seasonal_food.enabled` が `true` の場合、CSVファイルから1～365日分の食料再生成率を読み込みます。

```yaml
seasonal_food:
  enabled: true
  csv_path: "data/kasumigaura_sta9_food_respawn_365_v3.csv"
```

CSVには、少なくとも次の列が必要です。

- `day_of_year`
- `food_respawn_rate`

デフォルトでは、霞ヶ浦Sta.9における一次生産量の季節性を参照して作成した365日固定曲線を使用します。

この曲線は、長期の月次観測値をもとに、シミュレーションで利用できる滑らかな日次曲線として構成したものです。

一次生産量の物理単位を食料個数へ直接変換したものではなく、一次生産量の季節的な増減を、シミュレーション上の食料供給強度へ対応付けたモデルです。

複数年シミュレーションでは、同じ365日曲線を年ごとに繰り返します。

1日の値は、その日に含まれるすべてのstepで同じ `food_respawn_rate` として使用されます。

`seasonal_food.enabled` が `false` の場合は、次の固定値を使用します。

```yaml
environment:
  food_respawn_rate: 0.02
```

## 個体の行動

各個体は、エネルギー、年齢、寿命、位置、ゲノム、系譜情報などを持ちます。

各stepでは、周囲の食料や自身の戦略に基づいて行動します。

### 移動

移動近傍は、次のいずれかを指定できます。

- `moore`: 周囲8方向
- `von_neumann`: 上下左右4方向

```yaml
organism:
  move_type: "moore"
```

移動時にはエネルギーを消費します。

### 摂食

個体が食料の存在するセルに到達すると、食料を摂食してエネルギーを獲得します。

同じ食料セルへ複数個体が集まった場合には、複数個体が同一食料を共有する場合があります。

このとき、

- `eat_count` は摂食した個体数
- `food_consumed_count` は実際に削除された食料セル数

を表します。

### 無性生殖

個体のエネルギーが繁殖閾値を超えると、子個体を生成できます。

```yaml
organism:
  reproduction_threshold: 20
  reproduction_cost: 10
  offspring_energy: 5
```

繁殖後、親個体は繁殖コストを支払い、子個体には初期エネルギーが与えられます。

遺伝子交換が発生しない場合、子個体は親個体のゲノムを基礎として突然変異を受けます。

遺伝子交換が発生する場合は、親個体のゲノムの一部を提供個体由来の値へ置換した後、突然変異を適用します。

### 死亡

個体は、次のいずれかによって死亡します。

- エネルギー枯渇
- 寿命への到達

死亡原因は、系譜ログとstepログの両方に記録されます。

## ゲノムと表現型

### ゲノム構造

現在のゲノムは、120個の二値locusから構成されます。

```text
6形質 × 20 loci = 120 loci
```

各locusは、`0` または `1` の値を取ります。

各形質に割り当てられた20 lociのうち、値が `1` であるlocusの割合を用いて表現型を計算します。

```text
trait_value
  = 20 loci中の1の個数 / 20
```

これにより、形質値は原則として0.05刻みで表現されます。

### 実装されている形質

| 形質 | 範囲 | 概要 |
|---|---:|---|
| `exploration_tendency` | 0.0～1.0 | 周辺に食料がない場合の探索傾向 |
| `site_fidelity` | 0.0～1.0 | 過去に食料を取得した場所へ戻る傾向 |
| `risk_tolerance` | 0.0～1.0 | エネルギー状態に応じた移動判断に関わる傾向 |
| `reproduction_timing` | 0.0～1.0 | 繁殖開始に必要なエネルギー閾値を調整する形質 |
| `gene_exchange_probability` | 0.0～1.0 | 繁殖時に遺伝子交換を試みる確率 |
| `gene_exchange_fraction` | 0.0～0.5 | 1回の交換で提供個体からコピーするゲノム割合 |

`gene_exchange_fraction` は、最大でもゲノム全体の50%までを交換対象とするようにスケーリングされています。

### 突然変異

```yaml
genetics:
  genome_length: 120
  mutation_rate: 0.002
```

突然変異は、各locusに対して独立に適用されるビット反転として実装されています。

## 遺伝子交換

### 基本的な仕組み

遺伝子交換は、個体が無性生殖によって子個体を生成するときに発生します。

1. 親個体が繁殖条件を満たす
2. 親個体の周辺から遺伝子提供候補を探索する
3. 遺伝子交換確率に基づいて交換の発生を判定する
4. 候補個体から提供個体を1体選択する
5. 遺伝子交換割合に基づいて交換locus数を決定する
6. 重複しないlocusをランダムに選択する
7. 選択したlocusを提供個体の値で置換する
8. 置換後の子ゲノムに突然変異を適用する

### 提供個体の探索範囲

遺伝子提供候補は、親個体と同じセルおよび周囲8セルから探索します。

つまり、親個体を中心とする3×3のMoore近傍に存在する、自分以外の個体が候補になります。

周辺に提供候補が存在しない場合、その繁殖では遺伝子交換は発生しません。

### 遺伝子交換モード

#### 遺伝子交換を無効化

```yaml
gene_exchange:
  enabled: false
```

#### 固定値モード

```yaml
gene_exchange:
  enabled: true
  mode: "fixed"
  probability: 0.10
  fraction: 0.20
```

すべての個体に共通の遺伝子交換確率と交換割合を使用します。

#### 進化可能モード

```yaml
gene_exchange:
  enabled: true
  mode: "evolvable"
```

個体のゲノムにコードされた以下の形質を使用します。

- `gene_exchange_probability`
- `gene_exchange_fraction`

突然変異と自然選択を通して、個体群内の遺伝子交換能力が変化する可能性があります。

現在のデフォルト設定は、進化可能モードです。

## 系譜追跡

各個体には、次の系譜情報を持たせています。

- `organism_id`
- `parent_id`
- `founder_id`
- `generation`
- `birth_step`
- `death_step`
- `death_cause`

これにより、次の指標を計算できます。

- 生存しているfounder系統数
- 最大系統が占める個体割合
- 平均世代
- 最大世代
- founder系統ごとの行動戦略
- founder系統ごとの存続状況

遺伝子交換が発生した出生については、追加で次の情報を記録します。

- 出生時の遺伝子交換確率
- 出生時の遺伝子交換割合
- 遺伝子交換が発生したか
- 遺伝子提供個体のID
- 遺伝子提供個体のfounder ID
- 交換対象として選択されたlocus数
- 実際に値が変化したbit数

親子関係を表す系譜と、部分的な遺伝子提供関係は、別の情報として記録します。

## 食料ダイナミクスの追跡

各stepで、次の食料関連指標を記録します。

- `food_respawn_rate`
- `food_respawn_count`
- `food_consumed_count`
- `food_count`

初期状態を除き、食料を増減させる処理が再生成と摂食のみである場合、次の収支が成り立ちます。

```text
food_count[t]
  = food_count[t-1]
  + food_respawn_count[t]
  - food_consumed_count[t]
```

`food_respawn_rate` は環境側の入力条件を表し、`food_respawn_count`、`food_consumed_count`、`food_count` は、その条件下で実際に生じた食料動態を表します。

## 主な記録項目

### 個体群

- `population`
- `average_energy`
- `average_age`
- `birth_count`
- `death_count`
- `birth_rate`
- `death_rate`
- `age_death_count`
- `energy_death_count`
- `age_death_rate`
- `energy_death_rate`

### 行動・摂食

- `move_rate`
- `total_eat_rate`
- `eat_after_move_rate`
- `eat_without_move_rate`
- `eat_per_move`

### 食料共有

- `shared_food_cell_count`
- `shared_food_consumer_count`
- `shared_food_cell_ratio`
- `shared_food_consumer_ratio`
- `mean_consumers_per_shared_food`

### 形質

各形質について、平均値、標準偏差、最小値、最大値を記録します。

- `exploration_tendency`
- `site_fidelity`
- `risk_tolerance`
- `reproduction_timing`
- `gene_exchange_probability`
- `gene_exchange_fraction`

### 系譜構造

- `active_lineage_count`
- `largest_lineage_share`
- `average_generation`
- `max_generation`

### 遺伝子交換

- `gene_exchange_eligible_count`
- `gene_exchange_event_count`
- `gene_exchange_selected_loci_count`
- `gene_exchange_changed_bit_count`
- `gene_exchange_eligible_rate`
- `gene_exchange_event_rate`
- `gene_exchange_birth_rate`

## 可視化

単一seedの形質標準偏差やrangeグラフは、同一試行内の個体群内部のばらつきを表します。

一方、複数seed実験のmean±stdは、同一条件で実行したseed間の試行結果のばらつきを表します。

## 依存パッケージ

- numpy
- pandas
- matplotlib
- imageio
- imageio-ffmpeg
- PyYAML

依存関係は `requirements.txt` に記載しています。

## セットアップ

```bash
git clone https://github.com/mi2yumaru/daphnia_evolution_sim.git
cd daphnia_evolution_sim
python -m venv .venv
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

### Windows cmd

```cmd
.venv\Scripts\activate.bat
```

### macOS / Linux

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

## 実行方法

### 単一seedの実行

```bash
python src/main.py
```

利用できる主なオプションは次のとおりです。

- `--seed <n>`: 使用する乱数seedを指定
- `--live`: リアルタイム可視化を有効化
- `--no-csv`: 詳細ログCSVを保存しない
- `--no-plots`: 静的グラフを保存しない

例：

```bash
python src/main.py --seed 0 --live
```

### 複数seedの実行

```bash
python src/run_experiments.py --seeds 0 1 2 3 4 5 6 7 8 9 --experiment-name baseline_10seeds --save-run-plots
```

主なオプションは次のとおりです。

- `--seeds`: 実行するseedの一覧
- `--experiment-name`: 実験結果ディレクトリ名
- `--save-run-plots`: 各seedの個別グラフも保存

### ヘルプ

```bash
python src/main.py --help
python src/run_experiments.py --help
```

## 出力構成

### 単一seed実行

```text
results/single_runs/seed_{seed}/
```

主なCSVファイル：

- `log.csv`
- `lineage.csv`
- `lineage_strategy_summary.csv`

主なグラフ：

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
- `gene_exchange_probability_range.png`
- `gene_exchange_fraction_range.png`
- `birth_death_rates.png`
- `birth_death_counts.png`
- `food_sharing_ratios.png`
- `consumers_per_shared_food.png`
- `food_respawn_rate.png`
- `food_dynamics.png`
- `active_lineage_count.png`
- `largest_lineage_share.png`
- `generation.png`
- `gene_exchange_events.png`
- `gene_exchange_loci.png`
- `gene_exchange_rates.png`
- `gene_exchange_traits.png`

### 複数seed実験

```text
results/experiments/{experiment_name}/
```

主なCSVファイル：

- `aggregate.csv`
- `summary.csv`
- `lineage_strategy_all_seeds.csv`

主なグラフ：

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
- `food_dynamics_mean_std.png`
- `food_respawn_rate.png`
- `active_lineage_count_mean_std.png`
- `largest_lineage_share_mean_std.png`
- `generation_mean_std.png`
- `gene_exchange_events_mean_std.png`
- `gene_exchange_loci_mean_std.png`
- `gene_exchange_rates_mean_std.png`
- `gene_exchange_traits_mean_std.png`

## 主要設定

主な挙動は、`configs/default.yaml` から変更できます。

### シミュレーション時間

- `simulation.duration_mode`
- `simulation.steps`
- `simulation.duration_years`
- `simulation.days_per_year`
- `simulation.steps_per_day`
- `simulation.random_seed`

### 環境

- `environment.width`
- `environment.height`
- `environment.mode`
- `environment.patch_layout`
- `environment.patch_count`
- `environment.initial_food_count`
- `environment.food_respawn_rate`
- `environment.food_energy`

### 季節変動

- `seasonal_food.enabled`
- `seasonal_food.csv_path`

### 個体

- `organism.initial_population`
- `organism.initial_energy`
- `organism.move_cost`
- `organism.living_cost`
- `organism.reproduction_threshold`
- `organism.reproduction_cost`
- `organism.offspring_energy`
- `organism.randomize_initial_age`
- `organism.randomize_lifespan`
- `organism.lifespan_min`
- `organism.lifespan_max`
- `organism.max_age`
- `organism.move_type`

### 遺伝

- `genetics.genome_length`
- `genetics.mutation_rate`

### 遺伝子交換

- `gene_exchange.enabled`
- `gene_exchange.mode`
- `gene_exchange.probability`
- `gene_exchange.fraction`

### 可視化

- `visualization.enabled`
- `visualization.interval_ms`
- `visualization.show_food`
- `visualization.show_organisms`
- `visualization.save_animation`
- `visualization.animation_path`
- `visualization.save_video`
- `visualization.video_path`

## プロジェクト構造

```text
daphnia_evolution_sim/
├─ README.md
├─ requirements.txt
├─ configs/
│  └─ default.yaml
├─ data/
│  └─ kasumigaura_sta9_food_respawn_365_v3.csv
├─ results/
│  ├─ single_runs/
│  └─ experiments/
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

- `src/main.py`: 単一seed実行のエントリーポイント
- `src/runner.py`: 単一シミュレーションの実行と結果保存
- `src/run_experiments.py`: 複数seedの反復実験と集計
- `src/simulation.py`: シミュレーション全体の制御
- `src/environment.py`: 2D環境と食料配置の管理
- `src/organism.py`: 個体、ゲノム、行動、繁殖、遺伝子交換の管理
- `src/food.py`: 食料オブジェクトの管理
- `src/logger.py`: stepごとの統計記録と系譜記録
- `src/visualizer.py`: 静的グラフの生成
- `src/live_visualizer.py`: リアルタイム可視化

## 今後の実験・拡張

### 遺伝子交換条件の比較

- 遺伝子交換なし
- 固定された遺伝子交換
- 進化可能な遺伝子交換
- 遺伝子交換確率のみ進化可能
- 遺伝子交換割合のみ進化可能
- 両方を進化可能

### 環境条件の比較

- random環境
- patch環境
- 一定の食料供給
- 季節的な食料供給
- 季節変動の強度・周期を変更した環境
- 環境変動の予測可能性が異なる条件

### 感度分析

- 突然変異率
- 集団サイズ
- 食料供給量
- 食料エネルギー
- 移動コスト
- 生活コスト
- 遺伝子交換確率
- 遺伝子交換割合
- 交換可能な空間範囲

### モデル拡張

- 遺伝子交換に伴うエネルギーコスト
- 遺伝子交換の失敗確率
- 遺伝子提供個体の選択戦略
- 環境ストレスに応じた交換行動
- 天敵や病気などの選択圧
- 休眠卵や有性生殖的な生活史への拡張

## 補足

- 季節的食料供給曲線は、実測値の季節性を参考にしたシミュレーション用の環境入力です。
- 一次生産量から食料個数への物理単位の直接変換ではありません。
- 現在の遺伝子交換は、無性生殖時に局所的な他個体の遺伝情報を子ゲノムへコピーするモデルです。
- 完全な有性生殖や二倍体遺伝を再現するものではありません。
- ライブ可視化は、必要に応じてGIFまたはMP4として保存できます。
- ライブ可視化の保存先は、`configs/default.yaml` の `visualization.animation_path` および `visualization.video_path` から変更できます。
