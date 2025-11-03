"""
OpenAI provider adapter with streaming and function calling support
"""
import os
import time
from typing import Callable, Optional
import json

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

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
    Command,
    SafetyAnalysis,
)


class OpenAIAdapter(ProviderAdapter):
    """OpenAI API adapter with GPT-4, GPT-3.5, etc."""
    
    def initialize(self) -> None:
        """Initialize OpenAI client"""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        api_key = self.config.api_key or os.getenv(self.config.api_key_name or "OPENAI_API_KEY")
        if not api_key:
            raise ValueError(f"OpenAI API key not found. Set {self.config.api_key_name} environment variable.")
        
        self.client = OpenAI(api_key=api_key)
        self.initialized = True
    
    def generate(self, prompt: Prompt, options: GenerateOptions) -> LLMResponse:
        """Generate complete response"""
        if not self.initialized:
            self.initialize()
        
        messages = self._build_messages(prompt)
        model = options.model or self.config.model or "gpt-4o-mini"
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=options.max_tokens or self.config.max_tokens,
                temperature=options.temperature or self.config.temperature,
                timeout=self.config.timeout,
            )
            
            content = response.choices[0].message.content
            
            # Try to parse as JSON
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(content, provider=self.config.provider.value, model=model)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"OpenAI API error: {str(e)}",
                commands=[],
                metadata={"provider": "openai", "model": model, "error": str(e)},
                raw_response=None,
            )
    
    def stream_generate(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        on_chunk: Callable[[str], None]
    ) -> LLMResponse:
        """Stream generation with chunk callbacks"""
        if not self.initialized:
            self.initialize()
        
        messages = self._build_messages(prompt)
        model = options.model or self.config.model or "gpt-4o-mini"
        
        try:
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=options.max_tokens or self.config.max_tokens,
                temperature=options.temperature or self.config.temperature,
                stream=True,
                timeout=self.config.timeout,
            )
            
            full_content = []
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content.append(content)
                    on_chunk(content)
            
            # Parse complete response
            complete_text = "".join(full_content)
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(complete_text, provider=self.config.provider.value, model=model)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"OpenAI streaming error: {str(e)}",
                commands=[],
                metadata={"provider": "openai", "model": model, "error": str(e)},
                raw_response=None,
            )
    
    def function_call(
        self,
        prompt: Prompt,
        functions: list[FunctionSpec],
        options: GenerateOptions
    ) -> FunctionCallResult:
        """Use OpenAI function calling"""
        if not self.initialized:
            self.initialize()
        
        messages = self._build_messages(prompt)
        model = options.model or self.config.model or "gpt-4o-mini"
        
        # Convert FunctionSpec to OpenAI format
        tools = [
            {
                "type": "function",
                "function": {
                    "name": func.name,
                    "description": func.description,
                    "parameters": func.parameters,
                }
            }
            for func in functions
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                timeout=self.config.timeout,
            )
            
            message = response.choices[0].message
            
            if message.tool_calls:
                tool_call = message.tool_calls[0]
                return FunctionCallResult(
                    function_name=tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments),
                    raw_response=response,
                )
            
            # No function call made
            return FunctionCallResult(
                function_name="",
                arguments={},
                raw_response=response,
            )
            
        except Exception as e:
            raise RuntimeError(f"OpenAI function call error: {e}")
    
    def health_check(self) -> HealthStatus:
        """Check OpenAI API health"""
        try:
            if not self.initialized:
                self.initialize()
            
            start = time.time()
            # Simple test completion
            self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            latency = (time.time() - start) * 1000
            
            return HealthStatus(
                healthy=True,
                latency_ms=latency,
                provider="openai",
                model=self.config.model or "gpt-4o-mini",
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                error=str(e),
                provider="openai",
                model=self.config.model or "gpt-4o-mini",
            )
    
    def token_cost_estimate(self, prompt: Prompt, model: Optional[str] = None) -> CostEstimate:
        """Estimate tokens and cost for OpenAI"""
        # Rough estimation (proper implementation would use tiktoken)
        base_estimate = super().token_cost_estimate(prompt, model)
        
        model_name = model or self.config.model or "gpt-4o-mini"
        
        # Approximate pricing (as of 2024)
        pricing = {
            "gpt-4": 0.03 / 1000,  # per token
            "gpt-4-32k": 0.06 / 1000,
            "gpt-4o": 0.005 / 1000,
            "gpt-4o-mini": 0.00015 / 1000,
            "gpt-3.5-turbo": 0.0015 / 1000,
        }
        
        # Find matching pricing
        cost_per_token = 0.001 / 1000  # default
        for model_prefix, price in pricing.items():
            if model_name.startswith(model_prefix):
                cost_per_token = price
                break
        
        return CostEstimate(
            estimated_tokens=base_estimate.estimated_tokens,
            estimated_cost_usd=base_estimate.estimated_tokens * cost_per_token,
            provider="openai",
            model=model_name,
        )
    
    def supports_streaming(self) -> bool:
        return True
    
    def supports_function_calling(self) -> bool:
        return True
