#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "==> git pull"
git pull

echo "==> docker compose up -d --build"
docker compose up -d --build

echo "==> prune dangling images"
docker image prune -f

echo "==> status"
docker compose ps

echo "==> health check :8011"
for i in $(seq 1 10); do
  if curl -sf http://localhost:8011/ -o /dev/null; then
    echo "OK"
    exit 0
  fi
  sleep 1
done
echo "FAIL: service not responding on :8011" >&2
exit 1
