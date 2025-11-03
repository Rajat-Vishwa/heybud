"""
Plugin API for heybud extensions
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass


@dataclass
class CommandSuggestion:
    """A command suggestion from a plugin"""
    command: str
    description: str
    risk_score: float = 0.0
    env: Dict[str, str] = None
    
    def __post_init__(self):
        if self.env is None:
            self.env = {}


class HeybudAPI:
    """API provided to plugins for interacting with heybud"""
    
    def __init__(self, context_manager, config_manager, logger):
        self._context = context_manager
        self._config = config_manager
        self._logger = logger
        self._intent_handlers: Dict[str, Callable] = {}
    
    def get_context(self) -> Dict[str, Any]:
        """Get current execution context"""
        return {
            'cwd': self._context.context.cwd,
            'shell': self._context.context.shell,
            'venv_path': self._context.context.venv_path,
            'git_repo': self._context.context.git_repo,
            'git_branch': self._context.context.git_branch,
        }
    
    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update execution context"""
        for key, value in updates.items():
            if hasattr(self._context.context, key):
                setattr(self._context.context, key, value)
        self._context.save_context()
    
    def produce_command(self, cmd: str, meta: Dict[str, Any]) -> CommandSuggestion:
        """Produce a command suggestion"""
        return CommandSuggestion(
            command=cmd,
            description=meta.get('description', ''),
            risk_score=meta.get('risk_score', 0.0),
            env=meta.get('env', {}),
        )
    
    def log(self, event: str, payload: Dict[str, Any]) -> None:
        """Log an event"""
        self._logger.logger.info(f"Plugin event: {event}", extra=payload)
    
    def register_intent(self, name: str, handler: Callable) -> None:
        """Register an intent handler"""
        self._intent_handlers[name] = handler
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self._config.get_config_value(key) or default


class HeybudPlugin(ABC):
    """Base class for heybud plugins"""
    
    name: str = "unnamed_plugin"
    version: str = "0.1.0"
    description: str = ""
    author: str = ""
    
    @abstractmethod
    def register(self, api: HeybudAPI) -> None:
        """
        Register plugin with heybud API.
        Called once when plugin is loaded.
        """
        pass
    
    def handle_query(self, query: str, context: Dict[str, Any]) -> Optional[CommandSuggestion]:
        """
        Handle a user query and optionally return a command suggestion.
        
        Args:
            query: The user's query string
            context: Current execution context
            
        Returns:
            CommandSuggestion if plugin can handle this query, None otherwise
        """
        return None
    
    def on_command_generated(self, commands: list, metadata: Dict[str, Any]) -> None:
        """
        Hook called after commands are generated.
        Plugin can modify commands or add metadata.
        """
        pass
    
    def on_command_executed(self, command: str, success: bool, output: str) -> None:
        """
        Hook called after a command is executed.
        """
        pass
