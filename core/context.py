"""
Context management for tracking session state, environment, and history
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import subprocess

from .types import ExecutionContext, LLMResponse, Command


class ContextManager:
    """Manage execution context and session state"""
    
    def __init__(self, heybud_dir: Optional[Path] = None):
        self.heybud_dir = heybud_dir or Path.home() / ".heybud"
        self.heybud_dir.mkdir(exist_ok=True)
        
        self.context_file = self.heybud_dir / "context.json"
        self.last_command_file = self.heybud_dir / "last_command.json"
        
        self.context = self._load_context()
    
    def _load_context(self) -> ExecutionContext:
        """Load context from file or create new"""
        if self.context_file.exists():
            try:
                with open(self.context_file, 'r') as f:
                    data = json.load(f)
                    return ExecutionContext(**data)
            except:
                pass
        
        # Create new context
        return self._detect_context()
    
    def _detect_context(self) -> ExecutionContext:
        """Detect current execution context"""
        cwd = os.getcwd()
        shell = os.environ.get('SHELL', 'bash').split('/')[-1]
        env = dict(os.environ)
        
        # Detect virtual environment
        venv_path = None
        if 'VIRTUAL_ENV' in os.environ:
            venv_path = os.environ['VIRTUAL_ENV']
        elif os.path.exists('./venv'):
            venv_path = './venv'
        elif os.path.exists('./.venv'):
            venv_path = './.venv'
        
        # Detect git repo
        git_repo = None
        git_branch = None
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=2,
            )
            if result.returncode == 0:
                git_repo = result.stdout.strip()
                
                # Get branch
                result = subprocess.run(
                    ['git', 'branch', '--show-current'],
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                    timeout=2,
                )
                if result.returncode == 0:
                    git_branch = result.stdout.strip()
        except:
            pass
        
        return ExecutionContext(
            cwd=cwd,
            shell=shell,
            env=env,
            venv_path=venv_path,
            git_repo=git_repo,
            git_branch=git_branch,
            timestamp=datetime.now().isoformat(),
        )
    
    def save_context(self) -> None:
        """Save context to file"""
        # Update timestamp
        self.context.timestamp = datetime.now().isoformat()
        
        # Convert to dict (exclude large env dict)
        data = {
            'cwd': self.context.cwd,
            'shell': self.context.shell,
            'venv_path': self.context.venv_path,
            'git_repo': self.context.git_repo,
            'git_branch': self.context.git_branch,
            'session_id': self.context.session_id,
            'timestamp': self.context.timestamp,
        }
        
        with open(self.context_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Ensure secure permissions
        os.chmod(self.context_file, 0o600)
    
    def save_last_command(self, response: LLMResponse) -> None:
        """Save last command for 'heybud okay' to execute"""
        data = {
            'intent': response.intent.value,
            'explanation': response.explanation,
            'commands': [
                {
                    'id': cmd.id,
                    'cmd': cmd.cmd,
                    'description': cmd.description,
                    'runnable': cmd.runnable,
                    'cwd': cmd.cwd,
                    'env': cmd.env,
                    'risk_score': cmd.risk_score,
                }
                for cmd in response.commands
            ],
            'safety': {
                'risk_score': response.safety.risk_score,
                'warnings': response.safety.warnings,
                'dangerous': response.safety.dangerous,
                'patterns_matched': response.safety.patterns_matched,
            },
            'metadata': response.metadata,
            'timestamp': datetime.now().isoformat(),
        }
        
        with open(self.last_command_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        os.chmod(self.last_command_file, 0o600)
    
    def load_last_command(self) -> Optional[LLMResponse]:
        """Load last saved command"""
        if not self.last_command_file.exists():
            return None
        
        try:
            with open(self.last_command_file, 'r') as f:
                data = json.load(f)
            
            from .types import IntentType, Command, SafetyAnalysis
            
            commands = [
                Command(**cmd_data)
                for cmd_data in data.get('commands', [])
            ]
            
            safety_data = data.get('safety', {})
            safety = SafetyAnalysis(
                risk_score=safety_data.get('risk_score', 0.0),
                warnings=safety_data.get('warnings', []),
                dangerous=safety_data.get('dangerous', False),
                patterns_matched=safety_data.get('patterns_matched', []),
            )
            
            return LLMResponse(
                intent=IntentType(data.get('intent', 'runnable_command')),
                explanation=data.get('explanation', ''),
                commands=commands,
                safety=safety,
                metadata=data.get('metadata', {}),
                raw_response=None,
            )
        except Exception as e:
            print(f"Error loading last command: {e}")
            return None
    
    def update_venv(self, venv_path: str) -> None:
        """Update virtual environment path"""
        self.context.venv_path = venv_path
        self.save_context()
    
    def update_cwd(self, cwd: str) -> None:
        """Update current working directory"""
        self.context.cwd = cwd
        self.save_context()
    
    def get_context_prompt(self) -> str:
        """Generate context string for LLM prompts"""
        parts = []
        
        parts.append(f"Current directory: {self.context.cwd}")
        parts.append(f"Shell: {self.context.shell}")
        
        if self.context.venv_path:
            parts.append(f"Active Python venv: {self.context.venv_path}")
        
        if self.context.git_repo:
            parts.append(f"Git repository: {self.context.git_repo}")
            if self.context.git_branch:
                parts.append(f"Git branch: {self.context.git_branch}")
        
        return "\n".join(parts)
    
    def refresh(self) -> None:
        """Refresh context by re-detecting environment"""
        self.context = self._detect_context()
        self.save_context()
