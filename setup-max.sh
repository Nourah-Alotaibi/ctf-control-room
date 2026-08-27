#!/usr/bin/env bash
set -e

echo "💜 CTF Control Room — Maximum Setup"
echo "No AI agent will be installed."
echo

# Recommended toolbox + Max power profile automatically.
CTF_SETUP_TOOLBOX=1 CTF_SETUP_POWER=3 ./setup.sh

echo
echo "Installing remaining optional category packs..."
./.venv/bin/ctf-tools install mobile malware osint -y || true

echo
echo "Running final status checks..."
./.venv/bin/ctf-tools status || true
./.venv/bin/ctf-power status || true
./.venv/bin/ctf-doctor || true

echo
echo "✓ Maximum setup finished."
echo "Launch:"
echo "  ./.venv/bin/ctf-go ~/CTF"
echo
echo "CAI and all other AI agents remain separate/optional."
