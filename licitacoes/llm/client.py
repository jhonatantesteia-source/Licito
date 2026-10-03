import requests
import json
from typing import Any, Type, TypeVar, Optional
from pydantic import ValidationError
from licitacoes.config import settings

T = TypeVar("T", bound="BaseModel")

class OllamaClient:
    """Local LLM client for structured data extraction."""

    def __init__(self):
        self.url = f"{settings.ollama.url}/api/generate"
        self.model = settings.ollama.model_extraction

    def generate_structured(self, prompt: str, schema: Type[T]) -> Optional[T]:
        """Sends a prompt to Ollama and validates the response against a Pydantic schema."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": settings.ollama.temperature,
                "num_ctx": 8192
            }
        }

        try:
            response = requests.post(self.url, json=payload, timeout=settings.ollama.timeout)
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "")

            # Parse and validate JSON
            data = json.loads(content)
            return schema(**data)
        except (requests.RequestException, json.JSONDecodeError, ValidationError) as e:
            print(f"Error extracting structured data: {e}")
            return None

# Singleton for the app
llm_client = OllamaClient()
