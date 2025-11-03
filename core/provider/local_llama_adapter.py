"""
Local llama.cpp adapter for running GGML models locally
"""
import subprocess
import time
import json
from typing import Callable, Optional
from pathlib import Path

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


class LocalLlamaAdapter(ProviderAdapter):
    """Adapter for local llama.cpp inference"""
    
    def initialize(self) -> None:
        """Initialize llama.cpp"""
        # Expected config:
        # - endpoint: path to llama.cpp binary or server
        # - model: path to GGML model file
        
        self.llama_binary = self.config.endpoint or "llama"
        self.model_path = self.config.model
        
        if not self.model_path:
            raise ValueError("Local llama adapter requires 'model' config with path to GGML file")
        
        # Check if binary exists
        try:
            subprocess.run(
                [self.llama_binary, "--version"],
                capture_output=True,
                timeout=5,
            )
            self.initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize llama.cpp: {e}")
    
    def generate(self, prompt: Prompt, options: GenerateOptions) -> LLMResponse:
        """Generate using llama.cpp subprocess"""
        if not self.initialized:
            self.initialize()
        
        full_prompt = self._build_system_prompt(prompt) + "\n\n" + prompt.user_query
        
        try:
            # Run llama.cpp
            cmd = [
                self.llama_binary,
                "-m", self.model_path,
                "-p", full_prompt,
                "-n", str(options.max_tokens or self.config.max_tokens),
                "--temp", str(options.temperature or self.config.temperature),
                "--log-disable",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"llama.cpp error: {result.stderr}")
            
            content = result.stdout.strip()
            
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(content, provider="local_llama", model=self.model_path)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"Local llama error: {str(e)}",
                commands=[],
                metadata={"provider": "local_llama", "model": self.model_path, "error": str(e)},
                raw_response=None,
            )
    
    def stream_generate(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        on_chunk: Callable[[str], None]
    ) -> LLMResponse:
        """Stream generation using llama.cpp"""
        if not self.initialized:
            self.initialize()
        
        full_prompt = self._build_system_prompt(prompt) + "\n\n" + prompt.user_query
        
        try:
            cmd = [
                self.llama_binary,
                "-m", self.model_path,
                "-p", full_prompt,
                "-n", str(options.max_tokens or self.config.max_tokens),
                "--temp", str(options.temperature or self.config.temperature),
                "--log-disable",
            ]
            
            # Stream output line by line
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            full_content = []
            if process.stdout:
                for line in process.stdout:
                    full_content.append(line)
                    on_chunk(line)
            
            process.wait(timeout=self.config.timeout)
            
            complete_text = "".join(full_content)
            from ..parser import ResponseParser
            parser = ResponseParser()
            return parser.parse(complete_text, provider="local_llama", model=self.model_path)
            
        except Exception as e:
            return LLMResponse(
                intent=IntentType.ERROR,
                explanation=f"Local llama streaming error: {str(e)}",
                commands=[],
                metadata={"provider": "local_llama", "model": self.model_path, "error": str(e)},
                raw_response=None,
            )
    
    def function_call(
        self,
        prompt: Prompt,
        functions: list[FunctionSpec],
        options: GenerateOptions
    ) -> FunctionCallResult:
        """Local llama doesn't support function calling"""
        raise NotImplementedError("Local llama function calling not supported")
    
    def health_check(self) -> HealthStatus:
        """Check if llama.cpp is available"""
        try:
            if not self.initialized:
                self.initialize()
            
            start = time.time()
            # Quick test generation
            result = subprocess.run(
                [self.llama_binary, "-m", self.model_path, "-p", "test", "-n", "5"],
                capture_output=True,
                timeout=10,
            )
            latency = (time.time() - start) * 1000
            
            return HealthStatus(
                healthy=result.returncode == 0,
                latency_ms=latency,
                provider="local_llama",
                model=self.model_path,
                error=result.stderr if result.returncode != 0 else None,
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                error=str(e),
                provider="local_llama",
                model=self.model_path,
            )
    
    def token_cost_estimate(self, prompt: Prompt, model: Optional[str] = None) -> CostEstimate:
        """Local models have no cost"""
        base_estimate = super().token_cost_estimate(prompt, model)
        return CostEstimate(
            estimated_tokens=base_estimate.estimated_tokens,
            estimated_cost_usd=0.0,
            provider="local_llama",
            model=model or self.model_path,
        )
    
    def supports_streaming(self) -> bool:
        return True
    
    def supports_function_calling(self) -> bool:
        return False
