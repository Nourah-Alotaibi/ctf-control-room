from __future__ import annotations

from datetime import datetime
import json
import re
from pathlib import Path


_SECTIONS = ("active", "evidence", "tested", "next")
_FLAG_RE = re.compile(r"\b[A-Za-z0-9_]{1,32}\{[^{}\n]{1,220}\}")


def _path(challenge_dir: Path) -> Path:
    p = challenge_dir / ".ctf" / "hypotheses.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_board(challenge_dir: Path) -> dict:
    p = _path(challenge_dir)
    if p.exists():
        try:
            board = json.loads(p.read_text())
            for section in _SECTIONS:
                board.setdefault(section, [])
            return board
        except Exception:
            pass
    return {
        "active": [],
        "evidence": [],
        "tested": [],
        "next": [],
        "updated": None,
    }


def _append_unique(board: dict, section: str, text: str, limit: int = 60) -> None:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return
    clean = clean[:320]
    values = board.setdefault(section, [])
    if clean not in values:
        values.append(clean)
    if len(values) > limit:
        board[section] = values[-limit:]


def render_board(challenge_dir: Path) -> str:
    b = load_board(challenge_dir)

    def lines(name):
        vals = b.get(name, [])
        return "\n".join(f"- {x}" for x in vals[-10:]) or "- none yet"

    return (
        "# Hypothesis Board\n\n"
        "## Active\n" + lines("active") + "\n\n"
        "## Evidence\n" + lines("evidence") + "\n\n"
        "## Tested / Failed\n" + lines("tested") + "\n\n"
        "## Next\n" + lines("next") + "\n"
    )


def save_board(challenge_dir: Path, board: dict) -> None:
    board["updated"] = datetime.now().isoformat(timespec="seconds")
    _path(challenge_dir).write_text(json.dumps(board, indent=2))
    # Keep a readable markdown mirror for humans, handoff, and agents.
    (challenge_dir / ".ctf" / "hypothesis.md").write_text(render_board(challenge_dir))


def add_item(challenge_dir: Path, section: str, text: str) -> dict:
    board = load_board(challenge_dir)
    if section not in _SECTIONS or not isinstance(board.get(section), list):
        raise ValueError("section must be active, evidence, tested, or next")
    _append_unique(board, section, text)
    save_board(challenge_dir, board)
    return board


def record_command(challenge_dir: Path, command: str, source: str = "human") -> dict:
    return add_item(challenge_dir, "tested", f"{source.title()} input/command: {command}")


def update_from_visible_output(challenge_dir: Path, text: str) -> dict:
    """Update the board only from visible terminal output.

    This is deliberately heuristic and does not infer or store hidden reasoning.
    It writes state only when a new visible item was actually discovered.
    """
    board = load_board(challenge_dir)
    before = {section: tuple(board.get(section, [])) for section in _SECTIONS}
    lines = []
    seen = set()
    for raw in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw).strip(" \t\r\n")
        if not line or len(line) < 3 or line in seen:
            continue
        seen.add(line)
        lines.append(line[:320])

    noise = (
        "ctrl+c", "esc dashboard", "shift+tab", "fullscreen renderer",
        "mousesupport", "clicktomove", "context left", "token",
    )

    for line in lines[-30:]:
        low = line.lower()
        if any(n in low for n in noise):
            continue

        if any(x in low for x in ("hypothesis", "likely ", "suspect", "appears to", "might be", "probably ")):
            _append_unique(board, "active", line)

        if any(x in low for x in (
            "found", "detected", "reveals", "contains", "metadata", "archive",
            "signature", "decrypted", "decoded", "success", "failed", "error",
            "flag:", "flag recovered", "candidate",
        )):
            _append_unique(board, "evidence", line)

        if any(x in low for x in (
            "ran ", "running ", "executed ", "used ", "checking ", "tested ",
            "trying ", "inspected ", "extracted ",
        )):
            _append_unique(board, "tested", line)

        if any(x in low for x in (
            "next:", "next step", "i'll ", "i will ", "let me ", "going to ",
            "need to ", "then ",
        )):
            _append_unique(board, "next", line)

        for flag in _FLAG_RE.findall(line):
            _append_unique(board, "evidence", f"Visible flag candidate: {flag}")

    changed = any(tuple(board.get(section, [])) != before[section] for section in _SECTIONS)
    if changed:
        save_board(challenge_dir, board)
    return board


def record_parallel_result(challenge_dir: Path, summary: dict) -> dict:
    board = load_board(challenge_dir)
    verdict = summary.get("verdict")
    candidate = summary.get("candidate_flag")
    if verdict:
        _append_unique(board, "evidence", f"Parallel result verdict: {verdict}")
    if candidate:
        _append_unique(board, "evidence", f"Parallel agreed/selected flag candidate: {candidate}")
    if verdict == "disagreement":
        _append_unique(board, "next", "Review both parallel branches and resolve their disagreement before accepting a flag.")
    save_board(challenge_dir, board)
    return board
