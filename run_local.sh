#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
SECRETS_FILE="${SCRIPT_DIR}/secrets.json"

if [ ! -d "${VENV_DIR}" ]; then
  echo "Missing virtualenv at ${VENV_DIR}" >&2
  exit 1
fi

if [ ! -f "${SECRETS_FILE}" ]; then
  echo "Missing secrets file at ${SECRETS_FILE}" >&2
  exit 1
fi

cd "${SCRIPT_DIR}"
source "${VENV_DIR}/bin/activate"

eval "$(
  "${VENV_DIR}/bin/python" - "${SECRETS_FILE}" <<'PY'
import json
import pathlib
import re
import shlex
import sys

path = pathlib.Path(sys.argv[1])

try:
    data = json.loads(path.read_text())
except json.JSONDecodeError as exc:
    raise SystemExit(f"Invalid JSON in {path}: {exc}")

if not isinstance(data, dict):
    raise SystemExit(f"{path} must contain a JSON object of env vars")

name_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

for key, value in data.items():
    if not isinstance(key, str) or not name_pattern.match(key):
        raise SystemExit(f"Invalid environment variable name: {key!r}")

    if value is None:
        value_str = ""
    elif isinstance(value, bool):
        value_str = "true" if value else "false"
    elif isinstance(value, (str, int, float)):
        value_str = str(value)
    else:
        raise SystemExit(
            f"Unsupported value type for {key!r}: {type(value).__name__}"
        )

    print(f"export {key}={shlex.quote(value_str)}")
PY
)"

export FLASK_APP="${FLASK_APP:-webserver}"

exec flask run "$@"
