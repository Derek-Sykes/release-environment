#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
command -v python3 >/dev/null || { printf 'Install Python 3.10 or later first.\n' >&2; exit 1; }
exec python3 -B "$ROOT/scripts/release.py" "$@"

