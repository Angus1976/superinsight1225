# Custom Label Studio with SSO support
FROM heartexlabs/label-studio:latest

# 与根 Dockerfile 一致的 PyPI 源（可由 compose build.args 覆盖）
ARG PIP_INDEX_URL=https://repo.huaweicloud.com/repository/pypi/simple
ARG PIP_TRUSTED_HOST=repo.huaweicloud.com

# Install label-studio-sso package（拉大 pip 超时，避免弱网构建失败）
ENV PIP_DEFAULT_TIMEOUT=600
RUN pip config set global.index-url "${PIP_INDEX_URL}" && \
    pip config set install.trusted-host "${PIP_TRUSTED_HOST}"
RUN pip install label-studio-sso

# Copy custom settings that will be imported
COPY settings_sso.py /label-studio/label_studio/core/settings/settings_sso.py

# Copy custom branding & i18n files for SuperInsight white-labeling
COPY i18n-inject.js /label-studio/custom/i18n-inject.js
COPY branding.css /label-studio/custom/branding.css
# NOTE: Add favicon.svg to deploy/label-studio/ and uncomment the line below
# COPY favicon.svg /label-studio/custom/favicon.svg

# Copy startup script
COPY --chmod=755 entrypoint-sso.sh /entrypoint-sso.sh

# Set environment variables
ENV LABEL_STUDIO_SSO_ENABLED=true

# Expose port
EXPOSE 8080

# Use custom entrypoint with original CMD
ENTRYPOINT ["/entrypoint-sso.sh"]
CMD ["label-studio"]
