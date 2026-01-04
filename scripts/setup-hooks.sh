#!/bin/bash
# Setup script for git hooks

echo "Installing git hooks..."

# Locate pre-commit in venv if available
GIT_ROOT=$(git rev-parse --show-toplevel)
PRE_COMMIT_CMD="pre-commit"
if [ -f "$GIT_ROOT/venv/bin/pre-commit" ]; then
    PRE_COMMIT_CMD="$GIT_ROOT/venv/bin/pre-commit"
fi

# Install pre-commit hooks
$PRE_COMMIT_CMD install
$PRE_COMMIT_CMD install --hook-type commit-msg

# Install prepare-commit-msg hook for interactive commit message generation
cat > .git/hooks/prepare-commit-msg << 'EOF'
#!/bin/bash
# Commitizen prepare-commit-msg hook

COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2

# Only run if no message is provided via -m flag
if [ -z "$COMMIT_SOURCE" ]; then
    # Find Python with commitizen installed
    GIT_ROOT=$(git rev-parse --show-toplevel)
    # Check for venv python first
    if [ -f "$GIT_ROOT/venv/bin/python" ]; then
        PYTHON_CMD="$GIT_ROOT/venv/bin/python"
    # Try pyenv first, then fall back to system python3
    elif command -v pyenv &> /dev/null; then
        PYTHON_CMD=$(pyenv which python3 2>/dev/null || python3 -c "import sys; print(sys.executable)")
    else
        PYTHON_CMD=$(python3 -c "import sys; print(sys.executable)")
    fi

    # Use the wrapper script to avoid asyncio issues on macOS
    exec < /dev/tty
    $PYTHON_CMD "$(git rev-parse --show-toplevel)/scripts/invoke_cz.py" commit --dry-run --write-message-to-file "$COMMIT_MSG_FILE" || {
        # If commitizen fails, let git continue with default editor
        exit 0
    }
fi
EOF

chmod +x .git/hooks/prepare-commit-msg

echo "✓ Git hooks installed successfully!"
echo ""
echo "Usage:"
echo "  - Run 'git commit' (without -m) to use the interactive commit wizard"
echo "  - Run 'git commit -m \"message\"' to bypass the wizard"
echo "  - All commits will be validated against conventional commits format"
