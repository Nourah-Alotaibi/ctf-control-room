
from __future__ import annotations
import os
import pty
import selectors
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

class PTYSession:
    def __init__(self, argv, cwd: Path, env=None, on_output: Callable[[str], None] | None=None):
        self.argv=list(argv); self.cwd=Path(cwd); self.env=env or os.environ.copy()
        self.on_output=on_output; self.master_fd=None; self.proc=None; self.started_at=None
        self._reader=None; self._stop=threading.Event()
        self.output_history=[]

    @property
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self):
        if self.running: return
        master_fd, slave_fd = pty.openpty()
        self.master_fd=master_fd
        self.proc=subprocess.Popen(
            self.argv, cwd=self.cwd, env=self.env,
            stdin=slave_fd, stdout=slave_fd, stderr=slave_fd,
            start_new_session=True, close_fds=True
        )
        os.close(slave_fd)
        self.started_at=time.time()
        self._stop.clear()
        self._reader=threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self):
        if self.master_fd is None: return
        sel=selectors.DefaultSelector(); sel.register(self.master_fd, selectors.EVENT_READ)
        try:
            while not self._stop.is_set():
                if self.proc and self.proc.poll() is not None: break
                for key,_ in sel.select(timeout=.2):
                    try: data=os.read(key.fd,4096)
                    except OSError: return
                    if not data: return
                    text=data.decode(errors="replace")
                    self.output_history.append(text)
                    if len(self.output_history)>200: self.output_history=self.output_history[-200:]
                    if self.on_output: self.on_output(text)
        finally:
            try: sel.close()
            except Exception: pass

    def send(self,text):
        if self.master_fd is not None: os.write(self.master_fd,text.encode())

    def send_line(self,text): self.send(text+"\n")
    def interrupt(self):
        if self.master_fd is not None: os.write(self.master_fd,b"\x03")

    def terminate(self):
        self._stop.set()
        if self.proc and self.proc.poll() is None:
            try: self.proc.terminate()
            except Exception: pass

    def close(self):
        self.terminate()
        if self.master_fd is not None:
            try: os.close(self.master_fd)
            except OSError: pass
            self.master_fd=None
