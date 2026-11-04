"""Portable setup operations. Network/package mutations are called only after consent."""

from contextlib import contextmanager
from dataclasses import dataclass
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import platform
import re
import shutil
import socket
import struct
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import venv
import zipfile

from docs_radar.model_policy import CONTEXT_TOKENS, MAX_MODEL_BYTES

GIB = 1024 ** 3
ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:11435"
OLLAMA_VERSION = "0.40.14"
# Official release asset sizes/SHA-256, checked 2026-11-03. No latest-version redirect.
ASSETS = {
    ("Windows", "amd64"): ("ollama-windows-amd64.zip", 1601954968,
        "65d68cade6cf6375f398b518224f8c8a15e062387f38cf477abfc848de7e7e29"),
    ("Windows", "arm64"): ("ollama-windows-arm64.zip", 215932926,
        "df8a4e954587ac65ba52ec26b453490a21cd58f80b55f75cf0d706f1506764a8"),
    ("Darwin", "amd64"): ("ollama-darwin.tgz", 186686970,
        "f3bf9a528e908da0da5a2b3a4ad3252a369d62186501dc4880261e8d9023bff5"),
    ("Darwin", "arm64"): ("ollama-darwin.tgz", 186686970,
        "f3bf9a528e908da0da5a2b3a4ad3252a369d62186501dc4880261e8d9023bff5"),
}


class SetupError(Exception):
    pass


@dataclass(frozen=True)
class Model:
    tag: str
    download_bytes: int
    memory_gib: float
    digest: str

    @property
    def source(self):
        return "https://ollama.com/library/" + self.tag

    @property
    def manual_source(self):
        size = self.tag.split(":")[1].upper()
        return "https://huggingface.co/Qwen/Qwen3-" + size + "-GGUF"


# Apache 2.0 licences and manifest hashes verified against registry.ollama.ai.
# Conservative footprints include context/runtime overhead; not a performance benchmark.
# Never recommend larger models as a workaround for missing evidence or weak prose.
MODELS = (
    Model("qwen3:0.6b", 522653767, 2.0,
          "7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435"),
    Model("qwen3:1.7b", 1359293444, 3.0,
          "8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7"),
    Model("qwen3:4b", 2497293931, 4.5,
          "359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7"),
)


@dataclass(frozen=True)
class Hardware:
    system: str
    architecture: str
    os_version: str
    total_ram: int
    available_ram: int
    gpu: str
    free_vram: int
    free_disk: int
    notes: str = ""


@dataclass(frozen=True)
class LocalModel:
    name: str
    path: Path
    kind: str
    size: int
    usable: bool
    note: str


def command_text(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def available_disk(path):
    path = Path(path)
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free


def parse_vm_stat(text):
    page_size = re.search(r"page size of (\d+) bytes", text)
    if not page_size:
        return 0
    pages = 0
    for name in ("Pages free", "Pages inactive", "Pages speculative"):
        match = re.search(r"^" + name + r":\s*(\d+)", text, re.MULTILINE)
        pages += int(match.group(1)) if match else 0
    return pages * int(page_size.group(1))


def detect_hardware(root=ROOT):
    system = platform.system()
    raw_arch = platform.machine().lower()
    architecture = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(raw_arch, raw_arch)
    total = available = free_vram = 0
    gpu = "CPU only / accelerator not verified"
    notes = "Unknown memory measurements disable automatic model recommendations."
    version = platform.release()
    if system == "Windows":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in (
                    "total_phys", "avail_phys", "total_page", "avail_page",
                    "total_virtual", "avail_virtual", "avail_extended")]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            total, available = status.total_phys, status.avail_phys
        version = platform.version()
        smi = shutil.which("nvidia-smi")
        if smi:
            output = command_text([smi, "--query-gpu=name,memory.free", "--format=csv,noheader,nounits"])
            choices = []
            for line in output.splitlines():
                try:
                    name, memory = line.rsplit(",", 1)
                    choices.append((int(memory.strip()) * 1024 ** 2, name.strip()))
                except ValueError:
                    continue
            if choices:
                free_vram, gpu = max(choices)
        notes = "NVIDIA free VRAM is measured when available; AMD/unknown acceleration uses the CPU sizing policy."
    elif system == "Darwin":
        # Detect Apple silicon even when Python is running through Rosetta.
        if command_text(["sysctl", "-n", "hw.optional.arm64"]) == "1":
            architecture = "arm64"
        total_text = command_text(["sysctl", "-n", "hw.memsize"])
        total = int(total_text) if total_text.isdigit() else 0
        available = min(total, parse_vm_stat(command_text(["vm_stat"])))
        version = platform.mac_ver()[0]
        gpu = "Apple silicon / unified memory" if architecture == "arm64" else "Intel Mac / CPU only"
        notes = "macOS available RAM is an estimate from free, inactive and speculative pages; not a memory-pressure benchmark."
    return Hardware(system, architecture, version, total, available, gpu, free_vram, available_disk(root), notes)


def supported_runtime(hardware):
    if (hardware.system, hardware.architecture) not in ASSETS:
        return False
    if hardware.system == "Darwin":
        major = hardware.os_version.split(".")[0]
        return major.isdigit() and int(major) >= 14
    # Windows 10 22H2 / Windows 11; fail closed if the build cannot be established.
    numbers = hardware.os_version.split(".")
    return len(numbers) >= 3 and numbers[2].isdigit() and int(numbers[2]) >= 19045


def runtime_directory(hardware):
    if hardware.system == "Windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / "Library" / "Application Support"
    return base / "DocsRadar" / "ollama" / OLLAMA_VERSION / hardware.architecture


def runtime_binary(directory, system):
    name = "ollama.exe" if system == "Windows" else "ollama"
    for relative in (name, "bin/" + name):
        candidate = directory / relative
        if candidate.is_file():
            return candidate
    return None


def cached_runtime(hardware):
    directory = runtime_directory(hardware)
    marker = directory / "docs-radar-install.json"
    try:
        record = json.loads(marker.read_text(encoding="utf-8"))
        if record.get("archive_sha256") == ASSETS[(hardware.system, hardware.architecture)][2]:
            return runtime_binary(directory, hardware.system)
    except (OSError, ValueError, KeyError, AttributeError):
        pass
    return None


def recommend_model(hardware, runtime_missing=True):
    if not supported_runtime(hardware) or not hardware.available_ram:
        return None
    apple_gpu = hardware.system == "Darwin" and hardware.architecture == "arm64"
    accelerated = apple_gpu or hardware.free_vram > 0
    budget = hardware.available_ram / GIB * 0.6
    if hardware.free_vram:
        budget = min(hardware.free_vram / GIB * 0.9, hardware.available_ram / GIB * 0.6)
    reserve = 3 * GIB
    if runtime_missing:
        reserve += ASSETS[(hardware.system, hardware.architecture)][1] * 5
    eligible = [model for model in MODELS if
                model.memory_gib <= budget and
                (accelerated or model.memory_gib <= 4.5) and
                reserve + model.download_bytes * 2 <= hardware.free_disk]
    return eligible[-1] if eligible else None


def inspect_models(directory):
    directory = Path(directory)
    if not directory.exists():
        return []
    found = []
    for path in sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".gguf"):
        try:
            with path.open("rb") as stream:
                header = stream.read(24)
            valid = len(header) == 24 and header[:4] == b"GGUF" and struct.unpack("<I", header[4:8])[0] in (2, 3)
            split = bool(re.search(r"-\d{5}-of-\d{5}\.gguf$", path.name, re.IGNORECASE))
            valid = valid and not split and not path.is_symlink()
            note = "GGUF header found; compatibility not yet tested" if valid else "Invalid header, symlink or split GGUF; use a complete single-file model"
            size = path.stat().st_size
            if size > MAX_MODEL_BYTES:
                valid, note = False, "Above the 3 GiB lightweight limit; left on disk, not offered"
            found.append(LocalModel(path.name, path, "gguf", size, valid, note))
        except OSError as error:
            found.append(LocalModel(path.name, path, "gguf", 0, False, str(error)))
    manifest_root = directory / "ollama" / "manifests"
    for path in sorted(manifest_root.glob("registry.ollama.ai/*/*/*")):
        if not path.is_file():
            continue
        parts = path.relative_to(manifest_root).parts
        name = ("" if parts[1] == "library" else parts[1] + "/") + parts[2] + ":" + parts[3]
        try:
            if path.stat().st_size > 1024 ** 2 or path.is_symlink():
                raise ValueError("Invalid manifest")
            manifest = json.loads(path.read_text(encoding="utf-8"))
            layers = manifest["layers"]
            if not any(layer.get("mediaType") == "application/vnd.ollama.image.model" for layer in layers):
                raise ValueError("Not a local weights manifest")
            records = [manifest["config"], *layers]
            for record in records:
                digest = record["digest"]
                if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
                    raise ValueError("Invalid digest")
                blob = directory / "ollama" / "blobs" / digest.replace(":", "-")
                if blob.is_symlink() or blob.stat().st_size != record["size"]:
                    raise ValueError("Missing or incomplete blob")
            size = sum(record["size"] for record in records)
            usable = size <= MAX_MODEL_BYTES
            note = "Local cache complete; compatibility not yet tested" if usable else "Above the 3 GiB lightweight limit; left on disk, not offered"
            found.append(LocalModel(name, path, "ollama", size, usable, note))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            found.append(LocalModel(name, path, "ollama", 0, False, "Incomplete cache: " + str(error)))
    for suffix in ("*.safetensors", "*.bin", "*.ggml", "*.partial"):
        for path in sorted(directory.glob(suffix)):
            found.append(LocalModel(path.name, path, "unsupported", 0, False, "Not a supported single-file GGUF / complete Ollama cache"))
    return found


def download_archive(url, destination, size, digest, ui):
    sha = hashlib.sha256()
    received = 0
    request = urllib.request.Request(url, headers={"User-Agent": "DocsRadar-local-setup"})
    with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
        if not response.geturl().startswith("https://"):
            raise SetupError("Refusing a non-HTTPS runtime download.")
        while block := response.read(1024 * 1024):
            received += len(block)
            if received > size:
                raise SetupError("Runtime download exceeds its pinned size.")
            sha.update(block)
            output.write(block)
            ui.status(f"Downloading Ollama: {received / size:.0%}")
    if received != size or sha.hexdigest() != digest:
        raise SetupError("Ollama archive size/SHA-256 mismatch; nothing from it was executed.")


def safe_member(name):
    posix = PurePosixPath(name.replace("\\", "/"))
    return not (posix.is_absolute() or PureWindowsPath(name).drive or ".." in posix.parts)


def extract_archive(archive, destination):
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                mode = member.external_attr >> 16
                if not safe_member(member.filename) or mode & 0o170000 == 0o120000:
                    raise SetupError("Unsafe path or symlink in runtime archive.")
            bundle.extractall(destination)
    else:
        with tarfile.open(archive, "r:gz") as bundle:
            for member in bundle.getmembers():
                if not safe_member(member.name):
                    raise SetupError("Unsafe path in runtime archive.")
            bundle.extractall(destination, filter="data")


def promote_runtime(stage, destination):
    """Allow a bounded retry when Windows scanners briefly hold extracted files."""
    for attempt in range(5):
        if destination.exists():
            raise SetupError("Runtime destination appeared during installation; refusing to overwrite it.")
        try:
            stage.rename(destination)
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) not in (5, 32) or attempt == 4:
                raise
            time.sleep(0.1 * 2 ** attempt)


def install_runtime(hardware, ui):
    existing = cached_runtime(hardware)
    if existing:
        return existing
    name, size, digest = ASSETS[(hardware.system, hardware.architecture)]
    destination = runtime_directory(hardware)
    if destination.exists():
        raise SetupError(f"Unverified runtime directory already exists: {destination}. Move it aside and rerun; it was not overwritten.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/ollama/ollama/releases/download/v{OLLAMA_VERSION}/{name}"
    with tempfile.TemporaryDirectory(prefix="docs-radar-download-") as temporary:
        archive = Path(temporary) / name
        download_archive(url, archive, size, digest, ui)
        ui.status("Verified SHA-256. Extracting Ollama (no administrator privileges needed)...")
        with tempfile.TemporaryDirectory(prefix=".staging-", dir=destination.parent) as staging:
            # Leave the TemporaryDirectory root in place and move its payload.
            # This avoids the root-rename failure caught by the Windows test.
            stage = Path(staging) / "payload"
            stage.mkdir()
            extract_archive(archive, stage)
            binary = runtime_binary(stage, hardware.system)
            if not binary:
                raise SetupError("Official archive layout was not recognized; runtime was not installed.")
            if hardware.system == "Darwin":
                binary.chmod(binary.stat().st_mode | 0o700)
            (stage / "docs-radar-install.json").write_text(json.dumps({"archive_sha256": digest}), encoding="utf-8")
            promote_runtime(stage, destination)
    return runtime_binary(destination, hardware.system)


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)


def run_command(args, ui, label, **kwargs):
    ui.status(label)
    with tempfile.TemporaryFile(mode="w+b") as log:
        process = subprocess.Popen([str(arg) for arg in args], stdout=log, stderr=subprocess.STDOUT, **kwargs)
        try:
            frame = 0
            while process.poll() is None:
                ui.status(label + " " + "." * (frame % 4))
                frame += 1
                time.sleep(0.4)
        finally:
            stop_process(process)
        if process.returncode:
            log.seek(0, os.SEEK_END)
            log.seek(max(0, log.tell() - 5000))
            detail = log.read().decode("utf-8", errors="replace")
            raise SetupError(label + " failed:\n" + detail)


def install_python(root, ui, *, with_model=False):
    environment = root / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if environment.exists() and not python.is_file():
        raise SetupError("Existing .venv is incomplete or from another OS; move it aside and rerun. It was not overwritten.")
    if not environment.exists():
        ui.status("Creating this machine's Python virtual environment...")
        venv.EnvBuilder(with_pip=True).create(environment)
    run_command([python, "-c", "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'"], ui, "Checking virtual-environment Python")
    # Model requirements include the base app and its shared pinned constraints.
    requirements = "requirements-model.txt" if with_model else "requirements.txt"
    label = "Installing app + local-model Python dependencies from PyPI" if with_model else "Installing Python requirements from PyPI"
    run_command([python, "-m", "pip", "--isolated", "--disable-pip-version-check", "install",
                 "--index-url", "https://pypi.org/simple", "-r", root / "scripts" / requirements], ui, label)
    run_command([python, "-m", "pip", "check"], ui, "Checking installed dependency compatibility")
    run_command([python, "-c", "import streamlit"], ui, "Checking Streamlit import")
    if with_model:
        run_command([python, "-c", "from langchain_ollama import ChatOllama"], ui, "Checking local-model integration import")
    return python


def model_environment(root):
    return {**os.environ, "OLLAMA_MODELS": str(root / "models" / "ollama"),
            "OLLAMA_HOST": BASE_URL.removeprefix("http://"), "OLLAMA_NO_CLOUD": "1",
            "OLLAMA_CONTEXT_LENGTH": str(CONTEXT_TOKENS), "OLLAMA_NUM_PARALLEL": "1",
            "OLLAMA_MAX_LOADED_MODELS": "1", "OLLAMA_MAX_QUEUE": "1", "OLLAMA_KEEP_ALIVE": "0"}


def local_json(path):
    # Do not route loopback API traffic through a user's external HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(BASE_URL + path, timeout=2) as response:
        return json.load(response)


@contextmanager
def model_server(binary, root, ui):
    try:
        with socket.create_connection(("127.0.0.1", 11435), timeout=0.5):
            raise SetupError("Port 11435 is already in use. Stop the project model server and retry; setup will not control an unrelated server.")
    except (ConnectionRefusedError, TimeoutError):
        pass
    directory = root / "models"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "server.log").open("ab") as log:
        process = subprocess.Popen([str(binary), "serve"], env=model_environment(root), stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise SetupError("Ollama stopped unexpectedly. See models/server.log.")
                try:
                    version = local_json("/api/version").get("version")
                    if version != OLLAMA_VERSION:
                        raise SetupError("Unexpected Ollama server version; refusing to use it.")
                    break
                except (OSError, ValueError):
                    time.sleep(0.3)
                    ui.status("Starting the isolated, local-only Ollama server...")
            else:
                raise SetupError("Ollama did not start within 60 seconds. See models/server.log.")
            yield process
        finally:
            stop_process(process)


def verify_model_reference(model):
    tag = model.tag.split(":")[1]
    url = "https://registry.ollama.ai/v2/library/qwen3/manifests/" + tag
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(1024 ** 2)
    if hashlib.sha256(raw).hexdigest() != model.digest:
        raise SetupError("The model tag no longer matches the reviewed download manifest. No model was pulled; update/review the installer catalogue rather than silently downloading a different model.")


def prepare_model(binary, root, selection, ui):
    env = model_environment(root)
    if isinstance(selection, Model):
        tag = selection.tag
        run_command([binary, "pull", tag], ui, "Downloading " + tag + " into models/ollama", env=env)
        expected = selection.digest
    elif selection.kind == "gguf":
        ui.status("Hashing the selected local GGUF...")
        with selection.path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        tag = "docs-radar-local-" + digest[:16] + ":latest"
        with tempfile.TemporaryDirectory(prefix="docs-radar-import-") as temporary:
            modelfile = Path(temporary) / "Modelfile"
            source = selection.path.resolve().as_posix()
            if any(ord(char) < 32 for char in source):
                raise SetupError("Control characters in a GGUF filename are not supported.")
            modelfile.write_text("FROM " + json.dumps(source, ensure_ascii=False) + f"\nPARAMETER num_ctx {CONTEXT_TOKENS}\n", encoding="utf-8")
            run_command([binary, "create", tag, "-f", modelfile], ui, "Importing existing GGUF (no model download)", env=env)
        expected = None
    else:
        tag = selection.name
        expected = hashlib.sha256(selection.path.read_bytes()).hexdigest()
    entries = local_json("/api/tags").get("models", [])
    record = next((item for item in entries if item.get("name") == tag), None)
    if not record or not re.fullmatch(r"[a-f0-9]{64}", str(record.get("digest", ""))) or (expected and record.get("digest") != expected):
        raise SetupError("Installed model was not found or its manifest digest did not match. Setup is not complete.")
    return tag, record["digest"]


def check_space(root, hardware, selection):
    required = 3 * GIB  # Conservative Python environment / dependency allowance.
    locations = [root]
    if selection:
        if not cached_runtime(hardware):
            required += ASSETS[(hardware.system, hardware.architecture)][1] * 5
            locations.extend([runtime_directory(hardware), Path(tempfile.gettempdir())])
        if isinstance(selection, Model):
            required += selection.download_bytes * 2
        elif selection.kind == "gguf":
            required += selection.size * 2
    # Deliberately conservative for split-volume installs: each destination must
    # accommodate the combined budget, rather than undercount shared volumes.
    for location in locations:
        if available_disk(location) < required:
            raise SetupError(f"Insufficient free disk near {location}: need a conservative {required / GIB:.1f} GiB for setup, temporary files and model storage.")
