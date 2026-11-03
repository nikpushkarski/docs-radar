from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.setup_support import SetupError, promote_runtime


class RuntimePromotionTests(unittest.TestCase):
    def test_transient_windows_sharing_error_retries_without_overwrite(self):
        # Test the retry schedule independently of additional real scanner locks.
        # Native extraction/promotion is covered by the existing installer test.
        stage, destination = Mock(), Mock()
        destination.exists.return_value = False
        error = PermissionError("synthetic Windows scanner lock")
        error.winerror = 5
        stage.rename.side_effect = [error, None]
        with patch("scripts.setup_support.time.sleep") as sleep:
            promote_runtime(stage, destination)
        self.assertEqual(stage.rename.call_count, 2)
        stage.rename.assert_called_with(destination)
        sleep.assert_called_once_with(.1)

    def test_persistent_permission_error_is_not_hidden(self):
        error = PermissionError("synthetic persistent error")
        error.winerror = 32
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(Path, "rename", side_effect=error) as rename, patch("scripts.setup_support.time.sleep"):
                with self.assertRaises(PermissionError):
                    promote_runtime(root / "stage", root / "destination")
            self.assertEqual(rename.call_count, 5)

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "destination"
            destination.mkdir()
            with self.assertRaises(SetupError), patch.object(Path, "rename") as rename:
                promote_runtime(root / "stage", destination)
            rename.assert_not_called()
