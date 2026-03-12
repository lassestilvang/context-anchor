# ContextAnchor Installation Guide

ContextAnchor is composed of a Command Line Interface (CLI) tool and an AWS Serverless backend. This guide covers how to set up both parts.

## Backend Infrastructure (AWS Resources)

When you deploy the backend using the provided scripts, the following AWS resources will be provisioned in your account:

### 1. Compute (AWS Lambda)
- **CaptureContextFunction**: Processes Git signals and developer intent using Amazon Bedrock.
- **GetLatestContextFunction**: Retrieves the most recent snapshot for a branch.
- **GetContextFunction**: Retrieves a specific snapshot by ID.
- **ListContextsFunction**: Handles repository-wide and branch-specific listing.
- **DeleteContextFunction**: Performs soft-deletion of snapshots.
- **HealthCheck**: Provides system status monitoring.

> [!NOTE]
> All Lambda functions are standardized to use unified entry points via the `contextanchor.handlers` package, ensuring consistent logic and security enforcement across all endpoints.

### 2. Database (Amazon DynamoDB)
- **ContextSnapshotsTable**: Stores all context data.
  - **Partition Key**: `PK` (REPO#<id>)
  - **Sort Key**: `SK` (BRANCH#<name>#TS#<timestamp>)
  - **Global Secondary Indexes**: `BySnapshotId`, `ByDeveloper` for efficient lookups.
  - **Encryption**: AES-256 at rest.
  - **TTL**: Automatically purges items older than 90 days.

### 3. API & Security (Amazon API Gateway)
- **REST API**: A regional endpoint providing the secure interface for the CLI.
- **API Key**: Required for all authenticated requests.
- **Usage Plan**: Configured with rate limiting and throttling to stay within free tier limits.
- **TLS 1.3**: Enforced for all data in transit.

### 4. Storage & Monitoring
- **Amazon S3**: For application logs and infrastructure artifacts.
- **CloudWatch Logs**: Centralized logging for all Lambda functions.
- **AWS Budgets**: Configured with a $5/month threshold to prevent unexpected costs.

---

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

4. **Configure the API Key:**
   Store your API Gateway key in `~/.contextanchor/credentials`.

   ```bash
   mkdir -p ~/.contextanchor
   chmod 700 ~/.contextanchor
   printf '%s' '<your-api-key>' > ~/.contextanchor/credentials
   chmod 600 ~/.contextanchor/credentials
   ```

## Production Operations Docs

Before user rollout, complete:

- `docs/production-readiness-checklist.md`
- `docs/operational-runbook.md`
- `docs/user-onboarding.md`

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
