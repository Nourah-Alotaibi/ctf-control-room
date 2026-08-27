# Setup

Choose the path that fits you.

## Beginner

Use:

```bash
./setup.sh
```

Then:

```bash
./.venv/bin/ctf-go ~/CTF
```

See [`BEGINNER.md`](BEGINNER.md).

## Advanced

Manual setup, custom packs, MCP, and environment variables:

See [`ADVANCED.md`](ADVANCED.md).

## Important

The toolbox is shared by Control Room and the AI agent working in the same WSL/Linux environment.

Control Room does not install AI agents.


## If one tool fails to install

The installer continues with the remaining optional tools.

After setup run:

```bash
ctf-tools status
ctf-doctor
```

This shows what is available on your actual WSL installation.
