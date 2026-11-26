#!/usr/bin/env bash
# 示例任务入口：可从任意目录调用。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$ROOT/scripts/rsr" collect run -c "$ROOT/configs/stub/default.toml" "$@"
