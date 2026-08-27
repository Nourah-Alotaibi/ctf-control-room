
from __future__ import annotations
from pathlib import Path
import subprocess
import shutil
import shlex
import json
import time
import re
import io
from typing import Callable
from .models import Challenge, ScanEvent
from .config import load_category_config
from .metrics import log_command, add_seconds, set_status
from .tool_registry import write_agent_tool_map
from .cache import get_cached, save_cached, cache_key
from .hypothesis import add_item, render_board
from .tool_planner import plan_tools
from .router import route_role

MAX_RAW_BYTES = 2_000_000
MAX_SUMMARY_LINES = 14
MAX_SCAN_SECONDS = 60.0
MAX_USEFUL_EVENTS = 8

def _safe_name(value: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in value)

def _run(argv: list[str], cwd: Path, timeout: int) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            argv, cwd=cwd, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=timeout, errors="replace",
        )
        out = proc.stdout or ""
        if len(out.encode("utf-8", errors="ignore")) > MAX_RAW_BYTES:
            out = out[:MAX_RAW_BYTES] + "\n[raw output truncated locally]\n"
        return proc.returncode == 0, out
    except subprocess.TimeoutExpired as e:
        partial = e.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode(errors="replace")
        return False, f"{partial}\n[timeout after {timeout}s]"
    except Exception as e:
        return False, f"[runner error] {e}"

def _interesting_lines(text: str) -> list[str]:
    keywords = (
        "flag", "password", "secret", "archive", "zip", "elf", "png", "jpeg",
        "pdf", "sqlite", "base64", "xor", "section", "symbol", "import",
        "executable", "compressed", "encrypted", "key", "warning", "dns",
        "http", "tcp", "udp", "apk", "pe32", "memory", "firmware", "offset",
    )
    preferred = []
    fallback = []
    seen = set()

    # Stream lines instead of building/normalizing a giant list. Keep only a
    # tiny fallback sample and stop collecting preferred lines once enough are found.
    for raw in io.StringIO(text):
        line = raw.strip()
        if not line:
            continue
        if len(fallback) < 6:
            compact = " ".join(line.split())
            if compact not in seen:
                seen.add(compact)
                fallback.append(compact)

        low = line.lower()
        if any(k in low for k in keywords):
            compact = " ".join(line.split())
            if compact not in seen:
                seen.add(compact)
                preferred.append(compact)
                if len(preferred) >= MAX_SUMMARY_LINES:
                    break

    chosen = preferred[:MAX_SUMMARY_LINES]
    if len(chosen) < min(6, MAX_SUMMARY_LINES):
        for line in fallback:
            if line not in chosen:
                chosen.append(line)
            if len(chosen) >= min(6, MAX_SUMMARY_LINES):
                break
    return chosen[:MAX_SUMMARY_LINES]

def _file_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}: return "image"
    if suffix in {".pcap", ".pcapng"}: return "pcap"
    if suffix in {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"}: return "archive"
    if suffix in {".apk"}: return "apk"
    if suffix in {".raw", ".mem", ".vmem", ".dmp"}: return "memory"
    if suffix in {".bin", ".elf", ".so", ".exe", ".dll"}: return "binary"
    if suffix in {".py", ".js", ".ts", ".php", ".html", ".htm", ".java", ".c", ".cpp", ".go", ".rs", ".sh"}: return "source"
    return "generic"

def _tool_applies(tool: str, target: Path) -> bool:
    kind = _file_kind(target)
    t = tool.lower()
    if t in {"exiftool", "pngcheck", "zsteg"}:
        return kind == "image" or (t == "exiftool" and kind == "generic")
    if t == "binwalk":
        return kind in {"image", "archive", "binary", "generic"}
    if t in {"tshark", "capinfos"}:
        return kind == "pcap"
    if t in {"checksec", "readelf", "nm", "ldd"}:
        return kind in {"binary", "generic"}
    return True

def _useful(summary: str) -> bool:
    low = summary.lower()
    boring = ("no notable output", "tool not installed", "cannot open", "not found")
    return bool(summary.strip()) and not any(x in low for x in boring)

def _conditional_specs(challenge: Challenge, events: list[ScanEvent]) -> list[dict]:
    joined = "\n".join(e.summary.lower() for e in events)
    extras = []
    # Fast conditional branches only. Never heavy tools here.
    if challenge.category in {"forensics", "stego"} and ("zip archive" in joined or "pk\\x03\\x04" in joined):
        extras.append({"tool": "7z", "mode": "per_file", "args": ["l", "{file}"], "timeout": 8})
    if challenge.category in {"network", "forensics"} and "dns" in joined:
        extras.append({"tool": "tshark", "mode": "per_file", "args": ["-r", "{file}", "-Y", "dns", "-T", "fields", "-e", "dns.qry.name"], "timeout": 10})
    if challenge.category in {"network", "forensics"} and "http" in joined:
        extras.append({"tool": "tshark", "mode": "per_file", "args": ["-r", "{file}", "-Y", "http.request", "-T", "fields", "-e", "http.host", "-e", "http.request.uri"], "timeout": 10})
    return extras

def scan_challenge(
    challenge: Challenge,
    on_event: Callable[[ScanEvent], None] | None = None,
) -> list[ScanEvent]:
    started = time.monotonic()
    set_status(challenge.path, "Scanning")
    config = load_category_config(challenge.category)
    ctf_dir = challenge.path / ".ctf"
    raw_dir = ctf_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    targets = [p for p in challenge.path.iterdir() if p.is_file() and not p.name.startswith(".")]
    events: list[ScanEvent] = []
    useful_count = 0

    specs = list(config.get("tools", []))
    extra_added = False
    idx = 0

    while idx < len(specs):
        if time.monotonic() - started >= MAX_SCAN_SECONDS:
            break
        if useful_count >= MAX_USEFUL_EVENTS:
            break

        spec = specs[idx]
        idx += 1
        level = str(spec.get("level", "FAST")).upper()
        if level != "FAST":
            continue

        tool = str(spec.get("tool", "")).strip()
        if not tool:
            continue
        if shutil.which(tool) is None:
            ev = ScanEvent(tool=tool, target="-", ok=False, summary="tool not installed; skipped")
            events.append(ev)
            if on_event: on_event(ev)
            continue

        mode = spec.get("mode", "per_file")
        timeout = min(int(spec.get("timeout", 10)), max(1, int(MAX_SCAN_SECONDS - (time.monotonic() - started))))
        args_template = [str(x) for x in spec.get("args", [])]
        selected_targets = targets if mode == "per_file" else [challenge.path]

        for target in selected_targets:
            if time.monotonic() - started >= MAX_SCAN_SECONDS or useful_count >= MAX_USEFUL_EVENTS:
                break
            if target.is_file() and not _tool_applies(tool, target):
                continue

            argv = [tool]
            for arg in args_template:
                argv.append(arg.replace("{file}", str(target.resolve())).replace("{dir}", str(challenge.path.resolve())))
            if "{file}" not in " ".join(args_template) and mode == "per_file":
                argv.append(str(target.resolve()))
            command = shlex.join(argv)

            cache_files = [target] if target.is_file() else sorted(p for p in challenge.path.rglob("*") if p.is_file() and ".ctf" not in p.parts)
            cached = get_cached(challenge.path, command, cache_files)
            if cached:
                log_command(challenge.path, command, "pre-scan-cache", cached.get("output_path"), blocked=True)
                ev = ScanEvent(
                    tool=tool,
                    target=target.name if target.is_file() else ".",
                    ok=True,
                    summary=f"cached result reused instantly: {cached.get('output_path')}"
                )
                events.append(ev)
                if on_event: on_event(ev)
                continue

            ok, output = _run(argv, cwd=challenge.path, timeout=timeout)
            target_name = target.name if target.is_file() else "."
            key_short = cache_key(command, cache_files)[:12]
            out_name = f"{_safe_name(tool)}__{_safe_name(target_name)}__{key_short}.txt"
            out_path = raw_dir / out_name
            out_path.write_text("$ " + command + "\n\n" + output, errors="replace")
            log_command(challenge.path, command, "pre-scan", str(out_path))
            save_cached(challenge.path, command, out_path, cache_files)

            lines = _interesting_lines(output)
            summary = "\n".join(lines) if lines else "(no notable output)"
            ev = ScanEvent(tool=tool, target=target_name, ok=ok, output_path=out_path, summary=summary)
            events.append(ev)
            if _useful(summary):
                useful_count += 1
            if on_event: on_event(ev)

        if not extra_added and idx >= min(3, len(specs)):
            extras = _conditional_specs(challenge, events)
            if extras:
                specs.extend(extras)
            extra_added = True

    elapsed = time.monotonic() - started
    add_seconds(challenge.path, "scan_seconds", elapsed)
    _write_context(challenge, events, elapsed)
    _write_state(challenge, events, elapsed)
    write_agent_tool_map(challenge.path, challenge.category)
    set_status(challenge.path, "Scanned")
    return events

def _write_context(challenge: Challenge, events: list[ScanEvent], elapsed: float) -> None:
    ctf_dir = challenge.path / ".ctf"
    files = [p for p in challenge.path.iterdir() if p.is_file() and not p.name.startswith(".")]
    useful = [e for e in events if _useful(e.summary) and "duplicate blocked" not in e.summary.lower()]

    blocks = [
        "# Automatic Smart Pre-Scan (No AI)",
        "",
        f"**Challenge:** {challenge.name}",
        f"**Category:** {challenge.category}",
        f"**Scan time:** {elapsed:.2f} seconds (60-second maximum)",
        "",
        "## Files",
    ]
    for p in files:
        blocks.append(f"- `{p.name}` — {p.stat().st_size:,} bytes")

    blocks += ["", "## Useful findings"]
    if not useful:
        blocks.append("- No useful findings from the automatic pre-scan.")
        blocks.append("- Basic quick checks already ran; do not repeat them unless there is a reason.")
    else:
        for ev in useful[:MAX_USEFUL_EVENTS]:
            blocks += [f"### {ev.tool} → {ev.target}", "```text", ev.summary[:2800], "```"]

    context_preview = "\n".join(e.summary for e in useful[:MAX_USEFUL_EVENTS])
    routed = route_role(challenge.category, context_preview)
    planned = plan_tools(challenge.category, context_preview, limit=5)

    blocks += [
        "",
        "## Specialist routing",
        f"- Suggested role: **{routed['role']}**",
        f"- Hints: {', '.join(routed['hints']) if routed['hints'] else 'none'}",
        "",
        "## Recommended next tools",
    ]
    if planned:
        for item in planned:
            blocks.append(f"- `{item['name']}` [{item['level']}] — {item['description']}")
    else:
        blocks.append("- No additional installed tools were ranked.")

    blocks += [
        "",
        "## Raw evidence",
        "Full outputs are under `.ctf/raw/`. Use them when the compact summary is insufficient.",
        "",
        "## Tool registry",
        "See `.ctf/tool_registry.md` for relevant FAST / DEEP / EXPENSIVE tools.",
        "",
        "## Agent instruction",
        "Continue this authorized CTF challenge from the prepared context. "
        "Avoid repeating commands already logged in `.ctf/commands.jsonl`; inspect prior raw output first. "
        "Use DEEP tools when justified. Treat EXPENSIVE tools as deliberate escalation choices.",
    ]
    (ctf_dir / "context.md").write_text("\n".join(blocks))
    for ev in useful[:5]:
        add_item(challenge.path, "evidence", f"{ev.tool} on {ev.target}: {ev.summary.splitlines()[0][:180]}")
    add_item(challenge.path, "next", "Review prepared context and recommended tools before deeper investigation.")
    (ctf_dir / "hypothesis.md").write_text(render_board(challenge.path))

def _write_state(challenge: Challenge, events: list[ScanEvent], elapsed: float) -> None:
    payload = {
        "challenge": challenge.name,
        "category": challenge.category,
        "path": str(challenge.path),
        "scan_seconds": round(elapsed, 3),
        "scan_events": [
            {"tool": e.tool, "target": e.target, "ok": e.ok,
             "output_path": str(e.output_path) if e.output_path else None}
            for e in events
        ],
    }
    (challenge.path / ".ctf" / "state.json").write_text(json.dumps(payload, indent=2))
