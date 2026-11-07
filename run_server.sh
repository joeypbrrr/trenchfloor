#!/bin/bash
cd "$(dirname "$0")" || exit 1
while true; do
  python3 -u server.py &
  echo $! > server.child.pid
  wait $!
  code=$?
  echo "$(date -Is) server.py exited ${code}; restarting in 2s" >> logs/server.log
  sleep 2
done
