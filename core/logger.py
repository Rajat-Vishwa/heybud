"""
Logging and audit system for heybud
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .types import LLMResponse, Prompt


class HeybudLogger:
    """Structured logging for heybud"""
    
    def __init__(self, heybud_dir: Optional[Path] = None):
        self.heybud_dir = heybud_dir or Path.home() / ".heybud"
        self.logs_dir = self.heybud_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True, parents=True, mode=0o700)
        
        self.trace_dir = self.heybud_dir / "trace"
        self.trace_dir.mkdir(exist_ok=True, parents=True, mode=0o700)
        
        # Set up Python logger
        self.logger = logging.getLogger('heybud')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        log_file = self.logs_dir / f"heybud_{datetime.now().strftime('%Y%m%d')}.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
    
    def log_query(
        self,
        prompt: Prompt,
        response: LLMResponse,
        duration_ms: float,
        provider: str,
    ) -> None:
        """Log a query and response"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'query',
            'query': prompt.user_query,
            'template': prompt.template_name,
            'provider': provider,
            'model': response.metadata.get('model', ''),
            'duration_ms': duration_ms,
            'intent': response.intent.value,
            'commands_count': len(response.commands),
            'risk_score': response.safety.risk_score,
            'dangerous': response.safety.dangerous,
        }
        
        self._write_log(log_entry)
    
    def log_execution(
        self,
        command_id: str,
        command: str,
        success: bool,
        output: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log command execution"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'execution',
            'command_id': command_id,
            'command': command,
            'success': success,
            'output': output[:500] if output else None,
            'error': error[:500] if error else None,
        }
        
        self._write_log(log_entry)
    
    def log_error(self, error: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Log an error"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'error',
            'error': error,
            'context': context or {},
        }
        
        self._write_log(log_entry)
        self.logger.error(error, extra=context or {})
    
    def log_safety_warning(
        self,
        command: str,
        risk_score: float,
        warnings: list[str],
        approved: bool,
    ) -> None:
        """Log safety warnings"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'safety_warning',
            'command': command,
            'risk_score': risk_score,
            'warnings': warnings,
            'approved': approved,
        }
        
        self._write_log(log_entry)
        self.logger.warning(f"Safety warning for command: {command}", extra={'risk_score': risk_score})
    
    def log_provider_health(self, provider: str, healthy: bool, latency_ms: Optional[float]) -> None:
        """Log provider health check"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'provider_health',
            'provider': provider,
            'healthy': healthy,
            'latency_ms': latency_ms,
        }
        
        self._write_log(log_entry)
    
    def save_trace(
        self,
        trace_id: str,
        prompt: Prompt,
        response: LLMResponse,
        metadata: Dict[str, Any],
    ) -> None:
        """Save detailed trace for debugging"""
        trace_data = {
            'trace_id': trace_id,
            'timestamp': datetime.now().isoformat(),
            'prompt': {
                'user_query': prompt.user_query,
                'system_context': prompt.system_context,
                'history': prompt.history,
                'template_name': prompt.template_name,
                'shell_type': prompt.shell_type,
            },
            'response': {
                'intent': response.intent.value,
                'explanation': response.explanation,
                'commands': [
                    {
                        'id': cmd.id,
                        'cmd': cmd.cmd,
                        'description': cmd.description,
                        'risk_score': cmd.risk_score,
                    }
                    for cmd in response.commands
                ],
                'safety': {
                    'risk_score': response.safety.risk_score,
                    'warnings': response.safety.warnings,
                    'dangerous': response.safety.dangerous,
                },
                'metadata': response.metadata,
                'raw_response': response.raw_response,
            },
            'metadata': metadata,
        }
        
        trace_file = self.trace_dir / f"{trace_id}.json"
        with open(trace_file, 'w') as f:
            json.dump(trace_data, f, indent=2)
    
    def _write_log(self, entry: Dict[str, Any]) -> None:
        """Write log entry to file"""
        log_file = self.logs_dir / f"heybud_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def get_logs(self, date: Optional[str] = None, log_type: Optional[str] = None) -> list[Dict[str, Any]]:
        """Retrieve logs for a specific date"""
        if date:
            log_file = self.logs_dir / f"heybud_{date}.jsonl"
        else:
            log_file = self.logs_dir / f"heybud_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        if not log_file.exists():
            return []
        
        logs = []
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if log_type is None or entry.get('type') == log_type:
                        logs.append(entry)
                except:
                    continue
        
        return logs
