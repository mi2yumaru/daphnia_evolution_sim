
from pathlib import Path
import csv
import yaml

from src.simulation import Simulation

# ===== 計測設定 =====
SEED = 42
STEPS = 300
RECORD_EVERY = 10

# 設定ファイルを読み込み
with open("configs/default.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

config["simulation"]["random_seed"] = SEED
config["environment"]["mode"] = "patch"

# シミュレーション初期化
sim = Simulation(config)
env = sim.environment

# パッチ領域を取得
patch_cells = set(env._get_patch_cells())

total_area = env.width * env.height
patch_area = len(patch_cells)
outside_area = total_area - patch_area

print(f"Patch area: {patch_area}")
print(f"Outside area: {outside_area}")

def measure(step):
    # 現在存在する餌をパッチ内外に分類
    food_in = sum(
        pos in patch_cells for pos in env.food
    )
    food_out = len(env.food) - food_in

    # 面積あたりの餌密度
    density_in = food_in / patch_area
    density_out = food_out / outside_area

    # パッチ内外の密度比
    ratio = (
        density_in / density_out
        if density_out > 0
        else None
    )

    return {
        "step": step,
        "food_in": food_in,
        "food_out": food_out,
        "density_in": round(density_in, 6),
        "density_out": round(density_out, 6),
        "density_ratio": (
            round(ratio, 4)
            if ratio is not None
            else ""
        ),
    }

# 初期状態を記録
rows = [measure(0)]

# シミュレーション実行
for step in range(1, STEPS + 1):
    sim.step()

    if step % RECORD_EVERY == 0:
        result = measure(step)
        rows.append(result)

        if step % 100 == 0:
            print(
                f"Step {step}: "
                f"inside={result['density_in']:.4f}, "
                f"outside={result['density_out']:.4f}, "
                f"ratio={result['density_ratio']}"
            )

# CSV保存
output_dir = Path("results/patch_density_check")
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / f"seed_{SEED}.csv"

with open(
    output_path, "w", newline="", encoding="utf-8"
) as f:
    writer = csv.DictWriter(
        f, fieldnames=rows[0].keys()
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"Saved: {output_path}")
