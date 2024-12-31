# # Dockerfile
# FROM --platform=linux/arm64 node:18-slim

# # Install basic dependencies
# RUN apt-get update && apt-get install -y \
#     python3 \
#     python3-pip \
#     zip \
#     unzip \
#     curl \
#     git \
#     && rm -rf /var/lib/apt/lists/*

# # Create non-root user
# RUN useradd -m -s /bin/bash serverless_user

# # Install AWS CLI v2 for ARM64
# RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip" \
#     && unzip awscliv2.zip \
#     && ./aws/install \
#     && rm -rf aws awscliv2.zip

# # Install Serverless Framework
# RUN npm install -g serverless

# # Set working directory and permissions
# WORKDIR /app
# RUN mkdir -p /home/serverless_user/.aws && \
#     mkdir -p /home/serverless_user/.serverless && \
#     chown -R serverless_user:serverless_user /home/serverless_user && \
#     chown -R serverless_user:serverless_user /app

# # Switch to non-root user
# USER serverless_user

# # Create entrypoint script
# RUN echo '#!/bin/bash\n\
# mkdir -p $HOME/.aws\n\
# if [ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]; then\n\
#     echo "[default]" > $HOME/.aws/credentials\n\
#     echo "aws_access_key_id = $AWS_ACCESS_KEY_ID" >> $HOME/.aws/credentials\n\
#     echo "aws_secret_access_key = $AWS_SECRET_ACCESS_KEY" >> $HOME/.aws/credentials\n\
#     echo "[default]" > $HOME/.aws/config\n\
#     echo "region = ${AWS_DEFAULT_REGION:-us-east-1}" >> $HOME/.aws/config\n\
#     echo "output = json" >> $HOME/.aws/config\n\
# fi\n\
# exec "$@"' > $HOME/entrypoint.sh

# USER root
# RUN mv /home/serverless_user/entrypoint.sh /entrypoint.sh && \
#     chmod +x /entrypoint.sh

# USER serverless_user

# ENTRYPOINT ["/entrypoint.sh"]
# CMD ["bash"]

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