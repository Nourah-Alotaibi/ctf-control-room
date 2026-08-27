
from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

def _path(challenge_dir: Path) -> Path:
    p = challenge_dir/".ctf"/"hypotheses.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def load_board(challenge_dir: Path) -> dict:
    p=_path(challenge_dir)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return {
        "active": [],
        "evidence": [],
        "tested": [],
        "next": [],
        "updated": None,
    }

def save_board(challenge_dir: Path, board: dict) -> None:
    board["updated"]=datetime.now().isoformat(timespec="seconds")
    _path(challenge_dir).write_text(json.dumps(board,indent=2))

def add_item(challenge_dir: Path, section: str, text: str) -> dict:
    board=load_board(challenge_dir)
    if section not in board or not isinstance(board.get(section),list):
        raise ValueError("section must be active, evidence, tested, or next")
    if text and text not in board[section]:
        board[section].append(text)
    save_board(challenge_dir,board)
    return board

def render_board(challenge_dir: Path) -> str:
    b=load_board(challenge_dir)
    def lines(name):
        vals=b.get(name,[])
        return "\n".join(f"- {x}" for x in vals[-8:]) or "- none yet"
    return (
        "# Hypothesis Board\n\n"
        "## Active\n"+lines("active")+"\n\n"
        "## Evidence\n"+lines("evidence")+"\n\n"
        "## Tested / Failed\n"+lines("tested")+"\n\n"
        "## Next\n"+lines("next")+"\n"
    )
