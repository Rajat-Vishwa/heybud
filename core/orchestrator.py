"""
Provider orchestrator - manages multiple providers with failover
"""
from typing import List, Optional, Callable
import time

from .provider.base_adapter import ProviderAdapter
from .provider import (
    OpenAIAdapter,
    OllamaAdapter,
    GeminiAdapter,
    AnthropicAdapter,
    HuggingFaceAdapter,
    LocalLlamaAdapter,
    NoopAdapter,
)
from .types import (
    ProviderConfig,
    ProviderType,
    Prompt,
    GenerateOptions,
    LLMResponse,
    HealthStatus,
    FailoverStrategy,
    IntentType,
)


class ProviderOrchestrator:
    """Manages multiple LLM providers with failover"""
    
    ADAPTER_MAP = {
        ProviderType.OPENAI: OpenAIAdapter,
        ProviderType.OLLAMA: OllamaAdapter,
        ProviderType.GEMINI: GeminiAdapter,
        ProviderType.ANTHROPIC: AnthropicAdapter,
        ProviderType.HUGGINGFACE: HuggingFaceAdapter,
        ProviderType.LOCAL_LLAMA: LocalLlamaAdapter,
        ProviderType.NOOP: NoopAdapter,
    }
    
    def __init__(
        self,
        provider_configs: List[ProviderConfig],
        failover_strategy: FailoverStrategy = FailoverStrategy.FIRST_AVAILABLE,
    ):
        self.provider_configs = sorted(provider_configs, key=lambda x: x.priority)
        self.failover_strategy = failover_strategy
        self.adapters: List[ProviderAdapter] = []
        self.current_index = 0
        
        self._initialize_adapters()
    
    def _initialize_adapters(self) -> None:
        """Initialize all provider adapters"""
        for config in self.provider_configs:
            try:
                adapter_class = self.ADAPTER_MAP.get(config.provider)
                if not adapter_class:
                    print(f"Warning: Unknown provider type {config.provider}")
                    continue
                
                adapter = adapter_class(config)
                adapter.initialize()
                self.adapters.append(adapter)
            except Exception as e:
                print(f"Warning: Failed to initialize {config.provider}: {e}")
    
    def generate(
        self,
        prompt: Prompt,
        options: Optional[GenerateOptions] = None,
        stream: bool = False,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> LLMResponse:
        """Generate response with failover"""
        if not self.adapters:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation="No providers available",
                commands=[],
                metadata={"error": "no_providers"},
            )
        
        options = options or GenerateOptions()
        
        if self.failover_strategy == FailoverStrategy.FIRST_AVAILABLE:
            return self._generate_first_available(prompt, options, stream, on_chunk)
        elif self.failover_strategy == FailoverStrategy.ROUND_ROBIN:
            return self._generate_round_robin(prompt, options, stream, on_chunk)
        else:  # FALLBACK
            return self._generate_fallback(prompt, options, stream, on_chunk)
    
    def _generate_first_available(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        stream: bool,
        on_chunk: Optional[Callable[[str], None]],
    ) -> LLMResponse:
        """Try providers in priority order until one succeeds"""
        last_error = None
        
        for adapter in self.adapters:
            try:
                if stream and on_chunk and adapter.supports_streaming():
                    return adapter.stream_generate(prompt, options, on_chunk)
                else:
                    return adapter.generate(prompt, options)
            except Exception as e:
                last_error = e
                print(f"Provider {adapter.config.provider.value} failed: {e}")
                continue
        
        # All providers failed
        return LLMResponse(
            intent=IntentType.ERROR,
            explanation=f"All providers failed. Last error: {last_error}",
            commands=[],
            metadata={"error": str(last_error)},
        )
    
    def _generate_round_robin(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        stream: bool,
        on_chunk: Optional[Callable[[str], None]],
    ) -> LLMResponse:
        """Distribute requests across providers"""
        if not self.adapters:
            return self._generate_first_available(prompt, options, stream, on_chunk)
        
        # Try current adapter
        adapter = self.adapters[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.adapters)
        
        try:
            if stream and on_chunk and adapter.supports_streaming():
                return adapter.stream_generate(prompt, options, on_chunk)
            else:
                return adapter.generate(prompt, options)
        except Exception as e:
            print(f"Provider {adapter.config.provider.value} failed: {e}")
            # Fallback to first available
            return self._generate_first_available(prompt, options, stream, on_chunk)
    
    def _generate_fallback(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        stream: bool,
        on_chunk: Optional[Callable[[str], None]],
    ) -> LLMResponse:
        """Try primary, fallback to others on failure"""
        return self._generate_first_available(prompt, options, stream, on_chunk)
    
    def health_check_all(self) -> List[HealthStatus]:
        """Check health of all providers"""
        results = []
        for adapter in self.adapters:
            try:
                status = adapter.health_check()
                results.append(status)
            except Exception as e:
                results.append(HealthStatus(
                    healthy=False,
                    error=str(e),
                    provider=adapter.config.provider.value,
                ))
        return results
    
    def close_all(self) -> None:
        """Close all provider connections"""
        for adapter in self.adapters:
            try:
                adapter.close()
            except:
                pass
