# HermesOC — Hermes Agent + OpenCode Integration

HermesOC is a fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) integrated with [OpenCode](https://opencode.ai) for a unified AI agent experience where **Hermes orchestrates and OpenCode codes**.

## What It Is

- **Hermes Agent** handles: orchestration, system operations, research, messaging, scheduling, memory, skills, web/browser automation
- **OpenCode** handles: all substantive coding tasks — writing features, refactoring, debugging, code review, test writing
- **Hermes** can still do quick trivial code changes (1-2 line edits via `patch`), but delegates anything larger to OpenCode via the `opencode_code` tool

## Key Changes from Upstream Hermes

1. **New `opencode_code` tool** — delegates coding tasks to OpenCode CLI as a subprocess
2. **System prompt integration** — Hermes is instructed to route coding work through OpenCode
3. **Provider passthrough** — OpenCode inherits the same model and API endpoint from Hermes config
4. **Desktop apps stripped** — no Electron/Desktop app, just TUI + gateway + web UI
5. **CLI alias** — `hermesoc` command (with `hermes` kept for backward compatibility)

## Architecture

```
User → HermesOC (Hermes Agent core)
         ├── Research, system ops, messaging → Hermes tools (terminal, web, browser, etc.)
         ├── Quick file edits → read_file, write_file, patch
         └── Coding tasks → opencode_code tool → OpenCode CLI subprocess
                                              → Same model + provider as Hermes
                                              → Returns output + git diff
```

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ (for OpenCode CLI)
- curl

### Install HermesOC

```bash
# Clone the repo
git clone https://github.com/evangit2/hermes-opencode.git
cd hermes-opencode/hermes

# Install HermesOC
pip install -e .

# Install OpenCode CLI
npm i -g opencode-ai@latest

# Verify
hermesoc --version
opencode --version
```

### Configure Provider

HermesOC uses the same config as Hermes Agent. The model and provider settings are shared between Hermes and OpenCode automatically.

```bash
# Set your model and provider
hermesoc config set model.default "your-model-name"
hermesoc config set model.provider "your-provider"

# Or use the interactive setup
hermesoc setup
```

OpenCode automatically inherits:
- The API base URL from `model.base_url`
- The API key from `model.api_key` or auxiliary config
- The model name (mapped to OpenCode's format)

## Usage

### Interactive Chat

```bash
hermesoc
```

### Single Query

```bash
hermesoc chat -q "What files are in this project?"
```

### Coding Through OpenCode

When you ask HermesOC to write or modify code, it automatically delegates to OpenCode:

```
> Add a retry decorator to the API client in src/client.py

# HermesOC calls opencode_code with the task
# OpenCode reads the codebase, makes the edit, returns the result
# HermesOC verifies the change and reports back
```

### Gateway (Messaging Platforms)

Same as Hermes Agent — Telegram, Discord, Slack, etc.

```bash
hermesoc gateway setup
hermesoc gateway start
```

## OpenCode Tool Reference

The `opencode_code` tool accepts:

| Parameter | Type | Description |
|-----------|------|-------------|
| `task` | string | The coding task description (required) |
| `workdir` | string | Working directory for the codebase |
| `model` | string | Override the OpenCode model ID |
| `files` | array | File paths to attach as context |
| `thinking` | boolean | Show model reasoning blocks |
| `timeout` | integer | Max seconds (default 300) |

## Repository Structure

```
hermes-opencode/
├── README.md              ← this file
├── hermes/                ← Hermes Agent fork (Python)
│   ├── tools/opencode_tool.py   ← OpenCode integration tool
│   ├── agent/
│   │   ├── prompt_builder.py    ← System prompt with OpenCode guidance
│   │   └── system_prompt.py     ← Prompt assembly with OpenCode block
│   ├── toolsets.py              ← Toolset definitions (includes opencode)
│   └── ...                ← Rest of Hermes Agent
└── opencode/              ← OpenCode fork (TypeScript) — for customization
```

## License

MIT (both Hermes Agent and OpenCode are MIT licensed)
