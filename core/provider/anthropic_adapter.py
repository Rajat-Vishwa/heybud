"""
Anthropic Claude adapter
"""
import time
from typing import Callable, Optional
import os

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base_adapter import ProviderAdapter
from ..types import (
    Prompt,
    GenerateOptions,
    LLMResponse,
    FunctionSpec,
    FunctionCallResult,
    HealthStatus,
    CostEstimate,
    IntentType,
)


class AnthropicAdapter(ProviderAdapter):
    """Anthropic Claude API adapter"""
    
    def initialize(self) -> None:
        """Initialize Anthropic client"""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic not installed. Run: pip install anthropic")
        
        api_key = self.config.api_key or os.getenv(self.config.api_key_name or "ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(f"Anthropic API key not found. Set {self.config.api_key_name} environment variable.")
        
        self.client = Anthropic(api_key=api_key)
        self.model_name = self.config.model or "claude-3-5-sonnet-20241022"
        self.initialized = True
    
    def generate(self, prompt: Prompt, options: GenerateOptions) -> LLMResponse:
        """Generate complete response"""
        if not self.initialized:
            self.initialize()
        
        messages = self._build_messages(prompt)
        # Remove system message from messages (Anthropic uses separate system param)
        system_msg = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=options.max_tokens or self.config.max_tokens,
                temperature=options.temperature or self.config.temperature,
                system=system_msg or self._build_system_prompt(prompt),
                messages=user_messages,
            )
            
            content = response.content[0].text
            
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(content, provider="anthropic", model=self.model_name)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"Anthropic API error: {str(e)}",
                commands=[],
                metadata={"provider": "anthropic", "model": self.model_name, "error": str(e)},
                raw_response=None,
            )
    
    def stream_generate(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        on_chunk: Callable[[str], None]
    ) -> LLMResponse:
        """Stream generation"""
        if not self.initialized:
            self.initialize()
        
        messages = self._build_messages(prompt)
        system_msg = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        
        try:
            full_content = []
            
            with self.client.messages.stream(
                model=self.model_name,
                max_tokens=options.max_tokens or self.config.max_tokens,
                temperature=options.temperature or self.config.temperature,
                system=system_msg or self._build_system_prompt(prompt),
                messages=user_messages,
            ) as stream:
                for text in stream.text_stream:
                    full_content.append(text)
                    on_chunk(text)
            
            complete_text = "".join(full_content)
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(complete_text, provider="anthropic", model=self.model_name)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"Anthropic streaming error: {str(e)}",
                commands=[],
                metadata={"provider": "anthropic", "model": self.model_name, "error": str(e)},
                raw_response=None,
            )
    
    def function_call(
        self,
        prompt: Prompt,
        functions: list[FunctionSpec],
        options: GenerateOptions
    ) -> FunctionCallResult:
        """Anthropic function calling (tool use)"""
        if not self.initialized:
            self.initialize()
        
        messages = self._build_messages(prompt)
        system_msg = None
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                user_messages.append(msg)
        
        # Convert to Anthropic tools format
        tools = [
            {
                "name": func.name,
                "description": func.description,
                "input_schema": func.parameters,
            }
            for func in functions
        ]
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=options.max_tokens or self.config.max_tokens,
                system=system_msg or self._build_system_prompt(prompt),
                messages=user_messages,
                tools=tools,
            )
            
            # Check for tool use
            for block in response.content:
                if block.type == "tool_use":
                    return FunctionCallResult(
                        function_name=block.name,
                        arguments=block.input,
                        raw_response=response,
                    )
            
            return FunctionCallResult(
                function_name="",
                arguments={},
                raw_response=response,
            )
            
        except Exception as e:
            raise RuntimeError(f"Anthropic function call error: {e}")
    
    def health_check(self) -> HealthStatus:
        """Check Anthropic API health"""
        try:
            if not self.initialized:
                self.initialize()
            
            start = time.time()
            self.client.messages.create(
                model=self.model_name,
                max_tokens=5,
                messages=[{"role": "user", "content": "test"}],
            )
            latency = (time.time() - start) * 1000
            
            return HealthStatus(
                healthy=True,
                latency_ms=latency,
                provider="anthropic",
                model=self.model_name,
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                error=str(e),
                provider="anthropic",
                model=self.model_name,
            )
    
    def token_cost_estimate(self, prompt: Prompt, model: Optional[str] = None) -> CostEstimate:
        """Estimate cost for Anthropic"""
        base_estimate = super().token_cost_estimate(prompt, model)
        
        # Claude pricing (approximate)
        model_name = model or self.model_name
        cost_per_token = 0.003 / 1000  # claude-3-sonnet
        if "opus" in model_name:
            cost_per_token = 0.015 / 1000
        elif "haiku" in model_name:
            cost_per_token = 0.00025 / 1000
        
        return CostEstimate(
            estimated_tokens=base_estimate.estimated_tokens,
            estimated_cost_usd=base_estimate.estimated_tokens * cost_per_token,
            provider="anthropic",
            model=model_name,
        )
    
    def supports_streaming(self) -> bool:
        return True
    
    def supports_function_calling(self) -> bool:
        return True
