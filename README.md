# Daphnia Evolution Simulation

ミジンコをモチーフにしたエージェントベース進化シミュレーション

## プロジェクト概要

このプロジェクトは、将来的に「環境変動下での無性生殖・遺伝子交換・有性生殖的ふるまいの進化」を調べるためのシミュレーション基盤を提供します。

現在は、2Dグリッド上で個体と餌が存在し、個体が移動・摂食・繁殖・死亡し、ログとグラフが出力される最小モデルです。

## 現在の実装内容

- **2Dグリッド環境**: 指定されたサイズのグリッドで、個体と餌が共存
- **個体の行動**:
  - 移動（Moore型：周囲8方向）
  - 摂食
  - 無性生殖（個体複製）
  - 加齢と死亡
- **エネルギー管理**: 移動・生活・繁殖のコストを設定可能
- **ゲノム管理**: 各個体は0/1配列を持ち、変異率を設定可能
- **ログ機能**: 各ステップの個体数、食料数、平均エネルギーを記録
- **可視化**: 個体数と平均エネルギーのグラフを生成

## 将来的に追加予定の要素

- [ ] 有性生殖（2個体からの子個体生成）
- [ ] 組換え（遺伝子交換）
- [ ] 休眠卵（環境ストレス下での生存戦略）
- [ ] 環境変動（定期的な環境の変化）
- [ ] 天敵の存在
- [ ] より詳細なミジンコの生物学的設定
- [ ] 遺伝的多様性の指標
- [ ] 適応度の動的追跡

## セットアップ方法

### 必要環境
- Python 3.11 以降
- pip（Python パッケージマネージャー）

### インストール手順

1. リポジトリをクローンまたはダウンロード
```bash
cd daphnia_simulation
```

2. Python仮想環境を作成（推奨）
```bash
python -m venv .venv
```

3. 仮想環境を有効化
- Windows (PowerShell):
```powershell
.venv\Scripts\Activate.ps1
```
- Windows (cmd):
```cmd
.venv\Scripts\activate.bat
```
- macOS/Linux:
```bash
source .venv/bin/activate
```

4. 依存パッケージをインストール
```bash
pip install -r requirements.txt
```

## 実行方法

### 基本的な実行（通常モード）

CSV ログと静的グラフを出力します：
```bash
python src/main.py
```

### リアルタイム可視化モード

シミュレーション中に個体と食料の位置をリアルタイムで表示します：
```bash
python src/main.py --live
```

**リアルタイム可視化の特徴:**
- 2Dグリッド上で個体と食料をリアルタイムに表示
- 青い点: 通常の個体
- 赤い点: 繁殖可能な個体
- 緑の点: 食料
- タイトルに現在のステップ、個体数、食料数、平均エネルギーを表示
- ウィンドウを閉じるか Ctrl+C で終了

### ヘルプ表示

```bash
python src/main.py --help
```

### 出力ファイル

実行後、以下が `results/` ディレクトリに生成されます：

- **log.csv**: 各ステップの統計情報（ステップ数、個体数、食料数、平均エネルギー）
- **population.png**: 個体数の時系列グラフ
- **average_energy.png**: 平均エネルギーの時系列グラフ

### 設定のカスタマイズ

`configs/default.yaml` ファイルを編集することで、シミュレーションパラメータを変更できます。

```yaml
simulation:
  steps: 1000              # シミュレーションのステップ数
  random_seed: 42          # 乱数シード
  output_csv: "results/log.csv"
  population_plot: "results/population.png"
  energy_plot: "results/average_energy.png"

environment:
  width: 50                # グリッド幅
  height: 50               # グリッド高さ
  initial_food_count: 500  # 初期食料数
  food_respawn_rate: 0.02  # 毎ステップの食料再生成率
  food_energy: 5           # 食料1個のエネルギー値

organism:
  initial_population: 100  # 初期個体数
  initial_energy: 10       # 個体の初期エネルギー
  move_cost: 1.0           # 移動コスト
  living_cost: 0.1         # 生活維持コスト
  reproduction_threshold: 20  # 繁殖に必要なエネルギー
  reproduction_cost: 10    # 繁殖にかかるコスト
  offspring_energy: 5      # 生まれた子のエネルギー
  max_age: 200             # 最大年齢
  move_type: "moore"       # 移動タイプ（"moore" または "von_neumann"）

genetics:
  genome_length: 20        # ゲノム長
  mutation_rate: 0.01      # 1ビットあたりの変異率
  recombination_rate: 0.0  # 組換え率（将来実装用）

environment_change:
  enabled: false           # 環境変動の有無
  period: 200              # 環境変動の周期（将来実装用）

visualization:
  enabled: true            # 可視化機能の有効/無効
  interval_ms: 100         # リアルタイム描画の更新間隔（ミリ秒）
  show_food: true          # 食料を表示するか
  show_organisms: true     # 個体を表示するか
  save_animation: false    # アニメーション保存（将来実装用）
  animation_path: "results/simulation.gif"  # アニメーション保存先
```

## プロジェクト構造

```
daphnia_simulation/
├─ README.md                    # このファイル
├─ requirements.txt             # Python 依存パッケージ
├─ configs/
│  └─ default.yaml              # デフォルト設定ファイル
├─ src/
│  ├─ main.py                   # 実行エントリーポイント
│  ├─ simulation.py             # Simulation クラス（シミュレーション主制御）
│  ├─ environment.py            # Environment クラス（環境・グリッド管理）
│  ├─ organism.py               # Organism クラス（個体）
│  ├─ food.py                   # Food クラス（食料、将来拡張用）
│  ├─ logger.py                 # SimulationLogger クラス（ログ記録）
│  ├─ visualizer.py             # グラフ出力関数
│  └─ live_visualizer.py        # リアルタイム可視化クラス
├─ data/                        # 入力データ用ディレクトリ
└─ results/                     # 出力ファイル用ディレクトリ
    ├─ log.csv                  # 統計ログ
    ├─ population.png           # 個体数グラフ
    └─ average_energy.png       # 平均エネルギーグラフ
```

## 各モジュールの説明

### `src/organism.py`
個体を表現するクラス。属性としてx, y, energy, age, genome を持ち、移動、摂食、繁殖、死亡判定のメソッドを提供します。

### `src/environment.py`
2Dグリッド環境を管理するクラス。食料の配置、再生成、クエリーを行います。

### `src/food.py`
将来的な食料の複雑化に備えた Food データクラス。現在は Environment 内で座標セットとして管理されています。

### `src/logger.py`
各ステップの統計情報を記録し、CSV形式で保存するクラス。

### `src/visualizer.py`
ログデータをグラフとして可視化する関数群。

### `src/simulation.py`
Simulation クラスが主制御ロジックを担い、各ステップでの環境、個体群、食料の更新を行います。

### `src/main.py`
実行エントリーポイント。YAML設定を読み込み、シミュレーションを実行し、結果を出力します。
コマンドラインオプション（`--live`, `--help`）をサポートしています。

### `src/live_visualizer.py`
matplotlib を使ってシミュレーション状態をリアルタイムに可視化するクラス。
`python src/main.py --live` で実行時に、2Dグリッド上の個体と食料の位置をリアルタイムに表示します。
個体の繁殖状態や統計情報もグラフに表示されます。

## トラブルシューティング

### ImportError が発生する場合
- Python のパス設定を確認してください
- 依存パッケージが正しくインストールされているか確認してください: `pip list`
- 仮想環境が有効になっているか確認してください

### グラフが表示されない場合
- `results/` ディレクトリが存在することを確認してください
- matplotlib のバックエンド設定を確認してください

## 今後の開発ガイド

このシミュレーションを拡張する際は、以下の指針に従ってください：

1. **モジュール性の維持**: 各クラスの責務を明確に分けて、変更の影響を局所化する
2. **型ヒントの利用**: 新しいコードには必ず型ヒントを付ける
3. **設定の外部化**: ハードコードされた値は避け、YAML設定に移す
4. **後方互換性**: 既存の設定ファイルで実行できるように変更する
5. **テスト駆動**: 新機能追加時はテストを書いてから実装する

## ライセンス

このプロジェクトはの研究用です。

## 著者・連絡先

ご質問やご提案がありましたら、お気軽にお問い合わせください。
