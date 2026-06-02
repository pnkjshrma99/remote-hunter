#!/usr/bin/env bash
set -euo pipefail

echo "=== Setting up JobSpy / Playwright ==="

pip install python-jobspy playwright 2>&1 | tail -5

echo "Installing Playwright browsers (Chromium)..."
python3 -m playwright install chromium 2>&1 | tail -5

echo "=== JobSpy setup complete ==="
