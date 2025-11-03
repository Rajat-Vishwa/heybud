"""
Noop adapter for testing without making real API calls
"""
import time
from typing import Callable, Optional
import uuid

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


class NoopAdapter(ProviderAdapter):
    """No-op adapter for testing"""
    
    def __init__(self, config, mock_response: Optional[LLMResponse] = None):
        super().__init__(config)
        self.mock_response = mock_response
        self.call_count = 0
    
    def initialize(self) -> None:
        """Initialize (no-op)"""
        self.initialized = True
    
    def generate(self, prompt: Prompt, options: GenerateOptions) -> LLMResponse:
        """Return mock response"""
        self.call_count += 1
        
        if self.mock_response:
            return self.mock_response
        
        # Default mock response
        return LLMResponse(
            intent=IntentType.RUNNABLE_COMMAND,
            explanation="Mock command generated for testing",
            commands=[
                Command(
                    id="c1",
                    cmd="echo 'test'",
                    description="Test command",
                    runnable=True,
                    risk_score=0.0,
                )
            ],
            safety=SafetyAnalysis(risk_score=0.0),
            metadata={
                "provider": "noop",
                "model": "mock",
                "prompt_id": str(uuid.uuid4()),
            },
            raw_response='{"intent": "runnable_command", "commands": [{"cmd": "echo \'test\'"}]}',
        )
    
    def stream_generate(
        self,
        prompt: Prompt,
        options: GenerateOptions,
        on_chunk: Callable[[str], None]
    ) -> LLMResponse:
        """Simulate streaming"""
        self.call_count += 1
        
        # Simulate chunks
        mock_text = "Mock streaming response"
        for char in mock_text:
            on_chunk(char)
            time.sleep(0.01)  # Simulate latency
        
        return self.generate(prompt, options)
    
    def function_call(
        self,
        prompt: Prompt,
        functions: list[FunctionSpec],
        options: GenerateOptions
    ) -> FunctionCallResult:
        """Mock function call"""
        self.call_count += 1
        
        if functions:
            return FunctionCallResult(
                function_name=functions[0].name,
                arguments={"mock": "args"},
                raw_response=None,
            )
        
        return FunctionCallResult(
            function_name="",
            arguments={},
            raw_response=None,
        )
    
    def health_check(self) -> HealthStatus:
        """Always healthy"""
        return HealthStatus(
            healthy=True,
            latency_ms=1.0,
            provider="noop",
            model="mock",
        )
    
    def token_cost_estimate(self, prompt: Prompt, model: Optional[str] = None) -> CostEstimate:
        """Mock cost estimate"""
        return CostEstimate(
            estimated_tokens=100,
            estimated_cost_usd=0.0,
            provider="noop",
            model="mock",
        )
    
    def supports_streaming(self) -> bool:
        return True
    
    def supports_function_calling(self) -> bool:
        return True
