"""Interactive Windows/macOS bootstrap. Requires Python 3.11.8+; no UI packages.

Run from the repository: py -m scripts.setup_local (Windows) or python3 -m scripts.setup_local (macOS).
Run with --serve to start the previously installed project model server.
"""

import hashlib
import json
import sys
import subprocess
import tarfile
import tempfile
import zipfile

from scripts.setup_support import (
    ASSETS, BASE_URL, GIB, OLLAMA_VERSION, ROOT, LocalModel, Model, SetupError,
    cached_runtime, check_space, detect_hardware, inspect_models, install_python,
    install_runtime, model_server, prepare_model, recommend_model, runtime_directory,
    supported_runtime, verify_model_reference,
)
from scripts.setup_tui import Cancelled, TerminalUI


def hardware_summary(hardware):
    return (f"{hardware.system} {hardware.os_version} / {hardware.architecture} | "
            f"RAM {hardware.available_ram / GIB:.1f} GiB available of {hardware.total_ram / GIB:.1f} | "
            f"VRAM {hardware.free_vram / GIB:.1f} GiB free | disk {hardware.free_disk / GIB:.1f} GiB free\n"
            f"Accelerator: {hardware.gpu}")


def choose_model(ui, root, hardware):
    found = inspect_models(root / "models")
    if found:
        ui.page("Existing models", f"Found in {root / 'models'}:")
        ui.table(("Model", "Format", "Status"), [(item.name, item.kind, item.note) for item in found])
        usable = [item for item in found if item.usable]
        options = ["Continue with already existing " + item.name for item in usable]
        options += ["Analyze hardware to suggest a new download", "Install extractive app only (no model)"]
        choice = ui.choose("Use an existing model or analyze hardware?", options)
        if choice < len(usable):
            return usable[choice]
        if choice == len(usable) + 1:
            return None
    recommendation = recommend_model(hardware, runtime_missing=not bool(cached_runtime(hardware)))
    ui.page("Hardware analysis", hardware_summary(hardware), hardware.notes)
    if recommendation:
        ui.text(f"Recommended: {recommendation.tag} (Apache 2.0), with a 4096-token context. "
                "This is a conservative memory/disk heuristic, not a performance or answer-quality benchmark. "
                "CPU recommendations are capped at 4B for latency; smaller models may give weaker answers.")
        selection = ui.choose("Choose setup mode", ["Continue with " + recommendation.tag,
                                                   "Install extractive app only (no model)"])
        return recommendation if selection == 0 else None
    ui.text("No safe automatic model recommendation: OS support, measured memory or available disk is insufficient/unknown. "
            "You can still install the Python extractive app; no model or paid fallback is required.")
    ui.choose("Continue?", ["Install extractive app only (no model)"])
    return None


def show_plan(ui, root, hardware, selection):
    ui.page("Recommended downloads for your machine configuration", hardware_summary(hardware), f"Project: {root}")
    requirements = [line.strip() for line in (root / "scripts" / "requirements.txt").read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
    rows = [("Python requirements + dependencies (PyPI)", "Size varies; existing packages reused", ".venv/ in project")]
    if selection:
        if cached_runtime(hardware):
            rows.append(("Ollama " + OLLAMA_VERSION, "Already installed; no runtime download", str(runtime_directory(hardware))))
        else:
            name, size, _ = ASSETS[(hardware.system, hardware.architecture)]
            rows.append(("Ollama " + OLLAMA_VERSION + " / " + name, f"{size / 1e9:.2f} GB; MIT", str(runtime_directory(hardware))))
        if isinstance(selection, Model):
            rows.append((selection.tag, f"{selection.download_bytes / 1e9:.2f} GB; Apache 2.0", "models/ollama/ in project"))
        else:
            rows.append((selection.name, "Existing model; no model download", "models/ollama/ (GGUF imports may copy weights)"))
    ui.table(("Download / reuse", "Transfer / licence", "Destination"), rows)
    ui.text("Python requirements: " + ", ".join(requirements))
    if selection:
        ui.text("Official sources: github.com/ollama/ollama (pinned standalone archive); registry.ollama.ai (model). "
                f"Archive staging: {tempfile.gettempdir()} (removed after use).")
        ui.text("No administrator access, global PATH edits or cloud service. Models stay Git-ignored. "
                "The isolated server uses 127.0.0.1:11435 and is stopped when setup ends.")
    ui.text("Yes authorizes the listed package downloads and local installation; existing model selection does not download new weights.")


def decline(ui, root, selection):
    directory = root / "models"
    directory.mkdir(parents=True, exist_ok=True)
    ui.page("No downloads started", "Thank you — nothing will be downloaded or installed.")
    if isinstance(selection, LocalModel):
        ui.text("Your existing model was left unchanged. Rerun when you are ready to install any missing Python/Ollama dependencies.")
    else:
        ui.text("To finish local-model setup manually, please download a compatible, complete single-file GGUF from a trusted publisher, "
                f"put it directly in {directory}, then rerun this script. "
                "Setup will offer to reuse it and will still ask before downloading missing runtime dependencies.")
        if isinstance(selection, Model):
            ui.text("Suggested publisher page: " + selection.manual_source)
        ui.text("Use a single-file GGUF, not a split/sharded model, Safetensors folder or partial download. "
                "The extractive app can also be installed without a model.")
    ui.draw()


def setup(ui, root=ROOT):
    if any(path.is_symlink() for path in (root / "models", root / "models" / "ollama", root / ".venv")):
        raise SetupError("models/, models/ollama/ and .venv/ must be local project directories, not symlinks to unrelated installations.")
    hardware = detect_hardware(root)
    if hardware.system not in ("Windows", "Darwin"):
        raise SetupError("This installer targets Windows and macOS; use the manual Python setup on other systems.")
    selection = choose_model(ui, root, hardware)
    if selection and not supported_runtime(hardware):
        raise SetupError("This OS/architecture cannot run the supported Ollama archive. Use extractive-only setup instead.")
    show_plan(ui, root, hardware, selection)
    if not ui.confirm():
        decline(ui, root, selection)
        return False
    # All network/package/model mutations live below the explicit consent gate.
    check_space(root, hardware, selection)
    ui.page("Installing the approved downloads", "Ctrl+C cancels. Completed files are kept for reruns; existing models are never deleted.")
    if isinstance(selection, Model):
        verify_model_reference(selection)
    python = install_python(root, ui)
    if selection:
        binary = install_runtime(hardware, ui)
        with model_server(binary, root, ui):
            tag, digest = prepare_model(binary, root, selection, ui)
        record = {
            "schema_version": 1, "platform": hardware.system,
            "ollama_version": OLLAMA_VERSION, "ollama_binary": str(binary),
            "model": tag, "model_digest": digest, "context_tokens": 4096,
            "base_url": BASE_URL, "model_directory": str(root / "models" / "ollama"),
            "generation_tested": False,
        }
        target = root / "models" / "setup.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
    ui.page("Installation complete", f"Python environment: {python}",
            "The Streamlit app still displays extractive evidence; local generation is not integrated yet.",
            "Activate .venv and run from the repository: python -m streamlit run docs_radar/app.py")
    if selection:
        ui.text(f"Model installed: {tag}\nDigest: {digest}\nGeneration has NOT been smoke-tested. "
                "Start its local-only server with: python -m scripts.setup_local --serve\n"
                "The setup server has been stopped; no background service was installed.")
    ui.draw()
    return True


def serve(ui, root=ROOT):
    hardware = detect_hardware(root)
    record = json.loads((root / "models" / "setup.json").read_text(encoding="utf-8"))
    binary = cached_runtime(hardware)
    if not binary or not isinstance(record, dict) or record.get("platform") != hardware.system:
        raise SetupError("No verified runtime for this OS. Rerun setup; do not copy native installations between operating systems.")
    models = inspect_models(root / "models")
    selected = next((item for item in models if item.kind == "ollama" and item.usable and item.name == record.get("model")), None)
    if not selected or hashlib.sha256(selected.path.read_bytes()).hexdigest() != record.get("model_digest"):
        raise SetupError("The configured local model is missing, incomplete or changed. Rerun setup to select or import a model.")
    ui.page("Project model server", f"Model: {record['model']}\nLocal API: {BASE_URL}\nCloud disabled; context: 4096 tokens.",
            "This does not enable generated answers in the current Streamlit app. "
            "Keep this terminal open for local API experiments; stopping it terminates only this server.")
    with model_server(binary, root, ui):
        ui.choose("Server ready", ["Stop the project model server and exit"])
    ui.text("Project model server stopped.")
    ui.draw()


def main():
    try:
        with TerminalUI() as ui:
            try:
                if sys.version_info < (3, 11, 8):
                    raise SetupError("Install Python 3.11.8+ first (python.org), then rerun. Python itself is the bootstrap prerequisite.")
                if sys.argv[1:] == ["--serve"]:
                    serve(ui)
                elif not sys.argv[1:]:
                    setup(ui)
                else:
                    raise SetupError("Run python -m scripts.setup_local from the repository, without arguments or with --serve.")
                return 0
            except (Cancelled, KeyboardInterrupt):
                ui.page("Cancelled", "Active child processes have been stopped. Existing models were not deleted; rerun to resume setup.")
                ui.draw()
                return 130
            except (SetupError, OSError, ValueError, tarfile.TarError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
                ui.page("Setup did not complete", str(error), "No hosted fallback was attempted. Correct the issue and rerun.")
                ui.draw()
                return 1
    except Cancelled as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
