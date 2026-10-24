"""Consola: mensajes en líneas propias y una línea de estado en vivo que se reescribe."""

from __future__ import annotations

import sys
import threading
import time


class Console:
    def __init__(self, stream=None, status_period_s: float = 0.2, plain_period_s: float = 2.0):
        self.stream = stream or sys.stdout
        self.tty = hasattr(self.stream, "isatty") and self.stream.isatty()
        self.status_period_s = status_period_s if self.tty else plain_period_s
        self._last_status = ""
        self._next = 0.0
        self._lock = threading.Lock()

    def log(self, msg: str) -> None:
        with self._lock:
            if self.tty:
                self.stream.write("\r\x1b[2K" + msg + "\n")
                if self._last_status:
                    self.stream.write(self._last_status)
            else:
                self.stream.write(msg + "\n")
            self.stream.flush()

    def status(self, line: str, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now < self._next:
            return
        self._next = now + self.status_period_s
        with self._lock:
            if self.tty:
                width = 160
                self._last_status = line[:width]
                self.stream.write("\r\x1b[2K" + self._last_status)
            else:
                self.stream.write(line + "\n")
            self.stream.flush()

    def end(self) -> None:
        with self._lock:
            if self.tty and self._last_status:
                self.stream.write("\n")
                self.stream.flush()
            self._last_status = ""
