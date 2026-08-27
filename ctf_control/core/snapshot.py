
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import shutil, json

def create_snapshot(challenge_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = challenge_dir / ".ctf" / "snapshots" / stamp
    out.mkdir(parents=True, exist_ok=True)

    include = [
        challenge_dir / ".ctf" / "context.md",
        challenge_dir / ".ctf" / "tool_registry.md",
        challenge_dir / ".ctf" / "metrics.json",
        challenge_dir / ".ctf" / "commands.jsonl",
        challenge_dir / ".ctf" / "handoff.md",
        challenge_dir / "findings.md",
        challenge_dir / "notes.md",
    ]
    copied=[]
    for p in include:
        if p.exists() and p.is_file():
            dest=out/p.name
            shutil.copy2(p,dest); copied.append(p.name)

    scripts=[]
    for pattern in ("*.py","*.sh","*.js","*.ps1"):
        for p in challenge_dir.glob(pattern):
            dest=out/p.name
            shutil.copy2(p,dest); scripts.append(p.name)

    (out/"snapshot.json").write_text(json.dumps({
        "challenge": challenge_dir.name,
        "files": copied,
        "scripts": scripts,
    },indent=2))
    return out
