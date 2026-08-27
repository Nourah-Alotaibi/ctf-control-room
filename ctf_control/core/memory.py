
from __future__ import annotations
from pathlib import Path
import json

def save_lesson(ctf_root: Path, category: str, challenge: str, text: str) -> Path:
    root = ctf_root / ".control-room" / "memory" / category
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{challenge}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"challenge": challenge, "lesson": text}) + "\n")
    return path

def related_lessons(ctf_root: Path, category: str, limit: int = 8) -> list[str]:
    root = ctf_root / ".control-room" / "memory" / category
    if not root.exists():
        return []
    lessons = []
    for path in sorted(root.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        for line in path.read_text(errors="replace").splitlines():
            try:
                rec = json.loads(line)
                if rec.get("lesson"):
                    lessons.append(rec["lesson"])
            except Exception:
                pass
            if len(lessons) >= limit:
                return lessons
    return lessons
