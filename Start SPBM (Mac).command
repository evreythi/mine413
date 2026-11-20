#!/bin/bash
# Double-click to start SPBM. The first start installs the Python packages
# (a few minutes, needs Python 3.10 or later). After that it starts in seconds,
# opens the page in your browser, and stops by itself about 15 minutes after
# the page is closed (never during a run). If macOS blocks it the first time,
# right-click the file and choose Open.
cd "$(dirname "$0")" || exit 1
exec ./start_spbm.sh
