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
        Tries JSON parsing first, then falls back to text parsing.
        """
        # Try JSON parsing
        try:
            data = self._extract_json(content)
            if data:
                return self._parse_json(data, content, provider, model)
        except:
            pass
        
        # Fall back to text parsing
        return self._parse_text(content, provider, model)
    
    def _extract_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from content (may be wrapped in markdown code blocks)"""
        # Try direct JSON parse
        try:
            return json.loads(content)
        except:
            pass
        
        # Try to extract from code blocks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[0])
            except:
                pass
        
        # Try to find JSON object anywhere in text
        json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_obj_pattern, content, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and ('commands' in data or 'intent' in data):
                    return data
            except:
                continue
        
        return None
    
    def _parse_json(self, data: Dict[str, Any], raw: str, provider: str, model: str) -> LLMResponse:
        """Parse JSON structured response"""
        intent = IntentType(data.get('intent', 'runnable_command'))
        explanation = data.get('explanation', '')
        
        # Parse commands
        commands = []
        for cmd_data in data.get('commands', []):
            cmd = Command(
                id=cmd_data.get('id', f'c{len(commands)+1}'),
                cmd=cmd_data.get('cmd', ''),
                description=cmd_data.get('description', ''),
                runnable=cmd_data.get('runnable', True),
                cwd=cmd_data.get('cwd'),
                env=cmd_data.get('env', {}),
                risk_score=cmd_data.get('risk_score', 0.0),
            )
            commands.append(cmd)
        
        # Parse safety
        safety_data = data.get('safety', {})
        safety = SafetyAnalysis(
            risk_score=safety_data.get('risk_score', 0.0),
            warnings=safety_data.get('warnings', []),
            dangerous=safety_data.get('dangerous', False),
            patterns_matched=safety_data.get('patterns_matched', []),
        )
        
        # Metadata
        metadata = data.get('metadata', {})
        metadata.update({
            'provider': provider,
            'model': model,
            'prompt_id': metadata.get('prompt_id', str(uuid.uuid4())),
        })
        
        return LLMResponse(
            intent=intent,
            explanation=explanation,
            commands=commands,
            safety=safety,
            metadata=metadata,
            raw_response=raw,
        )
    
    def _parse_text(self, content: str, provider: str, model: str) -> LLMResponse:
        """Parse plain text response and extract commands"""
        # Try to extract bash commands from text
        commands = []
        
        # Look for code blocks
        code_block_pattern = r'```(?:bash|sh|shell)?\s*\n(.*?)\n```'
        code_blocks = re.findall(code_block_pattern, content, re.DOTALL)
        
        for i, block in enumerate(code_blocks):
            # Split into individual commands
            for line in block.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    cmd = Command(
                        id=f'c{len(commands)+1}',
                        cmd=line,
                        description=f'Command {len(commands)+1}',
                        runnable=True,
                        risk_score=0.0,
                    )
                    commands.append(cmd)
        
        # If no code blocks, look for lines that look like commands
        if not commands:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                # Simple heuristic: lines starting with common command patterns
                if any(line.startswith(prefix) for prefix in [
                    'cd ', 'ls ', 'mkdir ', 'touch ', 'echo ', 'cat ',
                    'python ', 'pip ', 'npm ', 'git ', 'docker ',
                    'curl ', 'wget ', 'ssh ', 'scp ', 'rsync ',
                    'grep ', 'find ', 'sed ', 'awk ', 'chmod ', 'chown ',
                ]):
                    cmd = Command(
                        id=f'c{len(commands)+1}',
                        cmd=line,
                        description=f'Extracted command',
                        runnable=True,
                        risk_score=0.0,
                    )
                    commands.append(cmd)
        
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
