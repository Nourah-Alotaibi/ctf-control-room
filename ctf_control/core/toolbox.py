
from pathlib import Path
import json, shutil, subprocess, sys, os
from .config import CONFIG_DIR

def _package_commands():
    path = CONFIG_DIR / 'package_commands.json'
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}

def _command_for_package(pkg: str) -> str:
    return _package_commands().get(pkg, pkg)

def load_packs():
    return json.loads((CONFIG_DIR / "tool_packs.json").read_text())

def _run(argv, check=False):
    print("$", " ".join(argv))
    try:
        proc = subprocess.run(argv, check=check)
        return proc.returncode
    except Exception as exc:
        print(f"Command failed: {exc}")
        return 1

def _apt_available(pkg: str) -> bool:
    if shutil.which("apt-cache") is None:
        return True
    try:
        p = subprocess.run(
            ["apt-cache","show",pkg],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return p.returncode == 0
    except Exception:
        return True

def _pip_install(pkg: str) -> bool:
    rc = _run([sys.executable, "-m", "pip", "install", pkg])
    return rc == 0

def _clone_repo(repo: dict, tools_root: Path) -> Path | None:
    dest = tools_root / repo["name"]
    if dest.exists():
        print(f"✓ {repo['name']} already exists")
        return dest
    if shutil.which("git") is None:
        print("git is missing; cannot clone repositories.")
        return None
    rc = _run(["git","clone","--depth","1",repo["url"],str(dest)])
    return dest if rc == 0 else None

def _post_setup_repo(name: str, dest: Path) -> None:
    """Best-effort setup only. Never abort the whole toolbox."""
    try:
        if name == "pwndbg":
            setup = dest / "setup.sh"
            if setup.exists():
                print("Configuring pwndbg...")
                _run(["bash", str(setup)])
        elif name == "RsaCtfTool":
            req = dest / "requirements.txt"
            if req.exists():
                print("Installing RsaCtfTool Python requirements...")
                _run([sys.executable,"-m","pip","install","-r",str(req)])
        elif name == "jwt_tool":
            req = dest / "requirements.txt"
            if req.exists():
                print("Installing jwt_tool Python requirements...")
                _run([sys.executable,"-m","pip","install","-r",str(req)])
        elif name == "sherlock":
            # Sherlock packaging changes over time. Prefer its local pyproject if present.
            if (dest/"pyproject.toml").exists() or (dest/"setup.py").exists():
                print("Installing Sherlock from cloned repository...")
                _run([sys.executable,"-m","pip","install","-e",str(dest)])
    except Exception as exc:
        print(f"Optional setup for {name} failed: {exc}")

def install_pack(pack_name, tools_root: Path, assume_yes=False):
    packs = load_packs()
    if pack_name not in packs:
        print(f"Unknown pack: {pack_name}")
        return 2

    pack = packs[pack_name]
    print(f"\n== {pack_name.upper()} ==")
    print(pack.get("description",""))

    # Install apt packages one-by-one so one missing package never breaks the whole pack.
    apt = pack.get("apt", [])
    for pkg in apt:
        command = _command_for_package(pkg)
        if shutil.which(command):
            print(f"✓ {pkg} already installed ({command})")
            continue
        if not _apt_available(pkg):
            print(f"↷ {pkg}: not available in this apt repository, skipped")
            continue
        cmd = ["sudo","apt-get","install"]
        if assume_yes:
            cmd.append("-y")
        cmd.append(pkg)
        rc = _run(cmd)
        if rc != 0:
            print(f"↷ {pkg}: install failed, skipped")

    # Install Python packages one-by-one as well.
    for pkg in pack.get("pip", []):
        print(f"Python package: {pkg}")
        if not _pip_install(pkg):
            print(f"↷ {pkg}: pip install failed, skipped")

    tools_root.mkdir(parents=True, exist_ok=True)
    for repo in pack.get("git", []):
        dest = _clone_repo(repo, tools_root)
        if dest:
            _post_setup_repo(repo["name"], dest)

    return 0

def print_status(tools_root: Path):
    packs = load_packs()
    print("\nCTF TOOLBOX STATUS")
    print("="*64)
    for name, pack in packs.items():
        apt = pack.get("apt", [])
        present = sum(1 for x in apt if shutil.which(_command_for_package(x)))
        git = pack.get("git", [])
        repos = sum(1 for r in git if (tools_root/r["name"]).exists())
        print(f"{name:10} commands {present}/{len(apt)} | repos {repos}/{len(git)}")
