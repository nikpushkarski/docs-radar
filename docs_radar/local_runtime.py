"""One owned, optional model server per app process; no installs or inference.

Imported modules survive Streamlit reruns. A lock also protects simultaneous tabs.
Normal process shutdown closes only the child we started, never another service.
"""

import atexit
from dataclasses import dataclass
import logging
from pathlib import Path
import threading

from scripts.setup_support import SetupError, configured_model, inspect_models, model_server


@dataclass(frozen=True)
class RuntimeStatus:
    model: str = ""
    error: str = ""


class StartupLog:
    def status(self, message):
        logging.getLogger(__name__).info(message)


def installed_model_tags(root):
    """List usable managed models locally; unimported GGUFs are not server tags."""
    try:
        return tuple(sorted({item.name for item in inspect_models(Path(root) / "models")
                             if item.kind == "ollama" and item.usable}))
    except OSError:
        return ()  # Optional discovery must not prevent extractive use.


def check_integration():
    # Older installations may have weights but lack the optional Python packages.
    from langchain_ollama import ChatOllama  # noqa: F401


class AppModelServer:
    def __init__(self, root):
        self.root = Path(root)
        self._lock = threading.RLock()
        self._attempted = False
        self._context = None
        self._process = None
        self._status = RuntimeStatus()

    def start(self, *, retry=False):
        with self._lock:
            if self._process is not None and self._process.poll() is not None:
                self.close()
                self._status = RuntimeStatus(error="The app's model server stopped. Retry startup or use extractive mode.")
            if self._attempted and not retry:
                return self._status
            if self._process is not None:
                return self._status
            self._attempted = True
            self._status = RuntimeStatus()
            if not (self.root / "models" / "setup.json").exists():
                return self._status  # Fresh/extractive-only checkout: no hardware or network probe.
            try:
                binary, model = configured_model(self.root)
                check_integration()
                context = model_server(binary, self.root, StartupLog())
                process = context.__enter__()
                self._context, self._process = context, process
                self._status = RuntimeStatus(model=model)
            except ImportError:
                self._status = RuntimeStatus(error="Local-model Python dependencies are missing. Rerun setup and select the existing model.")
            except (SetupError, OSError, ValueError, KeyError, TypeError) as error:
                self._status = RuntimeStatus(error=str(error))
            return self._status

    def close(self):
        with self._lock:
            context, self._context = self._context, None
            self._process = None
            if context is not None:
                context.__exit__(None, None, None)


_servers = {}
_servers_lock = threading.Lock()


def app_model_server(root):
    """Return the same owner across sessions/reruns, not a session-owned process."""
    root = Path(root).resolve()
    with _servers_lock:
        if root not in _servers:
            server = AppModelServer(root)
            atexit.register(server.close)
            _servers[root] = server
        return _servers[root]


def start_app_model(root, *, retry=False):
    return app_model_server(root).start(retry=retry)
