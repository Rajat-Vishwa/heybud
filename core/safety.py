"""
Safety scanner for detecting dangerous command patterns
"""
import re
from typing import List
from .types import Command, SafetyAnalysis, SafetyConfig


class SafetyScanner:
    """Scan commands for dangerous patterns"""
    
    def __init__(self, config: SafetyConfig):
        self.config = config
        self.dangerous_patterns = [
            (r'rm\s+-rf\s+/', 'Recursive force delete from root', 1.0),
            (r'rm\s+-rf\s+\*', 'Recursive force delete all files', 0.9),
            (r'dd\s+if=.*of=/dev/[sh]d', 'Direct disk write', 1.0),
            (r'mkfs\.', 'Format filesystem', 1.0),
            (r':\(\)\s*\{\s*:\|:&\s*\};:', 'Fork bomb', 1.0),
            (r'chmod\s+-R\s+777', 'Overly permissive permissions', 0.7),
            (r'curl.*\|\s*(?:bash|sh)', 'Pipe URL to shell', 0.8),
            (r'wget.*\|\s*(?:bash|sh)', 'Pipe URL to shell', 0.8),
            (r'eval\s+\$\(', 'Eval command substitution', 0.6),
            (r'>\s*/dev/sd[a-z]', 'Write to raw disk', 1.0),
            (r'shutdown|poweroff|reboot', 'System power control', 0.5),
            (r'kill\s+-9\s+1', 'Kill init process', 1.0),
            (r'iptables\s+-F', 'Flush firewall rules', 0.7),
            (r'crontab\s+-r', 'Remove all cron jobs', 0.6),
            (r'/etc/passwd|/etc/shadow', 'Access sensitive files', 0.8),
            (r'sudo\s+su\s+-', 'Switch to root', 0.5),
        ]
        
        # Add user-configured patterns
        for pattern in self.config.dangerous_patterns:
            self.dangerous_patterns.append((pattern, 'User-defined dangerous pattern', 0.8))
    
    def scan_command(self, command: Command) -> SafetyAnalysis:
        """Scan a single command for safety issues"""
        warnings = []
        patterns_matched = []
        max_risk = 0.0
        
        for pattern, description, risk_score in self.dangerous_patterns:
            if re.search(pattern, command.cmd, re.IGNORECASE):
                warnings.append(f"{description}: {command.cmd[:50]}")
                patterns_matched.append(pattern)
                max_risk = max(max_risk, risk_score)
        
        # Additional heuristics
        if '${' in command.cmd or '`' in command.cmd:
            warnings.append("Command contains variable expansion or substitution")
            max_risk = max(max_risk, 0.3)
        
        if command.cmd.count('|') > 2:
            warnings.append("Command has multiple pipes (complex pipeline)")
            max_risk = max(max_risk, 0.2)
        
        dangerous = max_risk >= self.config.risk_threshold
        
        return SafetyAnalysis(
            risk_score=max_risk,
            warnings=warnings,
            dangerous=dangerous,
            patterns_matched=patterns_matched,
        )
    
    def scan_commands(self, commands: List[Command]) -> SafetyAnalysis:
        """Scan multiple commands and return aggregate analysis"""
        all_warnings = []
        all_patterns = []
        max_risk = 0.0
        
        for cmd in commands:
            analysis = self.scan_command(cmd)
            cmd.risk_score = analysis.risk_score
            all_warnings.extend(analysis.warnings)
            all_patterns.extend(analysis.patterns_matched)
            max_risk = max(max_risk, analysis.risk_score)
        
        return SafetyAnalysis(
            risk_score=max_risk,
            warnings=all_warnings,
            dangerous=max_risk >= self.config.risk_threshold,
            patterns_matched=list(set(all_patterns)),
        )
    
    def is_safe_to_execute(self, commands: List[Command]) -> bool:
        """Quick check if commands are safe to execute without confirmation"""
        if not self.config.safe_mode:
            return True
        
        analysis = self.scan_commands(commands)
        return not analysis.dangerous
