#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Install Python 3 from python.org, then run this file again."
  read -r -p "Press Enter to close."
  exit 1
fi
python3 manage.py serve
