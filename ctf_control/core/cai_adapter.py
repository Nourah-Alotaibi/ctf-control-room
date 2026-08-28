from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def cai_runnable(timeout: float = 6.0) -> bool:
    """Return True only when the installed CAI CLI can actually run."""
    path = shutil.which("cai")
    if path is None:
        return False
    try:
        proc = subprocess.run(
            [path, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def build_cai_invocation(
    challenge_dir: Path,
    *,
    initial_prompt: str | None = None,
    handoff: bool = False,
) -> tuple[list[str], dict]:
    """Build a safe interactive CAI invocation.

    We intentionally do not enable CAI's --yolo / unrestricted modes and we do
    not alter license or provider/API-key settings. Those remain user choices.
    """
    if not cai_runnable():
        raise RuntimeError(
            "`cai` is not installed/runnable in this WSL shell. "
            "Install/configure CAI separately, then verify `cai --version`."
        )

    argv = ["cai"]
    if initial_prompt:
        argv.extend(["--prompt", str(initial_prompt)])

    env = os.environ.copy()
    env["CTF_CONTROL_CONTEXT"] = str(challenge_dir / ".ctf" / "context.md")
    env["CTF_CONTROL_CHALLENGE"] = str(challenge_dir)
    if handoff:
        env["CTF_CONTROL_HANDOFF"] = str(challenge_dir / ".ctf" / "handoff.md")

    # Preserve a user-configured CAI workspace if one already exists.
    safe_workspace = "".join(
        ch if ch.isalnum() or ch in "-_" else "_" for ch in challenge_dir.name
    ) or "ctf_control_room"
    env.setdefault("CAI_WORKSPACE", safe_workspace)
    return argv, env
