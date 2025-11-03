"""
gitbud - Git helper plugin for heybud
"""
import re
import subprocess
from typing import Optional, Dict, Any

from plugins.plugin_api import HeybudPlugin, HeybudAPI, CommandSuggestion


class GitBudPlugin(HeybudPlugin):
    """Plugin for Git operations"""
    
    name = "gitbud"
    version = "1.0.0"
    description = "Git repository helper"
    author = "heybud"
    
    def __init__(self):
        self.api: Optional[HeybudAPI] = None
    
    def register(self, api: HeybudAPI) -> None:
        """Register plugin"""
        self.api = api
        api.log("gitbud_registered", {"version": self.version})
    
    def handle_query(self, query: str, context: Dict[str, Any]) -> Optional[CommandSuggestion]:
        """Handle git-related queries"""
        query_lower = query.lower()
        
        # Check if query is git-related
        git_keywords = ['git', 'commit', 'push', 'pull', 'branch', 'merge', 'clone', 'repository']
        
        if not any(keyword in query_lower for keyword in git_keywords):
            return None
        
        # Only provide suggestions if we're in a git repo
        if not context.get('git_repo'):
            return None
        
        # Common git patterns
        if 'status' in query_lower or 'what changed' in query_lower:
            return CommandSuggestion(
                command="git status",
                description="Show working tree status",
                risk_score=0.0,
            )
        
        if 'commit' in query_lower and 'all' in query_lower:
            msg = self._extract_commit_message(query)
            if msg:
                return CommandSuggestion(
                    command=f'git add -A && git commit -m "{msg}"',
                    description="Stage all changes and commit",
                    risk_score=0.2,
                )
        
        if 'push' in query_lower:
            branch = context.get('git_branch', 'main')
            return CommandSuggestion(
                command=f"git push origin {branch}",
                description=f"Push to origin/{branch}",
                risk_score=0.3,
            )
        
        if 'pull' in query_lower:
            return CommandSuggestion(
                command="git pull",
                description="Pull latest changes",
                risk_score=0.2,
            )
        
        if 'new branch' in query_lower or 'create branch' in query_lower:
            branch_name = self._extract_branch_name(query)
            if branch_name:
                return CommandSuggestion(
                    command=f"git checkout -b {branch_name}",
                    description=f"Create and switch to new branch: {branch_name}",
                    risk_score=0.1,
                )
        
        return None
    
    def _extract_commit_message(self, query: str) -> Optional[str]:
        """Extract commit message from query"""
        # Look for quoted strings
        matches = re.findall(r'"([^"]+)"', query)
        if matches:
            return matches[0]
        
        # Look for "with message X"
        match = re.search(r'(?:with message|message)\s+(.+)', query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    def _extract_branch_name(self, query: str) -> Optional[str]:
        """Extract branch name from query"""
        # Look for quoted strings
        matches = re.findall(r'"([^"]+)"', query)
        if matches:
            return matches[0].replace(' ', '-').lower()
        
        # Look for "called X" or "named X"
        match = re.search(r'(?:called|named)\s+(\S+)', query, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        
        return None
