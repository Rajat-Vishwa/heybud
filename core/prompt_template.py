"""
Prompt template loader and manager
"""
import yaml
from pathlib import Path
from typing import Dict, Optional
import re

from .types import Prompt


class PromptTemplateManager:
    """Load and render prompt templates"""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        if templates_dir is None:
            # Default to package templates
            templates_dir = Path(__file__).parent / "prompt_templates"
        
        self.templates_dir = templates_dir
        self.templates: Dict[str, Dict] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load all YAML templates from directory"""
        if not self.templates_dir.exists():
            return
        
        for template_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(template_file, 'r') as f:
                    template_data = yaml.safe_load(f)
                    name = template_data.get('name', template_file.stem)
                    self.templates[name] = template_data
            except Exception as e:
                print(f"Warning: Failed to load template {template_file}: {e}")
    
    def render_prompt(
        self,
        template_name: str,
        user_query: str,
        context: str = "",
        history: Optional[list] = None,
        shell_type: str = "bash",
    ) -> Prompt:
        """Render a prompt from template"""
        if template_name not in self.templates:
            # Fall back to default command generation
            template_name = "command_generation"
        
        template = self.templates.get(template_name, self.templates.get("command_generation"))
        
        # Render system prompt
        system_prompt = template.get('system_prompt', '')
        system_prompt = self._substitute(system_prompt, {
            'context': context,
            'shell_type': shell_type,
            'history': self._format_history(history or []),
        })
        
        # Render user template
        user_template = template.get('user_template', '{{user_query}}')
        user_message = self._substitute(user_template, {
            'user_query': user_query,
        })
        
        return Prompt(
            user_query=user_message,
            system_context=system_prompt,
            history=history or [],
            template_name=template_name,
            shell_type=shell_type,
        )
    
    def _substitute(self, template: str, variables: Dict[str, str]) -> str:
        """Simple variable substitution in templates"""
        result = template
        for key, value in variables.items():
            pattern = r'\{\{' + re.escape(key) + r'\}\}'
            result = re.sub(pattern, value, result)
        return result
    
    def _format_history(self, history: list) -> str:
        """Format conversation history for prompt"""
        if not history:
            return "No previous conversation"
        
        formatted = []
        for msg in history[-5:]:  # Last 5 messages
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            formatted.append(f"{role}: {content[:200]}")
        
        return "\n".join(formatted)
    
    def get_template_names(self) -> list[str]:
        """Get list of available template names"""
        return list(self.templates.keys())
