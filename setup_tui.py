"""Small dependency-free terminal UI for setup; no browser or GUI installer."""

import os
import select
import shutil
import sys
import textwrap


class Cancelled(Exception):
    """The user cancelled, or input ended without consent."""


def safe_text(value):
    # Filenames and subprocess output must not inject terminal control sequences.
    return "".join(c if c.isprintable() or c == "\n" else "?" for c in str(value))


def read_key():
    if os.name == "nt":
        import msvcrt

        key = msvcrt.getwch()
        if key in ("\x00", "\xe0"):
            return {"H": "up", "P": "down", "K": "left", "M": "right"}.get(msvcrt.getwch(), "unknown")
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        previous = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = os.read(fd, 1).decode("ascii", errors="replace")
            if key == "\x1b" and select.select([fd], [], [], 0.1)[0]:
                sequence = os.read(fd, 1)
                if sequence in (b"[", b"O") and select.select([fd], [], [], 0.1)[0]:
                    return {b"A": "up", b"B": "down", b"C": "right", b"D": "left"}.get(os.read(fd, 1), "unknown")
                return "unknown"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, previous)
    if key in ("\x03", "\x04", "\x1a", "\x1b", ""):
        raise Cancelled("Setup cancelled; no default answer was assumed.")
    return "enter" if key in ("\r", "\n") else key.lower()


class TerminalUI:
    def __init__(self, key_reader=read_key, output=None):
        self.key_reader = key_reader
        self.output = output or sys.stdout
        self.lines = []
        self._windows_mode = None

    def __enter__(self):
        if not sys.stdin.isatty() or not self.output.isatty():
            raise Cancelled("Run setup in an interactive terminal; redirected input cannot grant consent.")
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            kernel = ctypes.windll.kernel32
            kernel.GetStdHandle.restype = wintypes.HANDLE
            kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            handle = kernel.GetStdHandle(-11)
            mode = wintypes.DWORD()
            if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
                raise Cancelled("Use cmd/cmder or Windows Terminal with an interactive console.")
            if not kernel.SetConsoleMode(handle, mode.value | 0x0004):
                raise Cancelled("This terminal cannot display the setup TUI.")
            self._windows_mode = (handle, mode.value)
        self.output.write("\033[?25l")
        return self

    def __exit__(self, *args):
        self.output.write("\033[?25h\n")
        self.output.flush()
        if self._windows_mode:
            import ctypes

            ctypes.windll.kernel32.SetConsoleMode(*self._windows_mode)

    def page(self, title, *paragraphs):
        self.lines = ["DOCS RADAR | " + safe_text(title), "=" * 64, ""]
        for paragraph in paragraphs:
            self.text(paragraph)

    def text(self, paragraph):
        width = max(40, shutil.get_terminal_size((100, 30)).columns - 2)
        for line in safe_text(paragraph).splitlines():
            self.lines.extend(textwrap.wrap(line, width=width) or [""])
        self.lines.append("")

    def table(self, headers, rows):
        width = max(60, shutil.get_terminal_size((100, 30)).columns - 2)
        count = len(headers)
        cell_width = max(12, (width - 3 * count - 1) // count)
        border = "+" + "+".join("-" * (cell_width + 2) for _ in headers) + "+"
        self.lines.append(border)
        for row in [headers, *rows]:
            cells = [textwrap.wrap(safe_text(cell), cell_width) or [""] for cell in row]
            for index in range(max(map(len, cells))):
                self.lines.append("| " + " | ".join(
                    (cell[index] if index < len(cell) else "").ljust(cell_width)
                    for cell in cells
                ) + " |")
            self.lines.append(border)
        self.lines.append("")

    def draw(self, *extra):
        self.output.write("\033[2J\033[H" + "\n".join(self.lines + list(extra)) + "\n")
        self.output.flush()

    def choose(self, question, options):
        selected = 0
        while True:
            count = min(8, len(options))
            start = max(0, min(selected - count // 2, len(options) - count))
            self.draw(safe_text(question), *[
                ("> " if index == selected else "  ") + safe_text(options[index])
                for index in range(start, start + count)
            ], "", f"Option {selected + 1}/{len(options)} | Up/Down: select | Enter: confirm | Esc/Ctrl+C: cancel")
            key = self.key_reader()
            if key == "up":
                selected = (selected - 1) % len(options)
            elif key == "down":
                selected = (selected + 1) % len(options)
            elif key == "enter":
                return selected

    def confirm(self):
        # Page the plan so a small terminal cannot hide downloads above the prompt.
        height = max(6, shutil.get_terminal_size((100, 30)).lines - 6)
        pages = [self.lines[index:index + height] for index in range(0, len(self.lines), height)] or [[]]
        page = 0
        while True:
            last = page == len(pages) - 1
            prompt = "Start downloading? [Y/n]" if last else "Enter/Right: next page | N: decline"
            text = pages[page] + ["", f"Download plan: page {page + 1}/{len(pages)}", prompt,
                                 "Left: previous page | Esc/Ctrl+C: cancel"]
            self.output.write("\033[2J\033[H" + "\n".join(text) + "\n")
            self.output.flush()
            key = self.key_reader()
            if key == "n":
                return False
            if key in ("enter", "y") and last:
                return True
            if key in ("enter", "right"):
                page = min(len(pages) - 1, page + 1)
            elif key == "left":
                page = max(0, page - 1)

    def status(self, message):
        self.draw(safe_text(message), "Ctrl+C cancels the active operation.")
