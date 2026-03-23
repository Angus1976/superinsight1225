#!/bin/bash
# 修复 PVC 挂载目录权限后切回 elasticsearch 用户启动
chown -R 1000:1000 /usr/share/elasticsearch/data
exec su elasticsearch -s /bin/bash -c "/usr/local/bin/docker-entrypoint.sh"
