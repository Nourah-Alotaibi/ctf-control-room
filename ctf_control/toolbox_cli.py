
from pathlib import Path
import argparse, json
from .core.toolbox import load_packs, install_pack, print_status
from .core.config import CONFIG_DIR

DEFAULT_ROOT = Path.home() / "CTF" / "tools"

def load_presets():
    path = CONFIG_DIR / "tool_presets.json"
    return json.loads(path.read_text()) if path.exists() else {
        "minimal": ["core"],
        "recommended": ["core","forensics","network","pwn","reverse","crypto","web"]
    }

def install_many(names, tools_root, assume_yes=False):
    packs = load_packs()
    for name in names:
        if name not in packs:
            print(f"Skipping unknown pack: {name}")
            continue
        install_pack(name, tools_root, assume_yes)

def _manual_pick(packs):
    names = list(packs)
    print("\nChoose packs manually:")
    for i, name in enumerate(names, 1):
        print(f"{i:2}. {name:10} — {packs[name]['description']}")
    raw = input("\nEnter numbers or names separated by spaces: ").strip()
    if not raw:
        return []
    chosen = []
    for token in raw.split():
        if token.isdigit():
            idx = int(token)-1
            if 0 <= idx < len(names):
                chosen.append(names[idx])
        elif token in packs:
            chosen.append(token)
    return list(dict.fromkeys(chosen))

def wizard():
    packs = load_packs()
    presets = load_presets()

    print("💜 CTF Control Room — Optional Toolbox Setup")
    print("This installs CTF/security tools only.")
    print("NO AI agents are installed.\n")

    print("Choose your setup:")
    print("1. Recommended  — common CTF categories")
    print("2. Minimal      — small starter setup")
    print("3. Choose Manually")
    print("4. Skip toolbox")
    choice = input("\n> ").strip() or "1"

    if choice == "1":
        selected = presets["recommended"]
    elif choice == "2":
        selected = presets["minimal"]
    elif choice == "3":
        selected = _manual_pick(packs)
    else:
        print("Skipping toolbox installation.")
        return

    print("\nSelected packs:", ", ".join(selected) if selected else "none")
    if selected:
        install_many(selected, DEFAULT_ROOT, False)
        print_status(DEFAULT_ROOT)
        print("\nDone. You can add more later with:")
        print("  ctf-tools install <pack>")

def main():
    parser = argparse.ArgumentParser(
        prog="ctf-tools",
        description="Optional CTF toolbox setup. Never installs AI agents."
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("wizard")
    sub.add_parser("list")

    st = sub.add_parser("status")
    st.add_argument("--tools-root", type=Path, default=DEFAULT_ROOT)

    ins = sub.add_parser("install")
    ins.add_argument("packs", nargs="+")
    ins.add_argument("--tools-root", type=Path, default=DEFAULT_ROOT)
    ins.add_argument("-y","--yes", action="store_true")

    pre = sub.add_parser("preset")
    pre.add_argument("name", choices=["minimal","recommended"])
    pre.add_argument("--tools-root", type=Path, default=DEFAULT_ROOT)
    pre.add_argument("-y","--yes", action="store_true")

    args = parser.parse_args()

    if not args.cmd or args.cmd == "wizard":
        wizard()
        return

    packs = load_packs()

    if args.cmd == "list":
        print("Presets:")
        for name, items in load_presets().items():
            print(f"  {name:12} " + ", ".join(items))
        print("\nPacks:")
        for name, spec in packs.items():
            print(f"  {name:12} {spec['description']}")
        return

    if args.cmd == "status":
        print_status(args.tools_root)
        return

    if args.cmd == "install":
        install_many(args.packs, args.tools_root, args.yes)
        print_status(args.tools_root)
        return

    if args.cmd == "preset":
        install_many(load_presets()[args.name], args.tools_root, args.yes)
        print_status(args.tools_root)

if __name__ == "__main__":
    main()
