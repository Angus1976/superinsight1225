FROM node:20-alpine

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=development

# Install dependencies
RUN apk add --no-cache \
    curl \
    git

# Copy package files
COPY package.json package-lock.json ./

# Install npm dependencies
RUN npm ci

# Copy application code
COPY . .

# Expose port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5173 || exit 1

# Start the development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
