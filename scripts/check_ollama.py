"""Report local Ollama and configured-model readiness without mutating state."""

import json

from llm.client import OllamaClient
from llm.settings import LLM_SETTINGS


def main() -> int:
    result = OllamaClient(LLM_SETTINGS).discover()
    print(json.dumps({
        "ollama_available": result.available,
        "host": result.host,
        "version": result.version,
        "configured_model": result.configured_model,
        "model_installed": result.model_installed,
        "installed_models": result.installed_models,
        "readiness_issues": result.readiness_issues,
    }, indent=2))
    if not result.available:
        print("Setup: start Ollama, then retry. See https://ollama.com/download")
    elif not result.model_installed:
        print(f"Setup: review model size, then run `ollama pull {result.configured_model}`.")
    return 0 if result.available and result.model_installed else 1


if __name__ == "__main__":
    raise SystemExit(main())
