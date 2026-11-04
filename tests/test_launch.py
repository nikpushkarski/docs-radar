"""Offline setup-to-app handoff checks on both OS command paths."""

from contextlib import contextmanager
from pathlib import Path
import signal
import unittest
from unittest.mock import Mock, patch

from scripts import setup_local as setup
from scripts.setup_tui import Cancelled
from tests.test_setup import FakeUI


class LaunchTests(unittest.TestCase):
    def test_launch_prompt_requires_explicit_yes_and_cancellation_preserves_install(self):
        self.assertFalse(setup.offer_launch(FakeUI([0])))
        self.assertTrue(setup.offer_launch(FakeUI([1])))
        for error in (Cancelled(), KeyboardInterrupt()):
            ui = FakeUI()
            ui.choose = Mock(side_effect=error)
            self.assertFalse(setup.offer_launch(ui))
            self.assertIn("Installation is complete", str(ui.events))

    def test_success_yes_launches_only_after_terminal_ui_is_restored(self):
        events = []
        ui = FakeUI([1])

        @contextmanager
        def terminal():
            yield ui
            events.append("restored")

        def launch():
            self.assertEqual(events, ["restored"])
            return 0

        with patch.object(setup, "TerminalUI", side_effect=terminal), \
             patch.object(setup.sys, "argv", ["setup_local"]), \
             patch.object(setup, "setup", return_value=True), \
             patch.object(setup, "launch_application", side_effect=launch) as start:
            self.assertEqual(setup.main(), 0)
        start.assert_called_once()

    def test_no_decline_failure_and_cancel_never_launch(self):
        for result, choices, error, expected in ((True, [0], None, 0), (False, [], None, 0),
                (None, [], setup.SetupError("failed"), 1), (None, [], Cancelled(), 130)):
            with self.subTest(result=result, error=error):
                ui = FakeUI(choices)

                @contextmanager
                def terminal():
                    yield ui

                with patch.object(setup, "TerminalUI", side_effect=terminal), \
                     patch.object(setup.sys, "argv", ["setup_local"]), \
                     patch.object(setup, "setup", return_value=result, side_effect=error), \
                     patch.object(setup, "launch_application") as start:
                    self.assertEqual(setup.main(), expected)
                start.assert_not_called()

    def test_launch_failure_does_not_claim_installation_failed(self):
        ui = FakeUI([1])

        @contextmanager
        def terminal():
            yield ui

        with patch.object(setup, "TerminalUI", side_effect=terminal), \
             patch.object(setup.sys, "argv", ["setup_local"]), \
             patch.object(setup, "setup", return_value=True), \
             patch.object(setup, "launch_application", side_effect=OSError("missing executable")), \
             patch("builtins.print") as message:
            self.assertEqual(setup.main(), 1)
        self.assertIn("Installation is complete", message.call_args.args[0])

    def test_launch_uses_project_venv_root_loopback_and_no_shell_on_both_os_paths(self):
        root = Path.cwd()
        for os_name, relative in (("nt", "Scripts/python.exe"), ("posix", "bin/python")):
            with self.subTest(os=os_name):
                process = Mock()
                process.wait.return_value = 0
                with patch.object(setup.os, "name", os_name), \
                     patch.object(setup.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, create=True), \
                     patch.object(setup.subprocess, "Popen", return_value=process) as spawn, \
                     patch("builtins.print"):
                    self.assertEqual(setup.launch_application(root), 0)
                command = spawn.call_args.args[0]
                self.assertEqual(command[:5], [str(root / ".venv" / relative), "-m", "streamlit", "run", "docs_radar/app.py"])
                self.assertIn("--server.address=127.0.0.1", command)
                self.assertIn("--browser.gatherUsageStats=false", command)
                self.assertIn("--server.headless=false", command)
                self.assertEqual(spawn.call_args.kwargs["cwd"], root)
                self.assertNotIn("shell", spawn.call_args.kwargs)
                self.assertEqual(spawn.call_args.kwargs.get("creationflags" if os_name == "nt" else "start_new_session"),
                                 512 if os_name == "nt" else True)

    def test_ctrl_c_requests_graceful_child_shutdown_and_waits(self):
        process = Mock()
        process.wait.side_effect = [KeyboardInterrupt(), 0]
        process.poll.return_value = None
        with patch.object(setup.subprocess, "Popen", return_value=process), patch("builtins.print"):
            self.assertEqual(setup.launch_application(), 0)
        expected = signal.SIGBREAK if setup.os.name == "nt" else signal.SIGTERM
        process.send_signal.assert_called_once_with(expected)
        self.assertEqual(process.wait.call_count, 2)
        process.kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
