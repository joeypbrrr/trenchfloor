#!/bin/bash
cd "$(dirname "$0")" || exit 1
py=python3
[[ -x .venv-pumpportal/bin/python ]] && py=.venv-pumpportal/bin/python
exec "$py" -u pumpportal_collector.py
