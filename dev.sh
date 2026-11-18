#!/bin/sh
# Opens the dev container, or runs a command in it: ./dev.sh uv run pytest
exec docker compose -f "$(dirname "$0")/docker/compose.yml" run --rm dev "$@"