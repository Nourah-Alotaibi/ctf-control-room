
from __future__ import annotations
from pathlib import Path
import json
from .config import CONFIG_DIR

def load_profiles():
    return json.loads((CONFIG_DIR/"power_profiles.json").read_text())

def settings_path(ctf_root: Path) -> Path:
    p=ctf_root/".control-room"/"power.json"
    p.parent.mkdir(parents=True,exist_ok=True)
    return p

def load_settings(ctf_root: Path) -> dict:
    p=settings_path(ctf_root)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return load_profiles()["default"].copy()

def apply_profile(ctf_root: Path, profile: str) -> dict:
    cfg=load_profiles()
    if profile not in cfg["profiles"]:
        raise ValueError(profile)
    data=cfg["profiles"][profile].copy()
    settings_path(ctf_root).write_text(json.dumps(data,indent=2))
    return data

def set_feature(ctf_root: Path, name: str, value: bool) -> dict:
    data=load_settings(ctf_root)
    if name not in data:
        raise ValueError(name)
    data[name]=bool(value)
    settings_path(ctf_root).write_text(json.dumps(data,indent=2))
    return data
