
from __future__ import annotations
import shutil, sys, platform
from pathlib import Path

def main():
    print("CTF Control Room Install Check")
    print("="*48)
    print("Python:", sys.version.split()[0])
    print("Platform:", platform.platform())

    checks = [
        ("python3", shutil.which("python3")),
        ("git", shutil.which("git")),
        ("unzip", shutil.which("unzip")),
        ("sudo", shutil.which("sudo")),
        ("apt-get", shutil.which("apt-get")),
    ]
    for name, path in checks:
        print(("✓" if path else "·"), name, path or "not found")

    home = Path.home()
    print("Home:", home)
    print("CTF root:", home/"CTF")
    print("\nThis check installs nothing.")
    print("Internet is required later for pip packages and GitHub clones.")
