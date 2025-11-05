"""
CLI commands implementation
"""
import sys
import os
import time
from pathlib import Path
from typing import Optional
import uuid

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.status import Status
from rich.text import Text

from core.config import ConfigManager
from core.context import ContextManager
from core.logger import HeybudLogger
from core.orchestrator import ProviderOrchestrator
from core.prompt_template import PromptTemplateManager
from core.parser import ResponseParser
from core.safety import SafetyScanner
from core.types import (
    GenerateOptions,
    Prompt,
    IntentType,
    ProviderConfig,
    ProviderType,
    FailoverStrategy,
)

console = Console(stderr=True)

class Commands:
    """CLI command implementations"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.context_manager = ContextManager()
        self.logger = HeybudLogger()
        self.template_manager = PromptTemplateManager()
        self.debug = os.getenv('HEYBUD_DEBUG', '').lower() in ('1', 'true', 'yes')
    
    def query(self, user_query: str, stream: bool = True, dry_run: bool = False) -> int:
        """Handle a user query and generate responses/commands"""
        try:
            if not self.config_manager.config.providers:
                console.print("[red]No providers configured. Run 'heybud init' first.[/red]")
                return 1
            
            # Refresh context
            self.context_manager.refresh()
            
            # Classify query into chat vs command intent
            mode = self._classify_query(user_query)
            template_name = "assistant_chat" if mode == "chat" else "hybrid_command"

            # Create prompt
            context_str = self.context_manager.get_context_prompt()
            prompt = self.template_manager.render_prompt(
                template_name=template_name,
                user_query=user_query,
                context=context_str,
                shell_type=self.config_manager.config.shell.preferred,
            )
            
            # Create orchestrator
            orchestrator = ProviderOrchestrator(
                self.config_manager.config.providers,
                self.config_manager.config.failover_strategy,
            )
            
            # Generate response
            start_time = time.time()
            
            response = None
            explanation_streamed = False

            do_stream = stream

            if do_stream:                
                from rich.live import Live
                displayed_text = ""
                
                with Live(Panel(Status("Thinking...", spinner="dots"), title="heybud", title_align="left", border_style="blue"), 
                          refresh_per_second=20, 
                          console=console) as live:
                    
                    def render_panel_with_body(body_renderable):
                        return Panel(
                            body_renderable,
                            title="heybud",
                            title_align="left",
                            border_style="blue",
                        )
          
                    def on_chunk_animated(chunk: str):
                        nonlocal displayed_text
                        for char in chunk:
                            displayed_text += char
                            # Stream the explanation as Markdown inside the same panel
                            live.update(render_panel_with_body(Markdown(displayed_text)))
                            time.sleep(0.01)

                    # Stream tokens
                    response = orchestrator.generate(
                        prompt,
                        GenerateOptions(
                            max_tokens=self.config_manager.config.safety.max_tokens,
                            temperature=self.config_manager.config.safety.temperature,
                            stream=True,
                        ),
                        stream=True,
                        on_chunk=on_chunk_animated,
                    )

                    # After streaming completes, run a quick safety scan and append runnable commands (if any)
                    if response and response.commands:
                        scanner = SafetyScanner(self.config_manager.config.safety)
                        safety_analysis = scanner.scan_commands(response.commands)
                        response.safety = safety_analysis
                        for cmd in response.commands:
                            cmd_analysis = scanner.scan_command(cmd)
                            cmd.risk_score = cmd_analysis.risk_score

                        # Build a bash snippet for display (non-executable here)
                        snippet_lines = ["#heybud_runnable"]
                        # Mirror cwd/env in the snippet for context
                        for cmd in response.commands:
                            if cmd.cwd:
                                snippet_lines.append(f"cd {cmd.cwd}")
                            for k, v in (cmd.env or {}).items():
                                snippet_lines.append(f"export {k}='{v}'")
                            if cmd.cmd:
                                snippet_lines.append(cmd.cmd)
                        snippet = "\n".join(snippet_lines).strip()

                        # Minimal high-risk flag if any command is high risk
                        high_risk = any((getattr(cmd, 'risk_score', 0.0) or 0.0) >= 0.7 for cmd in response.commands)
                        parts = [Markdown(displayed_text.strip())]
                        parts.append(Syntax(snippet or "# No runnable commands", "bash", theme="monokai", word_wrap=True))
                        if high_risk:
                            parts.append(Text("HIGH RISK", style="bold red"))
                        body = Group(*parts)
                        live.update(render_panel_with_body(body))
                        # Keep the final view stable for a brief moment
                        time.sleep(0.1)
                
                explanation_streamed = True
            else:
                with console.status("Thinking...", spinner="dots"):
                    response = orchestrator.generate(
                        prompt,
                        GenerateOptions(
                            max_tokens=self.config_manager.config.safety.max_tokens,
                            temperature=self.config_manager.config.safety.temperature,
                        ),
                    )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Safety scan (skip recomputation if already done during streaming)
            if not (do_stream and explanation_streamed):
                scanner = SafetyScanner(self.config_manager.config.safety)
                safety_analysis = scanner.scan_commands(response.commands)
                response.safety = safety_analysis
                
                # Update command risk scores
                for cmd in response.commands:
                    cmd_analysis = scanner.scan_command(cmd)
                    cmd.risk_score = cmd_analysis.risk_score
            
            # Log query
            self.logger.log_query(
                prompt,
                response,
                duration_ms,
                response.metadata.get('provider', 'unknown'),
            )
            
            # Save for 'heybud okay'
            self.context_manager.save_last_command(response)
            
            # Display response
            # If we streamed and already rendered the commands panel, skip re-displaying
            self._display_response(
                response,
                dry_run,
                explanation_already_streamed=explanation_streamed,
                commands_already_displayed=do_stream and explanation_streamed and bool(response.commands),
            )
            
            # Close orchestrator
            orchestrator.close_all()
            
            return 0
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if self.debug:
                import traceback
                console.print(traceback.format_exc())
            self.logger.log_error(str(e), {'query': user_query})
            return 1
        

    def okay(self, force: bool = False, dry_run: bool = False) -> int:
        """Execute the last generated command"""
        try:
            # Load last command
            response = self.context_manager.load_last_command()
            
            if not response:
                console.print("[yellow]No command to execute. Run a query first.[/yellow]")
                return 1
            
            if not response.commands:
                console.print("[yellow]No executable commands found.[/yellow]")
                return 1
            
            # Safety check
            scanner = SafetyScanner(self.config_manager.config.safety)
            safety_analysis = scanner.scan_commands(response.commands)
            
            if safety_analysis.dangerous and not force:
                console.print(Panel(
                    f"[red]⚠️  DANGEROUS COMMAND DETECTED[/red]\n\n"
                    f"Risk score: {safety_analysis.risk_score:.2f}\n\n"
                    f"Warnings:\n" + "\n".join(f"  • {w}" for w in safety_analysis.warnings),
                    title="Safety Warning",
                    border_style="red",
                ))
                console.print("\nTo execute anyway, use: [bold]heybud okay --force[/bold]")
                
                # Log safety warning
                self.logger.log_safety_warning(
                    " && ".join(cmd.cmd for cmd in response.commands),
                    safety_analysis.risk_score,
                    safety_analysis.warnings,
                    approved=False,
                )
                
                return 1
            
            if safety_analysis.dangerous and force:
                self.logger.log_safety_warning(
                    " && ".join(cmd.cmd for cmd in response.commands),
                    safety_analysis.risk_score,
                    safety_analysis.warnings,
                    approved=True,
                )
            
            # Generate shell script with #EXEC_NOW marker
            script_lines = ["#EXEC_NOW"]
            script_lines.append(f"# heybud: {response.metadata.get('prompt_id', 'unknown')}")
            script_lines.append("")
            
            for cmd in response.commands:
                if not cmd.runnable:
                    continue
                
                # Add environment variables
                for key, value in cmd.env.items():
                    script_lines.append(f"export {key}='{value}'")
                
                # Add command
                if cmd.cwd:
                    script_lines.append(f"cd {cmd.cwd}")
                
                script_lines.append(cmd.cmd)
                script_lines.append("")
            
            script = "\n".join(script_lines)
            
            if dry_run:
                console.print(Panel(
                    Syntax(script, "bash", theme="monokai"),
                    title="Dry Run - Script that would execute",
                    border_style="blue",
                ))
                return 0
            
            # Output script to stdout (shell wrapper will source it)
            # Use sys.stdout.write to ensure it goes to stdout, not stderr
            sys.stdout.write(script)
            sys.stdout.write("\n")
            sys.stdout.flush()
            
            # Log execution (to log files, not stdout/stderr)
            for cmd in response.commands:
                if cmd.runnable:
                    self.logger.log_execution(
                        cmd.id,
                        cmd.cmd,
                        success=True,  # We don't know actual result
                    )
            
            return 0
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if self.debug:
                import traceback
                console.print(traceback.format_exc())
            return 1

    def explain(self, text: Optional[str] = None) -> int:
        """Explain a command or the last command"""
        try:
            if text is None:
                # Explain last command
                response = self.context_manager.load_last_command()
                if not response:
                    console.print("[yellow]No command to explain.[/yellow]")
                    return 1
                text = " && ".join(cmd.cmd for cmd in response.commands)
            
            text += "\n\nPlease provide a detailed explanation of the above command(s), including what they do and any potential risks."

            self.query(text, stream=True, dry_run=False)
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return 1
    
    def copy_last(self) -> int:
        """Copy last command to clipboard"""
        try:
            import pyperclip
            
            response = self.context_manager.load_last_command()
            if not response or not response.commands:
                console.print("[yellow]No command to copy.[/yellow]")
                return 1
            
            commands_text = "\n".join(cmd.cmd for cmd in response.commands if cmd.runnable)
            pyperclip.copy(commands_text)
            
            console.print("[green]✓ Commands copied to clipboard[/green]")
            return 0
            
        except ImportError:
            console.print("[red]pyperclip not installed. Run: pip install pyperclip[/red]")
            return 1
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return 1
    
    def show_last(self) -> int:
        """Show last command"""
        try:
            response = self.context_manager.load_last_command()
            if not response:
                console.print("[yellow]No saved command.[/yellow]")
                return 1
            
            self._display_response(response, dry_run=False)
            return 0
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return 1
    
    def _display_response(self, response, dry_run: bool = False, explanation_already_streamed: bool = False, commands_already_displayed: bool = False) -> None:
        """Display LLM response"""
        # Unified panel with explanation and a code block for commands
        body_parts = []
        if response.explanation and not explanation_already_streamed:
            body_parts.append(Markdown(response.explanation))

        if response.commands and not commands_already_displayed:
            snippet_lines = ["#heybud_runnable"]
            for cmd in response.commands:
                if cmd.cwd:
                    snippet_lines.append(f"cd {cmd.cwd}")
                for k, v in (cmd.env or {}).items():
                    snippet_lines.append(f"export {k}='{v}'")
                if cmd.cmd:
                    snippet_lines.append(cmd.cmd)
            snippet = "\n".join(snippet_lines).strip()
            body_parts.append(Syntax(snippet or "# No runnable commands", "bash", theme="monokai", word_wrap=True))

            # Minimal high-risk flag beneath the snippet
            if any((getattr(cmd, 'risk_score', 0.0) or 0.0) >= 0.7 for cmd in response.commands):
                body_parts.append(Text("HIGH RISK", style="bold red"))

        if body_parts:
            console.print(Panel(
                Group(*body_parts),
                title="heybud",
                title_align="left",
                border_style="blue",
            ))
            console.print()

        # Quick hints
        if response.commands:
            console.print("[dim]To execute: [/dim][bold green]heybud okay[/bold green]")
            console.print("[dim]To copy: [/dim][bold]heybud copy[/bold]")
        
        # Safety warnings
        if response.safety.warnings:
            console.print()
            console.print(Panel(
                "\n".join(f"⚠️  {w}" for w in response.safety.warnings),
                title="Safety Warnings",
                border_style="yellow",
            ))

    def _classify_query(self, user_query: str) -> str:
        """Heuristic classifier: 'chat' vs 'command' intent"""
        q = user_query.strip().lower()
        # Questions and conversational starters
        chat_starters = (
            "who are you",
            "what is",
            "what's",
            "explain",
            "why",
            "tell me",
            "help",
            "how does",
        )
        command_keywords = (
            "install",
            "create",
            "generate",
            "run ",
            "setup",
            "set up",
            "build",
            "init",
            "configure",
            "upgrade",
            "uninstall",
            "remove",
            "deploy",
        )
        if any(q.startswith(s) for s in chat_starters) or q.endswith("?"):
            return "chat"
        if any(k in q for k in command_keywords):
            return "command"
        # Default to chat to avoid forcing commands
        return "chat"
