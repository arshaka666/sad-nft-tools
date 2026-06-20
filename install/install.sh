#!/usr/bin/env bash
set -euo pipefail
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$HERMES_HOME/skills" "$HERMES_HOME/scripts"

backup_dir="$HERMES_HOME/backups/sad-nft-tools-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir"

if [ -d "$HERMES_HOME/skills" ]; then
  mkdir -p "$backup_dir/skills"
  cp -R "$HERMES_HOME/skills"/* "$backup_dir/skills/" 2>/dev/null || true
fi

if [ -d "$HERMES_HOME/scripts" ]; then
  mkdir -p "$backup_dir/scripts"
  cp "$HERMES_HOME/scripts"/* "$backup_dir/scripts/" 2>/dev/null || true
fi

cp -R "$REPO_DIR"/skills/* "$HERMES_HOME/skills/"
cp "$REPO_DIR"/scripts/* "$HERMES_HOME/scripts/"
chmod +x "$HERMES_HOME"/scripts/*.sh "$HERMES_HOME"/scripts/*.py 2>/dev/null || true
echo "Backup saved to $backup_dir"
echo "Installed skills and scripts into $HERMES_HOME"
echo "Run: hermes skills list | grep -E 'nft|web3|xurl|polymarket|blogwatcher'"
