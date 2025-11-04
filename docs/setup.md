# heybud Setup Guide

Complete setup instructions for heybud v1.

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- bash, zsh, or fish shell
- (Optional) Git for version control

## Installation Methods

### Method 1: Development Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/Rajat-Vishwa/heybud.git
cd heybud

# Install in development mode
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

<!-- ### Method 2: Direct Installation

```bash
# From PyPI (when published)
pip install heybud

# Or from source
pip install git+https://github.com/Rajat-Vishwa/heybud.git
``` -->

## Initial Configuration

### Step 1: Run Interactive Setup

```bash
heybud init
```

This wizard will guide you through:

1. **Provider Selection**
   - Choose one or more LLM providers
   - Enter API keys or configure local endpoints
   - Test provider connections
   
2. **Failover Strategy**
   - `first_available`: Try providers in priority order
   - `round_robin`: Distribute requests across providers
   - `fallback`: Primary with backup providers

3. **Shell Configuration**
   - Detect and configure your shell (bash/zsh/fish)
   
4. **Telemetry Preferences**
   - Opt-in to anonymous usage statistics

5. **Shell Wrapper Installation**
   - Automatically adds heybud function to shell RC file

### Step 2: Reload Shell Configuration

After installation, reload your shell:

```bash
# For bash
source ~/.bashrc

# For zsh
source ~/.zshrc

# For fish
source ~/.config/fish/config.fish

# Or just restart your terminal
```

## Provider-Specific Setup

### OpenAI Setup

1. Get API key from https://platform.openai.com/api-keys

2. Set environment variable:
```bash
export OPENAI_API_KEY="sk-..."
```

3. Or let `heybud init` save it securely

4. Configuration:
```json
{
  "id": "openai",
  "provider": "openai",
  "priority": 1,
  "model": "gpt-4o-mini",
  "api_key_name": "OPENAI_API_KEY"
}
```

### Anthropic Claude Setup

1. Get API key from https://console.anthropic.com/

2. Set environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

3. Configuration:
```json
{
  "id": "anthropic",
  "provider": "anthropic",
  "priority": 1,
  "model": "claude-3-5-sonnet-20241022",
  "api_key_name": "ANTHROPIC_API_KEY"
}
```

### Google Gemini Setup

1. Get API key from https://makersuite.google.com/app/apikey

2. Set environment variable:
```bash
export GOOGLE_API_KEY="..."
```

3. Configuration:
```json
{
  "id": "gemini",
  "provider": "gemini",
  "priority": 1,
  "model": "gemini-2.5-flash",
  "api_key_name": "GOOGLE_API_KEY"
}
```

### Ollama Local Setup

1. Install Ollama from https://ollama.ai/

2. Start Ollama server:
```bash
ollama serve
```

3. Pull a model:
```bash
ollama pull llama3
```

4. Configuration:
```json
{
  "id": "ollama",
  "provider": "ollama",
  "priority": 2,
  "endpoint": "http://127.0.0.1:11434",
  "model": "llama3"
}
```

### llama.cpp Local Setup

1. Install llama.cpp:
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make
```

2. Download a GGUF model file

3. Configuration:
```json
{
  "id": "local",
  "provider": "local_llama",
  "priority": 3,
  "endpoint": "/path/to/llama.cpp/main",
  "model": "/path/to/model.gguf"
}
```

### Hugging Face Setup

1. Get API token from https://huggingface.co/settings/tokens

2. Set environment variable:
```bash
export HUGGINGFACE_API_KEY="hf_..."
```

3. Configuration:
```json
{
  "id": "huggingface",
  "provider": "huggingface",
  "priority": 1,
  "model": "meta-llama/Llama-2-7b-chat-hf",
  "api_key_name": "HUGGINGFACE_API_KEY"
}
```

## Manual Configuration

If you prefer manual setup, create `~/.heybud/config.json`:

```json
{
  "providers": [
    {
      "id": "my-provider",
      "provider": "openai",
      "priority": 1,
      "model": "gpt-4o-mini",
      "api_key_name": "OPENAI_API_KEY",
      "max_tokens": 1024,
      "temperature": 0.2,
      "timeout": 30
    }
  ],
  "failover_strategy": "first_available",
  "safety": {
    "max_tokens": 1024,
    "temperature": 0.2,
    "safe_mode": true,
    "risk_threshold": 0.7,
    "require_confirmation": true
  },
  "shell": {
    "preferred": "bash",
    "install_shell_wrapper": true
  },
  "telemetry": {
    "enabled": false
  }
}
```

## Shell Wrapper Manual Installation

If automatic installation fails, manually add to your shell RC file:

### For Bash (~/.bashrc)

```bash
# heybud shell wrapper
heybud() {
    local HEYBUD_TEMP="/tmp/heybud_output_$$.sh"
    
    command heybud-cli "$@" > "$HEYBUD_TEMP" 2>&1
    local exit_code=$?
    
    if [ -f "$HEYBUD_TEMP" ] && grep -q "^#EXEC_NOW" "$HEYBUD_TEMP"; then
        source "$HEYBUD_TEMP"
        rm -f "$HEYBUD_TEMP"
    else
        cat "$HEYBUD_TEMP"
        rm -f "$HEYBUD_TEMP"
    fi
    
    return $exit_code
}

alias hb='heybud'
```

### For Zsh (~/.zshrc)

Same as bash (above)

### For Fish (~/.config/fish/config.fish)

```fish
function heybud
    set -l HEYBUD_TEMP "/tmp/heybud_output_"(echo %self)".sh"
    
    heybud-cli $argv > $HEYBUD_TEMP 2>&1
    set -l exit_code $status
    
    if test -f $HEYBUD_TEMP; and grep -q "^#EXEC_NOW" $HEYBUD_TEMP
        source $HEYBUD_TEMP
        rm -f $HEYBUD_TEMP
    else
        cat $HEYBUD_TEMP
        rm -f $HEYBUD_TEMP
    end
    
    return $exit_code
end

alias hb='heybud'
```

## Verification

Test your installation:

```bash
# Check version
heybud version

# Check status
heybud status

# Test provider health
heybud providers health

# Try a simple query
heybud "echo hello world"
```

## Troubleshooting

### Issue: Command not found

**Solution**: Ensure `~/.local/bin` is in your PATH:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### Issue: API key not found

**Solution**: Set environment variable or run `heybud init` to save securely

### Issue: Shell function not working

**Solution**: 
1. Check shell RC file for heybud function
2. Reload shell: `source ~/.bashrc` (or equivalent)
3. Verify with: `type heybud`

### Issue: Provider connection failed

**Solution**:
1. Check API key is correct
2. Verify network connectivity
3. For local providers (Ollama), ensure server is running
4. Check logs: `heybud log --type error`

### Issue: Permission denied

**Solution**: Ensure config directory has correct permissions:
```bash
chmod 700 ~/.heybud
chmod 600 ~/.heybud/config.json
chmod 600 ~/.heybud/credentials.json
```

## Advanced Configuration

### Multiple Providers with Failover

```json
{
  "providers": [
    {
      "id": "primary",
      "provider": "openai",
      "priority": 1,
      "model": "gpt-4o-mini"
    },
    {
      "id": "fallback",
      "provider": "ollama",
      "priority": 2,
      "endpoint": "http://localhost:11434",
      "model": "llama3"
    }
  ],
  "failover_strategy": "fallback"
}
```

### Custom Safety Patterns

```json
{
  "safety": {
    "dangerous_patterns": [
      "rm\\s+-rf\\s+/",
      "dd\\s+if=",
      "your-custom-pattern"
    ],
    "risk_threshold": 0.5
  }
}
```

## Next Steps

1. Read the [Architecture Documentation](architecture.md)
2. Explore [Plugin Development Guide](plugin-development.md)
3. Try example queries:
   ```bash
   heybud "create a python project with venv and requirements.txt"
   heybud "find all python files larger than 1MB"
   heybud "show git status and recent commits"
   ```

## Getting Help

- Check logs: `heybud log`
- Enable debug: `heybud --debug "your query"`
- View status: `heybud status`
- Report issues: https://github.com/Rajat-Vishwa/heybud/issues
