from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import re
import shutil


DEFAULT_STRATEGIES = [
    {
        "id": "reasoning-first",
        "label": "Reasoning First",
        "instruction": (
            "Use a reasoning-first investigation. Start from the challenge description and evidence, "
            "form a small number of hypotheses, connect clues, and use tools only to validate them. "
            "Prefer a different path from a brute-force/tool-sweep approach."
        ),
    },
    {
        "id": "tool-first",
        "label": "Tool First",
        "instruction": (
            "Use a tool-first investigation. Quickly inventory artifacts, run the most relevant local "
            "forensics/CTF tools, inspect concrete outputs, extract embedded data when justified, and "
            "work from evidence toward the flag. Avoid simply copying the reasoning-first path."
        ),
    },
]

# Kept for backward compatibility with older code/docs that only prepared a plan.
DEFAULT_BRANCHES = [
    {"name": s["id"], "instruction": s["instruction"]}
    for s in DEFAULT_STRATEGIES
]

_FLAG_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]{1,31}\{[^}\n]{1,160}\}")


def _ctf_dir(challenge_dir: Path) -> Path:
    p = Path(challenge_dir) / ".ctf"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _copy_workspace(challenge_dir: Path, workspace: Path) -> None:
    """Create an isolated copy of the challenge artifacts for one branch.

    The original .ctf state is intentionally not copied wholesale, which avoids
    recursive parallel-run data and prevents branches from sharing scratch files.
    Only compact context/tool-registry files are seeded into the branch workspace.
    """
    challenge_dir = Path(challenge_dir)
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    for item in challenge_dir.iterdir():
        if item.name == ".ctf":
            continue
        if item.is_symlink():
            continue
        target = workspace / item.name
        if item.is_dir():
            shutil.copytree(item, target, symlinks=False)
        elif item.is_file():
            shutil.copy2(item, target)

    source_ctf = challenge_dir / ".ctf"
    branch_ctf = workspace / ".ctf"
    branch_ctf.mkdir(parents=True, exist_ok=True)
    for name in ("context.md", "tool_registry.md"):
        src = source_ctf / name
        if src.exists() and src.is_file():
            shutil.copy2(src, branch_ctf / name)


def create_parallel_plan(challenge_dir: Path, branches=None) -> Path:
    """Legacy plan-only helper retained for compatibility."""
    branches = branches or DEFAULT_BRANCHES
    p = _ctf_dir(Path(challenge_dir)) / "parallel_plan.json"
    p.write_text(
        json.dumps(
            {
                "created": datetime.now().isoformat(timespec="seconds"),
                "branches": branches,
                "note": "Parallel agents are optional because they can multiply AI usage.",
            },
            indent=2,
        )
    )
    return p


def create_parallel_run(
    challenge_dir: Path,
    agents: list[str],
    strategies: list[dict] | None = None,
) -> dict:
    """Prepare two independent branch workspaces and return run metadata.

    If only one runnable AI agent exists, that agent is used twice with different
    strategies. With two or more agents, the first two assignments are different.
    """
    challenge_dir = Path(challenge_dir)
    if not agents:
        raise RuntimeError("No runnable AI agents are available for Parallel Mode.")

    strategies = list(strategies or DEFAULT_STRATEGIES)
    if len(strategies) < 2:
        raise RuntimeError("Parallel Mode requires two strategies.")

    assigned = [agents[0], agents[1] if len(agents) > 1 else agents[0]]
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    ctf = _ctf_dir(challenge_dir)
    run_dir = ctf / "parallel_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Stable workspace paths reduce repeated trust prompts from terminal AI CLIs.
    workspace_root = ctf / "parallel_workspaces"
    branches = []
    for index, strategy in enumerate(strategies[:2]):
        strategy_id = str(strategy.get("id") or f"method-{index + 1}")
        slot = "a" if index == 0 else "b"
        branch_id = f"{slot}-{strategy_id}"
        label = str(strategy.get("label") or strategy_id.replace("-", " ").title())
        instruction = str(strategy.get("instruction") or "Investigate independently.")
        workspace = workspace_root / branch_id
        _copy_workspace(challenge_dir, workspace)

        branch = {
            "id": branch_id,
            "label": label,
            "agent": assigned[index],
            "instruction": instruction,
            "workspace": str(workspace),
        }
        branches.append(branch)
        (run_dir / f"{branch_id}.json").write_text(json.dumps(branch, indent=2))

    metadata = {
        "run_id": run_id,
        "created": datetime.now().isoformat(timespec="seconds"),
        "challenge": challenge_dir.name,
        "challenge_dir": str(challenge_dir),
        "run_dir": str(run_dir),
        "branches": branches,
        "note": (
            "Branches run concurrently in separate workspace copies. Results are compared locally; "
            "the original challenge files are not automatically modified or merged."
        ),
    }
    (run_dir / "run.json").write_text(json.dumps(metadata, indent=2))
    (ctf / "parallel_latest.json").write_text(json.dumps(metadata, indent=2))
    return metadata


def extract_candidate_flags(text: str) -> list[str]:
    """Return unique flag-looking tokens in encounter order."""
    seen = set()
    out = []
    for match in _FLAG_RE.findall(text or ""):
        if match not in seen:
            seen.add(match)
            out.append(match)
    return out


def choose_candidate_flag(text: str) -> str | None:
    """Choose the strongest flag candidate while strongly rejecting decoys."""
    text = text or ""
    matches = list(_FLAG_RE.finditer(text))
    if not matches:
        return None

    best = None
    best_score = -10_000.0

    for index, match in enumerate(matches):
        candidate = match.group(0)
        candidate_lower = candidate.lower()

        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)
        line = text[line_start:line_end].lower()

        pre_start = max(line_start, match.start() - 90)
        local_before = text[pre_start:match.start()].lower()
        local = (local_before + " " + line).strip()

        score = index * 0.02

        if any(
            token in candidate_lower
            for token in ("decoy", "not_the_real", "not-the-real", "fake", "red_herring", "red-herring")
        ):
            score -= 100

        if any(
            token in local
            for token in ("decoy", "red herring", "fake flag", "not the real flag", "not_the_real")
        ):
            score -= 30

        if any(
            token in local_before
            for token in ("final flag", "real flag", "flag recovered", "recovered flag", "decrypted flag", "flag:")
        ):
            score += 20
        elif "flag" in local_before:
            score += 8

        if any(token in local for token in ("decrypting", "decrypted", "verified", "success", "solution complete")):
            score += 5

        if score > best_score:
            best_score = score
            best = candidate

    return best


def build_parallel_summary(metadata: dict, branch_results: dict[str, dict]) -> dict:
    """Build and persist a deterministic no-AI comparison of the two branches."""
    candidates = []
    for branch in metadata.get("branches", []):
        bid = branch["id"]
        result = branch_results.get(bid, {})
        candidates.append(result.get("candidate_flag"))

    nonempty = [x for x in candidates if x]
    if len(nonempty) >= 2 and len(set(nonempty)) == 1:
        verdict = "agreement"
        best = nonempty[0]
    elif len(nonempty) >= 2:
        verdict = "disagreement"
        best = None
    elif len(nonempty) == 1:
        verdict = "single-branch-candidate"
        best = nonempty[0]
    else:
        verdict = "no-flag-candidate"
        best = None

    summary = {
        "run_id": metadata.get("run_id"),
        "updated": datetime.now().isoformat(timespec="seconds"),
        "verdict": verdict,
        "candidate_flag": best,
        "branch_results": branch_results,
    }

    run_dir = Path(metadata["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2))

    md = [
        "# Parallel Agents Summary",
        "",
        f"- Verdict: **{verdict}**",
        f"- Candidate flag: `{best}`" if best else "- Candidate flag: none confirmed",
        "",
    ]
    for branch in metadata.get("branches", []):
        bid = branch["id"]
        result = branch_results.get(bid, {})
        md.extend(
            [
                f"## {branch['label']} — {branch['agent'].title()}",
                f"- Status: {result.get('status', 'unknown')}",
                f"- Runtime: {float(result.get('runtime_seconds', 0) or 0):.1f}s",
                f"- Candidates: {', '.join(result.get('flags') or []) or 'none'}",
                "",
            ]
        )
    (run_dir / "summary.md").write_text("\n".join(md))
    return summary
