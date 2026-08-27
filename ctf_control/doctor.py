
from pathlib import Path
import tempfile, shutil, sys, json
from .core.compatibility import detect_agent_compatibility
from .core.toolbox import print_status
from .core.detector import discover_challenges
from .core.scanner import scan_challenge

def main():
    print("💜 CTF Control Room Doctor")
    print("="*48)
    print(f"Python: {sys.version.split()[0]}")
    print(f"WSL/Linux home: {Path.home()}")
    print("\nAI clients (detection only; nothing installed):")
    for row in detect_agent_compatibility():
        mark="✓" if row["runnable"] else ("!" if row["found_on_path"] else "·")
        state="runnable" if row["runnable"] else ("found but broken" if row["found_on_path"] else "not found")
        print(f"{mark} {row['name']:12} {state:16} terminal={row['plain_terminal']} MCP={row['mcp_possible']}")

    print_status(Path.home()/"CTF"/"tools")

    print("\nRunning harmless self-test...")
    base=Path(tempfile.mkdtemp(prefix="ctf-control-selftest-"))
    try:
        d=base/"forensics"/"sample"
        d.mkdir(parents=True)
        (d/"hello.txt").write_text("CTF Control Room self-test\nexample metadata secret.zip")
        items=discover_challenges(base)
        if not items:
            print("✗ Challenge discovery failed")
            return 1
        events=scan_challenge(items[0])
        ok=(d/".ctf"/"context.md").exists() and (d/".ctf"/"tool_registry.md").exists()
        print("✓ Smart Pre-Scan/context/tool-registry test passed" if ok else "✗ Self-test failed")
        print(f"  Scan events: {len(events)}")
    finally:
        shutil.rmtree(base,ignore_errors=True)
    print("\nDoctor complete.")
