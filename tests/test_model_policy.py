from dataclasses import replace
import unittest

from docs_radar.model_policy import (
    MAX_MODEL_BYTES, ModelBudgetError, check_available_memory, check_model_size,
)
from tests.test_setup import WINDOWS


class ModelPolicyTests(unittest.TestCase):
    def small(self):
        return {"size": 2_497_294_790, "details": {"parameter_size": "4.0B"}}

    def test_existing_4b_fits_measured_windows_class(self):
        check_available_memory(self.small(), WINDOWS)

    def test_large_model_cannot_hide_behind_small_quantization(self):
        with self.assertRaises(ModelBudgetError):
            check_model_size({"size": 2_000_000_000, "details": {"parameter_size": "8B"}})

    def test_missing_or_invalid_metadata_fails_closed(self):
        for entry in ({}, {"size": 123}, {"size": True, "details": {"parameter_size": "4B"}},
                      {"size": MAX_MODEL_BYTES + 1, "details": {"parameter_size": "4B"}},
                      {"size": 123, "details": {"parameter_size": "unknown"}},
                      {"size": 123, "details": {"parameter_size": "0B"}}):
            with self.subTest(entry=entry), self.assertRaises(ModelBudgetError):
                check_model_size(entry)

    def test_no_unknown_memory_or_gpu_spill(self):
        for machine in (replace(WINDOWS, available_ram=0),
                        replace(WINDOWS, available_ram=4 * 1024 ** 3),
                        replace(WINDOWS, free_vram=2 * 1024 ** 3)):
            with self.subTest(machine=machine), self.assertRaises(ModelBudgetError):
                check_available_memory(self.small(), machine)

    def test_smaller_cpu_model_retains_ram_headroom(self):
        machine = replace(WINDOWS, available_ram=4 * 1024 ** 3, free_vram=0)
        check_available_memory({"size": 522_653_767, "details": {"parameter_size": "600M"}}, machine)
