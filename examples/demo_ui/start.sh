#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/../.."
exec python examples/demo_ui/server.py "$@"
