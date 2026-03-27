#!/bin/bash

set -e

# Create a local venv in the workspace and install requirements
PYTHON=$(which python)
if [ ! -d "dev/.venv" ]; then
  echo "Create virtual environment in dev/.venv"
  $PYTHON -m venv dev/.venv
fi
. dev/.venv/bin/activate

pip install --upgrade pip setuptools wheel
jq -r .requirements.[] custom_components/*/manifest.json | xargs pip install
