from __future__ import annotations
import shutil
from .agents import command_runnable

def detect_agent_compatibility():
    rows=[]
    checks=[
        ("Claude Code","claude",True,"MCP-capable in supported configurations; cloud or compatible local backend depends on user setup."),
        ("Codex CLI","codex",True,"Terminal agent; MCP/local backend support depends on installed version/configuration."),
        ("Gemini CLI","gemini",True,"Terminal agent; MCP support depends on user configuration."),
        ("Ollama","ollama",False,"Local model runtime, not itself the Control Room agent. Can back compatible clients."),
    ]
    for name,exe,mcp,note in checks:
        found=shutil.which(exe) is not None
        runnable=command_runnable(exe) if found else False
        rows.append({
            "name":name,
            "command":exe,
            "installed":runnable,
            "found_on_path":found,
            "runnable":runnable,
            "plain_terminal": exe!="ollama",
            "mcp_possible":mcp,
            "ollama_backend_possible": name in {"Claude Code","Codex CLI"},
            "note":note,
        })
    return rows
