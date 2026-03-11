# ContextAnchor Installation Guide

ContextAnchor is composed of a Command Line Interface (CLI) tool and an AWS Serverless backend. This guide covers how to set up both parts.

## Prerequisites

### For the CLI
- Python 3.11 or higher
- Git
- pip (Python package installer)

### For the Backend (AWS Infrastructure)
- An AWS Account
- AWS CLI configured with administrator access
- Node.js (>= 18.0.0)
- Python 3.11+
- AWS CDK (`npm install -g aws-cdk`)

## Part 1: Backend Deployment

The backend uses AWS CDK to provision Lambda functions, API Gateway, and DynamoDB.

1. **Navigate to the infrastructure directory:**
   ```bash
   cd infrastructure
   ```

2. **Run the deployment script:**
   ```bash
   ./deploy.sh
   ```
   This script will create a Python virtual environment, install dependencies, run tests, and synthesize the CloudFormation template. Finally, it will deploy the resources to your AWS account.

3. **Note the API Endpoint:**
   After a successful deployment, the CDK will output an API Gateway endpoint (e.g., `https://xxxxxx.execute-api.us-east-1.amazonaws.com/prod/`). Save this URL, as you will need it to configure the CLI.

## Part 2: CLI Installation

1. **Install from source (while in the root of the project):**
   ```bash
   pip install .
   ```
   For development, you can install it in editable mode:
   ```bash
   pip install -e ".[dev]"
   ```

2. **Verify installation:**
   ```bash
   contextanchor --version
   ```

## Part 3: Configuration

To initialize ContextAnchor for a specific Git repository, follow these steps:

1. **Navigate to your Git repository:**
   ```bash
   cd /path/to/your/repo
   ```

2. **Initialize ContextAnchor:**
   ```bash
   contextanchor init
   ```
   This command creates a `.contextanchor` directory at the root of your repository and installs git hooks to monitor your activity.

3. **Configure the API Endpoint:**
   Open the generated `.contextanchor/config.yaml` file in your repository and update the `api_endpoint` field with the URL you received during the backend deployment.

   ```yaml
   api_endpoint: "https://xxxxxx.execute-api.us-east-1.amazonaws.com/prod/v1"
   ```

## Troubleshooting

- **"Git hook execution failed":** Ensure that you have permissions to write to the `.git/hooks` directory in your repository.
- **"Network Error":** Verify that your `api_endpoint` in `config.yaml` is correct and that the API Gateway is accessible. If you're offline, operations will be queued locally.
- **AWS CDK Issues:** If the deployment fails, ensure your AWS credentials are fully configured and you have sufficient permissions (e.g. `aws configure`).

## Teardown

If you wish to remove all AWS infrastructure created for ContextAnchor:

1. Navigate to the `infrastructure` directory:
   ```bash
   cd infrastructure
   ```
2. Run the teardown script:
   ```bash
   ./teardown.sh
   ```
