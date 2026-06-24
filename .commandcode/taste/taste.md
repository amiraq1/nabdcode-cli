# Taste (Continuously Learned by [CommandCode][cmd])

[cmd]: https://commandcode.ai/

# git
- Use the pattern: `git add .` → `git commit -m "..."` → `git push origin main`. Confidence: 0.60
- Use conventional commit format with emoji prefixes (e.g., "🚀 feat:", "🔒 security & ✨ feat:"). Confidence: 0.60

# workflow
- Prefer writing files via shell commands (e.g., `cat << 'EOF' > file.py`) rather than assistant file tools. Confidence: 0.85

# code-style
- Write docstrings and inline comments in Arabic for Arabic-language codebases. Confidence: 0.55

# registry
- Register all tools in the registry even if their source files don't exist yet (forward-looking tool registration). Confidence: 0.82

# config
- In `get_active_provider()`: merge `http_headers`, `env_http_headers`, and auto-added `Authorization: Bearer` into a single `headers` dict; copy to avoid mutation; warn when env var for a header is unset. Confidence: 0.70

# llm-client
- In `_execute_request()`: call `self.config_manager.get_active_provider()` directly and pass `active_provider["headers"]` to `requests.post()` rather than caching headers as `self.extra_headers`. Confidence: 0.60

# serialization
- Use pickle instead of JSON for vector DB binary serialization (faster, smaller, handles numpy arrays natively). Confidence: 0.65

# cli
- Clear the terminal screen before launching a CLI tool interface. Confidence: 0.70
- Keep CLI interface minimal: suppress INFO-level log messages, hide startup banners, and remove non-essential UI elements (shortcuts, tips). Confidence: 0.75
- Use prompt_toolkit with a Cyberpunk/Orange color scheme for interactive CLI menus (orange accent #d88a44 on dark backgrounds #2c2c2c/#1e1e1e). Confidence: 0.60

# security
- Use allowlist-based command validation (`ALLOWED_COMMANDS` set), `shlex.split()` for safe argument parsing, no `shell=True`, output truncation at 15K chars, and timeout protection for shell command execution. Confidence: 0.85

# agent
- Build system prompt via `_build_system_prompt(context)` that dynamically lists all registered tools and instructs the model to use `<use_tool name="ToolName">` XML format for tool invocation, one tool at a time. Confidence: 0.65
- Parse `<use_tool name="ToolName">arguments</use_tool>` XML tags from LLM responses via regex, execute the tool, append the result as a new user message, and recursively continue the agent loop. Confidence: 0.65
- Auto-summarize long tool outputs (CLI results, search results) before appending to conversation context to prevent token inflation. Confidence: 0.75
- Trim/prune old messages from the conversation history before sending to LLMClient to stay within context window limits. Confidence: 0.75

