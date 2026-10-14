"""Load project settings from config/project_config.yaml."""

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "project_config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Return the project configuration as a dictionary."""
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)
