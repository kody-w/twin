#!/bin/bash
# tests/run.sh — run the variant-layer test suite (pure stdlib unittest).
set -e
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -p "test_*.py" -v
