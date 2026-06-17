# HermesOC — OpenCode Coding Agent Built Into Hermes

> **A Hermes Agent plugin that embeds an OpenCode-style coding agent. No OpenCode CLI required. No conflicts with existing installs.**

## What It Is

HermesOC is a **plugin** that installs alongside your existing Hermes Agent. It adds an `opencode_code` tool that delegates coding tasks to an embedded coding engine — no external `opencode` CLI install needed, no conflicts with your existing Hermes or OpenCode setups.

- **Installs as a plugin** — doesn't modify Hermes core files
- **Embedded engine** — the coding agent runs in-process using Hermes's own provider config
- **Zero external deps** — no `opencode` CLI, no Node.js, no separate process
- **Auto-inherits config** — uses your Hermes model, base_url, and API key automatically

## How It Differs from the Bundled OpenCode Skill

The [bundled OpenCode skill](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-opencode) in upstream Hermes is a **skill document** — instructions that teach the agent to run `opencode` CLI commands via `terminal()`. It requires the `opencode` CLI to be installed separately.

| Aspect | OpenCode Skill (upstream) | HermesOC (this plugin) |
|--------|--------------------------|------------------------|
| **What it is** | Skill document (instructions) | Plugin with embedded engine |
| **Requires OpenCode CLI** | Yes (`npm i -g opencode-ai`) | **No** — engine is built in |
| **Requires Node.js** | Yes | **No** |
| **How coding is triggered** | Agent runs `terminal("opencode run '...'")` | Agent calls `opencode_code(task="...")` — first-class tool |
| **Provider config** | Manual env var setup | **Automatic** — inherits from Hermes config |
| **System prompt** | No coding-routing guidance | Built-in guidance injected via plugin hook |
| **Conflicts with existing installs** | Shares the `opencode` binary | **None** — completely independent |
| **Output** | Raw terminal stdout | Structured JSON: `success`, `output`, `edits`, `git_diff` |
| **Installs alongside Hermes** | N/A (it's a skill, always present) | **Yes** — plugin, no core modifications |

## Installation

### Prerequisites

- Hermes Agent already installed ([install here](https://hermes-agent.nousresearch.com/docs))

### Install HermesOC

```bash
git clone https://github.com/evangit2/hermes-opencode.git
cd hermes-opencode
bash install.sh
```

That's it. The plugin installs to `~/.hermes/plugins/hermesoc/` and registers automatically.

### Verify

```bash
hermes tools list | grep opencode
# Should show: ✓ enabled  opencode  🔧 OpenCode coding agent
```

## Usage

Once installed, Hermes automatically has the `opencode_code` tool available. When you ask Hermes to write or modify code, it delegates to the embedded engine:

```
> Create a Flask app with a /health endpoint in /tmp/myapp

# Hermes calls opencode_code(task="...", workdir="/tmp/myapp")
# The embedded engine:
#   1. Reads the codebase context (file tree, git status, relevant files)
#   2. Sends the task to the LLM using your Hermes provider config
#   3. Parses the response for file edits
#   4. Applies the edits to disk
#   5. Returns structured JSON with git diff
```

### Tool Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task` | string | The coding task description (required) |
| `workdir` | string | Working directory for the codebase |
| `model` | string | Override the model ID (auto-detected if empty) |
| `files` | array | File paths to attach as context |
| `thinking` | boolean | Show model reasoning in output |
| `timeout` | integer | Max seconds (default 300) |

### Output Format

```json
{
  "success": true,
  "output": "Added /health endpoint to app.py...",
  "edits": [{"file": "app.py", "status": "written"}],
  "git_diff": "app.py | 5 +++++",
  "model": "umans/umans-glm-5.2",
  "workdir": "/tmp/myapp",
  "files_modified": 1
}
```

## Architecture

```
User → Hermes Agent (unchanged)
         ├── Normal tools (terminal, web, browser, etc.)
         └── opencode_code tool (from HermesOC plugin)
              ├── Read codebase context (file tree, git status, files)
              ├── Call LLM using Hermes's provider config (in-process)
              ├── Parse response for EDIT blocks
              ├── Apply file edits to disk
              └── Return JSON with output + git diff
```

**Key design decisions:**
- **In-process, not subprocess** — no external CLI, no Node.js, no process management
- **Uses Hermes's HTTP client** (httpx) and provider config — no separate auth setup
- **Plugin-based** — installs to `~/.hermes/plugins/hermesoc/`, doesn't touch core files
- **System prompt injection via hook** — `pre_session_init` hook adds coding-routing guidance

## Repository Structure

```
hermes-opencode/
├── README.md
├── install.sh              ← one-command installer
├── pyproject.toml          ← pip package + entry-point registration
└── hermesoc/               ← the plugin
    ├── __init__.py         ← plugin entry point (register function)
    ├── plugin.yaml         ← Hermes plugin manifest
    └── tools/
        └── opencode_tool.py  ← embedded coding engine
```

## License

MIT
