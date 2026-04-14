#!/bin/bash
set -e

echo "Running scoring tests..."
cd /task
python3 -m pytest tests/test_outputs.py -v --tb=short 2>&1
echo "Scoring complete."
