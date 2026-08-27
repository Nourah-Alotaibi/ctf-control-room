
from __future__ import annotations
from pathlib import Path
import os, re

DEFAULT_ROOT = Path.home() / "CTF" / "tools"

def search_reference_repo(query: str, repo: str | None=None, limit: int=20, tools_root: Path|None=None):
    root = tools_root or Path(os.environ.get("CTF_CONTROL_TOOLS_ROOT", str(DEFAULT_ROOT)))
    repos = [root/repo] if repo else [p for p in root.iterdir() if p.is_dir()] if root.exists() else []
    terms=[t.lower() for t in query.split() if t.strip()]
    results=[]
    allowed={".md",".txt",".rst",".py",".json",".yaml",".yml",".html"}

    for r in repos:
        if not r.exists(): continue
        for p in r.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in allowed:
                continue
            try:
                text=p.read_text(errors="replace")
            except Exception:
                continue
            for i,line in enumerate(text.splitlines(),1):
                low=line.lower()
                if all(t in low for t in terms):
                    results.append({
                        "repo": r.name,
                        "file": str(p.relative_to(r)),
                        "line": i,
                        "text": line.strip()[:400],
                    })
                    if len(results)>=limit:
                        return results
    return results
