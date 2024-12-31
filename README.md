# README

## Overview
This guide provides steps to set up, build, deploy, and manage a Serverless project with AWS Lambda using Docker. It includes commands for initializing the project, managing dependencies, and interacting with AWS Lambda functions.

---

## Docker Setup


### Build and Start the Container
Build the Docker image and start the container:
```bash
docker compose up -d --build
```

### Check if Container is Running
Verify that the container is up and running:
```bash
docker compose ps
```

### Check Logs
View the logs from the container for debugging purposes:
```bash
docker compose logs
```

### Access the Container
Open a bash shell inside the running container:
```bash
docker compose exec serverless bash
```

### Stop and Remove All Containers
To stop and clean up existing Docker containers and networks:
```bash
docker compose down
docker stop $(docker ps -a -q)
```

### Remove Any Existing Images
Remove any Docker images for the serverless project to ensure a clean build:
```bash
docker rmi $(docker images -q serverless-project_serverless)
```

---

## Serverless Framework Setup

### Step 1: Create a Serverless Project
The following command initializes a new Serverless project using the AWS Python 3 template:
```bash
serverless create --template aws-python3 --path my-lambda-api
```

### Step 2: Set Up Project Files
Run the following commands to set up the necessary project files and dependencies:
```bash
# Create a requirements.txt file
touch requirements.txt

# Initialize a Node.js project
npm init -f

# Install the Serverless Python Requirements plugin
npm install --save-dev serverless-python-requirements
npm install --save-dev serverless-dotenv-plugin

# List all files to confirm the setup
ls -la
```

---

## Deployment and Management

### Deploy the Project
Deploy the Serverless application to AWS:
```bash
serverless deploy
```

### Remove the Deployment
To clean up and remove the deployment:
```bash
serverless remove
```

### Check Deployed Lambda Functions
List all Lambda functions deployed and filter for your project:
```bash
aws lambda list-functions | grep my-lambda-api
```

### Get Deployment Information
Retrieve detailed information about the current deployment:
```bash
serverless info --verbose
```

