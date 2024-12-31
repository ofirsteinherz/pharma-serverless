#!/bin/bash

# Configure AWS credentials
if [ ! -z "$AWS_ACCESS_KEY_ID" ] && [ ! -z "$AWS_SECRET_ACCESS_KEY" ]; then
    aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
    aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
    aws configure set default.region ${AWS_DEFAULT_REGION:-us-east-1}
    aws configure set default.output json
fi

# Configure Serverless credentials
if [ ! -z "$SERVERLESS_ACCESS_KEY" ]; then
    mkdir -p $HOME/.serverless
    cat > $HOME/.serverless/config.json << EOF
{
  "accessKey": "$SERVERLESS_ACCESS_KEY"
}
EOF
fi

exec "$@"