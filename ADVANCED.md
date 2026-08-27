# Advanced Setup

Use this path if you want full control.

## Install manually

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Tool packs

```bash
ctf-tools list
ctf-tools install core
ctf-tools preset recommended
ctf-tools status
```

## Optional MCP

```bash
pip install -e '.[mcp]'
```

Then for a challenge:

```bash
export CTF_CONTROL_CHALLENGE="$PWD"
ctf-mcp
```

## Custom toolbox root

```bash
export CTF_CONTROL_TOOLS_ROOT=/path/to/tools
```

## Run

```bash
ctf-go ~/CTF
```

No AI agent is installed automatically.


## Power profiles

```bash
ctf-power profile standard
ctf-power profile advanced
ctf-power profile max
ctf-power status
```

Optional higher-token features:

```bash
ctf-power enable stuck_recovery
ctf-power enable parallel_agents
```

CAI remains a separate optional installation.


## Install checks

Before relying on the environment:

```bash
ctf-install-check
ctf-tools status
ctf-doctor
```

Optional apt/Python tools are installed individually. A missing optional package should not stop an entire category pack.
