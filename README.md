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

本研究では、無性生殖を基盤とする個体集団において、**遺伝子交換能力の進化に影響する環境条件**を個体ベースシミュレーションにより検討します。

特に、食料の空間分布や時間変動が、個体の行動・局所的な遭遇機会・遺伝子交換の成立・遺伝子交換能力の進化に与える影響を調べます。**遭遇機会の増加によって交換頻度が高くなること**と、**交換確率や交換割合の遺伝形質が世代を通じて変化すること**を区別して評価します。

子個体は基本的に親個体のゲノムを継承します。繁殖時に周辺個体を遺伝子提供個体として選択できた場合、子ゲノムの一部を提供個体の値で置換します。交換確率および交換割合を進化可能な形質として扱うことで、環境条件と交換能力の変化の関係を調べます。

本モデルは二倍体・オスとメス・配偶子・減数分裂を再現する完全な有性生殖モデルではありません。**無性生殖を基盤にした局所的な遺伝情報の取り込みモデル**です。ミジンコは生態・環境設定のモチーフであり、種固有の生理を厳密に再現することを目的としません。

## 現在の研究進捗（2026年11月25日時点）

個体ベースモデル、環境・行動形質・系譜追跡・遺伝子交換機構の実装を終え、予備実験およびエネルギーパラメータ校正を進めてきました。

- ランダム／パッチ環境、季節的食料供給、周期境界、初期配置の比較を実装・検証
- 遺伝子交換なし／固定値／進化可能モード、実効交換・系譜・遺伝的多様性の追跡を実装
- 単一seed・複数seedのCSV記録、最終年の集計、ログからの再描画に対応
- 4パッチ・ランダムの2環境 × 12パラメータ条件 × 10 seed × 5年間の校正実験を実施し、**No.10**を本実験の基本エネルギー設定に採用

現在は**本実験の実行前**で、比較条件と出力・再現性の最終確認を行っている段階です。過去の3年・10 seedベースライン実験と校正実験は本実験の結果とは区別します。

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

現在の `configs/default.yaml` における標準設定は次のとおりです。

```yaml
simulation:
  duration_mode: "years"
  duration_years: 5
  days_per_year: 365
  steps_per_day: 10
```

したがって、現在の標準5年間のシミュレーションは次のstep数になります。

```text
5 × 365 × 10 = 18,250 step
```

実行中は、以下の時間情報をログに記録します。

- `simulation_year`
- `day_of_year`
- `month`
- `day_of_month`

ライブ可視化でも、現在の年・日情報を表示します。

現在は閏年を扱わず、すべての年を固定の365日として扱います。

## 環境

### 2Dグリッドと想定空間スケール

個体と食料は、設定された幅と高さを持つ2Dグリッド上に配置されます。

本研究では **50 m × 50 m（2,500 m²）の局所環境**を想定し、標準の100 × 100マスを **1マスあたり0.5 m × 0.5 m** に対応付けます。これは環境スケールの解釈のための**モデル上の想定**であり、特定の湖沼範囲を実測に基づいて再現したものではありません。個体の移動は1 step当たり近傍セルへの選択として実装され、実測の遊泳速度を直接校正したものではありません。

```yaml
environment:
  width: 100
  height: 100
```

**局所環境の端を不自然な壁として扱わず、その外側にも同様の環境が続く近似**として、標準設定では周期境界を採用しています。X・Y座標がマップ外に出た場合、対応する反対側の端へ折り返します。周期境界は、50 m四方の領域内での移動・遭遇を境界効果に左右されにくくするための**計算上の近似**であり、実際の湖沼がトーラス状であることや、外部への移出入を再現するものではありません。従来の境界条件を再現する場合は `environment.periodic_boundary: false` に指定してください。

```yaml
environment:
  width: 100
  height: 100
  periodic_boundary: true
```

周期距離は各軸の最短折り返し距離から計算し、移動、餌の探索、遺伝子提供候補の探索、出生位置、記憶した餌場への接近判定で共通に使用します。マップの境界に物理的な壁が存在するわけではありません。

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

#### 標準4パッチと予備実験用16パッチ

新しいパッチ比較では、同じ100×100マス・初期餌500個を維持し、パッチの個数と空間的分散を変更します。

| 設定 | パッチ数 | 実効半径 | 中心座標（XとYの全組合せ） | 1パッチ面積 | 総面積 |
| --- | ---: | ---: | --- | ---: | ---: |
| `configs/default.yaml` | 4 | 7.0 | 25, 75 | 149 | 596 |
| `configs/patch16.yaml` | 16 | 3.2 | 12, 37, 62, 87 | 37 | 592 |

両条件では、`environment.mode: patch` と `environment.patch_radius_mode: exact` を使用します。`exact` はマス中心からの距離について `dx² + dy² <= patch_radius²` で領域を判定します。小数半径も指定できます。

過去の `configs/step4_patch9.yaml` と `configs/step4_patch25.yaml` は変更していません。`patch_radius_mode` を省略した既存設定は旧実装どおり、`patch_radius + 0.5` の判定を適用します（`legacy` モード）。

**今回から標準の4パッチ・16パッチ条件は周期境界です。** 境界をまたいだ円形パッチも正しく折り返すよう実装しました。新しい配置では1パッチあたり149/37マス、総面積596/592マスで、個々のパッチは重複しません。

初期配置の `near`・`far` は周期距離で判定します。標準の4パッチ・16パッチでは、パッチ中心間の最短周期ユークリッド距離 `L` に応じて閾値を自動設定する `relative` モードを採用します。

```yaml
organism:
  initial_placement_mode: "uniform"  # uniform / inside / near / far
  initial_placement_distance_mode: "relative"
  initial_placement_near_fraction: 0.2
  initial_placement_far_fraction: 0.4
```

- near: パッチ領域外で、最も近いパッチ**領域のマス**までの距離が `0 < d <= L/5`
- far: パッチ領域外で、最も近いパッチ**領域のマス**までの距離が `d >= 0.4L`
- inside: パッチ領域内
- uniform: マップ全体の一様初期配置。near/farの閾値に影響されません

| 環境 | 中心間の最短周期距離L | near閾値 | far閾値 | near候補 | far候補 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 4パッチ | 50 | 10 | 20 | 2,928マス | 1,428マス |
| 16パッチ | 25 | 5 | 10 | 2,816マス | 1,600マス |

中心間の距離は**閾値のスケールを決めるためだけ**に使い、実際に配置可能かどうかは最も近いパッチ領域のセルから測った周期ユークリッド距離で判定します。4パッチと16パッチでは同じ相対距離基準を使いますが、餌への絶対距離が一致するわけではありません。

過去の設定を再現するには、`initial_placement_distance_mode: fixed`（またはキー省略）を使用し、`initial_placement_near_max_distance` と `initial_placement_far_min_distance` に固定値を指定します。過去の `step4_*.yaml` の固定距離設定と旧境界条件は変更しません。

過去の9・25パッチ比較用の `step4_*.yaml` は非周期・旧半径計算法のまま保存しており、過去データの再現用です。新しい比較では `configs/random_periodic.yaml`、`configs/default.yaml`（4パッチ）、`configs/patch16.yaml`（16パッチ）を使ってください。

新しい3条件の実行例：

```bash
python src/run_experiments.py --config configs/random_periodic.yaml --seeds 0 1 2 --experiment-name pilot_random_periodic --no-plots
python src/run_experiments.py --config configs/default.yaml --seeds 0 1 2 --experiment-name pilot_patch4_periodic --no-plots
```

16パッチを指定する場合：

```bash
python src/run_experiments.py --config configs/patch16.yaml --seeds 0 1 2 --experiment-name pilot_patch16 --no-plots
```


## 季節的な食料供給

`seasonal_food.enabled` が `true` の場合、CSVファイルから1～365日分の食料再生成率を読み込みます。

```yaml
seasonal_food:
  enabled: true
  csv_path: "data/kasumigaura_sta9_food_respawn_365_mean002.csv"
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

### 採用した基本エネルギーパラメータ（No.10）

12条件 × 4パッチ/ランダムの2環境 × 10seed × 5年間の校正実験から、
No.10（`L0p15_M1p00_T15_C10`）を本実験用の基準設定として採用しました。

| パラメータ | 採用値 |
|---|---:|
| `organism.living_cost`（毎stepの生活維持コスト） | `0.15` |
| `organism.move_cost`（実際に移動したstepのみ追加消費） | `1.0` |
| `organism.reproduction_threshold`（基本繁殖閾値） | `15` |
| `organism.reproduction_cost` | `10` |
| `organism.offspring_energy` | `5` |
| `environment.food_energy` | `5` |

`configs/default.yaml`（4パッチ）・`configs/random_periodic.yaml`（ランダム）・
`configs/patch16.yaml`（16パッチの追加検証用）を同じエネルギーパラメータに更新しています。
ただし、No.10の長期校正結果は4パッチ・ランダムで得られたものであり、
**16パッチでの妥当性は未検証**です。

過去データ再現用の`configs/step4_*.yaml`は変更しません。
また、過去のグリッドサーチは条件ごとの4パラメータを実行時に上書きするため、
今回の基本設定更新で過去の条件値が自動的にNo.10へ置換されることはありません。
過去の実験を再現する際は、保存済みの`config_used.yaml`と当時のコード版を使用してください。

### 無性生殖

個体のエネルギーが繁殖閾値を超えると、子個体を生成できます。

```yaml
organism:
  reproduction_threshold: 15
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

### 個体ごとの寿命上限

現在の標準設定は、200〜400 step（20〜40日）の**切断正規分布**です。正規乱数が範囲外になった場合は再抽選してから最近接整数に丸めます。

```yaml
organism:
  randomize_initial_age: false
  randomize_lifespan: true
  lifespan_distribution: "truncated_normal"
  lifespan_min: 200
  lifespan_max: 400
  lifespan_mean: 300
  lifespan_std: 50
```

- `lifespan_mean` と `lifespan_std` は**切断前**の正規分布のパラメータです。切断後の標準偏差は50 stepより小さくなります。
- この値は**年齢による死亡の上限**を表します。個体はエネルギー枯渇によって、これより早く死亡することがあります。
- 初期個体と出生した子個体は同じ分布から独立に寿命を抽選します。同じ乱数seedなら抽選は再現できます。
- `randomize_lifespan: false` なら `max_age` に固定します。`lifespan_distribution: "uniform"` または同キーを省略した従来設定では、`lifespan_min`〜`lifespan_max` の離散一様分布を使用します。
- 数値はモデル上の仮定であり、特定種の実測寿命分布を直接推定したものではありません。

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

- `gene_exchange_effective_count`（交換によって子ゲノムに実際の差が生じた出生数）
- `gene_exchange_effective_birth_rate`（出生数に対する実効交換出生数の割合）
- `gene_exchange_eligible_count`
- `gene_exchange_event_count`
- `gene_exchange_selected_loci_count`
- `gene_exchange_changed_bit_count`
- `gene_exchange_eligible_rate`
- `gene_exchange_event_rate`
- `gene_exchange_birth_rate`

### 遺伝的多様性

- `genetic_diversity_all`（全lociの集団内多様性）
- `genetic_diversity_behavior`（行動形質のloci）
- `genetic_diversity_exchange`（交換形質のloci）
- `genotype_diversity`
- `unique_genotype_ratio`

### 追加の分析・最終年集計

- `analysis.offspring_outcomes`：出生後の観察期間における生存・繁殖成績の分析
- `analysis.gene_flow`：親子系譜とは別に、遺伝子提供関係を時間窓で集計
- `src/last_year_summary.py`：最終年の指標をseedごとに集計し、複数seed間の平均・標準偏差も算出

指標の定義、分母、集計区間を確認した上で比較してください。特に交換イベント数と実効交換数は同じではなく、実効交換は交換対象のbitが実際に変更された場合に成立します。

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

現在の標準設定（4パッチ・5年間）によるログ保存のみの例：

```bash
python src/run_experiments.py --config configs/default.yaml --seeds 0 1 2 3 4 5 6 7 8 9 --experiment-name patch4_baseline_5y --no-plots
```

ランダム環境では `--config configs/random_periodic.yaml` を指定します。これらのコマンドはそれぞれ**1つの設定**を実行する例であり、遺伝子交換なし／固定／進化可能の全比較条件を自動で網羅するものではありません。実験ごとの設定ファイルと保存された `config_used.yaml` を確認してください。

```bash
python src/run_experiments.py --seeds 0 1 2 3 4 5 6 7 8 9 --experiment-name baseline_10seeds --save-run-plots
```

主なオプションは次のとおりです。

- `--seeds`: 実行するseedの一覧
- `--experiment-name`: 実験結果ディレクトリ名
- `--save-run-plots`: 各seedの個別グラフも保存

### 実行・ログ保存・グラフ描画の3モード

既存のCSV・分析集計は維持し、グラフ生成のタイミングを分離できます。

| モード | 単一seed | 複数seed |
| --- | --- | --- |
| 実行＋ログ＋グラフ | `python src/main.py --seed 42` | `python src/run_experiments.py --config configs/step4_patch9.yaml --seeds 0 1 2 3 4 5 6 7 8 9 --experiment-name patch9_10seeds` |
| 実行＋ログのみ（PNG不要） | `python src/main.py --seed 42 --no-plots` | `python src/run_experiments.py --config configs/step4_patch9.yaml --seeds 0 1 2 3 4 5 6 7 8 9 --experiment-name patch9_10seeds --no-plots` |
| 保存済みCSVから再描画（シミュレーションなし） | `python src/plot_from_logs.py --single-run-dir results/single_runs/seed_42` | `python src/plot_from_logs.py --experiment-dir results/experiments/patch9_10seeds` |

- 複数seedの`--no-plots`は`--save-run-plots`と同時に指定できません。CSV（各seedの`log.csv`、`lineage.csv`、集計用`aggregate.csv`、`summary.csv`、系譜・遺伝子交換分析CSVなど）は通常通り保存します。
- 複数seed実行で`--save-run-plots`を付けた場合、通常の集約グラフに加えて各seedの個別グラフも生成します。
- 再描画は既存のCSVを読み込んでPNGのみを出力し、シミュレーションを回したりCSVを再集計・書き換えたりしません。既存PNGがある場合は上書きします。
- 複数seedで各seedのグラフも後から出したい場合は、再描画コマンドに`--save-run-plots`を追加します。
- 複数seed再描画時は`aggregate.csv`と少なくとも一つの`seed_*/log.csv`が必要です。`summary.csv`があれば、そのseed一覧・順序に従います。`--reference-seed 0`で餌リポップ率グラフの代表seedを指定することもできます。
- 遺伝子交換関連のグラフは保存済みの`gene_flow_by_window.csv`または`gene_flow_windows_across_seeds.csv`がある場合のみ再描画します。
- 実行ステップ数は`configs/default.yaml`や`--config`で選択したYAMLの`simulation.duration_mode`に従います。`--no-plots`は実行期間を短縮するオプションではありません。

### 餌再生成処理の高速化（再現性の検証）

パッチ領域は実験中に変わらないため、`Environment._get_patch_cells()` の結果をキャッシュして再利用します。餌の再生成時、パッチ外の空きセル判定にはキャッシュされた `set` を利用します。**候補セルの列挙順序、`np.random.choice` の呼び出し、餌供給割合・個数の計算は変更していません。**

以下のテストでは、最適化前の再生成処理と最適化後の処理を、同じseedの初期状態・乱数状態から開始し、餌配置・食料フローカウンタ・乱数状態・短いシミュレーション全体のログを比較します。

```bash
python -m pytest tests/test_food_respawn_optimization.py -q
python -m pytest tests -q
```

Windows PowerShellで処理時間を比較するときは、最適化前と**同じ** `results/profile_config.yaml`（1,000step・seed 0）を使い、グラフを出力しない状態で計測します。

```powershell
Measure-Command {
    python src/run_experiments.py --config results/profile_config.yaml --seeds 0 --experiment-name speed_after --no-plots
}
```

結果が一致したことを確認してからマージしてください。計測は通常実行の `TotalSeconds` を比較します（cProfile実行は計測負荷があるので高速化率の判定に使いません）。

### 移動処理の高速化（行動ルールは変更しない）

`Organism.move()` について、移動前の「記憶している餌の場所までのマンハッタン距離」を移動候補ごとの計算から**個体・ステップあたり1回**の計算に変更しました。また、隣接移動先の折り返し座標を再利用し、方向の定義と重み配列の合計も再計算しないようにしました。

**探索傾向、移動重み、移動候補の順序、`np.random.choice` の呼び出し回数・確率、乱数の進行は変更しません。** 個体の行動重み（例：現在マス8・隣接餌4・記憶2）の変更は別途実施します。

旧実装は `tests/reference_move_baseline.py` に固定し、以下で各方向の選択確率・乱数状態・移動先・短いシミュレーション全体のログを厳密に比較できます。

```bash
python -m pytest tests/test_move_optimization.py -q
python -m pytest tests -q
```

比較前の基準は、餌再生成高速化後の `speed_after`（seed0、1000step、`--no-plots`）の **約31.09秒**です。同じ `results/profile_config.yaml` を使って計測してください。

```powershell
Measure-Command {
    python src/run_experiments.py --config results/profile_config.yaml --seeds 0 --experiment-name move_after --no-plots
}
```

`results/experiments/speed_after/` と `results/experiments/move_after/` に保存されたCSVを比較し、同じ出力になることを確認してからマージしてください。

### 行動重みの調整と場所記憶の距離評価

新しい比較条件（`configs/default.yaml`、`configs/patch16.yaml`、`configs/random_periodic.yaml`）では、行動に使う追加重みを次のように変更します。

| 設定 | 従来値 | 新しい値 | 加算対象 |
| --- | ---: | ---: | --- |
| `current_cell_food_weight` | 8.0 | 1.0 | 現在のマスに餌がある場合の「停止」候補 |
| `nearby_food_weight` | 4.0 | 0.5 | 餌が検知された**各方向** |
| `site_memory_weight` | 2.0 | 0.2 | **記憶地点に近づく方向全体の合計** |

`site_memory_mode: euclidean_inverse_total` は、周期境界を考慮したユークリッド距離を、**方向の選別と分配の両方**に用います。

- 現在位置から記憶地点までの周期ユークリッド距離を `d_before`、候補方向へ1マス進んだ後の距離を `d_i` とします。`d_i < d_before` の方向だけを対象にします
- 対象方向の優先度は `q_i = 1/(d_i + 1)` とし、合計 `site_memory_weight * site_fidelity` を `q_i / sum(q)` の比率で分配します
- 記憶が無効・期限切れ、場所忠実度0、または近づける方向がない場合、記憶による重みは付けません。記憶地点上で「停止」を優遇する処理はありません
- 元々の探索傾向の重みや餌による重みは従来通り加算し、最後に全候補の重みを正規化して移動方向を選択します
- 縦横・斜めを等しい1ステップで移動できるMoore近傍では、ユークリッド距離は厳密な「最短必要ステップ数」ではなく、**空間的な近さ**を評価する尺度です

旧実験の再現性のため、`site_memory_mode` を省略した場合は `legacy_manhattan`（従来の周期マンハッタン距離で、近づく各方向に`site_memory_weight * site_fidelity`を加算）を使います。旧実験用の `configs/step4_*.yaml` は**変更していません**。新しい設定を使う場合は `euclidean_inverse_total` を明示してください。

これは**意図的な行動モデルの変更**なので、既存の1000ステップ実験（`speed_after`、`move_after`）と新しい実験のCSVは一致しなくて正常です。再現性は「同じ新設定・同じseedで同じ結果になること」で検証してください。

**注意：** 以前作成した `results/profile_config.yaml` は旧行動重みのスナップショットです。そのまま実行しても新方式にはなりません。新設定を1000ステップで試す場合は、次のように新しい短縮版設定を生成してください（既存の比較データは残します）。

```powershell
python -c "from pathlib import Path; import yaml; c=yaml.safe_load(Path('configs/default.yaml').read_text(encoding='utf-8')); c['simulation']['duration_mode']='steps'; c['simulation']['steps']=1000; Path('results').mkdir(exist_ok=True); Path('results/euclidean_1000.yaml').write_text(yaml.safe_dump(c,allow_unicode=True,sort_keys=False),encoding='utf-8')"
python src/run_experiments.py --config results/euclidean_1000.yaml --seeds 0 --experiment-name euclidean_1000_seed0 --no-plots
```

```powershell
python -m pytest tests/test_euclidean_memory_weights.py -q
python -m pytest tests/test_move_optimization.py tests/test_periodic_boundaries.py -q
python -m pytest tests -q
```

### ヘルプ

```bash
python src/main.py --help
python src/run_experiments.py --help
python src/plot_from_logs.py --help
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

`behavior.current_cell_food_weight: 1.0`、`behavior.nearby_food_weight: 0.5`、`behavior.site_memory_weight: 0.2` を現在の標準行動重みとして使用します。上の「行動重みの調整と場所記憶の距離評価」は過去の値からの変更経緯を記録したものです。

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
- `organism.lifespan_distribution`
- `organism.lifespan_mean`
- `organism.lifespan_std`
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

以下は主要ファイルの抜粋です。予備実験・校正・追加分析・テスト用のスクリプトもリポジトリ内に存在します。

```text
daphnia_evolution_sim/
├─ README.md
├─ requirements.txt
├─ configs/
│  └─ default.yaml
├─ data/
│  └─ kasumigaura_sta9_food_respawn_365_mean002.csv
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
- `src/plot_from_logs.py`: 保存済みログからの再描画
- `src/run_grid_long12.py`: 12条件 × 2環境の5年間・10seed校正実験
- `src/last_year_summary.py`: 最終年の集計
- `src/analyze_gene_flow.py`: 遺伝子提供関係の分析
- `src/analyze_offspring_outcomes.py`: 出生後の生存・繁殖成績の分析
- `tests/`: モデルの回帰テスト・再現性検証

## 本実験の比較方針と今後の作業

本実験では、環境条件と遺伝子交換条件が、個体間の遭遇機会・交換成立・交換形質の変化に与える影響を比較します。

- **空間分布**：ランダム環境／パッチ環境（標準4パッチ。16パッチは追加検証用）
- **時間変動**：一定供給／季節変動あり
- **食料供給量**：年平均再生成率 0.01／0.02／0.03 を比較候補とする（条件生成・確定値は本実験設定で管理）
- **遺伝子交換**：交換なし／固定値（例：確率100%・割合50%、確率50%・割合25%）／進化可能（交換形質の初期値0・0またはランダム）
- **実行・評価**：原則5年間・seed 0〜9を想定。個体群動態、遭遇機会、交換イベントと実効交換、形質、遺伝的多様性、系譜、生存・繁殖成績、最終年の平均とばらつきを比較

上記は**研究計画を含む比較方針**であり、列挙した条件すべてが現時点で実行済みという意味ではありません。各条件の実装・実行可否および採用範囲は、本実験開始前に設定生成コード・実行ログと照合します。

モデル拡張（追加の交換コスト、環境ストレス応答、休眠卵など）は今回の本実験とは区別し、必要な場合に別途検討します。

## 補足

- 季節的食料供給曲線は、実測値の季節性を参考にしたシミュレーション用の環境入力です。
- 一次生産量から食料個数への物理単位の直接変換ではありません。
- 現在の遺伝子交換は、無性生殖時に局所的な他個体の遺伝情報を子ゲノムへコピーするモデルです。
- 完全な有性生殖や二倍体遺伝を再現するものではありません。
- ライブ可視化は、必要に応じてGIFまたはMP4として保存できます。
- ライブ可視化の保存先は、`configs/default.yaml` の `visualization.animation_path` および `visualization.video_path` から変更できます。
