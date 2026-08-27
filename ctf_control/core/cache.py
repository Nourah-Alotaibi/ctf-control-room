
from __future__ import annotations
from pathlib import Path
import hashlib, json

def _cache_dir(challenge_dir: Path) -> Path:
    p = challenge_dir / ".ctf" / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p

def cache_key(command: str, files: list[Path] | None = None) -> str:
    h = hashlib.sha256(command.encode())
    for p in files or []:
        try:
            st = p.stat()
            h.update(str(p.resolve()).encode())
            h.update(str(st.st_size).encode())
            h.update(str(st.st_mtime_ns).encode())
        except FileNotFoundError:
            h.update(f"MISSING:{p}".encode())
    return h.hexdigest()

def get_cached(challenge_dir: Path, command: str, files: list[Path] | None = None):
    key = cache_key(command, files)
    meta = _cache_dir(challenge_dir) / f"{key}.json"
    if not meta.exists():
        return None
    try:
        data = json.loads(meta.read_text())
        out = Path(data["output_path"])
        if out.exists():
            return data
    except Exception:
        pass
    return None

def save_cached(challenge_dir: Path, command: str, output_path: Path, files: list[Path] | None = None):
    key = cache_key(command, files)
    meta = _cache_dir(challenge_dir) / f"{key}.json"
    data = {
        "command": command,
        "output_path": str(output_path),
        "files": [str(p) for p in files or []],
    }
    meta.write_text(json.dumps(data, indent=2))
    return data
