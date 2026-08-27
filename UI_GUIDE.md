# CTF Control Room — UI Guide

## Visual rules

Use these consistently across Welcome, Dashboard, and Help:

- Background: near-black / charcoal.
- Borders: purple.
- Primary text: off-white.
- Secondary text: muted gray.
- Forensics / information: cyan.
- Crypto / warnings: yellow.
- Ready / success: green.
- Pwn / danger: red.
- Actions / shortcuts: purple.
- Keep the layout compact and terminal-first.

## Mascot

Use a small terminal robot as a friendly guide, not a large decorative image.

Example:

```text
        •
     ╭──────╮
   ╭─┤ ^  ^ ├─╮
   ╰─┤  ──  ├─╯
     ╰──────╯
```

Use the robot for:
- Welcome greeting,
- short tips,
- Help footer,
- status hints.

Do not let the mascot take significant terminal space during an active challenge.

## Navigation

```text
W   Welcome
?   Help & Guide
ESC Back
Q   Quit
```


## Windows Terminal rendering

The Welcome page avoids emoji-based robot art so alignment stays stable in WSL/Windows Terminal.
Purple is reserved mainly for borders, shortcuts, and accents; primary text stays off-white.
