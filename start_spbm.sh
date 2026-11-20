#!/bin/bash
# Start SPBM (Linux/macOS): set up on first use, start in the background,
# open the page, stop by itself ~15 min after the page is closed.
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  echo "First start: setting up SPBM. This takes a few minutes, once."
  PY=$(command -v python3 || command -v python)
  if [ -z "$PY" ]; then echo "Python 3.10 or later is needed (https://www.python.org/downloads/)."; read -r -p "Press Enter to close"; exit 1; fi
  "$PY" -m venv .venv && .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt \
    || { echo "Setting up failed - see the messages above."; read -r -p "Press Enter to close"; exit 1; }
fi
nohup .venv/bin/python -m spbm serve --open --idle-exit 15 > .spbm_server.log 2>&1 &
echo "SPBM is starting in your browser (http://127.0.0.1:8413). You can close this window."
sleep 2
