
from pathlib import Path
import shutil

SAFE_EXTENSIONS = {".py", ".sh", ".js", ".md", ".txt", ".json"}

def export_challenge(challenge_dir: Path) -> Path:
    export_root = challenge_dir / ".ctf" / "export"
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True)

    context = challenge_dir / ".ctf" / "context.md"
    notes = challenge_dir / "notes.md"
    handoff = challenge_dir / ".ctf" / "handoff.md"

    copied = []
    for p in challenge_dir.iterdir():
        if p.is_file() and p.suffix.lower() in SAFE_EXTENSIONS:
            dst = export_root / p.name
            shutil.copy2(p, dst)
            copied.append(p.name)

    readme = export_root / "README.md"
    context_text = context.read_text(errors="replace") if context.exists() else ""
    notes_text = notes.read_text(errors="replace") if notes.exists() else ""
    handoff_text = handoff.read_text(errors="replace") if handoff.exists() else ""

    readme.write_text(f"""# {challenge_dir.name}

> Draft prepared locally by CTF Control Room. This export step does not call any AI model or consume AI tokens. Review the event's publication rules and remove sensitive or prohibited content before publishing.

## Challenge summary

{context_text[:7000] or "Add a short description of the challenge here."}

## Notes

{notes_text[:7000] or "Add the final approach and important findings here."}

## Agent handoff / investigation state

{handoff_text[:5000] or "No handoff file was created."}

## Included files

{chr(10).join(f"- `{name}`" for name in copied) or "- No solver/source files were copied automatically."}

## Before publishing

- Remove flags if the event prohibits publishing them.
- Remove credentials, private endpoints, and organizer infrastructure details.
- Do not redistribute challenge binaries/files unless explicitly allowed.
- Credit teammates where appropriate.
""")
    return export_root
