# ContextAnchor AWS Infrastructure

This directory contains the AWS CDK infrastructure code for ContextAnchor.

## Architecture

The infrastructure is organized into four CDK stacks:

1. **DynamoDBStack** - Data persistence layer
   - ContextSnapshots table with GSIs
   - On-demand billing mode
   - AES-256 encryption at rest
   - TTL for 90-day retention

2. **LambdaStack** - Serverless compute layer
   - Context capture function (with Bedrock integration)
   - Context retrieval function
   - Context deletion function
   - Context listing function
   - Health check function

3. **ApiGatewayStack** - API layer
   - REST API with regional endpoint
   - API key authentication
   - Rate limiting and throttling
   - CORS configuration

4. **StorageStack** - Storage and cost management
   - S3 bucket with lifecycle policies
   - AWS Budgets for cost monitoring
   - CloudWatch alarms for usage alerts

## Prerequisites

- Python 3.11+
- AWS CLI configured with credentials
- AWS CDK CLI installed (`npm install -g aws-cdk`)

## Setup

1. Install dependencies:
```bash
cd infrastructure
pip install -r requirements.txt
```

2. Bootstrap CDK (first time only):
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

## Deployment

Deploy all stacks:
```bash
cdk deploy --all
```

Deploy specific stack:
```bash
cdk deploy ContextAnchorDynamoDBStack
```

## Useful Commands

- `cdk ls` - List all stacks
- `cdk synth` - Synthesize CloudFormation templates
- `cdk diff` - Compare deployed stack with current state
- `cdk deploy` - Deploy stacks to AWS
- `cdk destroy` - Remove stacks from AWS

## Cost Optimization

The infrastructure is designed to stay within AWS Free Tier limits:

- **DynamoDB**: On-demand billing, 25 GB storage limit
- **Lambda**: 1M requests/month, 400k GB-seconds compute
- **API Gateway**: 1M requests/month
- **S3**: 5 GB storage with lifecycle policies

Budget alerts are configured at $5/month threshold with notifications at 80% usage.

## Security

- All data encrypted at rest (AES-256)
- TLS 1.3 for data in transit
- API key authentication required
- Least-privilege IAM roles
- No public access to S3 buckets

## Monitoring

CloudWatch alarms monitor:
- Lambda invocation count
- DynamoDB read capacity
- API Gateway request count

Alerts are sent to SNS topic when thresholds are exceeded.
