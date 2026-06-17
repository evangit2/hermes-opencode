"""HermesOC — OpenCode coding agent built into Hermes as a plugin.

Installs alongside Hermes Agent (no conflict with existing installs).
Provides the `opencode_code` tool that delegates coding tasks to an embedded
OpenCode engine — no external `opencode` CLI required.

The plugin:
  - Registers `opencode_code` as a first-class Hermes tool
  - Injects system-prompt guidance to route coding tasks through OpenCode
  - Auto-inherits model + provider config from Hermes (no manual setup)
  - Bundles its own OpenCode engine so it doesn't touch the user's `opencode` CLI install
"""

from __future__ import annotations

import logging

from .tools.opencode_tool import check_requirements, opencode_code

logger = logging.getLogger(__name__)

# Tool schema — registered via PluginContext.register_tool()
TOOL_SCHEMA = {
    "name": "opencode_code",
    "description": (
        "Delegate a coding task to OpenCode — an autonomous coding agent embedded in Hermes. "
        "Use this as your PRIMARY method for any coding work: writing features, refactoring, "
        "debugging, code review, test writing, or any task that benefits from reading the full "
        "codebase context. For trivial single-file reads/edits, use read_file/patch instead. "
        "The model and provider are automatically inherited from Hermes config."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "The coding task description. Be specific about what to implement, fix, or review.",
            },
            "workdir": {
                "type": "string",
                "description": "Working directory containing the codebase. Defaults to the current directory.",
                "default": "",
            },
            "model": {
                "type": "string",
                "description": "Override the model ID. Auto-detected from Hermes config if empty.",
                "default": "",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "File paths to attach as context (relative to workdir).",
            },
            "thinking": {
                "type": "boolean",
                "description": "Show model thinking/reasoning blocks in output.",
                "default": False,
            },
            "timeout": {
                "type": "integer",
                "description": "Max seconds for the task (default 300).",
                "default": 300,
            },
        },
        "required": ["task"],
    },
}

# System-prompt guidance injected at session start
OPENCODE_DELEGATION_GUIDANCE = (
    "## OpenCode Coding Integration\n"
    "You have an `opencode_code` tool that delegates coding tasks to an embedded OpenCode "
    "coding agent. Use it as your PRIMARY method for coding work.\n\n"
    "**When to use `opencode_code`:**\n"
    "- Writing new code, features, or modules (anything beyond a 1-2 line change)\n"
    "- Refactoring or restructuring existing code\n"
    "- Debugging issues that require reading multiple files and iterating\n"
    "- Code review, test writing, or PR preparation\n"
    "- Any task that benefits from an agent reading the full codebase context\n\n"
    "**When NOT to use it (use your own tools instead):**\n"
    "- Quick single-file reads (use `read_file`)\n"
    "- Tiny edits or typo fixes (use `patch`)\n"
    "- Running shell commands or scripts (use `terminal`)\n"
    "- Research or analysis that isn't code editing (use `web_search`, `delegate_task`)\n\n"
    "**How to use it:**\n"
    "- Pass a clear, specific task description\n"
    "- Set `workdir` to the project root\n"
    "- The model and provider are automatically inherited from your Hermes config\n"
    "- Review the output: check `success`, `output`, `git_diff`, and `stderr`\n"
    "- For multi-step tasks, break them into sequential `opencode_code` calls\n"
    "- Always verify the results by reading modified files or running tests after\n"
)


def register(ctx):
    """Hermes plugin entry point — called by the plugin loader at startup."""
    # Register the opencode_code tool
    ctx.register_tool(
        name="opencode_code",
        toolset="opencode",
        schema=TOOL_SCHEMA,
        handler=lambda args, **kw: opencode_code(
            task=args.get("task", ""),
            workdir=args.get("workdir", ""),
            model=args.get("model", ""),
            files=args.get("files"),
            thinking=args.get("thinking", False),
            timeout=args.get("timeout", 300),
            task_id=kw.get("task_id"),
        ),
        check_fn=check_requirements,
        requires_env=[],
        description="OpenCode coding agent — autonomous code writing, refactoring, and review",
        emoji="🔧",
    )

    # Register the pre_session_init hook to inject system-prompt guidance
    ctx.register_hook("pre_session_init", _inject_opencode_guidance)

    logger.info("HermesOC plugin registered — opencode_code tool available")


def _inject_opencode_guidance(**kwargs):
    """Inject OpenCode delegation guidance into the system prompt at session start.

    Uses the pre_session_init hook to append the guidance to the agent's
    system prompt. This is cache-safe because it's set once at session start
    and never modified mid-session.
    """
    agent = kwargs.get("agent")
    if agent is None:
        return

    # Only inject if the opencode_code tool is available to this session
    if hasattr(agent, "valid_tool_names") and "opencode_code" in agent.valid_tool_names:
        # Append to the agent's extra system prompt
        if not hasattr(agent, "_hermesoc_guidance_injected"):
            if hasattr(agent, "extra_system_prompt"):
                agent.extra_system_prompt = (agent.extra_system_prompt or "") + "\n\n" + OPENCODE_DELEGATION_GUIDANCE
            agent._hermesoc_guidance_injected = True
            logger.info("OpenCode delegation guidance injected into system prompt")
