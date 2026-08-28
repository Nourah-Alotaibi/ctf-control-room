
from __future__ import annotations

from pathlib import Path
import json
import re
import shutil
import subprocess

from .parallel import choose_candidate_flag

SAFE_EXTENSIONS = {".py", ".sh", ".js", ".md", ".txt", ".json"}
_FLAG_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{1,31}\{[^}\n]{1,160}\}")


def _read_text(path: Path, limit: int | None = None) -> str:
    if not path.exists() or not path.is_file():
        return ""
    text = path.read_text(errors="replace")
    return text[:limit] if limit else text


def _slug(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", str(name).strip()).strip("-._")
    return value or "challenge"


def _display_path(path: Path) -> str:
    path = Path(path).resolve()
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def _challenge_files(challenge_dir: Path) -> list[str]:
    rows = []
    for p in sorted(challenge_dir.iterdir(), key=lambda item: item.name.lower()):
        if p.name == ".ctf":
            continue
        if p.is_file():
            rows.append(f"- `{p.name}` — {p.stat().st_size:,} bytes")
    return rows




def _scan_findings_excerpt(context_text: str, limit: int = 28) -> str:
    if not context_text.strip():
        return "No Smart Pre-Scan context was available."

    useful_words = (
        "comment", "warning", "metadata", "trailer", "iend", "archive", "zip",
        "signature", "embedded", "base64", "room_code", "operator", "key",
        "decoded", "decrypted", "flag", "candidate", "found", "detected",
        "contains", "reveals",
    )
    rows = []
    seen = set()
    for raw in context_text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 4:
            continue
        low = line.lower()
        if not any(word in low for word in useful_words):
            continue
        if line in seen:
            continue
        seen.add(line)
        rows.append(f"- {line[:420]}")
    return "\n".join(rows[:limit]) or "The scan completed, but no concise clue lines were extracted."


def _failed_excerpt(text: str, limit: int = 18) -> str:
    if not text.strip():
        return "No failed or rejected paths were recorded."
    rows = []
    seen = set()
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 4:
            continue
        low = line.lower()
        if not any(word in low for word in ("failed", "failure", "error", "decoy", "fake", "rejected", "not the real", "didn't work", "did not work")):
            continue
        if line in seen:
            continue
        seen.add(line)
        rows.append(f"- {line[:420]}")
    return "\n".join(rows[-limit:]) or "No failed or rejected paths were recorded."

def _copy_safe_files(challenge_dir: Path, export_root: Path) -> list[str]:
    copied = []
    for p in sorted(challenge_dir.iterdir(), key=lambda item: item.name.lower()):
        if p.is_file() and p.suffix.lower() in SAFE_EXTENSIONS:
            dst = export_root / p.name
            shutil.copy2(p, dst)
            copied.append(p.name)
    return copied


def _commands_markdown(challenge_dir: Path, limit: int = 80) -> str:
    path = challenge_dir / ".ctf" / "commands.jsonl"
    if not path.exists():
        return "No commands were logged."

    rows = []
    seen = set()
    for raw in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(raw)
        except Exception:
            continue
        command = str(rec.get("command") or "").strip()
        if not command or command in seen:
            continue
        seen.add(command)
        source = str(rec.get("source") or "unknown")
        blocked = " — duplicate blocked" if rec.get("blocked") else ""
        rows.append(f"- `{command}` — {source}{blocked}")

    return "\n".join(rows[-limit:]) or "No commands were logged."


def _session_text(challenge_dir: Path, per_session_limit: int = 12000) -> tuple[str, list[str]]:
    sessions_root = challenge_dir / ".ctf" / "sessions"
    if not sessions_root.exists():
        return "", []

    chunks = []
    session_names = []
    for session_dir in sorted(
        (p for p in sessions_root.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
    ):
        transcript = session_dir / "transcript.txt"
        if not transcript.exists():
            continue
        text = transcript.read_text(errors="replace")
        if not text.strip():
            continue
        session_names.append(session_dir.name)
        chunks.append(f"\n===== SESSION {session_dir.name} =====\n{text[-per_session_limit:]}")

    return "\n".join(chunks), session_names


def _parallel_text(challenge_dir: Path) -> str:
    runs_root = challenge_dir / ".ctf" / "parallel_runs"
    if not runs_root.exists():
        return ""

    summaries = []
    for run_dir in sorted(
        (p for p in runs_root.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
    ):
        summary = run_dir / "summary.md"
        if summary.exists():
            summaries.append(summary.read_text(errors="replace"))
    return "\n\n".join(summaries[-3:])


def _visible_investigation_excerpt(text: str, limit: int = 35) -> str:
    if not text.strip():
        return "No saved AI session transcript was available."

    useful_words = (
        "found", "detected", "metadata", "archive", "zip", "decode", "decoded",
        "decrypt", "decrypted", "extract", "extracted", "flag", "candidate",
        "failed", "error", "success", "contains", "reveals", "trying", "checking",
        "inspect", "binwalk", "exiftool", "strings", "python", "xor", "base64",
    )
    noise_words = (
        "ctrl+c", "context left", "fullscreen renderer", "mousesupport",
        "clicktomove", "shift+tab",
    )

    rows = []
    seen = set()
    for raw in text.splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if len(line) < 4:
            continue
        low = line.lower()
        if any(noise in low for noise in noise_words):
            continue
        if not any(word in low for word in useful_words):
            continue
        if line in seen:
            continue
        seen.add(line)
        rows.append(f"- {line[:420]}")

    return "\n".join(rows[-limit:]) or "No concise investigation lines were extracted from the saved transcript."


def _candidate_flag(*texts: str) -> str | None:
    combined = "\n".join(text for text in texts if text)
    if not combined:
        return None
    try:
        return choose_candidate_flag(combined)
    except Exception:
        matches = _FLAG_RE.findall(combined)
        for candidate in reversed(matches):
            low = candidate.lower()
            if not any(x in low for x in ("decoy", "fake", "not_the_real", "not-the-real")):
                return candidate
        return None


def _show_saved_popup(writeup_path: Path) -> None:
    """Show the saved-location modal when export_challenge is called from the TUI.

    Direct CLI use still works: if no Textual app is active, this silently does nothing.
    """
    app = None
    try:
        from textual._context import active_app
        app = active_app.get()
    except Exception:
        try:
            from textual.app import App
            getter = getattr(App, "get_current", None)
            app = getter() if getter else None
        except Exception:
            app = None
    if app is None or WriteupSavedScreen is None:
        return

    try:
        app.push_screen(WriteupSavedScreen(writeup_path))
    except Exception:
        pass


def _open_target(target: Path) -> bool:
    target = Path(target)
    for command in ("code", "xdg-open"):
        executable = shutil.which(command)
        if not executable:
            continue
        try:
            subprocess.Popen(
                [executable, str(target)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            return True
        except OSError:
            continue
    return False


try:
    from rich.markup import escape as rich_escape
    from textual.binding import Binding
    from textual.containers import Vertical
    from textual.screen import ModalScreen
    from textual.widgets import Static

    class WriteupSavedScreen(ModalScreen):
        """Confirmation popup shown after a local write-up is generated."""

        CSS = """
        WriteupSavedScreen {
            align: center middle;
            background: rgba(7, 9, 13, 0.72);
            color: #efeff5;
        }
        #writeup-shell {
            width: 88;
            height: 25;
            padding: 1 2;
            background: #090b10;
            border: round #8f5cff;
        }
        #writeup-title {
            height: 3;
            content-align: center middle;
            text-align: center;
            text-style: bold;
            color: #8cffc1;
            border-bottom: solid #5f3f88;
        }
        #writeup-body {
            height: 1fr;
            padding: 1 2;
            background: #0d1016;
            border: round #3b2b50;
            color: #f2eff8;
        }
        #writeup-help {
            height: 4;
            margin-top: 1;
            content-align: center middle;
            text-align: center;
            color: #c99cff;
        }
        """

        BINDINGS = [
            Binding("o", "open_writeup", "Open Write-up"),
            Binding("f", "open_folder", "Open Folder"),
            Binding("escape", "back", "Back"),
        ]

        def __init__(self, writeup_path: Path):
            super().__init__()
            self.writeup_path = Path(writeup_path)

        def compose(self):
            display = _display_path(self.writeup_path)
            with Vertical(id="writeup-shell"):
                yield Static("✓ WRITE-UP SAVED", id="writeup-title")
                yield Static(
                    f"[b]Challenge:[/b] {rich_escape(self.writeup_path.stem.removesuffix('-writeup'))}\n\n"
                    f"[b]File:[/b] {rich_escape(self.writeup_path.name)}\n\n"
                    f"[b]Saved to:[/b]\n{rich_escape(display)}",
                    id="writeup-body",
                )
                yield Static(
                    "[b]O[/b] Open Write-up    •    [b]F[/b] Open Folder    •    [b]ESC[/b] Back",
                    id="writeup-help",
                )

        def action_open_writeup(self):
            if not _open_target(self.writeup_path):
                self.notify(
                    f"Open manually: {_display_path(self.writeup_path)}",
                    title="Could not open editor",
                    severity="warning",
                )

        def action_open_folder(self):
            if not _open_target(self.writeup_path.parent):
                self.notify(
                    f"Open manually: {_display_path(self.writeup_path.parent)}",
                    title="Could not open folder",
                    severity="warning",
                )

        def action_back(self):
            self.dismiss()

except Exception:
    WriteupSavedScreen = None


def export_challenge(challenge_dir: Path) -> Path:
    """Build and save a deterministic local CTF write-up.

    The write-up uses already-saved local state only. It does not make a new AI call.
    """
    challenge_dir = Path(challenge_dir)
    export_root = challenge_dir / ".ctf" / "export"
    if export_root.exists():
        shutil.rmtree(export_root)
    export_root.mkdir(parents=True)

    ctf = challenge_dir / ".ctf"
    context_text = _read_text(ctf / "context.md", 9000)
    challenge_description = _read_text(challenge_dir / "README.md", 4500)
    notes_text = _read_text(challenge_dir / "notes.md", 7000)
    handoff_text = _read_text(ctf / "handoff.md", 7000)
    hypothesis_text = _read_text(ctf / "hypothesis.md", 7000)
    session_text, session_names = _session_text(challenge_dir)
    parallel_text = _parallel_text(challenge_dir)

    copied = _copy_safe_files(challenge_dir, export_root)
    files_text = "\n".join(_challenge_files(challenge_dir)) or "- No challenge files found."
    commands_text = _commands_markdown(challenge_dir)
    scan_findings_text = _scan_findings_excerpt(context_text)
    investigation_text = _visible_investigation_excerpt(session_text)
    failed_text = _failed_excerpt(session_text + "\n" + hypothesis_text + "\n" + parallel_text)
    flag = _candidate_flag(
        parallel_text,
        hypothesis_text,
        handoff_text,
        session_text,
        notes_text,
        context_text,
    )

    writeup_name = f"{_slug(challenge_dir.name)}-writeup.md"
    writeup_path = export_root / writeup_name

    final_result = (
        f"Candidate / recovered flag:\n\n`{flag}`"
        if flag
        else "No final flag was confidently detected in the saved local state."
    )
    sessions_line = (
        ", ".join(f"`{name}`" for name in session_names)
        if session_names
        else "No saved AI session transcripts."
    )
    parallel_section = parallel_text[-7000:].strip() or "No completed parallel-agent summary was found."
    notes_section = notes_text.strip() or "No manual notes were saved."
    handoff_section = handoff_text.strip() or "No handoff file was created."
    hypothesis_section = hypothesis_text.strip() or "No hypothesis board was saved."

    writeup_path.write_text(
        f"""# {challenge_dir.name} Write-up

> Generated locally by CTF Control Room from saved challenge state. No new AI call is made by this export step. Review the event's publication rules before publishing.

## Challenge

**Name:** {challenge_dir.name}

{challenge_description.strip() or "No challenge description file was available."}

### Files

{files_text}

## Initial Findings

{scan_findings_text}

## Investigation

Saved sessions: {sessions_line}

{investigation_text}

## Commands / Tools Used

{commands_text}

## Failed / Rejected Paths

{failed_text}

## Hypothesis Board

{hypothesis_section}

## Parallel-Agent Results

{parallel_section}

## Notes

{notes_section}

## Handoff / Investigation State

{handoff_section}

## Final Result

{final_result}

## Included Solver / Text Files

{chr(10).join(f"- `{name}`" for name in copied) or "- No safe text/source files were copied automatically."}

## Before Publishing

- Confirm the final flag and solution steps are correct.
- Remove flags if the event prohibits publishing them.
- Remove credentials, private endpoints, and organizer infrastructure details.
- Do not redistribute challenge binaries/files unless explicitly allowed.
- Credit teammates where appropriate.
""",
        encoding="utf-8",
    )

    _show_saved_popup(writeup_path)
    return writeup_path
