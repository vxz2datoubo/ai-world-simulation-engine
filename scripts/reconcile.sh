#!/bin/bash

echo "=== AWRSE RECONCILE ==="

echo "Branch:"
git branch --show-current

echo "Commit:"
git log -1 --oneline

echo "Status:"
git status

echo "Python:"
python --version

echo "Files:"
ls

echo "Tests:"
pytest --version || true
