#!/usr/bin/env bash
set -e

PURPLE='\033[0;35m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${PURPLE}"
echo "💜 CTF CONTROL ROOM — BEGINNER SETUP"
echo -e "${NC}"
echo "This setup installs Control Room."
echo "AI agents are NOT installed."
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${YELLOW}Python 3 is missing.${NC}"
  echo "Run:"
  echo "  sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is missing; installing it..."
  sudo apt update
  sudo apt install -y git || true
fi

if ! command -v unzip >/dev/null 2>&1; then
  echo "unzip is missing; installing it..."
  sudo apt update
  sudo apt install -y unzip || true
fi

echo "✓ Python found"

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo -e "${YELLOW}python3-venv is missing.${NC}"
  echo "Trying to install python3-venv..."
  sudo apt update
  sudo apt install -y python3-venv
fi

if [ ! -d ".venv" ]; then
  echo "Creating private Python environment..."
  python3 -m venv .venv
fi

echo "Installing Control Room..."
.venv/bin/python -m pip install --upgrade pip setuptools wheel >/dev/null
.venv/bin/python -m pip install -e .

echo "Creating CTF folders..."
mkdir -p "$HOME/CTF"/{web,reverse,pwn,crypto,forensics,network,stego,malware,mobile,osint,cloud,hardware-iot,ai-ml,misc}
mkdir -p "$HOME/CTF/tools"

echo "Optional CTF toolbox:"
echo "1. Recommended"
echo "2. Minimal"
echo "3. Choose Manually"
echo "4. Skip"
if [ -n "${CTF_SETUP_TOOLBOX:-}" ]; then
  CHOICE="$CTF_SETUP_TOOLBOX"
  echo "> $CHOICE"
else
  read -r -p "> " CHOICE
fi

case "$CHOICE" in
  1)
    .venv/bin/ctf-tools preset recommended
    ;;
  2)
    .venv/bin/ctf-tools preset minimal
    ;;
  3)
    .venv/bin/ctf-tools wizard
    ;;
  *)
    echo "Skipping optional toolbox."
    ;;
esac

echo
echo "AI power profile:"
echo "1. Standard  — Router + Tool Planner + Hypothesis Board (lowest AI cost)"
echo "2. Advanced  — Standard + optional Stuck Recovery"
echo "3. Max       — Advanced + optional Parallel/CAI modes (can cost more tokens)"
if [ -n "${CTF_SETUP_POWER:-}" ]; then
  POWER_CHOICE="$CTF_SETUP_POWER"
  echo "> $POWER_CHOICE"
else
  read -r -p "> " POWER_CHOICE
fi

case "$POWER_CHOICE" in
  2)
    .venv/bin/ctf-power profile advanced
    ;;
  3)
    .venv/bin/ctf-power profile max
    ;;
  *)
    .venv/bin/ctf-power profile standard
    ;;
esac

echo
echo "Running setup self-test..."
.venv/bin/ctf-doctor || true

echo
echo -e "${GREEN}✓ Setup complete${NC}"
echo
echo "Start Control Room with:"
echo "  ./.venv/bin/ctf-go ~/CTF"
echo
echo "Optional: add this shortcut later:"
echo "  alias ctf-go='$PWD/.venv/bin/ctf-go'"
echo
echo "AI agents are still separate. Control Room uses whichever agent YOU install."
