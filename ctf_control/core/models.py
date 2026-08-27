from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class Challenge:
    name: str
    category: str
    path: Path
    file_count: int
    has_context: bool = False
    status: str = "Ready"

@dataclass
class ScanEvent:
    tool: str
    target: str
    ok: bool
    output_path: Optional[Path] = None
    summary: str = ""
