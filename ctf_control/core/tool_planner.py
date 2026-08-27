
from __future__ import annotations
from .tool_registry import relevant_tools, is_installed

def plan_tools(category: str, context_text: str="", limit: int=5) -> list[dict]:
    low = context_text.lower()
    rows = []
    for name, info in relevant_tools(category):
        if not is_installed(name):
            continue
        level = info.get("level","DEEP")
        score = {"FAST": 30, "DEEP": 20, "EXPENSIVE": 5}.get(level, 10)
        desc = info.get("description","").lower()

        # Tiny deterministic relevance boosts.
        for token in ("png","pcap","dns","rsa","elf","apk","memory","archive","zip","http","jwt"):
            if token in low and token in (desc + " " + " ".join(info.get("input",[])).lower()):
                score += 15

        rows.append({
            "name": name,
            "level": level,
            "score": score,
            "description": info.get("description",""),
        })

    rows.sort(key=lambda x: (-x["score"], x["name"].lower()))
    return rows[:max(1,limit)]
