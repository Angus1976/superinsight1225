#!/usr/bin/env bash
# 兼容入口：等价于 ./scripts/docker-compose-resilient.sh pull
exec "$(cd "$(dirname "$0")" && pwd)/docker-compose-resilient.sh" pull
