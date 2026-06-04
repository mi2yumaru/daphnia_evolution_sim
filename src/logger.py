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
        death_count: int
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
        """
        self.logs.append({
            "step": step,
            "population_size": population_size,
            "food_count": food_count,
            "average_energy": average_energy,
            "average_age": average_age,
            "birth_count": birth_count,
            "death_count": death_count
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
