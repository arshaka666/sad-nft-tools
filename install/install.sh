#!/usr/bin/env bash
set -euo pipefail
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$HERMES_HOME/skills" "$HERMES_HOME/scripts"
cp -R "$REPO_DIR"/skills/* "$HERMES_HOME/skills/"
cp "$REPO_DIR"/scripts/* "$HERMES_HOME/scripts/"
chmod +x "$HERMES_HOME"/scripts/*.sh "$HERMES_HOME"/scripts/*.py 2>/dev/null || true
echo "Installed skills and scripts into $HERMES_HOME"
echo "Run: hermes skills list | grep -E 'nft|web3|xurl|polymarket|blogwatcher'"
