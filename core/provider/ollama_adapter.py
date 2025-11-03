"""
Ollama local LLM adapter for low-latency local inference
"""
import time
import json
from typing import Callable, Optional
import requests

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


class OllamaAdapter(ProviderAdapter):
    """Ollama local LLM adapter"""
    
    def initialize(self) -> None:
        """Initialize Ollama connection"""
        self.endpoint = self.config.endpoint or "http://127.0.0.1:11434"
        self.model = self.config.model or "llama3"
        self.initialized = True
    
    def generate(self, prompt: Prompt, options: GenerateOptions) -> LLMResponse:
        """Generate complete response from Ollama"""
        if not self.initialized:
            self.initialize()
        
        messages = self._build_messages(prompt)
        model = options.model or self.model
        
        try:
            response = requests.post(
                f"{self.endpoint}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": options.temperature or self.config.temperature,
                        "num_predict": options.max_tokens or self.config.max_tokens,
                    }
                },
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            content = data.get("message", {}).get("content", "")
            
            # Parse response
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(content, provider="ollama", model=model)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"Ollama error: {str(e)}",
                commands=[],
                metadata={"provider": "ollama", "model": model, "error": str(e)},
                raw_response=None,
            )
    
    def stream_generate(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        on_chunk: Callable[[str], None]
    ) -> LLMResponse:
        """Stream generation from Ollama"""
        if not self.initialized:
            self.initialize()
        
        messages = self._build_messages(prompt)
        model = options.model or self.model
        
        try:
            response = requests.post(
                f"{self.endpoint}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": options.temperature or self.config.temperature,
                        "num_predict": options.max_tokens or self.config.max_tokens,
                    }
                },
                timeout=self.config.timeout,
                stream=True,
            )
            response.raise_for_status()
            
            full_content = []
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "message" in data:
                        content = data["message"].get("content", "")
                        if content:
                            full_content.append(content)
                            on_chunk(content)
            
            complete_text = "".join(full_content)
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(complete_text, provider="ollama", model=model)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"Ollama streaming error: {str(e)}",
                commands=[],
                metadata={"provider": "ollama", "model": model, "error": str(e)},
                raw_response=None,
            )
    
    def function_call(
        self,
        prompt: Prompt,
        functions: list[FunctionSpec],
        options: GenerateOptions
    ) -> FunctionCallResult:
        """Ollama doesn't natively support function calling - use structured prompting"""
        # Fallback: add functions to prompt and parse response
        func_descriptions = "\n".join([
            f"- {func.name}: {func.description}"
            for func in functions
        ])
        
        modified_prompt = Prompt(
            user_query=f"{prompt.user_query}\n\nAvailable functions:\n{func_descriptions}\n\nRespond with JSON.",
            system_context=prompt.system_context,
            history=prompt.history,
            template_name=prompt.template_name,
            shell_type=prompt.shell_type,
        )
        
        response = self.generate(modified_prompt, options)
        
        # Try to extract function call from response
        try:
            if response.raw_response:
                data = json.loads(response.raw_response)
                return FunctionCallResult(
                    function_name=data.get("function", ""),
                    arguments=data.get("arguments", {}),
                    raw_response=response,
                )
        except:
            pass
        
        return FunctionCallResult(
            function_name="",
            arguments={},
            raw_response=response,
        )
    
    def health_check(self) -> HealthStatus:
        """Check Ollama server health"""
        try:
            if not self.initialized:
                self.initialize()
            
            start = time.time()
            response = requests.get(f"{self.endpoint}/api/tags", timeout=5)
            response.raise_for_status()
            latency = (time.time() - start) * 1000
            
            # Check if model is available
            models = response.json().get("models", [])
            model_available = any(m.get("name") == self.model for m in models)
            
            return HealthStatus(
                healthy=model_available,
                latency_ms=latency,
                provider="ollama",
                model=self.model,
                error=None if model_available else f"Model {self.model} not found",
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                error=str(e),
                provider="ollama",
                model=self.model,
            )
    
    def token_cost_estimate(self, prompt: Prompt, model: Optional[str] = None) -> CostEstimate:
        """Local models have no cost"""
        base_estimate = super().token_cost_estimate(prompt, model)
        return CostEstimate(
            estimated_tokens=base_estimate.estimated_tokens,
            estimated_cost_usd=0.0,  # Local inference is free
            provider="ollama",
            model=model or self.model,
        )
    
    def supports_streaming(self) -> bool:
        return True
    
    def supports_function_calling(self) -> bool:
        return False  # Not natively, but we can simulate
