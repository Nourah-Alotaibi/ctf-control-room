
# CTF Control Room v1.0.0 Agent Instructions

You are operating inside an authorized CTF challenge workspace.

Before deeper work:
1. Read `.ctf/context.md`.
2. Read `.ctf/tool_registry.md`.
3. Check `.ctf/commands.jsonl` before repeating a command.
4. Read the raw result from `.ctf/raw/` when a previous command already ran.
5. Use FAST tools for lightweight checks, DEEP tools when justified, and EXPENSIVE tools selectively.
6. Save useful solver scripts and concise findings in the challenge directory.
7. Do not repeat failed approaches mechanically.
8. Stay within the explicit CTF/lab scope and competition rules.

The Automatic Smart Pre-Scan is local and no-AI. It has a 60-second hard maximum
and should stop earlier when enough useful context is collected.


## Control Room orchestration

Read `.ctf/hypothesis.md` when present.
Use the recommended tool list in `.ctf/context.md` before scanning the entire toolbox.
Do not mechanically repeat failed approaches.
Parallel reasoning and recovery are optional features controlled by the user.
