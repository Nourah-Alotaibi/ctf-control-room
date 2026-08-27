
from pathlib import Path
import json, os, shutil, subprocess
from .core.tool_registry import relevant_tools, tool_info, is_installed
from .core.metrics import command_seen, log_command
from .core.repo_search import search_reference_repo

def _challenge_dir():
    raw = os.environ.get("CTF_CONTROL_CHALLENGE")
    if not raw:
        raise RuntimeError("CTF_CONTROL_CHALLENGE is not set.")
    return Path(raw).resolve()

def _run_registered(tool, args):
    info = tool_info(tool)
    if not info:
        return f"Tool `{tool}` is not registered."

    exe = shutil.which(tool)
    if exe is None:
        return f"`{tool}` is registered but is not an executable on PATH."

    challenge = _challenge_dir()
    command = " ".join([tool] + list(args))
    seen, previous = command_seen(challenge, command)
    if seen:
        return f"Already executed: {command}\nPrevious result: {previous or 'logged'}"

    if info.get("level") == "EXPENSIVE" and os.environ.get("CTF_CONTROL_ALLOW_EXPENSIVE","0") != "1":
        return (
            f"`{tool}` is marked EXPENSIVE and is blocked by default. "
            "For an authorized challenge, explicitly set CTF_CONTROL_ALLOW_EXPENSIVE=1 "
            "for the session if you want to allow it."
        )

    try:
        proc = subprocess.run(
            [exe] + list(args),
            cwd=challenge,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=120,
        )
        output = proc.stdout or ""
    except subprocess.TimeoutExpired as e:
        output = (e.stdout or "") + "\n[timeout after 120s]"

    rawdir = challenge / ".ctf" / "raw"
    rawdir.mkdir(parents=True, exist_ok=True)
    out = rawdir / f"mcp__{tool}__{abs(hash(command))}.txt"
    out.write_text(output[:2_000_000], errors="replace")
    log_command(challenge, command, "mcp", str(out))

    preview = "\n".join(output.splitlines()[:120])
    return f"Full output saved: {out}\n\nPreview:\n{preview}"

def main():
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print(
            "Optional MCP support is not installed.\n\n"
            "Install the MCP library only with:\n"
            "  pip install -e '.[mcp]'\n\n"
            "This does NOT install Claude, Codex, Gemini, Ollama, or any AI agent."
        )
        return

    mcp = FastMCP("CTF Control Room")

    @mcp.tool()
    def list_ctf_tools(category: str, max_level: str = "EXPENSIVE") -> str:
        """List registered tools relevant to a CTF category."""
        rows = []
        for name, info in relevant_tools(category, max_level=max_level):
            rows.append({
                "name": name,
                "level": info.get("level"),
                "installed": is_installed(name),
                "description": info.get("description",""),
            })
        return json.dumps(rows, indent=2)

    @mcp.tool()
    def recommend_ctf_tools(category: str, input_type: str = "generic") -> str:
        """Recommend installed registered tools for a category/input type."""
        rows = []
        for name, info in relevant_tools(category):
            accepted = info.get("input", [])
            if accepted and input_type not in accepted and "any" not in accepted and "generic" not in accepted:
                continue
            if is_installed(name):
                rows.append({
                    "name": name,
                    "level": info.get("level"),
                    "why": info.get("description",""),
                })
        return json.dumps(rows[:20], indent=2)

    @mcp.tool()
    def read_prepared_context() -> str:
        """Read Control Room's compact no-AI context for the current challenge."""
        p = _challenge_dir() / ".ctf" / "context.md"
        return p.read_text(errors="replace") if p.exists() else "No context.md yet. Run Smart Pre-Scan first."

    @mcp.tool()
    def search_ctf_references(query: str, repo: str = "", limit: int = 20) -> str:
        """Search locally cloned CTF reference repositories without dumping full files."""
        rows = search_reference_repo(query, repo or None, max(1, min(limit, 50)))
        return json.dumps(rows, indent=2)

    @mcp.tool()
    def run_ctf_tool(tool: str, args: list[str]) -> str:
        """Run a registered installed tool in the current authorized CTF challenge."""
        return _run_registered(tool, args)

    mcp.run()

if __name__ == "__main__":
    main()
