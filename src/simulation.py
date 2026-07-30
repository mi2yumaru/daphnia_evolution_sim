"""
simulation.py - シミュレーション主制御

Simulation クラスが各ステップでの環境、個体群、食料の更新を管理
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
from pathlib import Path
import csv
import numpy as np
try:
    from .organism import Organism
    from .environment import Environment
    from .logger import SimulationLogger
except Exception:
    # when running as a script (python src/main.py) the package-relative imports
    # fail; fall back to top-level module imports
    from organism import Organism
    from environment import Environment
    from logger import SimulationLogger


class Simulation:
    """
    シミュレーション全体を制御するクラス
    
    設定に基づいて初期化し、各ステップの環境更新、個体の行動、ログ記録を行う
    """
    
    MONTH_LENGTHS = (
        31, 28, 31, 30, 31, 30,
        31, 31, 30, 31, 30, 31,
    )

    def __init__(self, config: Dict[str, Any]):
        """
        シミュレーションを初期化
        
        Args:
            config: 設定辞書（YAMLから読み込まれたもの）
        """
        self.config = config
        
        # 設定の取得
        sim_config = config["simulation"]
        env_config = config["environment"]
        org_config = config["organism"]
        gen_config = config["genetics"]

        gene_exchange_config = config.get(
            "gene_exchange",
            {},
        )

        self.gene_exchange_enabled = bool(
            gene_exchange_config.get(
                "enabled",
                False,
            )
        )

        self.gene_exchange_probability = float(
            gene_exchange_config.get(
                "probability",
                0.0,
            )
        )

        self.gene_exchange_fraction = float(
            gene_exchange_config.get(
                "fraction",
                0.0,
        )
        )

        if not 0.0 <= self.gene_exchange_probability <= 1.0:
            raise ValueError(
                "gene_exchange.probability must be between 0.0 and 1.0"
            )

        if not 0.0 <= self.gene_exchange_fraction <= 0.5:
            raise ValueError(
                "gene_exchange.fraction must be between 0.0 and 0.5"
            )

        # -------------------------
        # 年間時間スケール
        # -------------------------

        self.steps_per_day = int(
            sim_config.get("steps_per_day", 10)
        )

        self.days_per_year = int(
            sim_config.get("days_per_year", 365)
        )

        if self.steps_per_day <= 0:
            raise ValueError(
                "simulation.steps_per_day must be greater than 0"
            )

        if self.days_per_year <= 0:
            raise ValueError(
                "simulation.days_per_year must be greater than 0"
            )


        # -------------------------
        # 季節的な餌再生成設定
        # -------------------------

        seasonal_food_config = config.get(
            "seasonal_food",
            {},
        )

        self.seasonal_food_enabled = bool(
            seasonal_food_config.get(
                "enabled",
                False,
            )
        )

        self.seasonal_food_rates: Dict[int, float] = {}

        if self.seasonal_food_enabled:
            csv_path = Path(
                seasonal_food_config["csv_path"]
            )

            # 相対パスならプロジェクトルート基準にする
            if not csv_path.is_absolute():
                project_root = (
                    Path(__file__).resolve().parent.parent
                )
                csv_path = project_root / csv_path

            self.seasonal_food_rates = (
                self._load_seasonal_food_rates(
                    csv_path,
                    self.days_per_year,
                )
            )
        
        # 乱数シードの設定
        np.random.seed(sim_config["random_seed"])

        # 初期年齢専用の独立した乱数生成器
        initial_age_rng = np.random.default_rng(
            np.random.SeedSequence(
                [int(sim_config["random_seed"]), 1]
            )
        )

        # 個体寿命専用の独立した乱数生成器
        self.lifespan_rng = np.random.default_rng(
            np.random.SeedSequence(
                [
                    int(sim_config["random_seed"]),
                    2,
                ]
            )
        )

        # 遺伝子交換専用の独立した乱数生成器
        self.gene_exchange_rng = np.random.default_rng(
            np.random.SeedSequence(
                [
                    int(sim_config["random_seed"]),
                    3,
                ]
            )
        )
        
        # 環境の初期化
        self.environment = Environment(
            env_config["width"],
            env_config["height"],
            respawn_mode=env_config.get("mode", "random"),
            patch_count=env_config.get("patch_count", 4),
            patch_radius=env_config.get("patch_radius", 5),
            patch_density=env_config.get("patch_density", 0.8),
            outside_respawn_fraction=env_config.get("outside_respawn_fraction", 0.05),
            patch_layout=env_config.get("patch_layout", "random"),
            patch_centers_config=env_config.get("patch_centers", None),
            patch_radial_fraction=env_config.get("patch_radial_fraction", 0.25),
            patch_spread_use_corners=env_config.get("patch_spread_use_corners", True),
            patch_spread_step=env_config.get("patch_spread_step", 0)
        )
        self.environment.init_food(env_config["initial_food_count"])
        
        # 初期年齢ランダム化設定
        randomize_initial_age = org_config.get(
            "randomize_initial_age",
            False,
        )

        max_age = int(org_config["max_age"])

        if max_age <= 0:
            raise ValueError(
                f"max_age must be positive, got {max_age}"
            )
        
        # 個体寿命設定
        self.randomize_lifespan = org_config.get(
            "randomize_lifespan",
            False,
        )

        self.fixed_lifespan = int(
            org_config["max_age"]
        )

        self.lifespan_min = int(
            org_config.get(
                "lifespan_min",
                self.fixed_lifespan,
            )
        )

        self.lifespan_max = int(
            org_config.get(
                "lifespan_max",
                self.fixed_lifespan,
            )
        )

        if self.fixed_lifespan <= 0:
            raise ValueError(
                f"max_age must be positive, got {self.fixed_lifespan}"
            )

        if self.randomize_lifespan:
            if self.lifespan_min <= 0:
                raise ValueError(
                    "lifespan_min must be positive"
                )

            if self.lifespan_min > self.lifespan_max:
                raise ValueError(
                    "lifespan_min must be <= lifespan_max"
                )
            
        # 個体ID管理
        self.next_organism_id: int = 0

        # 全個体の系譜履歴
        # 死亡して self.organisms から削除された後も記録を保持する
        self.lineage_records: Dict[int, Dict[str, Any]] = {}

        # 個体群の初期化
        self.organisms: List[Organism] = []
        for _ in range(org_config["initial_population"]):
            x = np.random.randint(0, env_config["width"])
            y = np.random.randint(0, env_config["height"])

            # 個体固有の寿命を生成
            lifespan = self._sample_lifespan()

            organism_id = self._allocate_organism_id()

            if randomize_initial_age:
                # lifespan以上の年齢を生成しない
                initial_age = int(
                    initial_age_rng.integers(
                        low=0,
                        high=lifespan,
                    )
                )
            else:
                initial_age = 0

            organism = Organism(
                x=x,
                y=y,
                initial_energy=org_config["initial_energy"],
                genome_length=gen_config["genome_length"],
                initial_age=initial_age,
                lifespan=lifespan,

                organism_id=organism_id,
                parent_id=None,
                founder_id=organism_id,
                generation=0,
                birth_step=0,
            )
            self.organisms.append(organism)

            self._register_lineage(organism)
        
        # ロガーの初期化
        self.logger = SimulationLogger()
        
        # 行動設定
        self.behavior_config = config.get("behavior", {})
        
        # ステップ数
        self.current_step = 0
        
        # リアルタイム可視化などで参照する現在の季節環境
        self.current_simulation_year = 1
        self.current_day_of_year = 1
        (
            self.current_month,
            self.current_day_of_month,
        ) = self._day_of_year_to_month_day(
            self.current_day_of_year
        )

        self.current_food_respawn_rate = (
            self._get_food_respawn_rate(
                self.current_day_of_year
            )
        )

        # 前ステップの生死情報（リアルタイム可視化用）
        self.last_birth_count = 0
        self.last_death_count = 0

    def _allocate_organism_id(self) -> int:
        """
        新しい個体IDを発行する。
        """
        organism_id = self.next_organism_id
        self.next_organism_id += 1

        return organism_id
    
    def _register_lineage(
        self,
        organism: Organism,
        gene_exchange_occurred: bool = False,
        donor: Organism | None = None,
        selected_loci_count: int = 0,
        changed_bit_count: int = 0,
    ) -> None:
        """
        個体の出生情報を系譜レジストリに登録する。
        """

        self.lineage_records[
            organism.organism_id
        ] = {
            "organism_id": organism.organism_id,
            "parent_id": organism.parent_id,
            "founder_id": organism.founder_id,
            "generation": organism.generation,
            "birth_step": organism.birth_step,

            "birth_x": organism.x,
            "birth_y": organism.y,

            "lifespan": organism.lifespan,

            "birth_exploration_tendency": organism.phenotype["exploration_tendency"],
            "birth_site_fidelity": organism.phenotype["site_fidelity"],
            "birth_risk_tolerance": organism.phenotype["risk_tolerance"],
            "birth_reproduction_timing": organism.phenotype["reproduction_timing"],

            "death_step": None,
            "death_cause": None,

            "gene_exchange_occurred": gene_exchange_occurred,
            "gene_exchange_donor_id": (
                donor.organism_id
                if donor is not None
                else None
            ),
            "gene_exchange_donor_founder_id": (
                donor.founder_id
                if donor is not None
                else None
            ),
            "gene_exchange_selected_loci_count": selected_loci_count,
            "gene_exchange_changed_bit_count": changed_bit_count,
        }
    
    def _sample_lifespan(self) -> int:
        """
        個体の寿命を生成する。

        randomize_lifespan=true:
            lifespan_min ～ lifespan_max の一様分布

        randomize_lifespan=false:
            max_age の固定値
        """
        if not self.randomize_lifespan:
            return self.fixed_lifespan

        return int(
            self.lifespan_rng.integers(
                low=self.lifespan_min,
                high=self.lifespan_max + 1,
            )
        )

    def _get_gene_exchange_donor_candidates(
        self,
        parent: Organism,
        organisms_by_position: Dict[
            Tuple[int, int],
            List[Organism],
        ],
    ) -> List[Organism]:
        """
        親個体と同一セルおよび周囲8セルから、
        遺伝子交換donor候補となる別個体を取得する。
        """

        candidates: List[Organism] = []

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                target_position = (
                    parent.x + dx,
                    parent.y + dy,
                )

                for candidate in organisms_by_position.get(
                    target_position,
                    [],
                ):
                    # 自分自身はdonorにしない
                    if candidate.organism_id == parent.organism_id:
                        continue

                    candidates.append(candidate)

        return candidates
    
    @staticmethod
    def _load_seasonal_food_rates(
        csv_path: Path,
        days_per_year: int,
    ) -> Dict[int, float]:
        """
        365日分の餌再生成率CSVを読み込む。

        必須列:
            day_of_year
            food_respawn_rate
        """

        if not csv_path.exists():
            raise FileNotFoundError(
                f"Seasonal food data not found: {csv_path}"
            )

        rates: Dict[int, float] = {}

        with csv_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as f:

            reader = csv.DictReader(f)

            required_columns = {
                "day_of_year",
                "food_respawn_rate",
            }

            if reader.fieldnames is None:
                raise ValueError(
                    "Seasonal food CSV has no header."
                )

            missing_columns = (
                required_columns
                - set(reader.fieldnames)
            )

            if missing_columns:
                raise ValueError(
                    "Seasonal food CSV is missing columns: "
                    f"{missing_columns}"
                )

            for row in reader:

                day = int(
                    row["day_of_year"]
                )

                rate = float(
                    row["food_respawn_rate"]
                )

                if rate < 0.0:
                    raise ValueError(
                        "food_respawn_rate must be >= 0.0"
                    )

                rates[day] = rate

        expected_days = set(
            range(1, days_per_year + 1)
        )

        actual_days = set(
            rates.keys()
        )

        if actual_days != expected_days:
            missing_days = sorted(
                expected_days - actual_days
            )

            extra_days = sorted(
                actual_days - expected_days
            )

            raise ValueError(
                "Seasonal food CSV must contain exactly "
                f"day 1-{days_per_year}. "
                f"missing={missing_days}, "
                f"extra={extra_days}"
            )

        return rates

    def _get_calendar_position(
        self,
    ) -> Tuple[int, int]:
        """
        current_stepから
        シミュレーション年と年内日を求める。

        Returns:
            simulation_year:
                1始まりの年
            day_of_year:
                1～365
        """

        steps_per_year = (
            self.steps_per_day
            * self.days_per_year
        )

        simulation_year = (
            self.current_step
            // steps_per_year
            + 1
        )

        day_of_year = (
            (
                self.current_step
                // self.steps_per_day
            )
            % self.days_per_year
            + 1
        )

        return (
            simulation_year,
            day_of_year,
        )

    def _day_of_year_to_month_day(
        self,
        day_of_year: int,
    ) -> tuple[int, int]:
        """
        1～365の日番号を月・日に変換する。

        例:
            1   -> (1, 1)
            32  -> (2, 1)
            60  -> (3, 1)
            365 -> (12, 31)
        """

        if not 1 <= day_of_year <= 365:
            raise ValueError(
                f"day_of_year must be between 1 and 365: "
                f"{day_of_year}"
            )

        remaining_day = day_of_year

        for month, month_length in enumerate(
            self.MONTH_LENGTHS,
            start=1,
        ):
            if remaining_day <= month_length:
                return month, remaining_day

            remaining_day -= month_length

        # 通常ここには到達しない
        raise RuntimeError(
            f"Failed to convert day_of_year: {day_of_year}"
        )

    def _get_food_respawn_rate(
        self,
        day_of_year: int,
    ) -> float:
        """
        現在日の餌再生成率を返す。

        季節変動OFF:
            environment.food_respawn_rate

        季節変動ON:
            CSVの365日周期
        """

        if self.seasonal_food_enabled:
            return self.seasonal_food_rates[
                day_of_year
            ]

        return float(
            self.config["environment"][
                "food_respawn_rate"
            ]
        )

    def step(self) -> None:
        """
        シミュレーションを1ステップ進める
        
        以下の順序で処理を実行：
        1. 第2ステップ以降の場合、餌を再生成する
        2. 各個体の age を増やす
        3. 個体を移動させる
        4. 移動先に餌があれば食べる
        5. エネルギーを消費する
        6. 繁殖可能なら子個体を作る
        7. 死亡個体を除く
        8. 新しい子個体を追加する
        9. 統計情報をログに記録する
        """
        org_config = self.config["organism"]
        env_config = self.config["environment"]
        gen_config = self.config["genetics"]
        
        # -------------------------
        # 現在の年・日・餌再生成率
        # -------------------------

        simulation_year,day_of_year = (
            self._get_calendar_position()
        )

        month, day_of_month = (
            self._day_of_year_to_month_day(
                day_of_year
            )
        )

        current_food_respawn_rate = (
            self._get_food_respawn_rate(
                day_of_year
            )
        )

        # 現在ステップで実際に使用する季節環境を保持
        self.current_simulation_year = simulation_year
        self.current_day_of_year = day_of_year
        self.current_month = month
        self.current_day_of_month = day_of_month
        self.current_food_respawn_rate = current_food_respawn_rate

        food_respawn_count = 0
        food_consumed_count = 0

        # 第2ステップ以降は、個体が行動する前に餌を再生成する
        # current_step は0始まりなので、
        # current_step == 0 が第1ステップ、
        # current_step == 1 が第2ステップに対応する
        if self.current_step > 0:
            food_respawn_count = self.environment.respawn_food(
                current_food_respawn_rate
            )

        # ステップ前の個体数（死亡数を計算するため）
        population_before = len(self.organisms)
        
        # 2. 各個体の age を増やす
        for organism in self.organisms:
            organism.age_one_step()
        
        # 3-6. 個体の行動を処理
        new_offspring: List[Organism] = []
        move_count = 0
        eat_count = 0
        
        # 摂食を「移動後」と「非移動」に分けて数える
        eat_after_move_count = 0
        eat_without_move_count = 0

        # 同じ餌マスを複数個体が共有した回数を記録する
        shared_food_cell_count = 0
        shared_food_consumer_count = 0

        # 遺伝子交換に関するstep単位の統計
        gene_exchange_eligible_count = 0
        gene_exchange_event_count = 0
        gene_exchange_selected_loci_count = 0
        gene_exchange_changed_bit_count = 0

        behavior_settings = {
            "low_energy_threshold_ratio": self.behavior_config.get("low_energy_threshold_ratio", 0.5),
            "food_detection_range": self.behavior_config.get("food_detection_range", 1),
            "site_memory_steps": self.behavior_config.get("site_memory_steps", 20),
            "current_cell_food_weight": self.behavior_config.get("current_cell_food_weight", 8.0),
            "nearby_food_weight": self.behavior_config.get("nearby_food_weight", 4.0),
            "site_memory_weight": self.behavior_config.get("site_memory_weight", 2.0),
            "current_step": self.current_step
        }

        # 各個体が移動したかどうかを保持する
        # [(organism, moved), ...] の形で保存
        movement_records = []

        # -------------------------
        # 3. 移動フェーズ
        # -------------------------
        for organism in self.organisms:
            low_energy_threshold = org_config["reproduction_threshold"] * behavior_settings["low_energy_threshold_ratio"]
            low_energy = organism.energy < low_energy_threshold

            moved = organism.move(
                env_config["width"],
                env_config["height"],
                org_config["move_type"],
                self.environment,
                low_energy,
                behavior_settings
            )
            if moved:
                move_count += 1

            movement_records.append((organism, moved))

        # -------------------------
        # 遺伝子交換donor探索用の位置インデックス
        # -------------------------
        organisms_by_position: Dict[
            Tuple[int, int],
            List[Organism],
        ] = defaultdict(list)

        for organism, _ in movement_records:
            organisms_by_position[
                (organism.x, organism.y)
            ].append(organism)

        # -------------------------
        # 4. 摂食フェーズ
        #    同じ餌マスにいる個体で food_energy を等分する
        # -------------------------
        eating_candidates: Dict[Tuple[int, int], List[tuple[Organism, bool]]] = defaultdict(list)

        # 餌があるマスにいる個体を、座標ごとに集める
        for organism, moved in movement_records:
            position = (organism.x, organism.y)

            if self.environment.has_food(organism.x, organism.y):
                eating_candidates[position].append((organism, moved))

        # 座標ごとに餌を分配する
        for (food_x, food_y), candidates in eating_candidates.items():
            # 念のため、まだ餌が存在するか確認
            if not self.environment.has_food(food_x, food_y):
                continue

            consumer_count = len(candidates)

            if consumer_count <= 0:
                continue

            # 2個体以上が同じ餌マスを利用する場合、「共有餌」として記録する
            if consumer_count > 1:
                shared_food_cell_count += 1
                shared_food_consumer_count += consumer_count

            # 同じ餌マスにいる個体数で food_energy を等分
            shared_food_energy = env_config["food_energy"] / consumer_count

            for organism, moved in candidates:
                organism.eat(shared_food_energy)
                organism.last_food_position = (food_x, food_y)
                organism.last_food_step = self.current_step

                eat_count += 1

                if moved:
                    eat_after_move_count += 1
                else:
                    eat_without_move_count += 1

            # そのマスの餌は、このstepで消費されたので削除
            self.environment.remove_food(food_x, food_y)
            food_consumed_count += 1


        # -------------------------
        # 5-6. エネルギー消費・繁殖フェーズ
        # -------------------------
        for organism, moved in movement_records:
            # living_cost は毎ステップ必ず消費
            # move_cost は実際に移動した場合のみ消費
            move_cost = org_config["move_cost"] if moved else 0.0
            organism.consume_energy(
                move_cost,
                org_config["living_cost"],
            )
            
            # 5. 繁殖可能なら子個体を作る
            if organism.can_reproduce(org_config["reproduction_threshold"]):
                donor = None
                exchange_loci = np.array([], dtype=int)
                selected_loci_count = 0
                changed_bit_count = 0

                donor_candidates = (
                    self._get_gene_exchange_donor_candidates(
                        organism,
                        organisms_by_position,
                    )
                )

                if donor_candidates:
                    gene_exchange_eligible_count += 1

                    exchange_occurs = False

                    if self.gene_exchange_enabled:
                        exchange_occurs = (
                            self.gene_exchange_rng.random()
                            < self.gene_exchange_probability
                        )

                    if exchange_occurs:
                        gene_exchange_event_count += 1

                        # donorを候補から1個体ランダム選択
                        donor_index = int(
                            self.gene_exchange_rng.integers(
                                len(donor_candidates)
                            )
                        )
                        donor = donor_candidates[donor_index]

                        # donorから受け継ぐlocus数を決定
                        selected_loci_count = int(
                            gen_config["genome_length"]
                            * self.gene_exchange_fraction
                            + 0.5
                        )

                        if selected_loci_count > 0:
                            exchange_loci = (
                                self.gene_exchange_rng.choice(
                                    gen_config["genome_length"],
                                    size=selected_loci_count,
                                    replace=False,
                                )
                            )

                            changed_bit_count = int(
                                np.sum(
                                    organism.genome[exchange_loci]
                                    != donor.genome[exchange_loci]
                                )
                            )

                        gene_exchange_selected_loci_count += (
                            selected_loci_count
                        )

                        gene_exchange_changed_bit_count += (
                            changed_bit_count
                        )

                offspring_lifespan = self._sample_lifespan()
                child_organism_id = self._allocate_organism_id()
                
                child = organism.reproduce(
                    width=env_config["width"],
                    height=env_config["height"],
                    offspring_energy=org_config["offspring_energy"],
                    reproduction_cost=org_config["reproduction_cost"],
                    mutation_rate=gen_config["mutation_rate"],
                    genome_length=gen_config["genome_length"],
                    offspring_lifespan=offspring_lifespan,
                    child_organism_id=child_organism_id,
                    birth_step=self.current_step,

                    donor_genome=(
                        donor.genome
                       if donor is not None
                       else None
                        ),
                    exchange_loci=exchange_loci,
                )
                self._register_lineage(
                    child,
                    gene_exchange_occurred=(donor is not None),
                    donor=donor,
                    selected_loci_count=selected_loci_count,
                    changed_bit_count=changed_bit_count,
                )
                new_offspring.append(child)
        
        # 7. 死亡個体を原因別に集計し、生存個体のみ残す
        survivors: List[Organism] = []

        age_death_count = 0
        energy_death_count = 0

        for organism in self.organisms:
            cause = organism.death_cause(
                org_config["max_age"]
            )

            if cause is not None:
                record = self.lineage_records.get(
                    organism.organism_id
                )

                if (
                    record is not None
                    and record["death_step"] is None
                ):
                    record["death_step"] = (
                        self.current_step
                    )

                    record["death_cause"] = cause

            if cause == "energy":
                energy_death_count += 1

            elif cause == "age":
                age_death_count += 1

            else:
                survivors.append(organism)


        self.organisms = survivors

        # 総死亡数
        death_count = (
            age_death_count
            + energy_death_count
        )

        birth_count = len(new_offspring)

        gene_exchange_eligible_rate = (
            gene_exchange_eligible_count / birth_count
            if birth_count > 0
            else 0.0
        )

        gene_exchange_event_rate = (
            gene_exchange_event_count
            / gene_exchange_eligible_count
            if gene_exchange_eligible_count > 0
            else 0.0
        )

        gene_exchange_birth_rate = (
            gene_exchange_event_count / birth_count
            if birth_count > 0
            else 0.0
        )
        
        # 8. 新しい子個体を追加する
        self.organisms.extend(new_offspring)
        
        # 9. 統計情報をログに記録する
        population_size = len(self.organisms)
        food_count = self.environment.food_count()

        move_rate = move_count / population_before if population_before > 0 else 0.0

        # 移動しなかった個体数
        non_move_count = population_before - move_count

        # 総摂食率: step開始時の個体数に対して、餌を食べた個体の割合
        total_eat_rate = eat_count / population_before if population_before > 0 else 0.0

        # 既存の eat_rate は互換性のため総摂食率として残す
        eat_rate = total_eat_rate

        # 移動後摂食率: 移動した個体のうち、移動後に餌を食べた割合
        eat_after_move_rate = (
            eat_after_move_count / move_count
            if move_count > 0
            else 0.0
        )

        # 非移動摂食率: step開始時の個体数に対して、移動せずに餌を食べた個体の割合
        eat_without_move_rate = (
            eat_without_move_count / non_move_count
            if non_move_count > 0
            else 0.0
        )

        # 旧 eat_per_move は互換性のため残す。
        # ただし意味は「移動後摂食率」と同じにする。
        eat_per_move = eat_after_move_rate

        # 共有された餌1マスあたりの平均摂食個体数
        mean_consumers_per_shared_food = (
            shared_food_consumer_count / shared_food_cell_count
            if shared_food_cell_count > 0
            else 0.0
        )

        # birth_rate / death_rate はステップ開始時の個体数に対する割合
        birth_rate = birth_count / population_before if population_before > 0 else 0.0
        death_rate = death_count / population_before if population_before > 0 else 0.0
        age_death_rate = (
            age_death_count / population_before
            if population_before > 0
            else 0.0
        )
        energy_death_rate = (
            energy_death_count / population_before
            if population_before > 0
            else 0.0
        )

        if population_size > 0:
            average_energy = sum(org.energy for org in self.organisms) / population_size
            average_age = sum(org.age for org in self.organisms) / population_size
            
            exploration_values = [org.phenotype["exploration_tendency"] for org in self.organisms]
            site_fidelity_values = [org.phenotype["site_fidelity"] for org in self.organisms]
            risk_tolerance_values = [org.phenotype["risk_tolerance"] for org in self.organisms]
            reproduction_timing_values = [org.phenotype["reproduction_timing"] for org in self.organisms]

            average_exploration_tendency = sum(org.phenotype["exploration_tendency"] for org in self.organisms) / population_size
            average_site_fidelity = sum(org.phenotype["site_fidelity"] for org in self.organisms) / population_size
            average_risk_tolerance = sum(org.phenotype["risk_tolerance"] for org in self.organisms) / population_size
            average_reproduction_timing = sum(org.phenotype["reproduction_timing"] for org in self.organisms) / population_size
        
            std_exploration_tendency = float(np.std(exploration_values))
            std_site_fidelity = float(np.std(site_fidelity_values))
            std_risk_tolerance = float(np.std(risk_tolerance_values))
            std_reproduction_timing = float(np.std(reproduction_timing_values))

            min_exploration_tendency = min(exploration_values)
            max_exploration_tendency = max(exploration_values)

            min_site_fidelity = min(site_fidelity_values)
            max_site_fidelity = max(site_fidelity_values)

            min_risk_tolerance = min(risk_tolerance_values)
            max_risk_tolerance = max(risk_tolerance_values)

            min_reproduction_timing = min(reproduction_timing_values)
            max_reproduction_timing = max(reproduction_timing_values)
        
        else:
            average_energy = 0.0
            average_age = 0.0
            average_exploration_tendency = 0.0
            average_site_fidelity = 0.0
            average_risk_tolerance = 0.0
            average_reproduction_timing = 0.0

            std_exploration_tendency = 0.0
            std_site_fidelity = 0.0
            std_risk_tolerance = 0.0
            std_reproduction_timing = 0.0

            min_exploration_tendency = 0.0
            max_exploration_tendency = 0.0

            min_site_fidelity = 0.0
            max_site_fidelity = 0.0

            min_risk_tolerance = 0.0
            max_risk_tolerance = 0.0

            min_reproduction_timing = 0.0
            max_reproduction_timing = 0.0

        # 系譜統計を計算
        if population_size > 0:
            lineage_counts = Counter(
                organism.founder_id
                for organism in self.organisms
            )

            # 現在生存しているFounder系統数
            active_lineage_count = len(
                lineage_counts
            )

            # 最大系統が現在の集団に占める割合
            largest_lineage_share = (
                max(lineage_counts.values())
                / population_size
            )

            # 現在の集団の平均世代
            average_generation = (
                sum(
                    organism.generation
                    for organism in self.organisms
                )
                / population_size
            )

            # 現在生存している個体の最大世代
            max_generation = max(
                organism.generation
                for organism in self.organisms
            )

        else:
            active_lineage_count = 0
            largest_lineage_share = 0.0
            average_generation = 0.0
            max_generation = 0

        
        self.logger.record(
            step=self.current_step,
            simulation_year=simulation_year,
            day_of_year=day_of_year,
            month=month,
            day_of_month=day_of_month,
            food_respawn_rate=current_food_respawn_rate,
            population_size=population_size,
            food_count=food_count,
            food_respawn_count=food_respawn_count,
            food_consumed_count=food_consumed_count,
            average_energy=average_energy,
            average_age=average_age,
            birth_count=birth_count,
            death_count=death_count,
            age_death_count=age_death_count,
            energy_death_count=energy_death_count,
            move_count=move_count,
            move_rate=move_rate,
            non_move_count=non_move_count,
            eat_count=eat_count,
            eat_rate=eat_rate,
            eat_per_move=eat_per_move,
            eat_after_move_count=eat_after_move_count,
            eat_without_move_count=eat_without_move_count,
            eat_after_move_rate=eat_after_move_rate,
            eat_without_move_rate=eat_without_move_rate,
            total_eat_rate=total_eat_rate,
            shared_food_cell_count=shared_food_cell_count,
            shared_food_consumer_count=shared_food_consumer_count,
            mean_consumers_per_shared_food=mean_consumers_per_shared_food,
            birth_rate=birth_rate,
            gene_exchange_eligible_count=gene_exchange_eligible_count,
            gene_exchange_event_count=gene_exchange_event_count,
            gene_exchange_selected_loci_count=gene_exchange_selected_loci_count,
            gene_exchange_changed_bit_count=gene_exchange_changed_bit_count,
            gene_exchange_eligible_rate=gene_exchange_eligible_rate,
            gene_exchange_event_rate=gene_exchange_event_rate,
            gene_exchange_birth_rate=gene_exchange_birth_rate,
            death_rate=death_rate,
            age_death_rate=age_death_rate,
            energy_death_rate=energy_death_rate,
            average_exploration_tendency=average_exploration_tendency,
            std_exploration_tendency=std_exploration_tendency,
            min_exploration_tendency=min_exploration_tendency,
            max_exploration_tendency=max_exploration_tendency,
            average_site_fidelity=average_site_fidelity,
            std_site_fidelity=std_site_fidelity,
            min_site_fidelity=min_site_fidelity,
            max_site_fidelity=max_site_fidelity,
            average_risk_tolerance=average_risk_tolerance,
            std_risk_tolerance=std_risk_tolerance,
            min_risk_tolerance=min_risk_tolerance,
            max_risk_tolerance=max_risk_tolerance,
            average_reproduction_timing=average_reproduction_timing,
            std_reproduction_timing=std_reproduction_timing,
            min_reproduction_timing=min_reproduction_timing,
            max_reproduction_timing=max_reproduction_timing,
            active_lineage_count=active_lineage_count,
            largest_lineage_share=largest_lineage_share,
            average_generation=average_generation,
            max_generation=max_generation,
        )
        
        # 前ステップの生死情報を更新
        self.last_birth_count = birth_count
        self.last_death_count = death_count
        
        self.current_step += 1
    
    def run(self) -> None:
        """
        シミュレーションを最後まで実行
        
        設定された steps の数だけ step() を呼び出す
        """
        total_steps = self.config["simulation"]["steps"]
        
        for _ in range(total_steps):
            self.step()
            
            # 個体数が0になってもエラーにならないようにする
            if len(self.organisms) == 0:
                # 個体がいない場合でも処理は続ける
                pass
    
    def get_state(self) -> Dict[str, Any]:
        """
        現在のシミュレーション状態を返す
        
        Returns:
            dict: 現在の状態を含む辞書
                - step: 現在のステップ数
                - organism_positions: 個体の座標リスト [(x, y), ...]
                - organism_energies: 個体のエネルギーリスト
                - organism_states: 個体の状態（"normal" or "can_reproduce"）
                - food_positions: 食料の座標リスト
                - population_size: 個体数
                - food_count: 食料数
                - average_energy: 平均エネルギー
        """
        org_config = self.config["organism"]
        
        organism_positions = [(org.x, org.y) for org in self.organisms]
        organism_energies = [org.energy for org in self.organisms]
        
        # 個体の状態を判定
        organism_states = []
        for org in self.organisms:
            if org.can_reproduce(org_config["reproduction_threshold"]):
                organism_states.append("can_reproduce")
            else:
                organism_states.append("normal")
        
        food_positions = list(self.environment.food)
        population_size = len(self.organisms)
        food_count = self.environment.food_count()
        
        if population_size > 0:
            average_energy = sum(organism_energies) / population_size
            average_age = sum(org.age for org in self.organisms) / population_size
        else:
            average_energy = 0.0
            average_age = 0.0
        
        return {
            "step": self.current_step,
            "simulation_year": self.current_simulation_year,
            "day_of_year": self.current_day_of_year,
            "month": self.current_month,
            "day_of_month": self.current_day_of_month,
            "food_respawn_rate": self.current_food_respawn_rate,
            "organism_positions": organism_positions,
            "organism_energies": organism_energies,
            "organism_states": organism_states,
            "organism_phenotypes": [org.phenotype for org in self.organisms],
            "food_positions": food_positions,
            "population_size": population_size,
            "food_count": food_count,
            "average_energy": average_energy,
            "average_age": average_age,
            "birth_count": self.last_birth_count,
            "death_count": self.last_death_count
        }
