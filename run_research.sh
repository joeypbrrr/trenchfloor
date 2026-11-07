#!/bin/bash
cd "$(dirname "$0")" || exit 1
while true; do
  python3 -u research.py &
  echo $! > research.child.pid
  wait $!
  code=$?
  echo "$(date -Is) research.py exited ${code}; restarting in 5s" >> logs/research.log
  sleep 5
done
