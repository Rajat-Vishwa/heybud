"""
Plugin loader and manager
"""
import importlib
import sys
from pathlib import Path
from typing import List, Dict, Optional

from .plugin_api import HeybudPlugin, HeybudAPI


class PluginLoader:
    """Load and manage heybud plugins"""
    
    def __init__(self, api: HeybudAPI, plugins_dir: Optional[Path] = None):
        self.api = api
        self.plugins_dir = plugins_dir or Path.home() / ".heybud" / "plugins"
        self.plugins_dir.mkdir(exist_ok=True, parents=True)
        
        self.loaded_plugins: Dict[str, HeybudPlugin] = {}
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins"""
        plugins = []
        
        # Built-in plugins
        builtin_dir = Path(__file__).parent
        for plugin_dir in builtin_dir.glob("*/"):
            if plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists():
                if plugin_dir.name not in ['__pycache__']:
                    plugins.append(plugin_dir.name)
        
        # User plugins
        for plugin_dir in self.plugins_dir.glob("*/"):
            if plugin_dir.is_dir() and (plugin_dir / "__init__.py").exists():
                plugins.append(plugin_dir.name)
        
        return plugins
    
    def load_plugin(self, plugin_name: str) -> bool:
        """Load a single plugin"""
        try:
            # Try built-in first
            builtin_path = Path(__file__).parent / plugin_name
            
            if builtin_path.exists():
                # Add to path and import
                if str(builtin_path.parent) not in sys.path:
                    sys.path.insert(0, str(builtin_path.parent))
                
                module = importlib.import_module(f"plugins.{plugin_name}")
            else:
                # Try user plugins
                user_plugin_path = self.plugins_dir / plugin_name
                
                if not user_plugin_path.exists():
                    return False
                
                if str(user_plugin_path.parent) not in sys.path:
                    sys.path.insert(0, str(user_plugin_path.parent))
                
                module = importlib.import_module(plugin_name)
            
            # Find plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, HeybudPlugin) and attr != HeybudPlugin:
                    plugin_class = attr
                    break
            
            if not plugin_class:
                return False
            
            # Instantiate and register
            plugin = plugin_class()
            plugin.register(self.api)
            
            self.loaded_plugins[plugin_name] = plugin
            return True
            
        except Exception as e:
            print(f"Failed to load plugin {plugin_name}: {e}")
            return False
    
    def load_all_plugins(self) -> None:
        """Load all available plugins"""
        plugins = self.discover_plugins()
        
        for plugin_name in plugins:
            self.load_plugin(plugin_name)
    
    def get_plugin(self, name: str) -> Optional[HeybudPlugin]:
        """Get a loaded plugin by name"""
        return self.loaded_plugins.get(name)
    
    def query_plugins(self, query: str, context: Dict) -> List:
        """Query all plugins for command suggestions"""
        suggestions = []
        
        for plugin in self.loaded_plugins.values():
            try:
                suggestion = plugin.handle_query(query, context)
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                print(f"Plugin {plugin.name} error: {e}")
        
        return suggestions
