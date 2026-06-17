# HermesOC — Hermes Agent + OpenCode Integration

> **Not just "using the OpenCode skill in Hermes" — a deeply integrated fork where coding delegation is built into the system prompt, toolset, and provider configuration.**

## How This Differs from the Default OpenCode Skill

The [bundled OpenCode skill](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-opencode) in upstream Hermes is a **skill document** — a set of instructions that teaches the agent *how to use* OpenCode CLI via `terminal()` calls. The agent reads the skill, then manually constructs `opencode run '...'` commands.

HermesOC is fundamentally different:

| Aspect | OpenCode Skill (upstream) | HermesOC (this project) |
|--------|--------------------------|------------------------|
| **Integration level** | Skill document (instructions only) | Core tool + system prompt + provider passthrough |
| **How coding is triggered** | Agent decides to run `terminal("opencode run '...'")` | Agent calls `opencode_code(task="...")` — a first-class tool |
| **Provider config** | Manual — agent must figure out env vars | **Automatic** — OpenCode inherits model + base_url + API key from Hermes config |
| **System prompt** | No coding-routing guidance | Built-in `OPENCODE_DELEGATION_GUIDANCE` block tells Hermes to route coding to OpenCode |
| **Toolset integration** | Not in any toolset — relies on `terminal` | `opencode_code` in `_HERMES_CORE_TOOLS`, coding posture, and all platform toolsets |
| **Output handling** | Raw terminal stdout | Structured JSON: `success`, `output`, `git_diff`, `stderr`, `model`, `workdir` |
| **Model auto-detection** | None — agent must specify `--model` | Reads Hermes config and auto-maps to OpenCode model ID |
| **Desktop apps** | Included (Electron, Tauri installer) | Stripped — TUI + gateway + web UI only |
| **CLI branding** | `hermes` | `hermesoc` (with `hermes` alias for compat) |
| **Identity** | "Hermes Agent by Nous Research" | "HermesOC (Hermes + OpenCode)" |

**In short:** The skill approach is "teach the agent to use OpenCode as a tool." HermesOC is "make OpenCode a native part of the agent's architecture."

## What It Is

HermesOC is a fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) integrated with [OpenCode](https://opencode.ai) for a unified AI agent experience where **Hermes orchestrates and OpenCode codes**.

- **Hermes Agent** handles: orchestration, system operations, research, messaging, scheduling, memory, skills, web/browser automation
- **OpenCode** handles: all substantive coding tasks — writing features, refactoring, debugging, code review, test writing
- **Hermes** can still do quick trivial code changes (1-2 line edits via `patch`), but delegates anything larger to OpenCode via the `opencode_code` tool

## Key Changes from Upstream Hermes

1. **New `opencode_code` tool** (`tools/opencode_tool.py`) — a first-class Hermes tool that delegates coding tasks to OpenCode CLI as a subprocess, with structured JSON output
2. **System prompt integration** (`agent/prompt_builder.py`) — `OPENCODE_DELEGATION_GUIDANCE` block instructs Hermes to route coding work through OpenCode as its primary coding method
3. **Provider passthrough** — OpenCode inherits the same model, base_url, and API key from Hermes config automatically (no manual env var setup)
4. **Desktop apps stripped** — no Electron/Desktop app, just TUI + gateway + web UI
5. **CLI alias** — `hermesoc` command (with `hermes` kept for backward compatibility)
6. **Toolset integration** — `opencode_code` added to `_HERMES_CORE_TOOLS`, coding posture, hermes-acp, and hermes-api-server toolsets

## Architecture

```
User → HermesOC (Hermes Agent core)
         ├── Research, system ops, messaging → Hermes tools (terminal, web, browser, etc.)
         ├── Quick file edits → read_file, write_file, patch
         └── Coding tasks → opencode_code tool → OpenCode CLI subprocess
                                              → Same model + provider as Hermes (auto-inherited)
                                              → Returns structured JSON: output + git diff
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
- The model name (mapped to OpenCode's format — e.g. `umans/umans-glm-5.2` → `hermes/umans/umans-glm-5.2`)

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

Returns JSON with: `success`, `output`, `stderr`, `exit_code`, `model`, `workdir`, `git_diff`

## Repository Structure

```
hermes-opencode/
├── README.md              ← this file
├── hermes/                ← Hermes Agent fork (Python)
│   ├── tools/opencode_tool.py   ← OpenCode integration tool (NEW)
│   ├── agent/
│   │   ├── prompt_builder.py    ← System prompt with OpenCode guidance (MODIFIED)
│   │   └── system_prompt.py     ← Prompt assembly with OpenCode block (MODIFIED)
│   ├── toolsets.py              ← Toolset definitions — includes opencode (MODIFIED)
│   ├── pyproject.toml           ← hermesoc entry point, hermes-oc package name (MODIFIED)
│   └── ...                ← Rest of Hermes Agent (desktop apps stripped)
└── opencode/              ← OpenCode fork (TypeScript) — for customization
```

## License

MIT (both Hermes Agent and OpenCode are MIT licensed)
