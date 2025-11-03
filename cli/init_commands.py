"""
Additional CLI commands for init, config, providers, and plugins
"""
import os
import sys
from pathlib import Path
from typing import Optional
import shutil

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel

from core.config import ConfigManager
from core.types import ProviderConfig, ProviderType, FailoverStrategy
from core.orchestrator import ProviderOrchestrator
from core.logger import HeybudLogger

console = Console()


class InitCommand:
    """Interactive initialization"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.logger = HeybudLogger()
    
    def run(self) -> int:
        """Run interactive setup"""
        console.print(Panel(
            "[bold blue]Welcome to heybud v1![/bold blue]\n\n"
            "Let's set up your LLM providers and preferences.",
            title="🤖 heybud init",
            border_style="blue",
        ))
        console.print()
        
        # Configure providers
        providers = self._configure_providers()
        
        if not providers:
            console.print("[red]No providers configured. Exiting.[/red]")
            return 1
        
        # Configure failover strategy
        failover = self._configure_failover()
        
        # Configure shell
        shell = self._configure_shell()
        
        # Telemetry opt-in
        telemetry = self._configure_telemetry()
        
        # Save configuration
        self.config_manager.config.providers = providers
        self.config_manager.config.failover_strategy = failover
        self.config_manager.config.shell.preferred = shell
        self.config_manager.config.telemetry.enabled = telemetry
        self.config_manager.save_config()
        
        console.print()
        console.print("[green]✓ Configuration saved![/green]")
        
        # Install shell wrapper
        if Confirm.ask("Install shell wrapper function?", default=True):
            self._install_shell_wrapper(shell)
        
        console.print()
        console.print(Panel(
            "[green]Setup complete![/green]\n\n"
            "Try: [bold]heybud \"create a python virtual environment\"[/bold]",
            title="🎉 Ready to go!",
            border_style="green",
        ))
        
        return 0
    
    def _configure_providers(self) -> list[ProviderConfig]:
        """Configure LLM providers"""
        console.print("[bold]Configure LLM Providers[/bold]")
        console.print("You can configure multiple providers for failover.\n")
        
        providers = []
        
        available = {
            "1": ("OpenAI (GPT-4, GPT-3.5)", ProviderType.OPENAI, "gpt-4o-mini", "OPENAI_API_KEY"),
            "2": ("Anthropic (Claude)", ProviderType.ANTHROPIC, "claude-3-5-sonnet-20241022", "ANTHROPIC_API_KEY"),
            "3": ("Google Gemini", ProviderType.GEMINI, "gemini-2.5-flash", "GOOGLE_API_KEY"),
            "4": ("Ollama (Local)", ProviderType.OLLAMA, "llama3", None),
            "5": ("Hugging Face", ProviderType.HUGGINGFACE, "meta-llama/Llama-2-7b-chat-hf", "HUGGINGFACE_API_KEY"),
            "6": ("llama.cpp (Local)", ProviderType.LOCAL_LLAMA, "", None),
        }
        
        table = Table(title="Available Providers")
        table.add_column("Option", style="cyan")
        table.add_column("Provider", style="green")
        table.add_column("Cost", style="yellow")
        
        for key, (name, _, _, _) in available.items():
            cost = "Free (local)" if "Local" in name else "Paid API"
            table.add_row(key, name, cost)
        
        console.print(table)
        console.print()
        
        while True:
            choice = Prompt.ask("Select provider (or 'done' to finish)", default="1")
            
            if choice.lower() == 'done':
                break
            
            if choice not in available:
                console.print("[red]Invalid choice[/red]")
                continue
            
            name, provider_type, default_model, api_key_name = available[choice]
            
            # Configure this provider
            provider_id = Prompt.ask("Provider ID", default=provider_type.value)
            priority = int(Prompt.ask("Priority (1=highest)", default=str(len(providers) + 1)))
            model = Prompt.ask("Model", default=default_model)
            
            # API key or endpoint
            if provider_type in [ProviderType.OLLAMA, ProviderType.LOCAL_LLAMA]:
                endpoint = Prompt.ask("Endpoint/path", default="http://127.0.0.1:11434" if provider_type == ProviderType.OLLAMA else "llama")
                api_key = None
                api_key_name = None
            else:
                # Check if API key exists in environment
                existing_key = os.getenv(api_key_name or "") if api_key_name else None
                
                if existing_key:
                    console.print(f"[green]✓ Found API key in {api_key_name}[/green]")
                    api_key = existing_key
                else:
                    api_key = Prompt.ask(f"API key (or env var name)", password=True)
                    
                    # Save to credentials file if it's an actual key
                    if api_key and not api_key.startswith('$'):
                        self.config_manager.save_credential(provider_id, api_key)
                        console.print(f"[green]✓ API key saved to ~/.heybud/credentials.json[/green]")
                
                endpoint = None
            
            provider = ProviderConfig(
                id=provider_id,
                provider=provider_type,
                priority=priority,
                model=model,
                api_key_name=api_key_name,
                api_key=api_key,
                endpoint=endpoint,
            )
            
            # Test provider
            if Confirm.ask("Test this provider?", default=True):
                if self._test_provider(provider):
                    providers.append(provider)
                    console.print(f"[green]✓ {name} configured successfully[/green]\n")
                else:
                    console.print(f"[red]✗ {name} test failed[/red]\n")
                    if not Confirm.ask("Add anyway?", default=False):
                        continue
                    providers.append(provider)
            else:
                providers.append(provider)
            
            if not Confirm.ask("Add another provider?", default=False):
                break
        
        return providers
    
    def _test_provider(self, config: ProviderConfig) -> bool:
        """Test provider connection"""
        try:
            from core.orchestrator import ProviderOrchestrator
            orchestrator = ProviderOrchestrator([config])
            
            console.print("[dim]Testing connection...[/dim]")
            health = orchestrator.health_check_all()
            
            if health and health[0].healthy:
                console.print(f"[green]✓ Healthy (latency: {health[0].latency_ms:.0f}ms)[/green]")
                return True
            else:
                error = health[0].error if health else "Unknown error"
                console.print(f"[red]✗ Health check failed: {error}[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            return False
    
    def _configure_failover(self) -> FailoverStrategy:
        """Configure failover strategy"""
        console.print("\n[bold]Failover Strategy[/bold]")
        console.print("1. first_available - Try providers in priority order")
        console.print("2. round_robin - Distribute requests across providers")
        console.print("3. fallback - Primary with fallback on failure\n")
        
        choice = Prompt.ask("Select strategy", choices=["1", "2", "3"], default="1")
        
        strategies = {
            "1": FailoverStrategy.FIRST_AVAILABLE,
            "2": FailoverStrategy.ROUND_ROBIN,
            "3": FailoverStrategy.FALLBACK,
        }
        
        return strategies[choice]
    
    def _configure_shell(self) -> str:
        """Configure shell preference"""
        console.print("\n[bold]Shell Preference[/bold]")
        
        # Detect current shell
        current_shell = os.environ.get('SHELL', '/bin/bash').split('/')[-1]
        
        shell = Prompt.ask("Preferred shell", choices=["bash", "zsh", "fish"], default=current_shell)
        return shell
    
    def _configure_telemetry(self) -> bool:
        """Configure telemetry"""
        console.print("\n[bold]Telemetry[/bold]")
        console.print("heybud can collect anonymous usage statistics to improve the tool.")
        console.print("No command contents or sensitive data will be sent.\n")
        
        return Confirm.ask("Enable telemetry?", default=False)
    
    def _install_shell_wrapper(self, shell: str) -> None:
        """Install shell wrapper function"""
        wrapper_file = Path(__file__).parent / "shell_wrapper_templates" / f"heybud.{shell}"
        
        if not wrapper_file.exists():
            console.print(f"[red]Shell wrapper for {shell} not found[/red]")
            return
        
        # Determine RC file
        rc_files = {
            "bash": Path.home() / ".bashrc",
            "zsh": Path.home() / ".zshrc",
            "fish": Path.home() / ".config" / "fish" / "config.fish",
        }
        
        rc_file = rc_files.get(shell)
        
        if not rc_file:
            console.print(f"[red]Unknown shell: {shell}[/red]")
            return
        
        # Read wrapper content
        with open(wrapper_file, 'r') as f:
            wrapper_content = f.read()
        
        # Check if already installed
        if rc_file.exists():
            with open(rc_file, 'r') as f:
                if 'heybud shell wrapper' in f.read():
                    console.print(f"[yellow]Shell wrapper already installed in {rc_file}[/yellow]")
                    return
        
        # Append to RC file
        try:
            rc_file.parent.mkdir(exist_ok=True, parents=True)
            
            with open(rc_file, 'a') as f:
                f.write(f"\n# heybud shell wrapper (added by heybud init)\n")
                f.write(wrapper_content)
                f.write("\n")
            
            console.print(f"[green]✓ Shell wrapper installed to {rc_file}[/green]")
            console.print(f"[yellow]Run: source {rc_file} (or restart your shell)[/yellow]")
            
        except Exception as e:
            console.print(f"[red]Failed to install wrapper: {e}[/red]")
            console.print(f"\nManual installation:\nAdd the following to {rc_file}:\n")
            console.print(Panel(wrapper_content, border_style="dim"))


class ConfigCommand:
    """Configuration management"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
    
    def get(self, key: str) -> int:
        """Get config value"""
        value = self.config_manager.get_config_value(key)
        
        if value is None:
            console.print(f"[red]Config key not found: {key}[/red]")
            return 1
        
        console.print(f"{key} = {value}")
        return 0
    
    def set(self, key: str, value: str) -> int:
        """Set config value"""
        # Try to parse value
        parsed_value = value
        if value.lower() in ('true', 'yes'):
            parsed_value = True
        elif value.lower() in ('false', 'no'):
            parsed_value = False
        elif value.isdigit():
            parsed_value = int(value)
        elif value.replace('.', '').isdigit():
            parsed_value = float(value)
        
        if self.config_manager.set_config_value(key, parsed_value):
            console.print(f"[green]✓ {key} = {parsed_value}[/green]")
            return 0
        else:
            console.print(f"[red]Failed to set {key}[/red]")
            return 1


class ProvidersCommand:
    """Provider management"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
    
    def list_providers(self) -> int:
        """List configured providers"""
        if not self.config_manager.config.providers:
            console.print("[yellow]No providers configured. Run 'heybud init'[/yellow]")
            return 1
        
        table = Table(title="Configured Providers")
        table.add_column("ID", style="cyan")
        table.add_column("Provider", style="green")
        table.add_column("Model", style="blue")
        table.add_column("Priority", style="yellow")
        table.add_column("Status", style="magenta")
        
        orchestrator = ProviderOrchestrator(
            self.config_manager.config.providers,
            self.config_manager.config.failover_strategy,
        )
        
        health_statuses = orchestrator.health_check_all()
        
        for provider, health in zip(self.config_manager.config.providers, health_statuses):
            status = f"✓ {health.latency_ms:.0f}ms" if health.healthy else f"✗ {health.error or 'Failed'}"
            
            table.add_row(
                provider.id,
                provider.provider.value,
                provider.model,
                str(provider.priority),
                status,
            )
        
        console.print(table)
        
        orchestrator.close_all()
        return 0


class LogCommand:
    """Log viewing"""
    
    def __init__(self):
        self.logger = HeybudLogger()
    
    def show_logs(self, date: Optional[str] = None, log_type: Optional[str] = None) -> int:
        """Show logs"""
        logs = self.logger.get_logs(date, log_type)
        
        if not logs:
            console.print("[yellow]No logs found[/yellow]")
            return 1
        
        for entry in logs[-20:]:  # Last 20 entries
            timestamp = entry.get('timestamp', '')
            entry_type = entry.get('type', '')
            
            if entry_type == 'query':
                console.print(f"[dim]{timestamp}[/dim] [cyan]QUERY[/cyan] {entry.get('query', '')[:50]}...")
            elif entry_type == 'execution':
                status = "✓" if entry.get('success') else "✗"
                console.print(f"[dim]{timestamp}[/dim] [green]EXEC[/green] {status} {entry.get('command', '')[:50]}...")
            elif entry_type == 'error':
                console.print(f"[dim]{timestamp}[/dim] [red]ERROR[/red] {entry.get('error', '')[:50]}...")
        
        return 0
