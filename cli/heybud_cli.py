#!/usr/bin/env python3
"""
heybud CLI - Main entry point
"""
import sys
import os
import click
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.init_commands import InitCommand, ConfigCommand, ProvidersCommand, LogCommand
from cli.commands import Commands


@click.group(invoke_without_command=True)
@click.pass_context
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--trace', is_flag=True, help='Enable tracing')
@click.option('--no-stream', is_flag=True, help='Disable streaming')
@click.argument('query', nargs=-1, required=False)  
def cli(ctx, debug, trace, no_stream, query):   
    """
    heybud - AI-powered CLI assistant
    
    Examples:
        heybud "create a python virtual environment"
        heybud okay
        heybud explain "rm -rf"
        heybud init
    """

    if debug:
        os.environ['HEYBUD_DEBUG'] = '1'
    
    if trace:
        os.environ['HEYBUD_TRACE'] = '1'

    if query:
        first_arg = query[0]
        if first_arg in ctx.command.commands:
            cmd = ctx.command.commands[first_arg]
            ctx.exit(ctx.invoke(cmd, *query[1:]))
        else:
            query_str = ' '.join(query)
            commands = Commands()
            sys.exit(commands.query(query_str, stream=not no_stream))
    
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@cli.command()
@click.option('--force', is_flag=True, help='Force execution even if dangerous')
@click.option('--dry-run', is_flag=True, help='Show what would be executed without running')
def okay(force, dry_run):
    """Execute the last generated command in same shell"""
    commands = Commands()
    sys.exit(commands.okay(force=force, dry_run=dry_run))

@cli.command()
def explain(*kwargs):
    """Explain a command or the last command"""
    commands = Commands()
    sys.exit(commands.explain(*kwargs))


@cli.command()
def copy():
    """Copy last command to clipboard"""
    commands = Commands()
    sys.exit(commands.copy_last())


@cli.command()
def last():
    """Show the last generated command"""
    commands = Commands()
    sys.exit(commands.show_last())


@cli.command()
def init():
    """Interactive setup wizard"""
    init_cmd = InitCommand()
    sys.exit(init_cmd.run())


@cli.group()
def config():
    """Manage configuration"""
    pass


@config.command()
@click.argument('key')
def get(key):
    """Get a configuration value"""
    config_cmd = ConfigCommand()
    sys.exit(config_cmd.get(key))


@config.command()
@click.argument('key')
@click.argument('value')
def set(key, value):
    """Set a configuration value"""
    config_cmd = ConfigCommand()
    sys.exit(config_cmd.set(key, value))


@cli.group()
def providers():
    """Manage LLM providers"""
    pass


@providers.command('list')
def list_providers():
    """List configured providers and their health status"""
    providers_cmd = ProvidersCommand()
    sys.exit(providers_cmd.list_providers())


@providers.command()
def health():
    """Check health of all providers"""
    providers_cmd = ProvidersCommand()
    sys.exit(providers_cmd.list_providers())


@cli.command()
@click.option('--date', help='Show logs for specific date (YYYYMMDD)')
@click.option('--type', 'log_type', help='Filter by log type')
def log(date, log_type):
    """View heybud logs"""
    log_cmd = LogCommand()
    sys.exit(log_cmd.show_logs(date, log_type))


@cli.command()
def status():
    """Show heybud status and context"""
    from rich.console import Console
    from rich.table import Table
    from core.context import ContextManager
    from core.config import ConfigManager
    
    console = Console()
    context_mgr = ContextManager()
    config_mgr = ConfigManager()
    
    table = Table(title="heybud Status")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Current Directory", context_mgr.context.cwd)
    table.add_row("Shell", context_mgr.context.shell)
    
    if context_mgr.context.venv_path:
        table.add_row("Python venv", context_mgr.context.venv_path)
    
    if context_mgr.context.git_repo:
        table.add_row("Git Repo", context_mgr.context.git_repo)
        if context_mgr.context.git_branch:
            table.add_row("Git Branch", context_mgr.context.git_branch)
    
    table.add_row("Providers", str(len(config_mgr.config.providers)))
    table.add_row("Safe Mode", "✓" if config_mgr.config.safety.safe_mode else "✗")
    
    console.print(table)


@cli.group()
def plugins():
    """Manage heybud plugins"""
    pass


@plugins.command('list')
def list_plugins():
    """List installed plugins"""
    from rich.console import Console
    console = Console()
    console.print("[yellow]Plugin system not yet implemented[/yellow]")


@plugins.command()
@click.argument('plugin_name')
def install(plugin_name):
    """Install a plugin"""
    from rich.console import Console
    console = Console()
    console.print(f"[yellow]Plugin installation not yet implemented: {plugin_name}[/yellow]")


@plugins.command()
@click.argument('plugin_name')
def remove(plugin_name):
    """Remove a plugin"""
    from rich.console import Console
    console = Console()
    console.print(f"[yellow]Plugin removal not yet implemented: {plugin_name}[/yellow]")


@cli.command()
def version():
    """Show heybud version"""
    from rich.console import Console
    console = Console()
    console.print("[bold blue]heybud v1.0.0[/bold blue]")
    console.print("AI-powered CLI assistant with multi-provider LLM support")


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        print("\n[Interrupted]")
        sys.exit(130)
    except Exception as e:
        if os.getenv('HEYBUD_DEBUG'):
            raise
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
