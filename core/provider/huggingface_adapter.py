"""
Hugging Face Inference API adapter
"""
import time
from typing import Callable, Optional
import os
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


class HuggingFaceAdapter(ProviderAdapter):
    """Hugging Face Inference API adapter"""
    
    def initialize(self) -> None:
        """Initialize HF client"""
        api_key = self.config.api_key or os.getenv(self.config.api_key_name or "HUGGINGFACE_API_KEY")
        if not api_key:
            raise ValueError(f"HuggingFace API key not found. Set {self.config.api_key_name} environment variable.")
        
        self.api_key = api_key
        self.model_name = self.config.model or "meta-llama/Llama-2-7b-chat-hf"
        self.endpoint = self.config.endpoint or f"https://api-inference.huggingface.co/models/{self.model_name}"
        self.initialized = True
    
    def generate(self, prompt: Prompt, options: GenerateOptions) -> LLMResponse:
        """Generate complete response"""
        if not self.initialized:
            self.initialize()
        
        full_prompt = self._build_system_prompt(prompt) + "\n\n" + prompt.user_query
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": options.max_tokens or self.config.max_tokens,
                "temperature": options.temperature or self.config.temperature,
                "return_full_text": False,
            }
        }
        
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                content = data[0].get("generated_text", "")
            else:
                content = str(data)
            
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(content, provider="huggingface", model=self.model_name)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"HuggingFace API error: {str(e)}",
                commands=[],
                metadata={"provider": "huggingface", "model": self.model_name, "error": str(e)},
                raw_response=None,
            )
    
    def stream_generate(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        on_chunk: Callable[[str], None]
    ) -> LLMResponse:
        """HF Inference API doesn't support streaming - fallback to regular generate"""
        response = self.generate(prompt, options)
        # Simulate streaming by chunking the response
        if response.explanation:
            for char in response.explanation:
                on_chunk(char)
        return response
    
    def function_call(
        self,
        prompt: Prompt,
        functions: list[FunctionSpec],
        options: GenerateOptions
    ) -> FunctionCallResult:
        """HuggingFace doesn't support function calling natively"""
        raise NotImplementedError("HuggingFace function calling not supported")
    
    def health_check(self) -> HealthStatus:
        """Check HF API health"""
        try:
            if not self.initialized:
                self.initialize()
            
            start = time.time()
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.post(
                self.endpoint,
                headers=headers,
                json={"inputs": "test", "parameters": {"max_new_tokens": 5}},
                timeout=10,
            )
            response.raise_for_status()
            latency = (time.time() - start) * 1000
            
            return HealthStatus(
                healthy=True,
                latency_ms=latency,
                provider="huggingface",
                model=self.model_name,
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                error=str(e),
                provider="huggingface",
                model=self.model_name,
            )
    
    def token_cost_estimate(self, prompt: Prompt, model: Optional[str] = None) -> CostEstimate:
        """HF Inference API is free (with rate limits)"""
        base_estimate = super().token_cost_estimate(prompt, model)
        return CostEstimate(
            estimated_tokens=base_estimate.estimated_tokens,
            estimated_cost_usd=0.0,
            provider="huggingface",
            model=model or self.model_name,
        )
    
    def supports_streaming(self) -> bool:
        return False
    
    def supports_function_calling(self) -> bool:
        return False
