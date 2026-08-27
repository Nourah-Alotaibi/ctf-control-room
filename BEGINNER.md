# Beginner Setup 💜

You do not need to understand Python virtual environments, MCP, or tool packs.

## 1. Open WSL / Linux

Enter the project folder.

## 2. Run one command

```bash
./setup.sh
```

The setup will:

1. check Python,
2. create the private Python environment,
3. install CTF Control Room,
4. create all CTF category folders,
5. ask whether you want optional CTF tools,
6. run a harmless self-test.

It does **not** install an AI agent.

## Toolbox choice

You will see:

```text
1. Recommended
2. Minimal
3. Choose Manually
4. Skip
```

### Recommended

Good default for most CTF users.

Includes packs for:

- core tools
- forensics
- network
- pwn
- reverse engineering
- crypto
- web

### Minimal

Only the small `core` starter pack.

### Choose Manually

Pick exactly which category packs you want.

### Skip

Use Control Room without installing optional security tools now.

You can always add tools later.

## Start Control Room

```bash
./.venv/bin/ctf-go ~/CTF
```

The AI agent, if you want one, is installed separately by you.


## AI power choice

Setup also asks:

```text
1. Standard
2. Advanced
3. Max
```

Choose **Standard** if you want the lowest AI cost. The Router, Tool Planner, and Hypothesis Board still work.

Advanced modes are optional and can be changed later.


## Pages

When Control Room opens:

1. **Welcome** — simple robot and heart welcome icon + brief CTF explanation.
2. **Main Dashboard** — challenges, Smart Pre-Scan, AI, terminal, activity.
3. **Help & Guide** — full simplified explanation of all controls and modes.

Navigation:

```text
W   Welcome
?   Help & Guide
ESC Back from Help
Q   Quit
```
