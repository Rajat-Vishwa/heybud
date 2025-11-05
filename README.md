# heybud

> **heybud**: Because typing `docker run -p 8080:80 -v /data:/app/data --name myapp myimage:latest` shouldn't require remembering all the flags.

Your friendly AI assistant that lives in your terminal, helping you craft the perfect commands.

heybud is a smart command-line tool that understands what you want to do and suggests the right shell commands. It works right in your current shell session, preserving your environment and context.

## ✨ What makes heybud special

- **Same-shell execution**: Commands run in your active shell, keeping environments, variables, and directory changes
- **Safety first**: Every command gets a risk score and dangerous patterns are flagged
- **Multi-provider support**: Works with OpenAI, Anthropic, Google Gemini, Ollama, and more
- **Context aware**: Remembers your current directory, shell history, and preferences
- **Extensible**: Plugin system for custom functionality
- **Developer friendly**: Clear output, debug modes, and comprehensive logging

## 🚀 Quick Start

```bash
# Install
pip install heybud

# Set up (interactive wizard) 
# (Use heybud-cli when running for the first time)
heybud-cli init 

# Ask for help
heybud "create a python virtual environment"
# Shows: python3 -m venv venv && source venv/bin/activate

# Execute it
heybud okay
```

That's it! Your virtual environment is now active in the same shell.

## 📦 Installation & Setup

For detailed installation instructions, API key configuration, and advanced setup options, see [docs/setup.md](docs/setup.md).

## 💡 What heybud can do

### Command Generation

heybud understands natural language and generates precise shell commands:

```bash
# File operations
heybud "find all python files larger than 1MB"
heybud "compress these log files with gzip"

# Git operations
heybud "create a new branch for feature-x"
heybud "squash the last 3 commits with a message"

# System administration
heybud "check disk usage on all mounted filesystems"
heybud "monitor cpu usage for 10 seconds and show top processes"

# Development workflows
heybud "run mypy on the src directory with strict settings"
heybud "build the docker image with multi-stage build"
heybud "set up nginx reverse proxy for my app"
```

### Command Explanation

Understand what any command does:

```bash
heybud explain "docker run -p 8080:80 --name myapp -v /data:/app/data myimage:latest"
# Explains each flag, volume mounts, port mapping, etc.
```

### Safety & Risk Assessment

Every command is automatically analyzed for safety:

```bash
heybud "delete all files in /tmp"
# ⚠️  WARNING: Dangerous command detected!
# Risk score: 0.85
# Pattern: 'rm -rf /*' matches dangerous deletion
#
# To execute anyway: heybud okay --force
```

<!-- ### Multi-Provider Intelligence

Choose from multiple AI providers based on your needs:

```bash
# Use different providers for different tasks
heybud "optimize this sql query" --provider ollama        # Local, fast
heybud "write a complex regex" --provider openai          # High quality
heybud "debug this error message" --provider anthropic    # Detailed analysis
``` -->

### Plugin System (IN DEVELOPMENT)

Extend heybud with specialized plugins:

```bash
# Built-in plugins
heybud "git status"              # gitbud: Enhanced git operations
heybud "read this file"          # filebud: Smart file operations
heybud "analyze this codebase"   # codebud: Code analysis (future)

# Custom plugins
heybud "deploy to kubernetes"    # k8s plugin
heybud "run terraform plan"      # terraform plugin
```

## 🔧 Advanced Features

### Context Awareness

heybud remembers your current state:

- **Directory context**: Knows where you are and adapts commands
- **Shell history**: Learns from your command patterns
- **Environment**: Preserves virtual environments, PATH changes, etc.
- **Project awareness**: Recognizes project types and tools

<!-- ### Streaming Responses

Get real-time command generation:

```bash
heybud "write a complex find command" --stream
# Command appears character by character as it's generated
``` -->

### Failover & Reliability

Automatic provider switching ensures you always get help:

```bash
# If OpenAI is down, automatically tries Anthropic
# If local Ollama is unavailable, falls back to cloud providers
heybud "install flask dependencies"
```

### Audit & Debugging

Complete visibility into what heybud does:

```bash
# View detailed logs
heybud logs --tail 50

# Debug mode for troubleshooting
heybud "your query" --debug

# Trace API calls
heybud "complex task" --trace
```

## 🔮 Future Capabilities

heybud is designed for growth. Upcoming features include:

### Enhanced Intelligence

- **Multi-modal input**: Screenshots, error messages, log files
- **Code generation**: Complete scripts and applications
- **Interactive mode**: Conversational command refinement
- **Learning from usage**: Personalized command suggestions

### Advanced Safety

- **Command validation**: Test commands before execution
- **Rollback capabilities**: Undo dangerous operations
- **Policy enforcement**: Organization-wide safety rules
- **Anomaly detection**: Flag unusual command patterns

### Ecosystem Integration

- **IDE extensions**: VS Code, JetBrains, Vim plugins
- **CI/CD integration**: Automated command generation in pipelines
- **Team sharing**: Share and learn from command patterns
- **API access**: Integrate heybud into other tools

### Specialized Domains

- **DevOps automation**: Infrastructure as code, deployment scripts
- **Data science**: ML workflows, data processing pipelines
- **Cloud operations**: Multi-cloud command generation
- **Security**: Safe command execution in restricted environments

## 🛡️ Safety Features

heybud takes safety seriously:

- **Risk scoring**: Every command gets scored 0.0-1.0
- **Pattern detection**: Identifies dangerous operations like `rm -rf /`
- **Confirmation flow**: High-risk commands require explicit approval
- **Audit logging**: All commands are logged for review
- **Sandbox execution**: Test commands in isolated environments

## 🔌 Plugin System

Extend heybud with plugins for domain-specific tasks.

### Built-in Plugins

- **gitbud**: Git repository helpers and advanced operations
- **filebud**: File operations, analysis, and manipulation

### Creating Plugins

See [docs/plugin-development.md](docs/plugin-development.md) for details on building custom plugins.

## 📊 Commands Reference

| Command | Description |
|---------|-------------|
| `heybud "query"` | Generate command for your query |
| `heybud okay` | Execute the last generated command |
| `heybud explain <query>` | Provide a detailed explanation of the query |
| `heybud init` | Interactive setup wizard |
| `heybud config` | View/edit configuration |
| `heybud logs` | View recent activity |
| `heybud plugins` | Manage plugins |
| `heybud status` | Show system status |

## 🐛 Troubleshooting

### Common issues

#### Command not found

```bash
# Make sure heybud is installed and in PATH
which heybud
pip show heybud
```

#### Provider not configured

```bash
# Run setup again
heybud init
```

#### High risk score on safe command

```bash
# Adjust safety settings
heybud config set safety.level medium
```

### Debug mode

```bash
# Enable verbose logging
heybud "your query" --debug

# View logs
heybud logs --tail 50
```

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development

```bash
# Clone and setup
git clone https://github.com/Rajat-Vishwa/heybud.git
cd heybud
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
mypy core cli
```

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

Built with ❤️ for developers who spend their days in terminals.
