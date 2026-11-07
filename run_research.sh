#!/bin/bash
cd "$(dirname "$0")" || exit 1
mkdir -p logs data/cache
exec 9>data/cache/research-runner.lock
flock -n 9 || { echo "Trenchfloor runner already active"; exit 1; }
while true; do
  py=python3
  if [[ -x .venv-pumpportal/bin/python ]] && python3 -c 'import json,sys; sys.exit(0 if json.load(open("config.json")).get("candidate_source") == "pumpportal" else 1)'; then
    py=.venv-pumpportal/bin/python
  fi
  "$py" -u research.py &
  echo $! > research.child.pid
  wait $!
  code=$?
  echo "$(date -Is) research.py exited ${code}; restarting in 5s" >> logs/research.log
  sleep 5
done
