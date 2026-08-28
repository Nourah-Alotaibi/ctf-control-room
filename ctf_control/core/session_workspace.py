from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path


def _safe(value: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(value))


def ensure_session_workspace(challenge_dir: Path, session_name: str) -> Path:
    safe = _safe(session_name)
    session = challenge_dir / ".ctf" / "sessions" / safe
    session.mkdir(parents=True, exist_ok=True)
    return session


def next_session_name(challenge_dir: Path, agent: str) -> str:
    root = challenge_dir / ".ctf" / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    prefix = _safe(agent) + "-"
    nums = []
    for path in root.iterdir():
        if not path.is_dir() or not path.name.startswith(prefix):
            continue
        tail = path.name[len(prefix):]
        if tail.isdigit():
            nums.append(int(tail))
    return f"{_safe(agent)}-{(max(nums) + 1) if nums else 1}"


def create_session_workspace(
    challenge_dir: Path,
    agent: str,
    *,
    purpose: str = "normal",
    prompt: str = "",
) -> tuple[str, Path]:
    session_name = next_session_name(challenge_dir, agent)
    session = ensure_session_workspace(challenge_dir, session_name)
    (session / "transcript.txt").touch(exist_ok=True)
    (session / "screen.txt").write_text("")
    if prompt:
        (session / "prompt.md").write_text(prompt)
    meta = {
        "session": session_name,
        "agent": agent,
        "purpose": purpose,
        "status": "running",
        "started": datetime.now().isoformat(timespec="seconds"),
        "ended": None,
        "runtime_seconds": 0.0,
        "candidate_flag": None,
        "challenge_dir": str(challenge_dir),
    }
    (session / "meta.json").write_text(json.dumps(meta, indent=2))
    return session_name, session


def session_env(challenge_dir: Path, session_name: str) -> dict:
    session = ensure_session_workspace(challenge_dir, session_name)
    return {
        "CTF_CONTROL_SESSION": session_name,
        "CTF_CONTROL_SESSION_DIR": str(session),
        "CTF_CONTROL_CHALLENGE_DIR": str(challenge_dir),
    }


def append_transcript(session_dir: Path, text: str) -> None:
    if not text:
        return
    with (session_dir / "transcript.txt").open("a", encoding="utf-8", errors="replace") as fh:
        fh.write(text)
        if not text.endswith("\n"):
            fh.write("\n")


def update_screen(session_dir: Path, screen: str) -> None:
    (session_dir / "screen.txt").write_text(screen or "", errors="replace")


def finalize_session(
    session_dir: Path,
    *,
    status: str,
    runtime_seconds: float,
    candidate_flag: str | None = None,
) -> None:
    meta_path = session_dir / "meta.json"
    try:
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    except Exception:
        meta = {}
    meta.update(
        {
            "status": status,
            "ended": datetime.now().isoformat(timespec="seconds"),
            "runtime_seconds": round(float(runtime_seconds or 0.0), 3),
            "candidate_flag": candidate_flag,
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2))


def latest_sessions_summary(challenge_dir: Path, limit: int = 5) -> str:
    root = challenge_dir / ".ctf" / "sessions"
    if not root.exists():
        return "- none yet"
    rows = []
    for session in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not session.is_dir():
            continue
        meta_path = session / "meta.json"
        try:
            meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        except Exception:
            meta = {}
        rows.append(
            f"- `{session.name}` • agent={meta.get('agent','?')} • "
            f"purpose={meta.get('purpose','?')} • status={meta.get('status','?')} • "
            f"runtime={float(meta.get('runtime_seconds',0) or 0):.1f}s"
            + (f" • flag={meta.get('candidate_flag')}" if meta.get("candidate_flag") else "")
        )
        if len(rows) >= limit:
            break
    return "\n".join(rows) if rows else "- none yet"
