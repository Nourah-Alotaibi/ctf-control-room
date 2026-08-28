from __future__ import annotations

from pathlib import Path
from .hypothesis import add_item, render_board


def build_recovery_prompt(challenge_dir: Path) -> str:
    board = render_board(challenge_dir)
    context_path = challenge_dir / ".ctf" / "context.md"
    context = context_path.read_text(errors="replace")[:5000] if context_path.exists() else ""
    return f"""The current approach appears stuck.

Do NOT simply repeat the same command or make a tiny variation of the same failed approach.

Prepared context:
{context}

Current hypothesis board:
{board}

Return exactly:
1. What appears to have failed.
2. Three genuinely different next approaches.
3. Which approach you recommend first and why.
4. The first concrete action for that approach.

Then execute the recommended different approach inside this authorized CTF challenge.
Keep visible progress concise and do not reveal private chain-of-thought.
"""


def write_recovery_prompt(challenge_dir: Path) -> Path:
    prompt = build_recovery_prompt(challenge_dir)
    path = challenge_dir / ".ctf" / "recovery_prompt.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt)
    add_item(
        challenge_dir,
        "next",
        "Stuck Recovery requested: choose a genuinely different approach instead of repeating the current path.",
    )
    return path


def recovery_resume_instruction() -> str:
    return (
        "Read `.ctf/recovery_prompt.md` now. Follow it and execute the recommended "
        "genuinely different recovery approach. Do not repeat the failed path."
    )
