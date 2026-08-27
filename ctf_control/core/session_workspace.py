
from __future__ import annotations
from pathlib import Path
import shutil

def ensure_session_workspace(challenge_dir: Path, session_name: str) -> Path:
    safe="".join(c if c.isalnum() or c in "-_" else "_" for c in session_name)
    session = challenge_dir / ".ctf" / "sessions" / safe
    session.mkdir(parents=True, exist_ok=True)
    return session

def session_env(challenge_dir: Path, session_name: str) -> dict:
    session=ensure_session_workspace(challenge_dir,session_name)
    return {
        "CTF_CONTROL_SESSION": session_name,
        "CTF_CONTROL_SESSION_DIR": str(session),
        "CTF_CONTROL_CHALLENGE_DIR": str(challenge_dir),
    }
