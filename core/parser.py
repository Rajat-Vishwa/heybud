"""
Response parser for structured LLM outputs
"""
import json
import re
from typing import Dict, Any, Optional
import uuid

from .types import (
    LLMResponse,
    Command,
    SafetyAnalysis,
    IntentType,
)


class ResponseParser:
    """Parse LLM responses into structured format"""
    
    def parse(self, content: str, provider: str, model: str) -> LLMResponse:
        """
        Parse LLM response into LLMResponse object.
        New strategy: treat output as natural text and only extract commands
        from bash code blocks that begin with `#heybud_runnable`.
        """
        return self._parse_text(content, provider, model)
    
    # Legacy JSON parsing has been removed in favor of explicit runnable code blocks.
    
    def _parse_text(self, content: str, provider: str, model: str) -> LLMResponse:
        """Parse plain text response and extract commands"""
        # Try to extract bash commands from text
        commands = []
        
        # Look for code blocks
        code_block_pattern = r'```(?:bash|sh|shell)?\s*\n(.*?)\n```'
        code_blocks = re.findall(code_block_pattern, content, re.DOTALL)
        
        for i, block in enumerate(code_blocks):
            # Only parse commands from code blocks explicitly marked as runnable
            # The marker must be the first non-empty line: `#heybud_runnable`
            lines = [l.rstrip() for l in block.split('\n')]
            # Find first non-empty line
            first_non_empty_idx = next((idx for idx, l in enumerate(lines) if l.strip() != ''), None)
            if first_non_empty_idx is None:
                continue
            if lines[first_non_empty_idx].strip() != '#heybud_runnable':
                # Skip unmarked blocks
                continue

            # Collect commands after the marker, skipping comment lines and blanks
            for line in lines[first_non_empty_idx + 1:]:
                stripped = line.strip()
                if not stripped or stripped.startswith('#'):
                    continue
                cmd = Command(
                    id=f'c{len(commands)+1}',
                    cmd=stripped,
                    description=f'Command {len(commands)+1}',
                    runnable=True,
                    risk_score=0.0,
                )
                commands.append(cmd)
        
        # Do not heuristically extract commands from plain text.
        # Only blocks marked with `#heybud_runnable` are considered runnable.
        
        # Extract explanation (text before first code block or all text)
        explanation = content
        if code_blocks:
            explanation = content.split('```')[0].strip()
        
        return LLMResponse(
            intent=IntentType.RUNNABLE_COMMAND if commands else IntentType.EXPLANATION,
            explanation=explanation or content[:500],
            commands=commands,
            safety=SafetyAnalysis(risk_score=0.0),
            metadata={
                'provider': provider,
                'model': model,
                'prompt_id': str(uuid.uuid4()),
                'parsed_from': 'text',
            },
            raw_response=content,
        )
