#!/usr/bin/env bash
# Zaroni Virtual Instruments launcher for macOS and Linux.
# Creates a local virtual environment (.venv) on first run, installs the
# dependencies when requirements.txt changes, then starts the application.
set -euo pipefail
cd "$(dirname "$0")"

# Find a Python 3.10+ interpreter.
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 &&
       "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.10 or newer is required. Install it from https://www.python.org/downloads/" >&2
    exit 1
fi

# Create the virtual environment on first run.
if [ ! -x .venv/bin/python ]; then
    echo "Creating virtual environment in .venv ..."
    if ! "$PYTHON" -m venv .venv; then
        echo "Error: could not create the virtual environment." >&2
        echo "On Debian/Ubuntu, install it with: sudo apt install python3-venv" >&2
        exit 1
    fi
fi
VENV_PY=.venv/bin/python

# Install dependencies when requirements.txt is new or has changed.
STAMP=.venv/.requirements.installed
if [ ! -f "$STAMP" ] || ! cmp -s requirements.txt "$STAMP"; then
    echo "Installing dependencies ..."
    "$VENV_PY" -m pip install --upgrade pip --quiet
    "$VENV_PY" -m pip install -r requirements.txt
    cp requirements.txt "$STAMP"
fi

exec "$VENV_PY" main.py "$@"
