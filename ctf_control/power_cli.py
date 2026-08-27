
from __future__ import annotations
from pathlib import Path
import argparse, json, subprocess, sys, shutil
from .core.power import apply_profile, load_settings, set_feature
from .core.cai_backend import cai_status

DEFAULT_ROOT=Path.home()/"CTF"

def _print(data):
    for k,v in data.items():
        print(f"{k:18} {'ON' if v else 'OFF'}")

def main():
    p=argparse.ArgumentParser(
        prog="ctf-power",
        description="Control optional advanced CTF Control Room features."
    )
    sub=p.add_subparsers(dest="cmd")

    prof=sub.add_parser("profile")
    prof.add_argument("name",choices=["standard","advanced","max"])
    prof.add_argument("--ctf-root",type=Path,default=DEFAULT_ROOT)

    st=sub.add_parser("status")
    st.add_argument("--ctf-root",type=Path,default=DEFAULT_ROOT)

    en=sub.add_parser("enable")
    en.add_argument("feature",choices=["stuck_recovery","parallel_agents","cai_backend"])
    en.add_argument("--ctf-root",type=Path,default=DEFAULT_ROOT)

    dis=sub.add_parser("disable")
    dis.add_argument("feature",choices=["stuck_recovery","parallel_agents","cai_backend"])
    dis.add_argument("--ctf-root",type=Path,default=DEFAULT_ROOT)

    sub.add_parser("install-cai")

    args=p.parse_args()

    if not args.cmd:
        print("Simple choices:")
        print("  ctf-power profile standard   # lowest AI cost")
        print("  ctf-power profile advanced   # adds stuck recovery")
        print("  ctf-power profile max        # enables costly optional modes")
        return

    if args.cmd=="profile":
        data=apply_profile(args.ctf_root,args.name)
        print(f"Applied {args.name} profile:")
        _print(data)
        if args.name=="max":
            print("\nNote: Parallel agents and CAI mode can increase token/API usage.")
        return

    if args.cmd=="status":
        _print(load_settings(args.ctf_root))
        print("\nCAI:", cai_status())
        return

    if args.cmd=="enable":
        data=set_feature(args.ctf_root,args.feature,True)
        _print(data); return

    if args.cmd=="disable":
        data=set_feature(args.ctf_root,args.feature,False)
        _print(data); return

    if args.cmd=="install-cai":
        print("CAI is OPTIONAL and may use additional model/API tokens when used.")
        print("For safety and reproducibility, Control Room does not silently install it.")
        print("Follow CAI's official installation instructions, then run:")
        print("  ctf-power enable cai_backend")
