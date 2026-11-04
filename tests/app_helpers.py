"""Keep UI tests model-free even when the developer has installed real weights."""

from unittest.mock import patch

from docs_radar.local_runtime import RuntimeStatus


class OfflineModelMixin:
    def setUp(self):
        super().setUp()
        patcher = patch("docs_radar.local_runtime.start_app_model", return_value=RuntimeStatus())
        self.runtime_start = patcher.start()
        self.addCleanup(patcher.stop)
        models = patch("docs_radar.local_runtime.installed_model_tags", return_value=())
        self.installed_tags = models.start()
        self.addCleanup(models.stop)
