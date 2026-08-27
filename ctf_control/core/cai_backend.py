
from __future__ import annotations
import shutil

def cai_available() -> bool:
    return shutil.which("cai") is not None

def cai_status() -> dict:
    return {
        "installed": cai_available(),
        "command": shutil.which("cai"),
        "note": "CAI is an optional advanced backend and is never installed automatically."
    }
