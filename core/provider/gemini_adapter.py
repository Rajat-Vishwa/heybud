"""
Google Gemini adapter
"""
import time
from typing import Callable, Optional
import os

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

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


class GeminiAdapter(ProviderAdapter):
    """Google Gemini API adapter"""
    
    def initialize(self) -> None:
        """Initialize Gemini client"""
        if not GEMINI_AVAILABLE:
            raise ImportError("google-generativeai not installed. Run: pip install google-generativeai")
        
        api_key = self.config.api_key or os.getenv(self.config.api_key_name or "GEMINI_API_KEY")
        if not api_key:
            raise ValueError(f"Gemini API key not found. Set {self.config.api_key_name} environment variable.")
        
        genai.configure(api_key=api_key)
        self.model_name = self.config.model or "gemini-pro"
        self.model = genai.GenerativeModel(self.model_name)
        self.initialized = True
    
    def generate(self, prompt: Prompt, options: GenerateOptions) -> LLMResponse:
        """Generate complete response"""
        if not self.initialized:
            self.initialize()
        
        # Build prompt text
        full_prompt = self._build_system_prompt(prompt) + "\n\n" + prompt.user_query
        
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=options.max_tokens or self.config.max_tokens,
                    temperature=options.temperature or self.config.temperature,
                )
            )
            
            content = response.text
            
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(content, provider="gemini", model=self.model_name)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"Gemini API error: {str(e)}",
                commands=[],
                metadata={"provider": "gemini", "model": self.model_name, "error": str(e)},
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
        
        full_prompt = self._build_system_prompt(prompt) + "\n\n" + prompt.user_query
        
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=options.max_tokens or self.config.max_tokens,
                    temperature=options.temperature or self.config.temperature,
                ),
                stream=True,
            )
            
            full_content = []
            for chunk in response:
                if chunk.text:
                    full_content.append(chunk.text)
                    on_chunk(chunk.text)
            
            complete_text = "".join(full_content)
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(complete_text, provider="gemini", model=self.model_name)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"Gemini streaming error: {str(e)}",
                commands=[],
                metadata={"provider": "gemini", "model": self.model_name, "error": str(e)},
                raw_response=None,
            )
    
    def function_call(
        self,
        prompt: Prompt,
        functions: list[FunctionSpec],
        options: GenerateOptions
    ) -> FunctionCallResult:
        """Gemini function calling support"""
        # Gemini supports function calling, but implementation varies
        # For now, use structured prompting
        raise NotImplementedError("Gemini function calling not yet implemented")
    
    def health_check(self) -> HealthStatus:
        """Check Gemini API health"""
        try:
            if not self.initialized:
                self.initialize()
            
            start = time.time()
            self.model.generate_content(
                "test",
                generation_config=genai.types.GenerationConfig(max_output_tokens=5)
            )
            latency = (time.time() - start) * 1000
            
            return HealthStatus(
                healthy=True,
                latency_ms=latency,
                provider="gemini",
                model=self.model_name,
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                error=str(e),
                provider="gemini",
                model=self.model_name,
            )
    
    def token_cost_estimate(self, prompt: Prompt, model: Optional[str] = None) -> CostEstimate:
        """Estimate cost for Gemini"""
        base_estimate = super().token_cost_estimate(prompt, model)
        
        # Gemini pricing (approximate)
        model_name = model or self.model_name
        cost_per_token = 0.00025 / 1000  # gemini-pro pricing
        
        return CostEstimate(
            estimated_tokens=base_estimate.estimated_tokens,
            estimated_cost_usd=base_estimate.estimated_tokens * cost_per_token,
            provider="gemini",
            model=model_name,
        )
    
    def supports_streaming(self) -> bool:
        return True
    
    def supports_function_calling(self) -> bool:
        return False  # Not implemented yet
