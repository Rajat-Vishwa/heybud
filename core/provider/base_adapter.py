"""
Base provider adapter interface that all LLM providers must implement
"""
from abc import ABC, abstractmethod
from typing import Optional, Callable, Any
from ..types import (
    ProviderConfig,
    Prompt,
    GenerateOptions,
    LLMResponse,
    FunctionSpec,
    FunctionCallResult,
    CostEstimate,
    HealthStatus,
)


class ProviderAdapter(ABC):
    """Abstract base class for all LLM provider adapters"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.initialized = False
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the provider adapter with configuration.
        May set up API clients, validate credentials, etc.
        """
        pass
    
    @abstractmethod
    def generate(
        self, 
        prompt: Prompt, 
        options: GenerateOptions
    ) -> LLMResponse:
        """
        Generate a complete response (non-streaming).
        
        Args:
            prompt: The prompt with context
            options: Generation options
            
        Returns:
            Structured LLM response
        """
        pass
    
    @abstractmethod
    def stream_generate(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        on_chunk: Callable[[str], None]
    ) -> LLMResponse:
        """
        Generate a streaming response, calling on_chunk for each token/chunk.
        
        Args:
            prompt: The prompt with context
            options: Generation options
            on_chunk: Callback function called with each chunk of text
            
        Returns:
            Complete LLM response after streaming finishes
        """
        pass
    
    @abstractmethod
    def function_call(
        self,
        prompt: Prompt,
        functions: list[FunctionSpec],
        options: GenerateOptions
    ) -> FunctionCallResult:
        """
        Request structured function calling (if supported by provider).
        
        Args:
            prompt: The prompt with context
            functions: List of available functions
            options: Generation options
            
        Returns:
            Function call result with function name and arguments
        """
        pass
    
    def token_cost_estimate(
        self, 
        prompt: Prompt, 
        model: Optional[str] = None
    ) -> CostEstimate:
        """
        Estimate token usage and cost for a prompt.
        
        Args:
            prompt: The prompt to estimate
            model: Optional model override
            
        Returns:
            Cost estimate with tokens and USD cost
        """
        # Default implementation: rough estimation
        text = prompt.user_query
        if prompt.system_context:
            text += prompt.system_context
        
        # Rough token estimate: 1 token ≈ 4 chars
        estimated_tokens = len(text) // 4
        
        return CostEstimate(
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=0.0,  # Override in subclasses
            provider=self.config.provider.value,
            model=model or self.config.model
        )
    
    @abstractmethod
    def health_check(self) -> HealthStatus:
        """
        Check if the provider is healthy and responsive.
        
        Returns:
            Health status with latency and error info
        """
        pass
    
    def close(self) -> None:
        """
        Clean up resources (connections, processes, etc.)
        """
        pass
    
    def supports_streaming(self) -> bool:
        """Check if this provider supports streaming"""
        return True
    
    def supports_function_calling(self) -> bool:
        """Check if this provider supports function calling"""
        return False
    
    def _build_system_prompt(self, prompt: Prompt) -> str:
        """Build system prompt with context"""
        # Trust the template's system_context entirely; do not force command-generation text
        return prompt.system_context or ""
    
    def _build_messages(self, prompt: Prompt) -> list[dict[str, str]]:
        """Build message history for chat-based models"""
        messages = []
        
        # Add system message
        system_prompt = self._build_system_prompt(prompt)
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        for msg in prompt.history:
            messages.append(msg)
        
        # Add current user query
        messages.append({"role": "user", "content": prompt.user_query})
        
        return messages
