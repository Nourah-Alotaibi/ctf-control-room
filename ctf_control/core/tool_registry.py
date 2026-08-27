
from __future__ import annotations
from pathlib import Path
import shutil
import os
import yaml
from .config import CONFIG_DIR

LEVEL_ORDER = {"FAST": 0, "DEEP": 1, "EXPENSIVE": 2}

def load_registry() -> dict:
    path = CONFIG_DIR / "tool_registry.yaml"
    return yaml.safe_load(path.read_text()) or {"tools": {}}

def all_tools() -> dict:
    return load_registry().get("tools", {})

def tool_info(name: str) -> dict:
    return all_tools().get(name, {})

def _tools_root() -> Path:
    return Path(os.environ.get(
        "CTF_CONTROL_TOOLS_ROOT",
        str(Path.home() / "CTF" / "tools")
    ))

def is_installed(name: str) -> bool:
    if shutil.which(name) is not None:
        return True
    return (_tools_root() / name).exists()

def relevant_tools(category: str, *, max_level: str | None = None) -> list[tuple[str, dict]]:
    max_rank = LEVEL_ORDER.get(max_level, 99) if max_level else 99
    out = []
    for name, info in all_tools().items():
        cats = info.get("categories", [])
        if "all" not in cats and category not in cats:
            continue
        if LEVEL_ORDER.get(info.get("level", "DEEP"), 1) > max_rank:
            continue
        out.append((name, info))
    return sorted(out, key=lambda x: (LEVEL_ORDER.get(x[1].get("level","DEEP"),1), x[0].lower()))

def write_agent_tool_map(challenge_dir: Path, category: str) -> Path:
    ctf = challenge_dir / ".ctf"
    ctf.mkdir(exist_ok=True)
    path = ctf / "tool_registry.md"
    lines = [
        "# CTF Control Room Tool Registry",
        "",
        f"Category: {category}",
        "",
        "Use this as a discovery map. FAST tools are suitable for lightweight checks; "
        "DEEP tools require a reason; EXPENSIVE tools should be used selectively.",
        "",
    ]
    for name, info in relevant_tools(category):
        installed = "yes" if is_installed(name) else "unknown/not on PATH"
        lines.append(
            f"- **{name}** — level={info.get('level','DEEP')}; installed={installed}; "
            f"{info.get('description','')}"
        )
    path.write_text("\n".join(lines))
    return path
