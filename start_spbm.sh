#!/bin/bash
# Start SPBM (Linux/macOS): set up on first use (finding or installing Python
# 3.10 or later), start in the background, open the page, and stop by itself
# about 15 minutes after the page is closed.
cd "$(dirname "$0")" || exit 1
# PyYAML has no ready-made build for the newest Python versions; this makes it
# install as plain Python instead of needing a C compiler.
export PYYAML_FORCE_LIBYAML=0

find_python() {   # first Python >= 3.10, preferring 3.13
  for p in python3.13 python3.12 python3.14 python3.11 python3.10 python3 python; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      command -v "$p"; return 0
    fi
  done
  return 1
}

fail() { echo "$1"; read -r -p "Press Enter to close"; exit 1; }

if [ ! -f .venv/spbm_ready.txt ]; then
  echo "Setting up SPBM. This takes a few minutes, once."
  if [ ! -x .venv/bin/python ]; then
    PY=$(find_python)
    if [ -z "$PY" ]; then
      if [ "$(uname)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
        echo "Python 3.10 or later was not found. Installing Python 3.13 with Homebrew..."
        brew install python@3.13 && PY=$(find_python)
      elif [ "$(uname)" = "Darwin" ]; then
        open "https://www.python.org/downloads/macos/"
        fail "Python 3.10 or later is needed. The download page has been opened: install Python 3.13, then start SPBM again."
      else
        fail "Python 3.10 or later is needed, for example: sudo apt install python3 python3-venv"
      fi
    fi
    [ -n "$PY" ] || fail "Python could not be installed - see the messages above."
    echo "Using $PY"
    "$PY" -m venv .venv || fail "Could not create the Python environment (on Debian/Ubuntu: sudo apt install python3-venv)."
  fi
  .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt \
    || fail "Installing the packages failed - see the messages above."
  echo ready > .venv/spbm_ready.txt
fi
nohup .venv/bin/python -m spbm serve --open --idle-exit 15 > .spbm_server.log 2>&1 &
echo "SPBM is starting in your browser (http://127.0.0.1:8413). You can close this window."
sleep 2
