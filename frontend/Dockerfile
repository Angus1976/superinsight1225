FROM node:20-alpine

WORKDIR /app

ENV NODE_ENV=development

# 可选：构建时传入国内镜像，例如 https://registry.npmmirror.com
ARG NPM_CONFIG_REGISTRY=
RUN if [ -n "$NPM_CONFIG_REGISTRY" ]; then npm config set registry "$NPM_CONFIG_REGISTRY"; fi

RUN apk add --no-cache curl git

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5173 || exit 1

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
