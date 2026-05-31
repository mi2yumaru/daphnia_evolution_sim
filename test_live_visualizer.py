"""
test_live_visualizer.py - リアルタイム可視化機能のテスト
"""
import sys
from pathlib import Path

# src ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

import yaml
from simulation import Simulation
from live_visualizer import LiveVisualizer

def test_get_state_method():
    """get_state() メソッドが正常に動作することを確認"""
    print("=" * 50)
    print("テスト 1: get_state() メソッドの確認")
    print("=" * 50)
    
    # 設定を読み込む
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Simulation を作成
    sim = Simulation(config)
    
    # get_state() メソッドが存在することを確認
    state = sim.get_state()
    print("✓ get_state() メソッドが正常に動作しています")
    print(f"  Step: {state['step']}")
    print(f"  Population: {state['population_size']}")
    print(f"  Food: {state['food_count']}")
    print(f"  Avg Energy: {state['average_energy']:.2f}")
    
    # 返却されたデータ構造を確認
    required_keys = [
        "step", "organism_positions", "organism_energies", "organism_states",
        "food_positions", "population_size", "food_count", "average_energy"
    ]
    for key in required_keys:
        assert key in state, f"Missing key: {key}"
    print(f"✓ すべての必須キーが含まれています: {required_keys}")
    print()


def test_live_visualizer_initialization():
    """LiveVisualizer が正常に初期化できることを確認"""
    print("=" * 50)
    print("テスト 2: LiveVisualizer の初期化")
    print("=" * 50)
    
    # 設定を読み込む
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # LiveVisualizer を初期化
    visualizer = LiveVisualizer(
        width=config['environment']['width'],
        height=config['environment']['height']
    )
    print("✓ LiveVisualizer が正常に初期化されました")
    
    # ビジュアライザーを閉じる
    visualizer.close()
    print("✓ ビジュアライザーを正常に閉じました")
    print()


def test_single_step_with_visualization():
    """1ステップの実行と可視化状態の確認"""
    print("=" * 50)
    print("テスト 3: 1ステップ実行と可視化状態の確認")
    print("=" * 50)
    
    # 設定を読み込む
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Simulation を作成
    sim = Simulation(config)
    
    # 初期状態
    state_before = sim.get_state()
    print(f"初期状態: Population={state_before['population_size']}, Food={state_before['food_count']}")
    
    # 1ステップ実行
    sim.step()
    
    # 更新後の状態
    state_after = sim.get_state()
    print(f"1ステップ後: Population={state_after['population_size']}, Food={state_after['food_count']}")
    
    # ステップが増えていることを確認
    assert state_after['step'] == state_before['step'] + 1, "Step number should increment"
    print("✓ ステップカウンターが正常に更新されました")
    print()


if __name__ == "__main__":
    try:
        test_get_state_method()
        test_live_visualizer_initialization()
        test_single_step_with_visualization()
        print("=" * 50)
        print("すべてのテストが成功しました！")
        print("=" * 50)
    except Exception as e:
        print(f"❌ テストが失敗しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
