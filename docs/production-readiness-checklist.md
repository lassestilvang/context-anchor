# ContextAnchor Production Readiness Checklist

Use this checklist before enabling ContextAnchor for a team or production workflow.

## Scope

This checklist validates:

- AWS infrastructure deployment health
- API endpoint and API key setup
- CLI configuration and smoke tests
- Monitoring, alerting, and cost guardrails
- Security and rollback readiness

## Release Metadata

- [ ] Release owner assigned
- [ ] Deployment window approved
- [ ] Rollback owner assigned
- [ ] Pager/on-call contact confirmed
- [ ] Change ticket linked

## Environment Variables

Run this once in your terminal before executing checklist commands:

```bash
export AWS_PROFILE=<your-profile>
export AWS_REGION=eu-north-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export API_ID=$(aws apigateway get-rest-apis \
  --query "items[?name=='ContextAnchor API'].id | [0]" \
  --output text)
export API_BASE="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
```

## 1. Pre-Deployment Validation

- [ ] `aws sts get-caller-identity` succeeds
- [ ] `node --version` returns `v18+`
- [ ] `python3 --version` returns `3.11+`
- [ ] `cdk --version` or `npx aws-cdk --version` works
- [ ] `infrastructure/tests` pass before deploy

```bash
cd infrastructure
./deploy.sh
```

## 2. Stack Deployment Validation

Validate every stack is in `CREATE_COMPLETE` or `UPDATE_COMPLETE`:

```bash
for stack in \
  ContextAnchorDynamoDBStack \
  ContextAnchorLambdaStack \
  ContextAnchorApiGatewayStack \
  ContextAnchorStorageStack \
  ContextAnchorBudgetStack; do
  aws cloudformation describe-stacks \
    --stack-name "$stack" \
    --query 'Stacks[0].StackStatus' \
    --output text
done
```

- [ ] DynamoDB stack healthy
- [ ] Lambda stack healthy
- [ ] API Gateway stack healthy
- [ ] Storage stack healthy
- [ ] Budget stack healthy

## 3. API Endpoint And Auth Validation

### 3.1 Health Endpoint

```bash
curl -sS "${API_BASE}/v1/health"
```

- [ ] Returns HTTP 200 with `"status": "healthy"`

### 3.2 Auth Guardrail

Without API key:

```bash
curl -i -sS "${API_BASE}/v1/contexts?repository_id=demo"
```

- [ ] Returns `403` (or equivalent unauthorized response)

With API key:

```bash
export API_KEY=$(aws apigateway get-api-keys \
  --name-query contextanchor-api-key \
  --include-values \
  --query 'items[0].value' \
  --output text)

curl -i -sS \
  -H "X-API-Key: ${API_KEY}" \
  "${API_BASE}/v1/contexts?repository_id=demo"
```

- [ ] Returns a response other than `401/403`, confirming key acceptance

## 4. Data Plane Validation

### 4.1 DynamoDB Schema

```bash
aws dynamodb describe-table --table-name ContextSnapshots \
  --query '{
    TableStatus:Table.TableStatus,
    BillingMode:Table.BillingModeSummary.BillingMode,
    SSE:Table.SSEDescription.Status,
    GSIs:Table.GlobalSecondaryIndexes[].IndexName
  }'

aws dynamodb describe-time-to-live \
  --table-name ContextSnapshots \
  --query 'TimeToLiveDescription.TimeToLiveStatus'
```

- [ ] Table is `ACTIVE`
- [ ] Billing mode is `PAY_PER_REQUEST`
- [ ] Encryption is enabled
- [ ] GSI `ByDeveloper` exists
- [ ] GSI `BySnapshotId` exists

### 4.2 Lambda Functions

```bash
for fn in \
  contextanchor-capture \
  contextanchor-retrieve \
  contextanchor-delete \
  contextanchor-list \
  contextanchor-health; do
  aws lambda get-function --function-name "$fn" \
    --query '{State:Configuration.State, Runtime:Configuration.Runtime, Timeout:Configuration.Timeout, Memory:Configuration.MemorySize}'
done
```

- [ ] All functions report `State: Active`
- [ ] Runtime is Python 3.11
- [ ] Timeout/memory values match deployment expectations

## 5. CLI Configuration Validation

### 5.1 API Endpoint Configuration

In each repository using ContextAnchor:

```bash
contextanchor init
```

Update `.contextanchor/config.yaml`:

```yaml
api_endpoint: "https://<api-id>.execute-api.<region>.amazonaws.com/prod/v1"
```

- [ ] Config file exists
- [ ] Endpoint points to deployed API

### 5.2 API Key Setup

```bash
mkdir -p ~/.contextanchor
chmod 700 ~/.contextanchor
printf '%s' '<api-key-value>' > ~/.contextanchor/credentials
chmod 600 ~/.contextanchor/credentials
```

- [ ] Credentials file exists
- [ ] File mode is `600`
- [ ] Key is readable by current user only

### 5.3 Smoke Test

```bash
contextanchor save-context -m "Production readiness smoke test"
contextanchor show-context
contextanchor list-contexts -l 5
contextanchor history -l 5
```

- [ ] Save succeeds
- [ ] Show/list/history return expected data

## 6. API Key Rotation Procedure

1. Create new key.

```bash
NEW_KEY_ID=$(aws apigateway create-api-key \
  --name "contextanchor-api-key-$(date +%Y%m%d)" \
  --enabled \
  --query id --output text)

USAGE_PLAN_ID=$(aws apigateway get-usage-plans \
  --query "items[?name=='Standard'].id | [0]" \
  --output text)

aws apigateway create-usage-plan-key \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --key-id "$NEW_KEY_ID" \
  --key-type API_KEY
```

2. Distribute new key to clients (`~/.contextanchor/credentials`).
3. Validate smoke test with new key.
4. Disable old key and monitor for failures.

```bash
aws apigateway update-api-key \
  --api-key <old-key-id> \
  --patch-operations op=replace,path=/enabled,value=false
```

5. Delete old key after stable period.

- [ ] New key created and attached to usage plan
- [ ] All environments updated
- [ ] Old key disabled and removed after validation

## 7. Monitoring And Alerting Validation

### 7.1 CloudWatch Alarms

```bash
aws cloudwatch describe-alarms \
  --alarm-names contextanchor-dynamodb-reads-high contextanchor-api-requests-high \
  --query 'MetricAlarms[].{Name:AlarmName,State:StateValue,Actions:AlarmActions}'
```

- [ ] Both alarms exist
- [ ] Alarm actions reference SNS topic(s)

### 7.2 SNS Topics And Subscriptions

```bash
aws sns list-topics --query "Topics[?contains(TopicArn, 'contextanchor')].TopicArn"
```

- [ ] `contextanchor-regional-alerts` topic exists
- [ ] `contextanchor-budget-alerts` topic exists
- [ ] At least one confirmed subscription exists for each topic

### 7.3 Budget Guardrails

```bash
aws budgets describe-budget \
  --account-id "$ACCOUNT_ID" \
  --budget-name ContextAnchor-Monthly-Budget
```

- [ ] Budget exists
- [ ] Monthly budget amount is set
- [ ] Notifications configured at expected thresholds

## 8. Security Validation

- [ ] `flake8 src tests` reports zero issues
- [ ] `bandit -r src` reports zero high-severity findings
- [ ] API key is not stored in repository files
- [ ] `.contextanchor/` remains git-ignored in monitored repositories
- [ ] No source file contents are transmitted in API payloads (metadata only)

## 9. Rollback Readiness

- [ ] `infrastructure/teardown.sh` tested in non-production account
- [ ] DynamoDB backup procedure validated
- [ ] Rollback communication template prepared
- [ ] Known-good deployment tag identified

## 10. Go/No-Go Signoff

- [ ] Infrastructure owner signoff
- [ ] Security owner signoff
- [ ] CLI owner signoff
- [ ] Product owner signoff

Release decision:

- [ ] GO
- [ ] NO-GO

If NO-GO, include blocking items and owners in the change ticket before rescheduling.
