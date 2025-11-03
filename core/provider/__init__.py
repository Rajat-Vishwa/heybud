"""
Provider adapters for multiple LLM backends
"""

from .base_adapter import ProviderAdapter
from .openai_adapter import OpenAIAdapter
from .ollama_adapter import OllamaAdapter
from .gemini_adapter import GeminiAdapter
from .anthropic_adapter import AnthropicAdapter
from .huggingface_adapter import HuggingFaceAdapter
from .local_llama_adapter import LocalLlamaAdapter
from .noop_adapter import NoopAdapter

__all__ = [
    "ProviderAdapter",
    "OpenAIAdapter",
    "OllamaAdapter",
    "GeminiAdapter",
    "AnthropicAdapter",
    "HuggingFaceAdapter",
    "LocalLlamaAdapter",
    "NoopAdapter",
]
