#!/usr/bin/env bash
set -Eeuo pipefail
export PYTHONUNBUFFERED=1
exec python /opt/ltx23/supervisor.py "$@"
