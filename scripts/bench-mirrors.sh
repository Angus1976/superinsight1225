#!/usr/bin/env bash
# 本机粗测 PyPI / Docker 镜像站延迟（仅参考，请以实测为准）。
# Docker Hub 加速：将 docker/daemon.json.example 内容合并进 Docker Desktop → Settings → Docker Engine，Apply & Restart 后执行 docker info | grep -A5 Mirrors

set -u
echo "=== PyPI simple/pip/ 总耗时（越小越好，15s 超时）==="
bench_pypi() {
  local name="$1" url="$2"
  printf '  %-12s ' "$name"
  curl -fsS -o /dev/null -m 15 -w '%{time_total}s\n' "$url" 2>&1 || echo 'FAIL'
}
bench_pypi huaweicloud 'https://repo.huaweicloud.com/repository/pypi/simple/pip/'
bench_pypi aliyun 'https://mirrors.aliyun.com/pypi/simple/pip/'
bench_pypi tuna 'https://pypi.tuna.tsinghua.edu.cn/simple/pip/'
bench_pypi tencent 'https://mirrors.cloud.tencent.com/pypi/simple/pip/'

echo ""
echo "=== Docker /v2/ 探测（401 属正常，看 total 时间）==="
bench_reg() {
  local name="$1" url="$2"
  printf '  %-12s ' "$name"
  curl -o /dev/null -m 15 -s -w '%{time_total}s http:%{http_code}\n' "$url" 2>&1 || echo 'FAIL'
}
bench_reg daocloud 'https://docker.m.daocloud.io/v2/'
bench_reg xuanyuan 'https://docker.xuanyuan.me/v2/'
bench_reg onems 'https://docker.1ms.run/v2/'

echo ""
echo "建议："
echo "  1) PyPI：在 .env 或 export 设置 PIP_INDEX_URL / PIP_TRUSTED_HOST（见 docker-compose.yml build.args）"
echo "  2) Docker Hub：合并 docker/daemon.json.example 到 Docker Engine 配置后重启 Docker"
