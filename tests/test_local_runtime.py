"""Offline lifecycle tests; never start a real model server or download anything."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, ExitStack
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from docs_radar import local_runtime as runtime
from scripts import setup_support as support
from tests.test_setup import WINDOWS, manifest


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "models").mkdir()
        (self.root / "models/setup.json").write_text("{}", encoding="utf-8")
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.config = self.stack.enter_context(patch.object(runtime, "configured_model", return_value=(Path("verified/ollama"), "test:latest")))
        self.integration = self.stack.enter_context(patch.object(runtime, "check_integration"))
        self.process = Mock()
        self.process.poll.return_value = None
        self.stops = 0

        @contextmanager
        def server(*args):
            try:
                yield self.process
            finally:
                self.stops += 1

        self.spawn = self.stack.enter_context(patch.object(runtime, "model_server", side_effect=server))
        self.owner = runtime.AppModelServer(self.root)
        self.addCleanup(self.owner.close)

    def test_no_setup_record_starts_nothing_and_needs_no_optional_packages(self):
        (self.root / "models/setup.json").unlink()
        self.assertEqual(self.owner.start(), runtime.RuntimeStatus())
        self.config.assert_not_called()
        self.integration.assert_not_called()
        self.spawn.assert_not_called()

    def test_start_is_shared_across_reruns_and_concurrent_tabs(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses = list(pool.map(lambda _: self.owner.start(), range(12)))
        self.assertTrue(all(s == runtime.RuntimeStatus(model="test:latest") for s in statuses))
        self.spawn.assert_called_once()
        self.integration.assert_called_once()
        self.assertEqual(self.spawn.call_args.args[:2], (Path("verified/ollama"), self.root))
        self.owner.close()
        self.owner.close()
        self.assertEqual(self.stops, 1)

    def test_registry_reuses_owner_and_registers_one_exit_cleanup(self):
        with patch.object(runtime, "_servers", {}), patch.object(runtime.atexit, "register") as register:
            first = runtime.app_model_server(self.root)
            self.assertIs(first, runtime.app_model_server(self.root / "."))
            register.assert_called_once_with(first.close)
            first.start()
            register.call_args.args[0]()
        self.assertEqual(self.stops, 1)

    def test_missing_optional_dependencies_leaves_extractive_available(self):
        self.integration.side_effect = ImportError("not installed")
        result = self.owner.start()
        self.assertIn("dependencies are missing", result.error)
        self.assertFalse(result.model)
        self.spawn.assert_not_called()

    def test_invalid_model_does_not_start_server(self):
        self.config.side_effect = support.SetupError("invalid selection")
        self.assertIn("invalid selection", self.owner.start().error)
        self.integration.assert_not_called()
        self.spawn.assert_not_called()

    def test_startup_failure_is_cached_until_explicit_retry(self):
        self.spawn.side_effect = support.SetupError("Port 11435 is already in use")
        first = self.owner.start()
        self.assertIn("already in use", first.error)
        self.assertEqual(first, self.owner.start())
        self.spawn.assert_called_once()
        self.owner.close()
        self.assertEqual(self.stops, 0)  # No ownership of the other listener.
        self.owner.start(retry=True)
        self.assertEqual(self.spawn.call_count, 2)

    def test_explicit_retry_recovers_missing_integration(self):
        self.integration.side_effect = ImportError()
        self.assertTrue(self.owner.start().error)
        self.integration.side_effect = None
        self.assertEqual(self.owner.start(retry=True).model, "test:latest")
        self.assertEqual(self.owner.start(retry=True).model, "test:latest")
        self.spawn.assert_called_once()

    def test_child_exit_is_reported_and_explicit_retry_restarts_it(self):
        self.owner.start()
        self.process.poll.return_value = 1
        self.assertIn("server stopped", self.owner.start().error)
        self.assertEqual(self.stops, 1)
        self.process.poll.return_value = None
        self.assertEqual(self.owner.start(retry=True).model, "test:latest")
        self.assertEqual(self.spawn.call_count, 2)


class ConfiguredModelTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        target = manifest(self.root / "models")
        import hashlib
        self.record = {"platform": "Windows", "model": "test-model:latest",
                       "model_digest": hashlib.sha256(target.read_bytes()).hexdigest(),
                       "ollama_binary": "untrusted.exe", "base_url": "https://remote.invalid"}
        self.target = self.root / "models/setup.json"
        self.save()
        for name, value in (("detect_hardware", WINDOWS), ("cached_runtime", Path("verified/ollama"))):
            patcher = patch.object(support, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def save(self):
        self.target.write_text(json.dumps(self.record), encoding="utf-8")

    def test_only_verified_binary_and_local_tag_are_used(self):
        self.assertEqual(support.configured_model(self.root), (Path("verified/ollama"), "test-model:latest"))

    def test_wrong_os_or_changed_digest_is_rejected(self):
        for key, value in (("platform", "Darwin"), ("model_digest", "wrong")):
            with self.subTest(key=key):
                previous = self.record[key]
                self.record[key] = value
                self.save()
                with self.assertRaises(support.SetupError):
                    support.configured_model(self.root)
                self.record[key] = previous

    def test_corrupt_record_is_rejected(self):
        for value in ("[]", "{bad json"):
            self.target.write_text(value, encoding="utf-8")
            with self.assertRaises((support.SetupError, ValueError)):
                support.configured_model(self.root)

    def test_missing_weights_are_rejected(self):
        next((self.root / "models/ollama/blobs").iterdir()).unlink()
        with self.assertRaisesRegex(support.SetupError, "missing, incomplete or changed"):
            support.configured_model(self.root)


if __name__ == "__main__":
    unittest.main()
