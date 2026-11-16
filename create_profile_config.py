
from pathlib import Path
import yaml

source = Path("configs/default.yaml")
config = yaml.safe_load(
    source.read_text(encoding="utf-8")
)

config["simulation"]["duration_mode"] = "steps"
config["simulation"]["steps"] = 1000
config["simulation"]["random_seed"] = 0

output = Path("results/profile_config.yaml")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(
    yaml.safe_dump(
        config,
        allow_unicode=True,
        sort_keys=False,
    ),
    encoding="utf-8",
)

print(f"作成完了: {output}")
