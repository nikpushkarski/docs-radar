"""Offline installer tests: never download models/packages or execute native runtimes."""

from contextlib import contextmanager, ExitStack
from dataclasses import replace
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

from scripts import setup_local as app
from scripts import setup_support as support
from scripts import setup_tui
from scripts.setup_tui import Cancelled, TerminalUI, safe_text


WINDOWS = support.Hardware("Windows", "amd64", "10.0.26200", 64 * support.GIB,
                           32 * support.GIB, "NVIDIA test GPU", 6 * support.GIB,
                           100 * support.GIB)


class FakeUI:
    def __init__(self, choices=(), consent=True):
        self.choices = iter(choices)
        self.consent = consent
        self.events = []

    def page(self, *text):
        self.events.append(("page", text))

    def text(self, text):
        self.events.append(("text", text))

    def table(self, headers, rows):
        self.events.append(("table", (headers, rows)))

    def choose(self, question, options):
        self.events.append(("choose", (question, options)))
        return next(self.choices)

    def confirm(self):
        self.events.append(("confirm", self.consent))
        return self.consent

    def draw(self, *text):
        self.events.append(("draw", text))

    def status(self, text):
        self.events.append(("status", text))


def gguf(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"GGUF" + struct.pack("<IQQ", 3, 1, 0))
    return path


def manifest(directory, missing=False):
    data = b"synthetic blob, not a model"
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    record = {"digest": digest, "size": len(data), "mediaType": "application/vnd.ollama.image.model"}
    blob = directory / "ollama" / "blobs" / digest.replace(":", "-")
    blob.parent.mkdir(parents=True, exist_ok=True)
    if not missing:
        blob.write_bytes(data)
    target = directory / "ollama" / "manifests" / "registry.ollama.ai" / "library" / "test-model" / "latest"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"config": record, "layers": [record]}), encoding="utf-8")
    return target


class HardwareTests(unittest.TestCase):
    def test_current_windows_class_uses_4b_not_8b(self):
        self.assertEqual(support.recommend_model(WINDOWS).tag, "qwen3:4b")

    def test_larger_gpu_does_not_raise_model_ceiling(self):
        self.assertEqual(support.recommend_model(replace(WINDOWS, free_vram=24 * support.GIB)).tag, "qwen3:4b")
        self.assertTrue(all(model.download_bytes <= support.MAX_MODEL_BYTES for model in support.MODELS))

    def test_cpu_caps_model_size(self):
        self.assertEqual(support.recommend_model(replace(WINDOWS, free_vram=0)).tag, "qwen3:4b")

    def test_apple_silicon_uses_unified_available_memory(self):
        mac = replace(WINDOWS, system="Darwin", architecture="arm64", os_version="14.5", free_vram=0,
                      available_ram=6 * support.GIB)
        self.assertEqual(support.recommend_model(mac).tag, "qwen3:1.7b")

    def test_intel_mac_stays_cpu_only(self):
        mac = replace(WINDOWS, system="Darwin", os_version="15.0", free_vram=0)
        self.assertEqual(support.recommend_model(mac).tag, "qwen3:4b")

    def test_small_memory_uses_small_model(self):
        self.assertEqual(support.recommend_model(replace(WINDOWS, free_vram=0, available_ram=4 * support.GIB)).tag,
                         "qwen3:0.6b")

    def test_unknown_or_insufficient_resources_do_not_guess(self):
        for hardware in (replace(WINDOWS, available_ram=0), replace(WINDOWS, available_ram=support.GIB),
                         replace(WINDOWS, free_disk=support.GIB), replace(WINDOWS, architecture="unknown")):
            with self.subTest(hardware=hardware):
                self.assertIsNone(support.recommend_model(hardware))

    def test_unsupported_os_versions(self):
        for hardware in (replace(WINDOWS, os_version="10.0.18000"),
                         replace(WINDOWS, system="Darwin", os_version="13.6"),
                         replace(WINDOWS, system="Darwin", os_version="unknown")):
            self.assertFalse(support.supported_runtime(hardware))

    def test_vm_stat_page_size_is_not_assumed(self):
        text = "Mach Virtual Memory Statistics: (page size of 16384 bytes)\nPages free: 10.\nPages inactive: 20.\nPages speculative: 3.\nPages wired down: 999."
        self.assertEqual(support.parse_vm_stat(text), 33 * 16384)
        self.assertEqual(support.parse_vm_stat("unavailable"), 0)

    def test_macos_probe_recognizes_rosetta_and_memory(self):
        answers = {("sysctl", "-n", "hw.optional.arm64"): "1",
                   ("sysctl", "-n", "hw.memsize"): str(16 * support.GIB),
                   ("vm_stat",): "page size of 4096 bytes\nPages free: 100.\nPages inactive: 200."}
        with patch.object(support.platform, "system", return_value="Darwin"), \
             patch.object(support.platform, "machine", return_value="x86_64"), \
             patch.object(support.platform, "mac_ver", return_value=("14.5", (), "")), \
             patch.object(support, "command_text", side_effect=lambda args: answers[tuple(args)]), \
             patch.object(support, "available_disk", return_value=100 * support.GIB):
            found = support.detect_hardware()
        self.assertEqual(found.architecture, "arm64")
        self.assertEqual(found.available_ram, 300 * 4096)

    def test_catalogue_has_pinned_https_archives(self):
        for name, size, digest in support.ASSETS.values():
            self.assertGreater(size, 0)
            self.assertRegex(digest, r"^[a-f0-9]{64}$")
            self.assertTrue(name.endswith((".tgz", ".zip")))
        for model in support.MODELS:
            self.assertRegex(model.digest, r"^[a-f0-9]{64}$")
            self.assertTrue(model.manual_source.startswith("https://huggingface.co/Qwen/"))


class ModelDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_absent_directory_is_empty(self):
        self.assertEqual(support.inspect_models(self.root / "absent"), [])

    def test_gguf_detection_accepts_uppercase_suffix(self):
        gguf(self.root / "Local Model.GGUF")
        found = support.inspect_models(self.root)
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].usable)
        self.assertIn("not yet tested", found[0].note)

    def test_oversized_gguf_and_cache_are_listed_but_not_offered_or_deleted(self):
        path = gguf(self.root / "too-large.gguf")
        cached = manifest(self.root)
        with patch.object(support, "MAX_MODEL_BYTES", 1):
            found = support.inspect_models(self.root)
        self.assertEqual(len(found), 2)
        self.assertTrue(all(not item.usable and "lightweight limit" in item.note for item in found))
        self.assertTrue(path.exists())
        self.assertTrue(cached.exists())

    def test_partial_bad_header_split_and_unsupported_files_are_not_reused(self):
        (self.root / "broken.gguf").write_bytes(b"GGUF")
        gguf(self.root / "split-00001-of-00002.gguf")
        (self.root / "weights.safetensors").write_bytes(b"fixture")
        found = support.inspect_models(self.root)
        self.assertEqual(len(found), 3)
        self.assertTrue(all(not model.usable for model in found))

    def test_complete_local_cache_is_found(self):
        manifest(self.root)
        found = support.inspect_models(self.root)
        self.assertEqual(found[0].name, "test-model:latest")
        self.assertTrue(found[0].usable)

    def test_missing_cache_blob_is_reported_not_reused(self):
        manifest(self.root, missing=True)
        found = support.inspect_models(self.root)
        self.assertFalse(found[0].usable)
        self.assertIn("Incomplete", found[0].note)

    def test_remote_only_manifest_is_not_a_local_model(self):
        target = manifest(self.root)
        target.write_text(json.dumps({"layers": []}), encoding="utf-8")
        self.assertFalse(support.inspect_models(self.root)[0].usable)

    def test_malformed_manifest_is_reported(self):
        target = manifest(self.root)
        target.write_text('{"layers": ["wrong type"]}', encoding="utf-8")
        self.assertFalse(support.inspect_models(self.root)[0].usable)


class TerminalTests(unittest.TestCase):
    def test_enter_is_yes(self):
        ui = TerminalUI(key_reader=lambda: "enter", output=io.StringIO())
        self.assertTrue(ui.confirm())
        self.assertIn("[Y/n]", ui.output.getvalue())

    def test_no_is_no(self):
        ui = TerminalUI(key_reader=lambda: "n", output=io.StringIO())
        self.assertFalse(ui.confirm())

    def test_arrows_and_enter_select_existing_model(self):
        keys = iter(["down", "down", "up", "enter"])
        ui = TerminalUI(key_reader=lambda: next(keys), output=io.StringIO())
        self.assertEqual(ui.choose("Select", ["first", "second", "third"]), 1)

    def test_up_wraps_to_last_option(self):
        keys = iter(["up", "enter"])
        ui = TerminalUI(key_reader=lambda: next(keys), output=io.StringIO())
        self.assertEqual(ui.choose("Select", ["first", "second"]), 1)

    def test_cancel_does_not_assume_yes(self):
        ui = TerminalUI(key_reader=Mock(side_effect=Cancelled()), output=io.StringIO())
        with self.assertRaises(Cancelled):
            ui.confirm()

    def test_redirected_input_is_rejected(self):
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(Cancelled):
                with TerminalUI(output=io.StringIO()):
                    self.fail("must not enter")

    def test_terminal_control_codes_are_not_rendered(self):
        self.assertNotIn("\x1b", safe_text("model\x1b[2J"))

    def test_all_download_pages_precede_default_yes(self):
        reader = Mock(side_effect=["enter", "enter", "enter"])
        ui = TerminalUI(key_reader=reader, output=io.StringIO())
        ui.lines = [f"planned download {index}" for index in range(13)]
        with patch.object(setup_tui.shutil, "get_terminal_size", return_value=os.terminal_size((80, 12))):
            self.assertTrue(ui.confirm())
        self.assertEqual(reader.call_count, 3)
        self.assertIn("page 3/3", ui.output.getvalue())
        self.assertIn("planned download 12", ui.output.getvalue())

    def test_windows_arrow_key_decoder(self):
        keys = iter(["\xe0", "P"])
        with patch.object(setup_tui.os, "name", "nt"), \
             patch.dict("sys.modules", {"msvcrt": SimpleNamespace(getwch=lambda: next(keys))}):
            self.assertEqual(setup_tui.read_key(), "down")

    def test_macos_arrow_decoder_restores_terminal_mode(self):
        terminal = SimpleNamespace(tcgetattr=Mock(return_value="old-mode"),
                                   tcsetattr=Mock(), TCSADRAIN=1)
        tty = SimpleNamespace(setraw=Mock())
        with patch.object(setup_tui.os, "name", "posix"), \
             patch.dict("sys.modules", {"termios": terminal, "tty": tty}), \
             patch("sys.stdin.fileno", return_value=42), \
             patch.object(setup_tui.os, "read", side_effect=[b"\x1b", b"[", b"B"]), \
             patch.object(setup_tui.select, "select", return_value=([42], [], [])):
            self.assertEqual(setup_tui.read_key(), "down")
        terminal.tcsetattr.assert_called_once_with(42, 1, "old-mode")

    def test_macos_eof_cancels_without_accepting_default(self):
        terminal = SimpleNamespace(tcgetattr=Mock(return_value="old-mode"),
                                   tcsetattr=Mock(), TCSADRAIN=1)
        with patch.object(setup_tui.os, "name", "posix"), \
             patch.dict("sys.modules", {"termios": terminal, "tty": SimpleNamespace(setraw=Mock())}), \
             patch("sys.stdin.fileno", return_value=42), \
             patch.object(setup_tui.os, "read", return_value=b""):
            with self.assertRaises(Cancelled):
                setup_tui.read_key()
        terminal.tcsetattr.assert_called_once_with(42, 1, "old-mode")


class ConsentFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "requirements.txt").write_text("streamlit==1.66.1\n", encoding="utf-8")
        (self.root / "scripts" / "requirements-model.txt").write_text(
            "-r requirements.txt\nlangchain-ollama==1.1.0\n", encoding="utf-8")
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.operations = {}
        for name, value in {
            "detect_hardware": WINDOWS, "cached_runtime": None, "check_space": None,
            "install_python": self.root / ".venv" / "python", "install_runtime": Path("external/ollama"),
            "verify_model_reference": None, "prepare_model": ("qwen3:4b", support.MODELS[2].digest),
        }.items():
            self.operations[name] = self.stack.enter_context(patch.object(app, name, return_value=value))
        self.server_stopped = False

        @contextmanager
        def server(*args):
            (self.root / "models").mkdir(exist_ok=True)
            try:
                yield
            finally:
                self.server_stopped = True
        self.server = self.stack.enter_context(patch.object(app, "model_server", side_effect=server))

    def test_no_prints_manual_folder_and_makes_no_download_or_install_calls(self):
        ui = FakeUI([0], consent=False)
        self.assertFalse(app.setup(ui, self.root))
        for name in ("install_python", "install_runtime", "verify_model_reference", "prepare_model"):
            self.operations[name].assert_not_called()
        self.server.assert_not_called()
        self.assertTrue((self.root / "models").is_dir())
        messages = "\n".join(value for kind, value in ui.events if kind == "text")
        self.assertIn(str(self.root / "models"), messages)
        self.assertIn("single-file GGUF", messages)
        self.assertFalse((self.root / "models" / "setup.json").exists())

    def test_cancelled_confirmation_never_downloads(self):
        ui = FakeUI([0])
        ui.confirm = Mock(side_effect=Cancelled())
        with self.assertRaises(Cancelled):
            app.setup(ui, self.root)
        self.operations["install_python"].assert_not_called()
        self.operations["verify_model_reference"].assert_not_called()

    def test_plan_and_consent_precede_every_install_step(self):
        ui = FakeUI([1])
        def verify(model):
            self.assertIn(("confirm", True), ui.events)
            self.assertTrue(any(event[0] == "table" for event in ui.events))
            ui.events.append(("mutation", model.tag))
        self.operations["verify_model_reference"].side_effect = verify
        self.assertTrue(app.setup(ui, self.root))
        kinds = [event[0] for event in ui.events]
        self.assertLess(kinds.index("table"), kinds.index("confirm"))
        self.assertLess(kinds.index("confirm"), kinds.index("mutation"))
        record = json.loads((self.root / "models" / "setup.json").read_text())
        self.assertFalse(record["generation_tested"])
        self.assertEqual(record["base_url"], support.BASE_URL)
        self.assertTrue(self.server_stopped)
        self.operations["install_python"].assert_called_once_with(self.root, ui, with_model=True)
        plan = str(ui.events[:kinds.index("confirm")])
        self.assertIn("Local-model Python integration (PyPI)", plan)
        self.assertIn("langchain-ollama==1.1.0", plan)
        self.assertIn("local-model Python dependencies are installed", str(ui.events))
        self.assertNotIn("requires scripts/requirements-model.txt", str(ui.events))

    def test_model_consent_declined_never_installs_dependencies_or_weights(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                if existing:
                    gguf(self.root / "models" / "existing.gguf")
                ui = FakeUI([1], consent=False)
                self.assertFalse(app.setup(ui, self.root))
                self.assertIn("Local-model Python integration (PyPI)", str(ui.events))
                for name in ("install_python", "install_runtime", "verify_model_reference", "prepare_model"):
                    self.operations[name].assert_not_called()
                self.server.assert_not_called()

    def test_model_dependency_failure_does_not_install_runtime_or_report_success(self):
        self.operations["install_python"].side_effect = support.SetupError("dependency install failed")
        ui = FakeUI([1])
        with self.assertRaisesRegex(support.SetupError, "dependency install failed"):
            app.setup(ui, self.root)
        self.operations["install_runtime"].assert_not_called()
        self.server.assert_not_called()
        self.assertFalse((self.root / "models" / "setup.json").exists())
        self.assertNotIn("Installation complete", str(ui.events))

    def test_macos_model_setup_also_installs_integration(self):
        self.operations["detect_hardware"].return_value = replace(
            WINDOWS, system="Darwin", architecture="arm64", os_version="14.5")
        ui = FakeUI([1])
        self.assertTrue(app.setup(ui, self.root))
        self.operations["install_python"].assert_called_once_with(self.root, ui, with_model=True)

    def test_existing_gguf_can_be_selected_without_new_model_download(self):
        path = gguf(self.root / "models" / "existing.gguf")
        ui = FakeUI([1])
        with patch.object(app, "recommend_model") as recommend:
            self.assertTrue(app.setup(ui, self.root))
        recommend.assert_not_called()
        self.operations["verify_model_reference"].assert_not_called()
        selection = self.operations["prepare_model"].call_args.args[2]
        self.assertEqual(selection.path, path)
        self.assertIn("Continue with already existing existing.gguf", str(ui.events))
        self.assertTrue(path.exists())
        self.operations["install_python"].assert_called_once_with(self.root, ui, with_model=True)

    def test_existing_cache_can_be_reused(self):
        manifest(self.root / "models")
        ui = FakeUI([1])
        app.setup(ui, self.root)
        self.operations["verify_model_reference"].assert_not_called()
        self.assertEqual(self.operations["prepare_model"].call_args.args[2].kind, "ollama")
        self.operations["install_python"].assert_called_once_with(self.root, ui, with_model=True)

    def test_existing_model_can_be_bypassed_for_hardware_recommendation(self):
        path = gguf(self.root / "models" / "existing.gguf")
        app.setup(FakeUI([2, 1], consent=False), self.root)
        self.assertTrue(path.exists())
        self.operations["install_python"].assert_not_called()

    def test_default_extractive_mode_skips_every_model_operation(self):
        ui = FakeUI([0])
        self.assertTrue(app.setup(ui, self.root))
        self.operations["install_python"].assert_called_once_with(self.root, ui, with_model=False)
        self.assertNotIn("langchain-ollama", str(ui.events))
        self.assertNotIn("Local-model Python integration (PyPI)", str(ui.events))
        self.operations["install_runtime"].assert_not_called()
        self.operations["verify_model_reference"].assert_not_called()
        self.server.assert_not_called()

    def test_existing_cache_does_not_change_extractive_default(self):
        manifest(self.root / "models")
        ui = FakeUI([0])
        self.assertTrue(app.setup(ui, self.root))
        self.assertEqual(next(v[1][0] for k, v in ui.events if k == "choose"), "Install extractive app only (no model)")
        self.operations["install_runtime"].assert_not_called()
        self.server.assert_not_called()

    def test_old_macos_still_offers_python_only_setup(self):
        self.operations["detect_hardware"].return_value = replace(WINDOWS, system="Darwin", os_version="13.0")
        self.assertTrue(app.setup(FakeUI([0]), self.root))
        self.operations["install_runtime"].assert_not_called()

    def test_insufficient_disk_blocks_all_payloads(self):
        self.operations["check_space"].side_effect = support.SetupError("disk full")
        with self.assertRaises(support.SetupError):
            app.setup(FakeUI([0]), self.root)
        self.operations["install_python"].assert_not_called()
        self.operations["verify_model_reference"].assert_not_called()

    def test_changed_model_tag_blocks_package_and_runtime_downloads(self):
        self.operations["verify_model_reference"].side_effect = support.SetupError("manifest changed")
        with self.assertRaises(support.SetupError):
            app.setup(FakeUI([1]), self.root)
        self.operations["install_python"].assert_not_called()
        self.operations["install_runtime"].assert_not_called()

    def test_serve_uses_known_local_runtime_not_recorded_external_urls(self):
        target = manifest(self.root / "models")
        record = {"platform": "Windows", "model": "test-model:latest",
                  "model_digest": hashlib.sha256(target.read_bytes()).hexdigest(),
                  "base_url": "https://remote.invalid", "ollama_binary": "untrusted-executable"}
        (self.root / "models" / "setup.json").write_text(json.dumps(record), encoding="utf-8")
        self.operations["cached_runtime"].return_value = Path("known-runtime/ollama")
        app.serve(FakeUI([0]), self.root)
        self.assertEqual(self.server.call_args.args[0], Path("known-runtime/ollama"))
        self.assertTrue(self.server_stopped)

    def test_changed_cached_model_does_not_start_server(self):
        manifest(self.root / "models")
        record = {"platform": "Windows", "model": "test-model:latest", "model_digest": "wrong"}
        (self.root / "models" / "setup.json").write_text(json.dumps(record), encoding="utf-8")
        self.operations["cached_runtime"].return_value = Path("known-runtime/ollama")
        with self.assertRaises(support.SetupError):
            app.serve(FakeUI([0]), self.root)
        self.server.assert_not_called()

    def test_failed_model_setup_stops_server_and_does_not_mark_success(self):
        self.operations["prepare_model"].side_effect = support.SetupError("pull failed")
        with self.assertRaises(support.SetupError):
            app.setup(FakeUI([1]), self.root)
        self.assertTrue(self.server_stopped)
        self.assertFalse((self.root / "models" / "setup.json").exists())


class MutationSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_valid_archive_checksum_and_size(self):
        payload = b"tiny synthetic archive"
        response = io.BytesIO(payload)
        response.geturl = lambda: "https://github.com/ollama/ollama/synthetic"
        target = self.root / "file.zip"
        with patch.object(support.urllib.request, "urlopen", return_value=response):
            support.download_archive("https://example.invalid/fixture", target, len(payload),
                                     hashlib.sha256(payload).hexdigest(), FakeUI())
        self.assertEqual(target.read_bytes(), payload)

    def test_bad_checksum_is_rejected_before_extraction(self):
        response = io.BytesIO(b"bad")
        response.geturl = lambda: "https://github.com/ollama/ollama/synthetic"
        with patch.object(support.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(support.SetupError):
                support.download_archive("https://example.invalid", self.root / "file.zip", 3, "0" * 64, FakeUI())

    def test_zip_path_traversal_is_rejected(self):
        archive = self.root / "bad.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("../escape.txt", b"fixture")
        with self.assertRaises(support.SetupError):
            support.extract_archive(archive, self.root / "unpack")
        self.assertFalse((self.root / "escape.txt").exists())

    def test_windows_absolute_paths_are_rejected_on_both_os_backends(self):
        for name in ("C:/escape", "C:\\escape", "\\\\server\\share", "/escape", "a/../../escape"):
            self.assertFalse(support.safe_member(name), name)

    def test_valid_zip_is_extracted(self):
        archive = self.root / "good.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("ollama.exe", b"synthetic, not executable")
        support.extract_archive(archive, self.root / "unpack")
        self.assertTrue((self.root / "unpack" / "ollama.exe").is_file())

    def test_tar_path_traversal_is_rejected(self):
        archive = self.root / "bad.tgz"
        with tarfile.open(archive, "w:gz") as output:
            member = tarfile.TarInfo("../escape")
            output.addfile(member)
        with self.assertRaises(support.SetupError):
            support.extract_archive(archive, self.root / "unpack")

    def test_valid_macos_tar_is_extracted(self):
        archive = self.root / "good.tgz"
        with tarfile.open(archive, "w:gz") as output:
            member = tarfile.TarInfo("ollama")
            member.mode = 0o755
            output.addfile(member)
        support.extract_archive(archive, self.root / "unpack")
        self.assertEqual(support.runtime_binary(self.root / "unpack", "Darwin"), self.root / "unpack" / "ollama")

    def test_model_environment_is_local_only_and_does_not_mutate_parent(self):
        with patch.dict(os.environ, {"OLLAMA_HOST": "https://remote.invalid", "OLLAMA_NO_CLOUD": "0"}):
            env = support.model_environment(self.root)
            self.assertEqual(env["OLLAMA_HOST"], "127.0.0.1:11435")
            self.assertEqual(env["OLLAMA_NO_CLOUD"], "1")
            self.assertEqual(env["OLLAMA_MODELS"], str(self.root / "models" / "ollama"))
            self.assertEqual(env["OLLAMA_CONTEXT_LENGTH"], "2048")
            self.assertEqual(env["OLLAMA_NUM_PARALLEL"], "1")
            self.assertEqual(env["OLLAMA_MAX_LOADED_MODELS"], "1")
            self.assertEqual(env["OLLAMA_MAX_QUEUE"], "1")
            self.assertEqual(env["OLLAMA_KEEP_ALIVE"], "0")
            self.assertEqual(os.environ["OLLAMA_HOST"], "https://remote.invalid")

    def test_occupied_port_does_not_start_or_control_another_server(self):
        connection = Mock()
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=False)
        with patch.object(support.socket, "create_connection", return_value=connection), \
             patch.object(support.subprocess, "Popen") as start:
            with self.assertRaises(support.SetupError):
                with support.model_server(Path("ollama"), self.root, FakeUI()):
                    self.fail("must not enter")
        start.assert_not_called()

    def test_server_is_stopped_when_setup_body_fails(self):
        process = Mock()
        process.poll.return_value = None
        with patch.object(support.socket, "create_connection", side_effect=ConnectionRefusedError), \
             patch.object(support.subprocess, "Popen", return_value=process), \
             patch.object(support, "local_json", return_value={"version": support.OLLAMA_VERSION}):
            with self.assertRaises(support.SetupError):
                with support.model_server(Path("ollama"), self.root, FakeUI()):
                    raise support.SetupError("fixture failure")
        process.terminate.assert_called_once()
        process.wait.assert_called_once()

    def test_registry_manifest_change_is_rejected(self):
        with patch.object(support.urllib.request, "urlopen", return_value=io.BytesIO(b"changed manifest")):
            with self.assertRaises(support.SetupError):
                support.verify_model_reference(support.MODELS[2])

    def test_existing_cache_does_not_invoke_pull(self):
        target = manifest(self.root / "models")
        item = support.inspect_models(self.root / "models")[0]
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        with patch.object(support, "run_command") as run, \
             patch.object(support, "local_json", return_value={"models": [{"name": item.name, "digest": digest}]}):
            result = support.prepare_model(Path("ollama"), self.root, item, FakeUI())
        self.assertEqual(result, (item.name, digest))
        run.assert_not_called()

    def test_gguf_import_uses_create_not_pull_with_spaces_and_unicode(self):
        gguf(self.root / "models" / "local modèle.gguf")
        item = support.inspect_models(self.root / "models")[0]
        seen = []
        def run(args, *unused, **kwargs):
            seen.append(args)
            text = Path(args[-1]).read_text(encoding="utf-8")
            self.assertIn(json.dumps(item.path.resolve().as_posix(), ensure_ascii=False), text)
            self.assertEqual(kwargs["env"]["OLLAMA_NO_CLOUD"], "1")
        def tags(path):
            return {"models": [{"name": seen[0][2], "digest": "a" * 64}]}
        with patch.object(support, "run_command", side_effect=run), patch.object(support, "local_json", side_effect=tags):
            support.prepare_model(Path("ollama"), self.root, item, FakeUI())
        self.assertEqual(seen[0][1], "create")
        self.assertNotIn("pull", seen[0])

    def test_pinned_runtime_installs_once_and_reuses_verified_cache(self):
        source = self.root / "source.zip"
        with zipfile.ZipFile(source, "w") as output:
            output.writestr("ollama.exe", b"synthetic executable, never launched")
        payload = source.read_bytes()
        response = io.BytesIO(payload)
        response.geturl = lambda: "https://github.com/ollama/ollama/synthetic"
        asset = ("fixture.zip", len(payload), hashlib.sha256(payload).hexdigest())
        destination = self.root / "runtime"
        with patch.dict(support.ASSETS, {("Windows", "amd64"): asset}), \
             patch.object(support, "runtime_directory", return_value=destination), \
             patch.object(support.urllib.request, "urlopen", return_value=response) as network:
            first = support.install_runtime(WINDOWS, FakeUI())
            second = support.install_runtime(WINDOWS, FakeUI())
            self.assertEqual(first, second)
            self.assertEqual(first.read_bytes(), b"synthetic executable, never launched")
            network.assert_called_once()

    def test_unverified_existing_runtime_is_never_overwritten(self):
        destination = self.root / "runtime"
        destination.mkdir()
        sentinel = destination / "keep.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        with patch.object(support, "runtime_directory", return_value=destination), \
             patch.object(support, "download_archive") as download:
            with self.assertRaises(support.SetupError):
                support.install_runtime(WINDOWS, FakeUI())
        download.assert_not_called()
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_python_installs_use_project_environment_and_pypi(self):
        environment = self.root / ".venv"
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python.parent.mkdir(parents=True)
        python.write_bytes(b"fixture, never launched")
        with patch.object(support, "run_command") as run:
            result = support.install_python(self.root, FakeUI())
        self.assertEqual(result, python)
        commands = [call.args[0] for call in run.call_args_list]
        self.assertTrue(all(command[0] == python for command in commands))
        install = next(command for command in commands if "install" in command)
        self.assertIn("--isolated", install)
        self.assertIn("https://pypi.org/simple", install)
        self.assertEqual(install[-1], self.root / "scripts" / "requirements.txt")

    def test_model_python_install_uses_combined_requirements_and_visible_progress(self):
        python = self.root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python.parent.mkdir(parents=True)
        python.write_bytes(b"fixture, never launched")
        ui = TerminalUI(output=io.StringIO())
        process = Mock()
        process.poll.return_value = 0
        process.returncode = 0
        with patch.object(support.subprocess, "Popen", return_value=process) as start:
            self.assertEqual(support.install_python(self.root, ui, with_model=True), python)
        commands = [call.args[0] for call in start.call_args_list]
        self.assertTrue(all(command[0] == str(python) for command in commands))
        installs = [command for command in commands if "install" in command]
        self.assertEqual(len(installs), 1)
        self.assertEqual(installs[0][-1], str(self.root / "scripts" / "requirements-model.txt"))
        self.assertIn("--isolated", installs[0])
        self.assertIn("https://pypi.org/simple", installs[0])
        self.assertIn([str(python), "-m", "pip", "check"], commands)
        self.assertIn([str(python), "-c", "from langchain_ollama import ChatOllama"], commands)
        progress = ui.output.getvalue()
        self.assertIn("Installing app + local-model Python dependencies from PyPI", progress)
        self.assertIn("Checking local-model integration import", progress)

    def test_failed_model_integration_import_is_not_reported_as_installed(self):
        python = self.root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        python.parent.mkdir(parents=True)
        python.write_bytes(b"fixture, never launched")
        with patch.object(support, "run_command", side_effect=[None, None, None, None,
                          support.SetupError("integration import failed")]):
            with self.assertRaisesRegex(support.SetupError, "integration import failed"):
                support.install_python(self.root, FakeUI(), with_model=True)

    def test_cancellation_stops_active_package_process(self):
        ui = FakeUI()
        ui.status = Mock(side_effect=[None, Cancelled()])
        process = Mock()
        process.poll.return_value = None
        with patch.object(support.subprocess, "Popen", return_value=process):
            with self.assertRaises(Cancelled):
                support.run_command(["not-executed"], ui, "fixture")
        process.terminate.assert_called_once()

    def test_wrong_os_virtualenv_is_not_overwritten(self):
        environment = self.root / ".venv"
        environment.mkdir()
        sentinel = environment / "keep.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        with patch.object(support, "run_command") as run:
            with self.assertRaises(support.SetupError):
                support.install_python(self.root, FakeUI())
        run.assert_not_called()
        self.assertEqual(sentinel.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
