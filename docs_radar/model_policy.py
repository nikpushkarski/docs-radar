"""Small-model resource policy shared by setup and the optional answer adapter."""
import re

MAX_MODEL_BYTES = 3 * 1024 ** 3
MAX_PARAMETERS = 4_100_000_000  # 4B class, including rounded publisher metadata.
CONTEXT_TOKENS = 2048
OUTPUT_TOKENS = 64
MAX_PROMPT_BYTES = 1536  # Conservative UTF-8 budget; never truncate evidence to fit.


class ModelBudgetError(ValueError):
    pass


def check_model_size(entry):
    """Fail closed on missing/oversized local-model metadata before inference."""
    size = entry.get("size")
    details = entry.get("details") or {}
    parameters = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([BMK])", str(details.get("parameter_size", "")), re.I)
    if type(size) is not int or not 0 < size <= MAX_MODEL_BYTES or not parameters:
        raise ModelBudgetError("Model size is unknown or exceeds the 3 GiB / 4B-class limit.")
    count = float(parameters[1]) * {"B": 1e9, "M": 1e6, "K": 1e3}[parameters[2].upper()]
    if not 0 < count <= MAX_PARAMETERS:
        raise ModelBudgetError("Models larger than 4B class are disabled, including installed models.")


def check_available_memory(entry, hardware):
    """Conservative headroom heuristic, not a latency or peak-memory guarantee."""
    check_model_size(entry)
    # Leave 40% of available RAM and at least 10% of measured VRAM untouched.
    # Count weights twice to allow for loading buffers, context and runtime work.
    required = entry["size"] * 2
    if hardware.available_ram <= 0 or required > hardware.available_ram * .6:
        raise ModelBudgetError("Insufficient/unknown free RAM for this model; use extractive mode.")
    if hardware.free_vram and required > hardware.free_vram * .9:
        raise ModelBudgetError("Insufficient measured free VRAM; use extractive mode instead of spilling to RAM.")
