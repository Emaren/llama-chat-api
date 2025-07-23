#!/bin/bash
echo "🔍 Checking Python virtual environments in /var/www/*/venv..."

for venv in /var/www/*/venv; do
  if [ -d "$venv" ]; then
    echo ""
    echo "📦 Found venv: $venv"
    du -sh "$venv"
    python_bin="$venv/bin/python"
    if [ -x "$python_bin" ]; then
      echo -n "🐍 Python version: "
      "$python_bin" --version
    else
      echo "⚠️  Python binary not found in $venv/bin/"
    fi
  fi
done
