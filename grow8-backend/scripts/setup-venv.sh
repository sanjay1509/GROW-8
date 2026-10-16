#!/bin/sh
# Creates grow8-backend/.venv for the EDITOR ONLY (VS Code / Pylance / ruff), from the
# same pinned requirement files the Docker images use. The code still RUNS in Docker
# (`make up`, `make test`); do not run the API or tests from this venv.
#
# Usage: sh scripts/setup-venv.sh        (or: make venv)
# Re-run after any requirements*.txt or shared/pyproject.toml change.
# Override the interpreter with: PYTHON=/path/to/python3.12 sh scripts/setup-venv.sh
set -e
cd "$(dirname "$0")/.."

is_py312() {
    "$@" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))' >/dev/null 2>&1
}

if [ -n "$PYTHON" ]; then
    set -- "$PYTHON"
elif is_py312 python3.12; then
    set -- python3.12
elif is_py312 py -3.12; then
    set -- py -3.12
elif is_py312 python3; then
    set -- python3
elif is_py312 python; then
    set -- python
else
    echo "Python 3.12 not found (the images use 3.12). Install it or set PYTHON=..." >&2
    exit 1
fi

if [ ! -d .venv ]; then
    echo "Creating .venv with: $*"
    "$@" -m venv .venv
fi

if [ -x .venv/Scripts/python.exe ]; then
    VENV_PY=.venv/Scripts/python.exe
else
    VENV_PY=.venv/bin/python
fi

"$VENV_PY" -m pip install --quiet --disable-pip-version-check --upgrade pip
"$VENV_PY" -m pip install --quiet --disable-pip-version-check \
    -e shared \
    -r api/requirements-dev.txt \
    -r services/creator_service/requirements-dev.txt \
    -r services/contributor_service/requirements-dev.txt \
    -r services/admin_service/requirements-dev.txt

echo "Editor venv ready: $VENV_PY"
echo "Open grow8.code-workspace (repository root) in VS Code (File > Open Workspace from File)."
