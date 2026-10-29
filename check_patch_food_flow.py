"""パッチ内外の餌供給・消費・存在密度を計測する独立した確認用スクリプト。

プロジェクトのルートに置き、`python check_patch_food_flow.py` で実行。
本体の Simulation/Environment のソースコードは書き換えない。
"""

import csv
from pathlib import Path

import yaml

from src.simulation import Simulation


# ===== 計測設定 =====
SEED = 42
STEPS = 10950
REPORT_EVERY = 10

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "results" / "patch_density_check"

with (ROOT / "configs" / "default.yaml").open(encoding="utf-8") as f:
    config = yaml.safe_load(f)

if config["environment"]["mode"] != "patch":
    raise ValueError('default.yaml の environment.mode を "patch" にしてください。')

config["simulation"]["random_seed"] = SEED
sim = Simulation(config)
env = sim.environment
patch_cells = set(env._get_patch_cells())
patch_area = len(patch_cells)
outside_area = env.width * env.height - patch_area
if patch_area == 0 or outside_area == 0:
    raise ValueError("パッチ内外の面積が0です。設定を確認してください。")

# 元のメソッドを保持し、呼び出し結果だけを記録する。
# 実際の餌生成・消費処理や乱数の呼び出し方は変更しない。
original_respawn_food = env.respawn_food
original_remove_food = env.remove_food
counts = {
    "respawn_in": 0,
    "respawn_out": 0,
    "consumed_in": 0,
    "consumed_out": 0,
}


def tracked_respawn_food(rate):
    before = set(env.food)
    added_count = original_respawn_food(rate)
    added_positions = env.food - before
    if added_count != len(added_positions):
        raise AssertionError("再生成数が実際に増えた餌数と一致しません。")
    counts["respawn_in"] += len(added_positions & patch_cells)
    counts["respawn_out"] += len(added_positions - patch_cells)
    return added_count


def tracked_remove_food(x, y):
    position = (x, y)
    existed = position in env.food
    original_remove_food(x, y)
    if existed and position not in env.food:
        key = "consumed_in" if position in patch_cells else "consumed_out"
        counts[key] += 1


env.respawn_food = tracked_respawn_food
env.remove_food = tracked_remove_food


def current_food_counts():
    inside = len(env.food & patch_cells)
    return inside, len(env.food) - inside


def build_row(step):
    food_in, food_out = current_food_counts()
    density_in = food_in / patch_area
    density_out = food_out / outside_area
    respawn_total = counts["respawn_in"] + counts["respawn_out"]
    consumed_total = counts["consumed_in"] + counts["consumed_out"]
    return {
        "step": step,
        "food_in": food_in,
        "food_out": food_out,
        "density_in": round(density_in, 6),
        "density_out": round(density_out, 6),
        "density_ratio": round(density_in / density_out, 4) if density_out else "",
        "respawn_in": counts["respawn_in"],
        "respawn_out": counts["respawn_out"],
        "consumed_in": counts["consumed_in"],
        "consumed_out": counts["consumed_out"],
        "respawn_out_fraction": round(counts["respawn_out"] / respawn_total, 6) if respawn_total else "",
        "consumed_out_fraction": round(counts["consumed_out"] / consumed_total, 6) if consumed_total else "",
        "population_size": len(sim.organisms),
    }


def write_csv(path, data):
    if not data:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)


print(f"seed={SEED}, steps={STEPS}, patch_area={patch_area}, outside_area={outside_area}")

# Step 0 は初期状態。初期配置は再生成・消費に含めない。
rows = [build_row(0)]
for step in range(1, STEPS + 1):
    previous_in, previous_out = current_food_counts()
    for key in counts:
        counts[key] = 0

    sim.step()
    row = build_row(step)

    # 領域ごとに「前時点 + 発生 - 消費 = 現時点」をチェック。
    assert previous_in + row["respawn_in"] - row["consumed_in"] == row["food_in"], (
        f"step {step}: パッチ内の餌収支が合いません"
    )
    assert previous_out + row["respawn_out"] - row["consumed_out"] == row["food_out"], (
        f"step {step}: パッチ外の餌収支が合いません"
    )
    rows.append(row)

    if step % 100 == 0:
        print(
            f"step={step}: density_in={row['density_in']:.4f}, "
            f"density_out={row['density_out']:.4f}, ratio={row['density_ratio']}"
        )

# 10ステップ単位の再生成・消費数を合算する。
summary_rows = []
for end in range(REPORT_EVERY, STEPS + 1, REPORT_EVERY):
    start = end - REPORT_EVERY + 1
    part = rows[start:end + 1]
    last = rows[end]
    totals = {
        key: sum(r[key] for r in part)
        for key in ("respawn_in", "respawn_out", "consumed_in", "consumed_out")
    }
    total_respawn = totals["respawn_in"] + totals["respawn_out"]
    summary_rows.append({
        "step_start": start,
        "step_end": end,
        **totals,
        "respawn_out_fraction": round(totals["respawn_out"] / total_respawn, 6) if total_respawn else "",
        # 領域の面積が違うため、供給・消費も「1マス当たり」で比較できるようにする。
        "respawn_per_cell_in": round(totals["respawn_in"] / patch_area, 6),
        "respawn_per_cell_out": round(totals["respawn_out"] / outside_area, 6),
        "consumed_per_cell_in": round(totals["consumed_in"] / patch_area, 6),
        "consumed_per_cell_out": round(totals["consumed_out"] / outside_area, 6),
        "net_in": totals["respawn_in"] - totals["consumed_in"],
        "net_out": totals["respawn_out"] - totals["consumed_out"],
        "food_in_end": last["food_in"],
        "food_out_end": last["food_out"],
        "density_in_end": last["density_in"],
        "density_out_end": last["density_out"],
        "density_ratio_end": last["density_ratio"],
    })

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
steps_file = OUTPUT_DIR / f"seed_{SEED}_food_flow_steps.csv"
summary_file = OUTPUT_DIR / f"seed_{SEED}_food_flow_10step.csv"
write_csv(steps_file, rows)
write_csv(summary_file, summary_rows)

print(f"Saved: {steps_file}")
print(f"Saved: {summary_file}")
print("計測完了。stepごとの餌収支は全件一致しました。")
