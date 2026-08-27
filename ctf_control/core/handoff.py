
from pathlib import Path
import json
from datetime import datetime
from .metrics import bump

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
    for pattern in ("*.py","*.sh","*.js","*.md","*.txt","*.json"):
        useful_files.extend(p.name for p in challenge_dir.glob(pattern) if ".ctf" not in p.parts)

    cmds = _tail_commands(challenge_dir)
    command_text = "\n".join(
        f"- {r.get('source','?')}: `{r.get('command','')}`"
        + (f" → {r.get('output_path')}" if r.get("output_path") else "")
        for r in cmds if not r.get("blocked")
    ) or "- none logged"

    out = ctf / "handoff.md"
    out.write_text(f"""# CTF Agent Handoff

Created: {datetime.now().isoformat(timespec="seconds")}
From: {from_agent}
To: {to_agent}

## Prepared context
{context[:10000]}

## Existing files
{chr(10).join(f"- `{x}`" for x in sorted(set(useful_files))) or "- none"}

## Recent commands
{command_text}

{notes}

## Unresolved questions
- Review the current evidence and identify what is still unknown.
- Avoid repeating logged commands unless there is a clear reason.

## Handoff instruction
Continue this authorized CTF challenge from the saved state. Read `.ctf/context.md`,
`.ctf/tool_registry.md`, existing scripts, notes, and raw outputs before restarting reconnaissance.
""")
    bump(challenge_dir, "handoffs")
    return out
