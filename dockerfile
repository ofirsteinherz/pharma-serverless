FROM --platform=linux/arm64 node:18-slim

# Install basic dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    zip \
    unzip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash serverless_user

# Install AWS CLI v2 for ARM64
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf aws awscliv2.zip

# Install Serverless Framework and plugins
RUN npm install -g serverless
RUN npm install -g serverless-dotenv-plugin

# Set working directory and permissions
WORKDIR /app
RUN mkdir -p /home/serverless_user/.aws && \
    mkdir -p /home/serverless_user/.serverless && \
    chown -R serverless_user:serverless_user /home/serverless_user && \
    chown -R serverless_user:serverless_user /app

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    chown serverless_user:serverless_user /entrypoint.sh

# Switch to non-root user
USER serverless_user

# Initialize package.json and install plugin locally
RUN cd /app && \
    npm init -y && \
    npm install --save-dev serverless-dotenv-plugin

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]