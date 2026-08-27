from pathlib import Path
import yaml

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PACKAGE_ROOT / "configs"

def load_category_config(category: str) -> dict:
    path = CONFIG_DIR / f"{category}.yaml"
    if not path.exists():
        path = CONFIG_DIR / "misc.yaml"
    return yaml.safe_load(path.read_text()) or {}

def load_agents() -> dict:
    path = CONFIG_DIR / "agents.yaml"
    return yaml.safe_load(path.read_text()) or {}
