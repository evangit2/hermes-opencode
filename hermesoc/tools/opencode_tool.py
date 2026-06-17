#!/usr/bin/env python3
"""
OpenCode Coding Tool — Embedded Engine

Delegates coding tasks to an embedded OpenCode engine that runs in-process.
No external `opencode` CLI install required — this module IS the engine.

The engine:
  1. Reads the codebase in the working directory
  2. Builds a coding-focused context (file tree, relevant files, git status)
  3. Sends the coding task to the LLM using Hermes's configured provider
  4. Parses the LLM response for file edits and applies them
  5. Runs any requested test commands
  6. Returns structured JSON with output + git diff

This does NOT conflict with the user's existing `opencode` CLI install —
it's a completely independent implementation that reuses Hermes's own
HTTP client and provider config.
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_hermes_config() -> Dict[str, Any]:
    """Read model/provider config from Hermes config.yaml."""
    try:
        import yaml
        from hermes_constants import get_hermes_home

        config_path = os.path.join(get_hermes_home(), "config.yaml")
        if os.path.exists(config_path):
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to read Hermes config: %s", e)
    return {}


def _resolve_model(config: Dict[str, Any], override: str = "") -> str:
    """Resolve the model ID from Hermes config or override."""
    if override:
        return override

    model_default = config.get("model", {}).get("default", "")
    if model_default:
        return model_default

    return "umans/umans-glm-5.2"


def _resolve_provider(config: Dict[str, Any]) -> Dict[str, str]:
    """Extract base_url and api_key from Hermes config."""
    model_cfg = config.get("model", {})
    base_url = model_cfg.get("base_url", "")
    api_key = model_cfg.get("api_key", "")

    # If no api_key in model config, check auxiliary config
    if not api_key:
        aux = config.get("auxiliary", {})
        for _key, val in aux.items():
            if isinstance(val, dict) and val.get("api_key"):
                api_key = val["api_key"]
                if not base_url:
                    base_url = val.get("base_url", "")
                break

    # Also check .env file
    if not api_key or not base_url:
        try:
            from hermes_constants import get_hermes_home
            env_path = os.path.join(get_hermes_home(), ".env")
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("#") or "=" not in line:
                            continue
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key == "OPENAI_API_KEY" and not api_key:
                            api_key = val
                        if key == "OPENAI_BASE_URL" and not base_url:
                            base_url = val
        except Exception:
            pass

    return {"base_url": base_url, "api_key": api_key}


def _get_workdir(workdir: str, task_id: Optional[str] = None) -> str:
    """Determine the working directory."""
    if workdir:
        return os.path.expanduser(workdir)

    try:
        from agent.runtime_cwd import resolve_agent_cwd
        cwd = resolve_agent_cwd(task_id=task_id)
        if cwd:
            return str(cwd)
    except Exception:
        pass

    return os.path.expanduser("~")


def _build_file_context(workdir: str, files: Optional[List[str]] = None) -> str:
    """Build a context string with file tree and relevant file contents."""
    wd = Path(workdir)
    parts = []

    # Git status
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=workdir, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts.append(f"## Git Status\n```\n{result.stdout.strip()}\n```")
    except Exception:
        pass

    # File tree (respect .gitignore)
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=workdir, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            tracked = result.stdout.strip().split("\n")
            # Limit to reasonable size
            if len(tracked) <= 200:
                parts.append(f"## Tracked Files\n```\n{chr(10).join(tracked)}\n```")
            else:
                parts.append(f"## Tracked Files ({len(tracked)} files)\n(Showing first 200)\n```\n{chr(10).join(tracked[:200])}\n```")
    except Exception:
        pass

    # Specific files requested as context
    if files:
        for fpath in files:
            full_path = wd / fpath
            if full_path.exists() and full_path.is_file():
                try:
                    content = full_path.read_text(encoding="utf-8", errors="replace")
                    # Truncate large files
                    if len(content) > 10000:
                        content = content[:10000] + "\n... (truncated)"
                    parts.append(f"## File: {fpath}\n```\n{content}\n```")
                except Exception as e:
                    parts.append(f"## File: {fpath}\n(Error reading: {e})")

    return "\n\n".join(parts) if parts else "(no file context available)"


def _call_llm(
    model: str,
    base_url: str,
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 300,
) -> Dict[str, Any]:
    """Call the LLM using the OpenAI-compatible API.

    Uses httpx for the HTTP call — same library Hermes already depends on.
    """
    import httpx

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 8192,
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"success": True, "content": content}
    except httpx.TimeoutException:
        return {"success": False, "error": f"LLM call timed out after {timeout}s"}
    except httpx.HTTPStatusError as e:
        return {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# The system prompt for the embedded coding agent
_CODING_AGENT_SYSTEM = """You are an expert coding agent embedded in HermesOC. You write, modify, and debug code directly.

## Your Capabilities
- Read and understand codebases from file context
- Write code changes as structured edit blocks
- Explain what you changed and why

## Output Format
When you need to modify a file, output edit blocks in this exact format:

### EDIT: <file_path>
```python
# The COMPLETE new content of the file (not a diff — the full file)
```

For multiple files, use multiple EDIT blocks. Always include the full file content,
not just the changed lines.

If you only need to read files and report findings (no edits), just write your analysis.

## Rules
- Always output the COMPLETE file content in edit blocks, not partial diffs
- One EDIT block per file
- Include a brief summary of changes after all edit blocks
- If a task requires running tests, mention the test command but don't run it
"""


def _parse_and_apply_edits(llm_output: str, workdir: str) -> List[Dict[str, str]]:
    """Parse EDIT blocks from LLM output and apply them to files."""
    import re

    edits = []
    # Match: ### EDIT: <path>\n```<lang>\n<content>\n```
    pattern = r"### EDIT:\s*(.+?)\n```[a-zA-Z]*\n(.*?)\n```"
    matches = re.findall(pattern, llm_output, re.DOTALL)

    for file_path, content in matches:
        file_path = file_path.strip()
        full_path = os.path.join(workdir, file_path)

        try:
            # Create parent dirs if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            # Write the file
            with open(full_path, "w") as f:
                f.write(content)
            edits.append({"file": file_path, "status": "written"})
        except Exception as e:
            edits.append({"file": file_path, "status": "error", "error": str(e)})

    return edits


def _get_git_diff(workdir: str) -> str:
    """Get a git diff stat for the working directory."""
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=workdir, capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def opencode_code(
    task: str,
    workdir: str = "",
    model: str = "",
    files: list = None,
    thinking: bool = False,
    timeout: int = 300,
    task_id: str = None,
) -> str:
    """Delegate a coding task to the embedded OpenCode engine.

    Runs entirely in-process — no external CLI needed. Reads the codebase,
    sends the task to the LLM (using Hermes's provider config), parses the
    response for file edits, and applies them.

    Args:
        task: The coding task description.
        workdir: Working directory for the codebase.
        model: Override the model ID. Auto-detected from Hermes config if empty.
        files: List of file paths to attach as context.
        thinking: Include reasoning in output.
        timeout: Max seconds (default 300).

    Returns:
        JSON string with: success, output, edits, git_diff, model, workdir.
    """
    if not task:
        return json.dumps({"success": False, "error": "No task provided"})

    # Resolve config
    config = _get_hermes_config()
    resolved_model = _resolve_model(config, model)
    provider = _resolve_provider(config)
    cwd = _get_workdir(workdir, task_id=task_id)

    if not provider["base_url"] or not provider["api_key"]:
        return json.dumps({
            "success": False,
            "error": "No provider config found. Set model.base_url and model.api_key in Hermes config.",
            "output": "",
        })

    # Build context
    file_context = _build_file_context(cwd, files)

    user_prompt = f"""## Task
{task}

## Codebase Context
{file_context}

## Instructions
Analyze the task and the codebase context above. Make the necessary code changes.
Output each modified file as an EDIT block with the COMPLETE new file content.
After all edits, write a brief summary of what you changed and why.
"""

    logger.info("HermesOC coding task: model=%s, cwd=%s, task=%s", resolved_model, cwd, task[:100])

    # Call the LLM
    start_time = time.time()
    llm_result = _call_llm(
        model=resolved_model,
        base_url=provider["base_url"],
        api_key=provider["api_key"],
        system_prompt=_CODING_AGENT_SYSTEM,
        user_prompt=user_prompt,
        timeout=timeout,
    )
    elapsed = time.time() - start_time

    if not llm_result["success"]:
        return json.dumps({
            "success": False,
            "error": llm_result.get("error", "Unknown error"),
            "output": "",
            "model": resolved_model,
            "workdir": cwd,
            "elapsed": f"{elapsed:.1f}s",
        })

    # Parse and apply edits
    llm_content = llm_result["content"]
    edits = _parse_and_apply_edits(llm_content, cwd)
    git_diff = _get_git_diff(cwd)

    # Build the summary output (strip the edit blocks for cleaner output)
    import re
    summary = re.sub(r"### EDIT:\s*.+?\n```[a-zA-Z]*\n.*?\n```", "[edit applied]", llm_content, flags=re.DOTALL)

    return json.dumps({
        "success": True,
        "output": summary.strip(),
        "edits": edits,
        "git_diff": git_diff,
        "model": resolved_model,
        "workdir": cwd,
        "elapsed": f"{elapsed:.1f}s",
        "files_modified": len(edits),
    }, ensure_ascii=False)


def check_requirements() -> bool:
    """Check if the embedded engine can run (always true — no external deps needed)."""
    return True
