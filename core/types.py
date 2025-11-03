"""
Core types and data structures for heybud
"""
from typing import List, Dict, Optional, Any, Callable, Literal
from dataclasses import dataclass, field
from enum import Enum
import uuid


class ProviderType(str, Enum):
    """Supported LLM provider types"""
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LOCAL_LLAMA = "local_llama"
    HUGGINGFACE = "huggingface"
    NOOP = "noop"


class IntentType(str, Enum):
    """Types of intents heybud can handle"""
    RUNNABLE_COMMAND = "runnable_command"
    EXPLANATION = "explanation"
    FOLLOW_UP = "follow_up"
    ERROR = "error"


class FailoverStrategy(str, Enum):
    """Provider failover strategies"""
    FIRST_AVAILABLE = "first_available"
    ROUND_ROBIN = "round_robin"
    FALLBACK = "fallback"


@dataclass
class ProviderConfig:
    """Configuration for a single LLM provider"""
    id: str
    provider: ProviderType
    priority: int = 1
    model: str = ""
    api_key_name: Optional[str] = None
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.2
    timeout: int = 30
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyConfig:
    """Safety and governance settings"""
    max_tokens: int = 1024
    temperature: float = 0.2
    safe_mode: bool = True
    risk_threshold: float = 0.7
    require_confirmation: bool = True
    dangerous_patterns: List[str] = field(default_factory=lambda: [
        r"rm\s+-rf\s+/",
        r"dd\s+if=",
        r"mkfs\.",
        r":(){ :|:& };:",  # fork bomb
        r"chmod\s+-R\s+777",
        r"curl.*\|\s*sh",
        r"wget.*\|\s*sh",
    ])


@dataclass
class ShellConfig:
    """Shell integration settings"""
    preferred: str = "bash"
    install_shell_wrapper: bool = True


@dataclass
class TelemetryConfig:
    """Telemetry settings"""
    enabled: bool = False
    endpoint: Optional[str] = None


@dataclass
class HeybudConfig:
    """Complete heybud configuration"""
    providers: List[ProviderConfig] = field(default_factory=list)
    failover_strategy: FailoverStrategy = FailoverStrategy.FIRST_AVAILABLE
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    shell: ShellConfig = field(default_factory=ShellConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)


@dataclass
class Command:
    """A single executable command"""
    id: str
    cmd: str
    description: str
    runnable: bool = True
    cwd: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    risk_score: float = 0.0


@dataclass
class SafetyAnalysis:
    """Safety analysis result for commands"""
    risk_score: float
    warnings: List[str] = field(default_factory=list)
    dangerous: bool = False
    patterns_matched: List[str] = field(default_factory=list)


@dataclass
class LLMResponse:
    """Structured LLM response"""
    intent: IntentType
    explanation: str
    commands: List[Command] = field(default_factory=list)
    safety: SafetyAnalysis = field(default_factory=lambda: SafetyAnalysis(risk_score=0.0))
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_response: Optional[str] = None


@dataclass
class Prompt:
    """Prompt with context for LLM"""
    user_query: str
    system_context: Optional[str] = None
    history: List[Dict[str, str]] = field(default_factory=list)
    template_name: str = "command_generation"
    shell_type: str = "bash"


@dataclass
class GenerateOptions:
    """Options for LLM generation"""
    model: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.2
    stream: bool = False
    functions: Optional[List[Dict[str, Any]]] = None
    stop_sequences: List[str] = field(default_factory=list)


@dataclass
class CostEstimate:
    """Token and cost estimation"""
    estimated_tokens: int
    estimated_cost_usd: float
    provider: str
    model: str


@dataclass
class HealthStatus:
    """Provider health status"""
    healthy: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    provider: str = ""
    model: str = ""


@dataclass
class FunctionSpec:
    """Function specification for function calling"""
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class FunctionCallResult:
    """Result from function calling"""
    function_name: str
    arguments: Dict[str, Any]
    raw_response: Any = None


@dataclass
class PluginMetadata:
    """Plugin metadata"""
    name: str
    version: str
    description: str
    author: str
    entry_point: str


@dataclass
class ExecutionContext:
    """Current execution context"""
    cwd: str
    shell: str
    env: Dict[str, str] = field(default_factory=dict)
    venv_path: Optional[str] = None
    git_repo: Optional[str] = None
    git_branch: Optional[str] = None
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: Optional[str] = None
