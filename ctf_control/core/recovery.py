
from __future__ import annotations
from pathlib import Path
from .hypothesis import render_board

def build_recovery_prompt(challenge_dir: Path) -> str:
    board=render_board(challenge_dir)
    context_path=challenge_dir/".ctf"/"context.md"
    context=context_path.read_text(errors="replace")[:5000] if context_path.exists() else ""
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

Stay within the authorized CTF challenge.
"""
