
from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

DEFAULT_BRANCHES = [
    {"name":"independent-analysis","instruction":"Analyze the challenge independently and look for a different path."},
    {"name":"tool-focused","instruction":"Focus on tool-assisted evidence and concrete experiments."},
]

def create_parallel_plan(challenge_dir: Path, branches=None) -> Path:
    branches=branches or DEFAULT_BRANCHES
    p=challenge_dir/".ctf"/"parallel_plan.json"
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({
        "created":datetime.now().isoformat(timespec="seconds"),
        "branches":branches,
        "note":"Parallel agents are optional because they can multiply AI usage.",
    },indent=2))
    return p
