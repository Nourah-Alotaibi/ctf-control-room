from pathlib import Path
import json
from datetime import datetime

from .metrics import bump
from .hypothesis import render_board
from .session_workspace import latest_sessions_summary


def _tail_commands(challenge_dir: Path, limit=30) -> list[dict]:
    path = challenge_dir / ".ctf" / "commands.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows[-limit:]


def _latest_parallel_summary(challenge_dir: Path) -> str:
    root = challenge_dir / ".ctf" / "parallel_runs"
    if not root.exists():
        return "- none yet"
    summaries = list(root.glob("*/summary.md"))
    if not summaries:
        return "- none yet"
    latest = max(summaries, key=lambda p: p.stat().st_mtime)
    return f"Source: `{latest}`\n\n" + latest.read_text(errors="replace")[:6000]


def _latest_recovery(challenge_dir: Path) -> str:
    path = challenge_dir / ".ctf" / "recovery_prompt.md"
    if not path.exists():
        return "- none yet"
    return path.read_text(errors="replace")[:5000]


def build_handoff(challenge_dir: Path, from_agent: str, to_agent: str) -> Path:
    ctf = challenge_dir / ".ctf"
    ctf.mkdir(exist_ok=True)
    context = (ctf / "context.md").read_text(errors="replace") if (ctf / "context.md").exists() else ""

    notes = ""
    for name in ("notes.md", "findings.md"):
        p = challenge_dir / name
        if p.exists():
            notes += f"\n## {name}\n{p.read_text(errors='replace')[:6000]}\n"

    useful_files = []
    for pattern in ("*.py", "*.sh", "*.js", "*.md", "*.txt", "*.json"):
        useful_files.extend(
            p.name for p in challenge_dir.glob(pattern) if ".ctf" not in p.parts
        )

    cmds = _tail_commands(challenge_dir)
    command_text = "\n".join(
        f"- {r.get('source','?')}: `{r.get('command','')}`"
        + (f" → {r.get('output_path')}" if r.get("output_path") else "")
        for r in cmds if not r.get("blocked")
    ) or "- none logged"

    hypothesis = render_board(challenge_dir)
    sessions = latest_sessions_summary(challenge_dir)
    parallel = _latest_parallel_summary(challenge_dir)
    recovery = _latest_recovery(challenge_dir)

    out = ctf / "handoff.md"
    out.write_text(
        f"""# CTF Agent Handoff

Created: {datetime.now().isoformat(timespec="seconds")}
From: {from_agent}
To: {to_agent}

## Prepared context
{context[:10000]}

## Hypothesis Board
{hypothesis}

## Recent persistent AI sessions
{sessions}

## Latest Parallel result
{parallel}

## Latest Stuck Recovery context
{recovery}

## Existing files
{chr(10).join(f"- `{x}`" for x in sorted(set(useful_files))) or "- none"}

## Recent commands
{command_text}

{notes}

## Unresolved questions
- Review the current evidence and identify what is still unknown.
- Resolve any Parallel disagreement before accepting a candidate.
- Avoid repeating logged commands unless there is a clear reason.

## Handoff instruction
Continue this authorized CTF challenge from the saved state. Read `.ctf/context.md`,
`.ctf/hypothesis.md`, `.ctf/tool_registry.md`, `.ctf/recovery_prompt.md` when present,
the newest `.ctf/parallel_runs/*/summary.md`, `.ctf/sessions/`, existing scripts,
notes, and raw outputs before restarting reconnaissance.
"""
    )
    bump(challenge_dir, "handoffs")
    return out
