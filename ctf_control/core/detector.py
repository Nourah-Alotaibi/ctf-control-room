
from pathlib import Path
from .models import Challenge

CATEGORIES = {
    "web", "pwn", "crypto", "reverse", "rev", "forensics", "network",
    "stego", "malware", "mobile", "osint", "cloud", "hardware-iot",
    "hardware", "iot", "ai-ml", "aiml", "misc"
}

ALIASES = {
    "rev": "reverse",
    "hardware": "hardware-iot",
    "iot": "hardware-iot",
    "aiml": "ai-ml",
}

def normalize_category(name: str) -> str:
    name = name.lower().strip()
    return ALIASES.get(name, name)

def discover_challenges(root: Path) -> list[Challenge]:
    found: list[Challenge] = []
    if not root.exists():
        return found
    for category_dir in sorted(root.iterdir()):
        if not category_dir.is_dir():
            continue
        category = normalize_category(category_dir.name)
        if category not in {normalize_category(c) for c in CATEGORIES}:
            continue
        for challenge_dir in sorted(category_dir.iterdir()):
            if not challenge_dir.is_dir() or challenge_dir.name.startswith("."):
                continue
            files = [
                p for p in challenge_dir.rglob("*")
                if p.is_file() and ".ctf" not in p.parts
            ]
            context = challenge_dir / ".ctf" / "context.md"
            found.append(
                Challenge(
                    name=challenge_dir.name,
                    category=category,
                    path=challenge_dir,
                    file_count=len(files),
                    has_context=context.exists(),
                    status="Scanned" if context.exists() else "Ready",
                )
            )
    return found
