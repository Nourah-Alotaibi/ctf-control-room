from pathlib import Path
import shutil
import os
import subprocess

from .config import load_agents
from .cai_adapter import build_cai_invocation, cai_runnable


def _command_for(name: str) -> str:
    if name == "cai":
        return "cai"
    config = load_agents().get("agents", {})
    spec = config.get(name, {})
    return str(spec.get("command", name))


def command_runnable(command: str, timeout: float = 4.0) -> bool:
    path = shutil.which(command)
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


def available_agents() -> list[str]:
    """Return only agents whose CLI is installed and actually runnable."""
    config = load_agents().get("agents", {})
    agents = [
        name for name, spec in config.items()
        if command_runnable(str(spec.get("command", name)))
    ]
    if cai_runnable() and "cai" not in agents:
        agents.append("cai")
    return agents


def build_agent_invocation(
    name: str,
    challenge_dir: Path,
    handoff: bool = False,
    initial_prompt: str | None = None,
):
    # CAI is an optional separate backend/CLI and is not required in agents.yaml.
    if name == "cai":
        return build_cai_invocation(
            challenge_dir,
            initial_prompt=initial_prompt,
            handoff=handoff,
        )

    config = load_agents().get("agents", {})
    if name not in config:
        raise RuntimeError(f"Unknown agent: {name}")

    spec = config[name]
    command = str(spec.get("command", name))
    if shutil.which(command) is None:
        raise RuntimeError(f"`{command}` is not installed or not on PATH.")
    if not command_runnable(command):
        raise RuntimeError(
            f"`{command}` was found on PATH but is not runnable. "
            f"Run `{command} --version` in this WSL shell and fix its runtime/dependencies first."
        )

    argv = [command] + [str(x) for x in spec.get("args", [])]
    if initial_prompt:
        if name == "gemini":
            argv.extend(["-i", str(initial_prompt)])
        else:
            argv.append(str(initial_prompt))

    env = os.environ.copy()
    env["CTF_CONTROL_CONTEXT"] = str(challenge_dir / ".ctf" / "context.md")
    env["CTF_CONTROL_CHALLENGE"] = str(challenge_dir)
    if handoff:
        env["CTF_CONTROL_HANDOFF"] = str(challenge_dir / ".ctf" / "handoff.md")
    return argv, env
