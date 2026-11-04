"""Gemini model discovery and consistent model ranking."""

import re
from typing import Any


def model_rank(name: str) -> tuple[int, int, str]:
    lowered_name = name.lower()
    if "pro" in lowered_name or "ultra" in lowered_name:
        tier = 4
    elif "flash" in lowered_name:
        tier = 3
    elif "gemma" in lowered_name:
        tier = 2
    else:
        tier = 1

    version_numbers = [int(part) for part in re.findall(r"\d+", lowered_name)]
    version = sum(
        number * (100**index) for index, number in enumerate(reversed(version_numbers))
    )
    return (-tier, -version, lowered_name)


def list_available_gemini_models(api_key: str) -> list[dict[str, str]]:
    """Return unique, generateContent-capable models ordered by preferred tier."""
    from google import genai

    client = genai.Client(api_key=api_key)
    models: dict[str, dict[str, str]] = {}
    for model in client.models.list():
        supported_actions: Any = getattr(model, "supported_actions", None) or []
        if supported_actions and "generateContent" not in supported_actions:
            continue
        name = (getattr(model, "name", "") or "").removeprefix("models/")
        if name:
            models[name] = {
                "id": name,
                "display_name": getattr(model, "display_name", None) or name,
            }
    return sorted(models.values(), key=lambda item: model_rank(item["id"]))
