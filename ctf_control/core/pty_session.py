from __future__ import annotations

import fcntl
import os
import pty
import re
import selectors
import signal
import struct
import subprocess
import termios
import threading
import time
from pathlib import Path
from typing import Callable


_ANSI_CSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_ANSI_OSC_RE = re.compile(r"\x1b\].*?(?:\x07|\x1b\\)", re.DOTALL)
_OTHER_ESC_RE = re.compile(r"\x1b[@-_]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_terminal_controls(text: str) -> str:
    """Return readable text for activity inference/logging.

    Interactive CLIs such as Claude Code repaint the terminal using ANSI/VT100
    escape sequences. RichLog cannot interpret those terminal control codes, so
    keep a cleaned transcript separately from the emulated screen.
    """
    text = _ANSI_OSC_RE.sub("", text)
    text = _ANSI_CSI_RE.sub("", text)
    text = _OTHER_ESC_RE.sub("", text)
    text = text.replace("\r", "\n")
    text = _CONTROL_RE.sub("", text)
    # Collapse excessive redraw whitespace while preserving useful lines.
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line.strip())


class VirtualTerminal:
    """Small VT100/ANSI screen emulator for interactive terminal AI clients.

    It is deliberately lightweight: enough cursor movement/erase support to
    render Claude/Gemini/Codex TUIs inside Textual without adding another
    runtime dependency.
    """

    def __init__(self, cols: int = 120, rows: int = 28):
        self.cols = max(40, int(cols))
        self.rows = max(10, int(rows))
        self.buffer = [[" "] * self.cols for _ in range(self.rows)]
        self.row = 0
        self.col = 0
        self.saved = (0, 0)
        self.scroll_top = 0
        self.scroll_bottom = self.rows - 1
        self._state = "normal"
        self._csi = ""
        self._osc = ""
        self._osc_esc = False

    def resize(self, cols: int, rows: int) -> None:
        cols = max(40, int(cols))
        rows = max(10, int(rows))
        old_lines = self.display_lines()
        self.cols, self.rows = cols, rows
        self.buffer = [[" "] * cols for _ in range(rows)]
        for r, line in enumerate(old_lines[-rows:]):
            for c, ch in enumerate(line[:cols]):
                self.buffer[r][c] = ch
        self.row = min(len(old_lines), rows - 1)
        self.col = 0
        self.scroll_top = 0
        self.scroll_bottom = rows - 1

    def _blank_line(self):
        return [" "] * self.cols

    def _scroll_up(self):
        top, bottom = self.scroll_top, self.scroll_bottom
        if top < 0 or bottom >= self.rows or top >= bottom:
            top, bottom = 0, self.rows - 1
        del self.buffer[top]
        self.buffer.insert(bottom, self._blank_line())

    def _linefeed(self):
        if self.row >= self.scroll_bottom:
            self._scroll_up()
            self.row = self.scroll_bottom
        else:
            self.row = min(self.rows - 1, self.row + 1)

    def _put(self, ch: str):
        if not ch:
            return
        if self.col >= self.cols:
            self.col = 0
            self._linefeed()
        self.buffer[self.row][self.col] = ch
        self.col += 1

    @staticmethod
    def _params(body: str):
        private = body.startswith("?") or body.startswith(">") or body.startswith("!")
        if private:
            body = body[1:]
        # Ignore CSI intermediates for our simple renderer.
        body = re.sub(r"[ -/]", "", body)
        vals = []
        for part in body.split(";") if body else []:
            try:
                vals.append(int(part) if part else 0)
            except ValueError:
                vals.append(0)
        return private, vals

    def _handle_csi(self, seq: str):
        if not seq:
            return
        final = seq[-1]
        body = seq[:-1]
        private, p = self._params(body)
        n = (p[0] if p else 1) or 1

        if final in ("H", "f"):
            r = ((p[0] if len(p) > 0 else 1) or 1) - 1
            c = ((p[1] if len(p) > 1 else 1) or 1) - 1
            self.row = max(0, min(self.rows - 1, r))
            self.col = max(0, min(self.cols - 1, c))
        elif final == "A":
            self.row = max(0, self.row - n)
        elif final == "B":
            self.row = min(self.rows - 1, self.row + n)
        elif final == "C":
            self.col = min(self.cols - 1, self.col + n)
        elif final == "D":
            self.col = max(0, self.col - n)
        elif final == "E":
            self.row = min(self.rows - 1, self.row + n); self.col = 0
        elif final == "F":
            self.row = max(0, self.row - n); self.col = 0
        elif final in ("G", "`"):
            self.col = max(0, min(self.cols - 1, n - 1))
        elif final == "d":
            self.row = max(0, min(self.rows - 1, n - 1))
        elif final == "J":
            mode = p[0] if p else 0
            if mode in (2, 3):
                self.buffer = [[" "] * self.cols for _ in range(self.rows)]
                self.row = self.col = 0
            elif mode == 0:
                # cursor to end of screen
                for c in range(self.col, self.cols):
                    self.buffer[self.row][c] = " "
                for r in range(self.row + 1, self.rows):
                    self.buffer[r] = self._blank_line()
            elif mode == 1:
                for r in range(0, self.row):
                    self.buffer[r] = self._blank_line()
                for c in range(0, self.col + 1):
                    self.buffer[self.row][c] = " "
        elif final == "K":
            mode = p[0] if p else 0
            if mode == 0:
                for c in range(self.col, self.cols):
                    self.buffer[self.row][c] = " "
            elif mode == 1:
                for c in range(0, self.col + 1):
                    self.buffer[self.row][c] = " "
            elif mode == 2:
                self.buffer[self.row] = self._blank_line()
        elif final == "s":
            self.saved = (self.row, self.col)
        elif final == "u":
            self.row, self.col = self.saved
        elif final == "r":
            top = ((p[0] if len(p) > 0 else 1) or 1) - 1
            bottom = ((p[1] if len(p) > 1 else self.rows) or self.rows) - 1
            if 0 <= top < bottom < self.rows:
                self.scroll_top, self.scroll_bottom = top, bottom
        elif final in ("m", "h", "l", "n", "t", "q"):
            # Styling, private modes, status requests, title ops, cursor style.
            pass
        elif private:
            pass

    def feed(self, text: str):
        for ch in text:
            if self._state == "osc":
                if self._osc_esc:
                    if ch == "\\":
                        self._state = "normal"
                        self._osc = ""
                        self._osc_esc = False
                    else:
                        self._osc_esc = False
                    continue
                if ch == "\x07":
                    self._state = "normal"
                    self._osc = ""
                    continue
                if ch == "\x1b":
                    self._osc_esc = True
                    continue
                self._osc += ch
                continue

            if self._state == "esc":
                if ch == "[":
                    self._state = "csi"
                    self._csi = ""
                elif ch == "]":
                    self._state = "osc"
                    self._osc = ""
                elif ch == "7":
                    self.saved = (self.row, self.col); self._state = "normal"
                elif ch == "8":
                    self.row, self.col = self.saved; self._state = "normal"
                else:
                    self._state = "normal"
                continue

            if self._state == "csi":
                self._csi += ch
                if "@" <= ch <= "~":
                    self._handle_csi(self._csi)
                    self._state = "normal"
                    self._csi = ""
                continue

            if ch == "\x1b":
                self._state = "esc"
            elif ch == "\r":
                self.col = 0
            elif ch in ("\n", "\v", "\f"):
                self._linefeed()
            elif ch == "\b":
                self.col = max(0, self.col - 1)
            elif ch == "\t":
                next_tab = min(self.cols - 1, ((self.col // 8) + 1) * 8)
                while self.col < next_tab:
                    self._put(" ")
            elif ch == "\x0c":
                self.buffer = [[" "] * self.cols for _ in range(self.rows)]
                self.row = self.col = 0
            elif ord(ch) >= 32 and ch != "\x7f":
                self._put(ch)

    def display_lines(self):
        return ["".join(line).rstrip() for line in self.buffer]

    def snapshot(self) -> str:
        lines = self.display_lines()
        # Keep leading blank rows out so the useful Claude UI is visible.
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines) if lines else "Waiting for terminal output…"


class PTYSession:
    def __init__(
        self,
        argv,
        cwd: Path,
        env=None,
        on_output: Callable[[str, str], None] | None = None,
        cols: int = 120,
        rows: int = 28,
    ):
        self.argv = list(argv)
        self.cwd = Path(cwd)
        self.env = env or os.environ.copy()
        self.on_output = on_output
        self.master_fd = None
        self.proc = None
        self.started_at = None
        self.ended_at = None
        self._reader = None
        self._stop = threading.Event()
        self.output_history: list[str] = []
        self.raw_history: list[str] = []
        self.cols = cols
        self.rows = rows
        self.terminal = VirtualTerminal(cols=cols, rows=rows)
        self._screen_lock = threading.Lock()

    @property
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        if self.running:
            return
        master_fd, slave_fd = pty.openpty()
        self.master_fd = master_fd
        # Interactive AI CLIs need a real non-zero terminal size to render.
        winsz = struct.pack("HHHH", self.rows, self.cols, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsz)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsz)
        self.proc = subprocess.Popen(
            self.argv,
            cwd=self.cwd,
            env=self.env,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            start_new_session=True,
            close_fds=True,
        )
        os.close(slave_fd)
        self.started_at = time.time()
        self.ended_at = None
        self._stop.clear()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self):
        if self.master_fd is None:
            return
        sel = selectors.DefaultSelector()
        sel.register(self.master_fd, selectors.EVENT_READ)
        try:
            while not self._stop.is_set():
                if self.proc and self.proc.poll() is not None:
                    # Drain one final read if available before exiting.
                    pass
                events = sel.select(timeout=0.2)
                if not events:
                    if self.proc and self.proc.poll() is not None:
                        break
                    continue
                for key, _ in events:
                    try:
                        data = os.read(key.fd, 8192)
                    except OSError:
                        return
                    if not data:
                        return
                    raw = data.decode(errors="replace")
                    self.raw_history.append(raw)
                    if len(self.raw_history) > 300:
                        self.raw_history = self.raw_history[-300:]

                    clean = strip_terminal_controls(raw)
                    if clean:
                        self.output_history.append(clean)
                        if len(self.output_history) > 500:
                            self.output_history = self.output_history[-500:]

                    with self._screen_lock:
                        self.terminal.feed(raw)
                        screen = self.terminal.snapshot()

                    if self.on_output:
                        self.on_output(clean, screen)
        finally:
            if self.started_at is not None and self.ended_at is None:
                self.ended_at = time.time()
            try:
                sel.close()
            except Exception:
                pass

    def screen_snapshot(self) -> str:
        with self._screen_lock:
            return self.terminal.snapshot()

    @property
    def runtime_seconds(self) -> float:
        if self.started_at is None:
            return 0.0
        end = time.time() if self.running else (self.ended_at or time.time())
        return max(0.0, float(end - self.started_at))

    def resize(self, cols: int, rows: int):
        self.cols = max(40, int(cols))
        self.rows = max(10, int(rows))
        with self._screen_lock:
            self.terminal.resize(self.cols, self.rows)
        if self.master_fd is not None:
            winsz = struct.pack("HHHH", self.rows, self.cols, 0, 0)
            try:
                fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsz)
            except OSError:
                pass

    def send(self, text):
        if self.master_fd is not None:
            os.write(self.master_fd, text.encode())

    def send_line(self, text):
        self.send(text + "\n")

    def interrupt(self):
        """Interrupt the active AI/command like Ctrl-C in a real terminal.

        The child is started in its own session/process group, so signaling the
        whole group reliably reaches Claude/Gemini and any foreground command
        they launched. Writing a raw ^C byte alone is not sufficient when the
        PTY is not the controlling terminal of the subprocess.
        """
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGINT)
                return
            except (OSError, ProcessLookupError):
                pass
        # Last-resort fallback for unusual platforms/process states.
        if self.master_fd is not None:
            try:
                os.write(self.master_fd, b"\x03")
            except OSError:
                pass

    def terminate(self):
        self._stop.set()
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                try:
                    self.proc.terminate()
                except Exception:
                    pass

    def close(self):
        self.terminate()
        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None
