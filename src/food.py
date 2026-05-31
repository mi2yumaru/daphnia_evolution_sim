"""
food.py - 食料の定義

現在は環境内で座標セットとして管理されていますが、
将来的に食料の属性（栄養価、可食性など）を拡張するために用意されています。
"""

from dataclasses import dataclass


@dataclass
class Food:
    """
    食料を表現するクラス
    
    将来的には以下のような属性を追加予定：
    - quality: 栄養価
    - age: 食料の経過時間
    - toxicity: 毒性レベル
    
    属性:
        x: グリッド上のx座標
        y: グリッド上のy座標
        energy: 食料が持つエネルギー量
    """
    x: int
    y: int
    energy: float
