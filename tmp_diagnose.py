import sys
from pathlib import Path
sys.path.insert(0, str(Path('src').resolve()))
import yaml
from simulation import Simulation

config_path = Path('configs/default.yaml')
with open(config_path, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

sim = Simulation(config)
for i in range(80):
    sim.step()
    print(i+1, 'step', 'org', len(sim.organisms), 'food', sim.environment.food_count())
    if sim.environment.food_count() >= sim.environment.width * sim.environment.height:
        print('grid full at step', i+1)
        break
