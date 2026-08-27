
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import json
import time

def _ctf(challenge_dir: Path) -> Path:
    p = challenge_dir / ".ctf"
    p.mkdir(exist_ok=True)
    return p

def load_metrics(challenge_dir: Path) -> dict:
    path = _ctf(challenge_dir) / "metrics.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {
        "scan_seconds": 0.0,
        "commands": 0,
        "duplicates_blocked": 0,
        "handoffs": 0,
        "takeovers": 0,
        "interrupts": 0,
        "agent_runtime_seconds": 0.0,
        "agent_runs": 0,
        "stuck_warnings": 0,
        "status": "Ready",
    }

def save_metrics(challenge_dir: Path, data: dict) -> None:
    (_ctf(challenge_dir) / "metrics.json").write_text(json.dumps(data, indent=2))

def bump(challenge_dir: Path, key: str, amount=1) -> None:
    d = load_metrics(challenge_dir)
    d[key] = d.get(key, 0) + amount
    save_metrics(challenge_dir, d)

def set_status(challenge_dir: Path, status: str) -> None:
    d = load_metrics(challenge_dir)
    d["status"] = status
    save_metrics(challenge_dir, d)

def add_seconds(challenge_dir: Path, key: str, seconds: float) -> None:
    d = load_metrics(challenge_dir)
    d[key] = round(float(d.get(key, 0.0)) + seconds, 3)
    save_metrics(challenge_dir, d)

def log_command(challenge_dir: Path, command: str, source: str, output_path: str | None = None, blocked=False) -> None:
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "command": command,
        "output_path": output_path,
        "blocked": bool(blocked),
    }
    with (_ctf(challenge_dir) / "commands.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    if blocked:
        bump(challenge_dir, "duplicates_blocked")
    else:
        bump(challenge_dir, "commands")

def command_seen(challenge_dir: Path, command: str) -> tuple[bool, str | None]:
    path = _ctf(challenge_dir) / "commands.jsonl"
    if not path.exists():
        return False, None
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if rec.get("command") == command and not rec.get("blocked"):
            return True, rec.get("output_path")
    return False, None
