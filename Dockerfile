# SuperInsight Platform - Production Dockerfile for TCB
# 适用于腾讯云 CloudBase (TCB) 云托管部署

# 使用 Python 3.11 以获得更好的 Debian Bookworm 兼容性
FROM python:3.11-slim

# PyPI 源（构建时可通过 compose / build-arg 覆盖；默认华为云在本机测速较快）
ARG PIP_INDEX_URL=https://repo.huaweicloud.com/repository/pypi/simple
ARG PIP_TRUSTED_HOST=repo.huaweicloud.com

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /app

# 配置阿里云镜像源 (使用 Debian Trixie 以匹配基础镜像的包版本)
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        echo "Types: deb" > /etc/apt/sources.list.d/debian.sources && \
        echo "URIs: http://mirrors.aliyun.com/debian" >> /etc/apt/sources.list.d/debian.sources && \
        echo "Suites: trixie trixie-updates" >> /etc/apt/sources.list.d/debian.sources && \
        echo "Components: main contrib non-free non-free-firmware" >> /etc/apt/sources.list.d/debian.sources && \
        echo "Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg" >> /etc/apt/sources.list.d/debian.sources && \
        echo "" >> /etc/apt/sources.list.d/debian.sources && \
        echo "Types: deb" >> /etc/apt/sources.list.d/debian.sources && \
        echo "URIs: http://mirrors.aliyun.com/debian-security" >> /etc/apt/sources.list.d/debian.sources && \
        echo "Suites: trixie-security" >> /etc/apt/sources.list.d/debian.sources && \
        echo "Components: main contrib non-free non-free-firmware" >> /etc/apt/sources.list.d/debian.sources && \
        echo "Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg" >> /etc/apt/sources.list.d/debian.sources; \
    elif [ -f /etc/apt/sources.list ]; then \
        sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && \
        sed -i 's|security.debian.org/debian-security|mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list; \
    fi

# 配置 pip 镜像（备选：阿里云 mirrors.aliyun.com、清华 pypi.tuna.tsinghua.edu.cn）
RUN pip config set global.index-url "${PIP_INDEX_URL}" && \
    pip config set install.trusted-host "${PIP_TRUSTED_HOST}"

# 安装系统依赖 (移除 git 以避免依赖冲突)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（先安装 setuptools 以支持旧版包如 cx-Oracle）
# 国内镜像偶发 ReadTimeout，拉长默认超时避免 compose build --no-cache 失败
ENV PIP_DEFAULT_TIMEOUT=600
RUN pip install --no-cache-dir setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/
COPY main.py .

# 复制数据库迁移文件
COPY alembic/ ./alembic/
COPY alembic.ini .

# 空库时一键种子管理员（可选 docker exec 运行）
COPY scripts/seed_default_admin.py ./scripts/seed_default_admin.py

# 创建必要的目录
RUN mkdir -p /app/logs /app/uploads /app/exports /app/data

# 创建非 root 用户（安全最佳实践）
RUN useradd --create-home --shell /bin/bash --uid 1000 app \
    && chown -R app:app /app

# 切换到非 root 用户
USER app

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["python", "main.py"]
