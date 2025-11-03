"""
Configuration management for heybud
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from .types import (
    HeybudConfig,
    ProviderConfig,
    SafetyConfig,
    ShellConfig,
    TelemetryConfig,
    ProviderType,
    FailoverStrategy,
)


class ConfigManager:
    """Manage heybud configuration"""
    
    def __init__(self, heybud_dir: Optional[Path] = None):
        self.heybud_dir = heybud_dir or Path.home() / ".heybud"
        self.heybud_dir.mkdir(exist_ok=True, mode=0o700)
        
        self.config_file = self.heybud_dir / "config.json"
        self.credentials_file = self.heybud_dir / "credentials.json"
        
        self.config = self._load_config()
    
    def _load_config(self) -> HeybudConfig:
        """Load configuration from file"""
        if not self.config_file.exists():
            return self._create_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            return self._parse_config(data)
        except Exception as e:
            print(f"Warning: Failed to load config: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> HeybudConfig:
        """Create default configuration"""
        return HeybudConfig(
            providers=[],
            failover_strategy=FailoverStrategy.FIRST_AVAILABLE,
            safety=SafetyConfig(),
            shell=ShellConfig(),
            telemetry=TelemetryConfig(enabled=False),
        )
    
    def _parse_config(self, data: Dict[str, Any]) -> HeybudConfig:
        """Parse configuration from dict"""
        # Parse providers
        providers = []
        for p in data.get('providers', []):
            provider_config = ProviderConfig(
                id=p.get('id'),
                provider=ProviderType(p.get('provider')),
                priority=p.get('priority', 1),
                model=p.get('model', ''),
                api_key_name=p.get('api_key_name'),
                endpoint=p.get('endpoint'),
                max_tokens=p.get('max_tokens', 1024),
                temperature=p.get('temperature', 0.2),
                timeout=p.get('timeout', 30),
                extra=p.get('extra', {}),
            )
            
            # Load API key from environment if specified
            if provider_config.api_key_name:
                provider_config.api_key = os.getenv(provider_config.api_key_name)
            
            # Or load from credentials file
            if not provider_config.api_key:
                provider_config.api_key = self._load_credential(provider_config.id)
            
            providers.append(provider_config)
        
        # Parse safety config
        safety_data = data.get('safety', {})
        safety = SafetyConfig(
            max_tokens=safety_data.get('max_tokens', 1024),
            temperature=safety_data.get('temperature', 0.2),
            safe_mode=safety_data.get('safe_mode', True),
            risk_threshold=safety_data.get('risk_threshold', 0.7),
            require_confirmation=safety_data.get('require_confirmation', True),
            dangerous_patterns=safety_data.get('dangerous_patterns', SafetyConfig().dangerous_patterns),
        )
        
        # Parse shell config
        shell_data = data.get('shell', {})
        shell = ShellConfig(
            preferred=shell_data.get('preferred', 'bash'),
            install_shell_wrapper=shell_data.get('install_shell_wrapper', True),
        )
        
        # Parse telemetry config
        telemetry_data = data.get('telemetry', {})
        telemetry = TelemetryConfig(
            enabled=telemetry_data.get('enabled', False),
            endpoint=telemetry_data.get('endpoint'),
        )
        
        return HeybudConfig(
            providers=providers,
            failover_strategy=FailoverStrategy(data.get('failover_strategy', 'first_available')),
            safety=safety,
            shell=shell,
            telemetry=telemetry,
        )
    
    def save_config(self, config: Optional[HeybudConfig] = None) -> None:
        """Save configuration to file"""
        if config:
            self.config = config
        
        data = {
            'providers': [
                {
                    'id': p.id,
                    'provider': p.provider.value,
                    'priority': p.priority,
                    'model': p.model,
                    'api_key_name': p.api_key_name,
                    'endpoint': p.endpoint,
                    'max_tokens': p.max_tokens,
                    'temperature': p.temperature,
                    'timeout': p.timeout,
                    'extra': p.extra,
                }
                for p in self.config.providers
            ],
            'failover_strategy': self.config.failover_strategy.value,
            'safety': {
                'max_tokens': self.config.safety.max_tokens,
                'temperature': self.config.safety.temperature,
                'safe_mode': self.config.safety.safe_mode,
                'risk_threshold': self.config.safety.risk_threshold,
                'require_confirmation': self.config.safety.require_confirmation,
            },
            'shell': {
                'preferred': self.config.shell.preferred,
                'install_shell_wrapper': self.config.shell.install_shell_wrapper,
            },
            'telemetry': {
                'enabled': self.config.telemetry.enabled,
                'endpoint': self.config.telemetry.endpoint,
            },
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        os.chmod(self.config_file, 0o600)
    
    def _load_credential(self, provider_id: str) -> Optional[str]:
        """Load credential from credentials file"""
        if not self.credentials_file.exists():
            return None
        
        try:
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)
            return credentials.get(provider_id)
        except:
            return None
    
    def save_credential(self, provider_id: str, api_key: str) -> None:
        """Save credential securely"""
        credentials = {}
        if self.credentials_file.exists():
            try:
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
            except:
                pass
        
        credentials[provider_id] = api_key
        
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        os.chmod(self.credentials_file, 0o600)
    
    def get_config_value(self, key_path: str) -> Optional[Any]:
        """Get config value by dot-separated path"""
        parts = key_path.split('.')
        obj = self.config
        
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return None
        
        return obj
    
    def set_config_value(self, key_path: str, value: Any) -> bool:
        """Set config value by dot-separated path"""
        parts = key_path.split('.')
        obj = self.config
        
        # Navigate to parent
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return False
        
        # Set final value
        if hasattr(obj, parts[-1]):
            setattr(obj, parts[-1], value)
            self.save_config()
            return True
        
        return False
