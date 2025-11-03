"""
filebud - File operations helper plugin for heybud
"""
import os
import re
from pathlib import Path
from typing import Optional, Dict, Any

from plugins.plugin_api import HeybudPlugin, HeybudAPI, CommandSuggestion


class FileBudPlugin(HeybudPlugin):
    """Plugin for file operations"""
    
    name = "filebud"
    version = "1.0.0"
    description = "File and directory operations helper"
    author = "heybud"
    
    def __init__(self):
        self.api: Optional[HeybudAPI] = None
    
    def register(self, api: HeybudAPI) -> None:
        """Register plugin"""
        self.api = api
        api.log("filebud_registered", {"version": self.version})
    
    def handle_query(self, query: str, context: Dict[str, Any]) -> Optional[CommandSuggestion]:
        """Handle file-related queries"""
        query_lower = query.lower()
        
        # File/directory keywords
        file_keywords = ['file', 'directory', 'folder', 'create', 'delete', 'move', 'copy', 'find', 'search']
        
        if not any(keyword in query_lower for keyword in file_keywords):
            return None
        
        # Create directory
        if 'create' in query_lower and ('directory' in query_lower or 'folder' in query_lower):
            dir_name = self._extract_path(query)
            if dir_name:
                return CommandSuggestion(
                    command=f"mkdir -p {dir_name}",
                    description=f"Create directory: {dir_name}",
                    risk_score=0.1,
                )
        
        # Create file
        if 'create' in query_lower and 'file' in query_lower:
            file_name = self._extract_path(query)
            if file_name:
                return CommandSuggestion(
                    command=f"touch {file_name}",
                    description=f"Create file: {file_name}",
                    risk_score=0.1,
                )
        
        # List files
        if any(word in query_lower for word in ['list', 'show', 'display']) and 'file' in query_lower:
            return CommandSuggestion(
                command="ls -lah",
                description="List all files with details",
                risk_score=0.0,
            )
        
        # Find files
        if 'find' in query_lower or 'search' in query_lower:
            pattern = self._extract_pattern(query)
            if pattern:
                return CommandSuggestion(
                    command=f"find . -name '*{pattern}*'",
                    description=f"Find files matching: {pattern}",
                    risk_score=0.0,
                )
        
        # Copy files
        if 'copy' in query_lower:
            paths = self._extract_two_paths(query)
            if paths:
                src, dst = paths
                return CommandSuggestion(
                    command=f"cp -r {src} {dst}",
                    description=f"Copy {src} to {dst}",
                    risk_score=0.2,
                )
        
        # Move/rename files
        if 'move' in query_lower or 'rename' in query_lower:
            paths = self._extract_two_paths(query)
            if paths:
                src, dst = paths
                return CommandSuggestion(
                    command=f"mv {src} {dst}",
                    description=f"Move/rename {src} to {dst}",
                    risk_score=0.3,
                )
        
        # Delete files (high risk)
        if 'delete' in query_lower or 'remove' in query_lower:
            path = self._extract_path(query)
            if path and not path.startswith('/'):  # Don't allow absolute paths
                return CommandSuggestion(
                    command=f"rm -rf {path}",
                    description=f"Delete: {path}",
                    risk_score=0.8,  # High risk
                )
        
        return None
    
    def _extract_path(self, query: str) -> Optional[str]:
        """Extract file/directory path from query"""
        # Look for quoted strings
        matches = re.findall(r'"([^"]+)"', query)
        if matches:
            return matches[0]
        
        # Look for common patterns
        match = re.search(r'(?:called|named)\s+(\S+)', query, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_pattern(self, query: str) -> Optional[str]:
        """Extract search pattern from query"""
        # Look for quoted strings
        matches = re.findall(r'"([^"]+)"', query)
        if matches:
            return matches[0]
        
        # Look for "for X"
        match = re.search(r'for\s+(\S+)', query, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_two_paths(self, query: str) -> Optional[tuple[str, str]]:
        """Extract source and destination paths"""
        # Look for quoted strings
        matches = re.findall(r'"([^"]+)"', query)
        if len(matches) >= 2:
            return (matches[0], matches[1])
        
        # Look for "from X to Y"
        match = re.search(r'from\s+(\S+)\s+to\s+(\S+)', query, re.IGNORECASE)
        if match:
            return (match.group(1), match.group(2))
        
        return None
