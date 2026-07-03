"""
logger.py - シミュレーション結果のログ記録

各ステップの統計情報を記録し、CSV形式で保存
"""

from typing import List, Dict, Any
import pandas as pd


class SimulationLogger:
    """
    シミュレーション結果をログに記録するクラス
    
    各ステップでの個体数、食料数、平均エネルギーなどを記録します
    """
    
    def __init__(self):
        """ロガーを初期化"""
        self.logs: List[Dict[str, Any]] = []
    
    def record(
        self,
        step: int,
        population_size: int,
        food_count: int,
        average_energy: float,
        average_age: float,
        birth_count: int,
        death_count: int,
        move_count: int,
        move_rate: float,
        non_move_count: int,
        eat_count: int,
        eat_rate: float,
        eat_per_move: float,
        eat_after_move_count: int,
        eat_without_move_count: int,
        eat_after_move_rate: float,
        eat_without_move_rate: float,
        total_eat_rate: float,
        birth_rate: float,
        death_rate: float,
        average_exploration_tendency: float,
        std_exploration_tendency: float,
        min_exploration_tendency: float,
        max_exploration_tendency: float,
        average_site_fidelity: float,
        std_site_fidelity: float,
        min_site_fidelity: float,
        max_site_fidelity: float,
        average_risk_tolerance: float,
        std_risk_tolerance: float,
        min_risk_tolerance: float,
        max_risk_tolerance: float,
        average_reproduction_timing: float,
        std_reproduction_timing: float,
        min_reproduction_timing: float,
        max_reproduction_timing: float
    ) -> None:
        """
        1ステップ分のデータを記録
        
        Args:
            step: ステップ数
            population_size: 現在の個体数
            food_count: 現在の食料数
            average_energy: 個体群の平均エネルギー
            average_age: 個体群の平均年齢
            birth_count: このステップで生まれた個体数
            death_count: このステップで死んだ個体数
            move_count: このステップで移動した個体数
            move_rate: 移動率
            non_move_count: このステップで移動しなかった個体数
            eat_count: このステップで餌を食べた個体数
            eat_rate: 摂食率
            eat_per_move: 互換性用。現在は eat_after_move_rate と同じ値
            eat_after_move_count: 移動後に餌を食べた個体数
            eat_without_move_count: 移動せずに餌を食べた個体数
            eat_after_move_rate: 移動した個体のうち、移動後に餌を食べた割合
            eat_without_move_rate: 移動しなかった個体のうち、餌を食べた割合
            total_eat_rate: step開始時個体数に対する、摂食個体全体の割合
            birth_rate: 繁殖率
            death_rate: 死亡率
            std_exploration_tendency: 探索傾向の標準偏差
            min_exploration_tendency: 探索傾向の最小値
            max_exploration_tendency: 探索傾向の最大値
            std_site_fidelity: 場所忠誠心の標準偏差
            min_site_fidelity: 場所忠誠心の最小値
            max_site_fidelity: 場所忠誠心の最大値
            std_risk_tolerance: リスク許容度の標準偏差
            min_risk_tolerance: リスク許容度の最小値
            max_risk_tolerance: リスク許容度の最大値
            std_reproduction_timing: 繁殖タイミングの標準偏差
            min_reproduction_timing: 繁殖タイミングの最小値
            max_reproduction_timing: 繁殖タイミングの最大値
        """
        self.logs.append({
            "step": step,
            "population_size": population_size,
            "food_count": food_count,
            "average_energy": average_energy,
            "average_age": average_age,
            "birth_count": birth_count,
            "death_count": death_count,
            "move_count": move_count,
            "move_rate": move_rate,
            "non_move_count": non_move_count,
            "eat_count": eat_count,
            "eat_rate": eat_rate,
            "eat_per_move": eat_per_move,
            "eat_after_move_count": eat_after_move_count,
            "eat_without_move_count": eat_without_move_count,
            "eat_after_move_rate": eat_after_move_rate,
            "eat_without_move_rate": eat_without_move_rate,
            "total_eat_rate": total_eat_rate,
            "birth_rate": birth_rate,
            "death_rate": death_rate,
            "average_exploration_tendency": average_exploration_tendency,
            "std_exploration_tendency": std_exploration_tendency,
            "min_exploration_tendency": min_exploration_tendency,
            "max_exploration_tendency": max_exploration_tendency,
            "average_site_fidelity": average_site_fidelity,
            "std_site_fidelity": std_site_fidelity,
            "min_site_fidelity": min_site_fidelity,
            "max_site_fidelity": max_site_fidelity,
            "average_risk_tolerance": average_risk_tolerance,
            "std_risk_tolerance": std_risk_tolerance,
            "min_risk_tolerance": min_risk_tolerance,
            "max_risk_tolerance": max_risk_tolerance,
            "average_reproduction_timing": average_reproduction_timing,
            "std_reproduction_timing": std_reproduction_timing,
            "min_reproduction_timing": min_reproduction_timing,
            "max_reproduction_timing": max_reproduction_timing
        })
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        ログデータをDataFrameに変換
        
        Returns:
            pd.DataFrame: ログデータを持つDataFrame
        """
        return pd.DataFrame(self.logs)
    
    def save_csv(self, path: str) -> None:
        """
        ログをCSVファイルに保存
        
        Args:
            path: 保存先のファイルパス
        """
        df = self.to_dataframe()
        df.to_csv(path, index=False)
