#!/usr/bin/env bash
set -euo pipefail
umask 077
cd "$(dirname "$0")"
exec python3 scripts/fresh_fury.py "$@"
