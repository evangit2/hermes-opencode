#!/usr/bin/env bash
# HermesOC Installer
# Installs the HermesOC plugin alongside an existing Hermes Agent install.
# Does NOT modify Hermes core files. Does NOT require OpenCode CLI.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> HermesOC Installer"
echo "    Source: $SCRIPT_DIR"

# Check Hermes is installed
if ! command -v hermes &>/dev/null; then
    echo "ERROR: Hermes Agent is not installed. Install it first:"
    echo "  curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash"
    exit 1
fi

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PLUGINS_DIR="$HERMES_HOME/plugins"
HERMESOC_DIR="$PLUGINS_DIR/hermesoc"

echo "    Hermes home: $HERMES_HOME"
echo "    Plugin dir:  $HERMESOC_DIR"

# Create plugins dir if needed
mkdir -p "$PLUGINS_DIR"

# Install the plugin
if [ -d "$HERMESOC_DIR" ]; then
    echo "    Updating existing HermesOC install..."
    rm -rf "$HERMESOC_DIR"
fi

cp -r "$SCRIPT_DIR/hermesoc" "$HERMESOC_DIR"

# Also install as a pip package for the entry-point
pip install -e "$SCRIPT_DIR" --quiet 2>/dev/null || pip install -e "$SCRIPT_DIR" --user --quiet 2>/dev/null || {
    echo "    WARNING: pip install failed — plugin will load from ~/.hermes/plugins/ instead"
}

echo ""
echo "==> HermesOC installed successfully!"
echo ""
echo "    The opencode_code tool is now available in Hermes."
echo "    It uses your existing Hermes model/provider config — no extra setup needed."
echo ""
echo "    Quick start:"
echo "      hermes chat -q 'Create a hello world Flask app in /tmp/myapp'"
echo ""
echo "    To verify:"
echo "      hermes tools list | grep opencode"
