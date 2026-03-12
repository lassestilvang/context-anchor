# ContextAnchor Operational Runbook

This runbook is the operational playbook for running ContextAnchor in production.

## 1. Service Overview

- CLI: `contextanchor` (developer workstations)
- API: API Gateway (`/v1/...` endpoints)
- Compute: Lambda (`contextanchor-capture`, `contextanchor-retrieve`, `contextanchor-delete`, `contextanchor-list`, `contextanchor-health`)
- Storage: DynamoDB table `ContextSnapshots`
- AI: Amazon Bedrock model invocation from `contextanchor-capture`
- Cost guardrails: CloudWatch alarms and AWS Budget

## 2. Ownership And Escalation

- Primary owner: Platform/Infra team
- Secondary owner: CLI/Application team
- Escalation trigger: Sustained `5xx`, failed context saves, or cost alarms
- Escalation channel: Team on-call channel + incident ticket

## 3. Operational Cadence

### Daily

1. Verify API health endpoint.
2. Review Lambda error counts and duration trends.
3. Confirm no active critical CloudWatch alarms.

### Weekly

1. Run DynamoDB on-demand backup.
2. Review offline queue failure patterns from logs.
3. Validate API key inventory and stale keys.

### Monthly

1. Rotate API keys.
2. Review AWS Budget actual vs forecasted spend.
3. Review incident log and close follow-up tasks.

## 4. Standard Environment Setup

```bash
export AWS_PROFILE=<your-profile>
export AWS_REGION=eu-north-1
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export API_ID=$(aws apigateway get-rest-apis \
  --query "items[?name=='ContextAnchor API'].id | [0]" \
  --output text)
export API_BASE="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com/prod"
```

## 5. Common Operational Procedures

### 5.1 Health Check

```bash
curl -sS "${API_BASE}/v1/health"
```

Expected response:

```json
{"status":"healthy","dynamodb":"connected","version":"0.1.0"}
```

### 5.2 Cloud Logs Inspection

```bash
aws logs tail /aws/lambda/contextanchor-capture --since 15m --follow --region "$AWS_REGION"
```

Repeat for:

- `/aws/lambda/contextanchor-retrieve`
- `/aws/lambda/contextanchor-delete`
- `/aws/lambda/contextanchor-list`
- `/aws/lambda/contextanchor-health`

### 5.3 Local Client Logs

```bash
tail -n 200 ~/.contextanchor/logs/contextanchor.log
```

## 6. Backup And Restore

### 6.1 Create DynamoDB Backup

```bash
BACKUP_NAME="contextanchor-$(date +%Y%m%d-%H%M%S)"

aws dynamodb create-backup \
  --table-name ContextSnapshots \
  --backup-name "$BACKUP_NAME"
```

Validate backup status:

```bash
aws dynamodb list-backups \
  --table-name ContextSnapshots \
  --backup-type USER \
  --query 'BackupSummaries[].{Name:BackupName,Status:BackupStatus,Arn:BackupArn}'
```

### 6.2 Restore From Backup

Restore into a new table first (safer cutover):

```bash
aws dynamodb restore-table-from-backup \
  --target-table-name ContextSnapshotsRestore-$(date +%Y%m%d) \
  --backup-arn <backup-arn>
```

After restore:

1. Validate restored table schema and item counts.
2. Decide between rollback cutover or forensic-only restore.
3. If cutting over, redeploy Lambda config to point `TABLE_NAME` at restored table.
4. Run smoke tests (`save-context`, `show-context`, `list-contexts`).

## 7. Scaling Guidance

ContextAnchor already uses managed scaling primitives (API Gateway, Lambda, DynamoDB on-demand), but these controls are available for sustained load.

### 7.1 API Throughput

Increase usage plan limits if client traffic is throttled:

```bash
USAGE_PLAN_ID=$(aws apigateway get-usage-plans \
  --query "items[?name=='Standard'].id | [0]" \
  --output text)

aws apigateway update-usage-plan \
  --usage-plan-id "$USAGE_PLAN_ID" \
  --patch-operations \
    op=replace,path=/throttle/rateLimit,value=200 \
    op=replace,path=/throttle/burstLimit,value=400
```

### 7.2 Lambda Throughput

For hotspots, set reserved concurrency for specific functions:

```bash
aws lambda put-function-concurrency \
  --function-name contextanchor-capture \
  --reserved-concurrent-executions 20
```

If latency remains high, update memory/timeout in `infrastructure/stacks/lambda_stack.py` and redeploy.

## 8. Troubleshooting Playbooks

### 8.1 `save-context` Fails With Auth Error

Symptoms:

- CLI error mentions invalid/missing API key
- API returns `401` or `403`

Actions:

1. Confirm `~/.contextanchor/credentials` exists and is non-empty.
2. Check file permissions are `600`.
3. Verify key is attached to usage plan.
4. Retry `contextanchor save-context -m "auth validation"`.

### 8.2 Context Not Restoring On Branch Switch

Symptoms:

- No context panel after `git checkout`

Actions:

1. Verify hook files exist:
   - `.git/hooks/post-checkout`
   - `.git/hooks/post-commit`
2. Verify executable bit (`chmod +x .git/hooks/post-checkout .git/hooks/post-commit`).
3. Run manual fallback: `contextanchor show-context`.
4. Inspect local logs for hook errors.

### 8.3 Offline Queue Not Draining

Symptoms:

- `contextanchor sync` keeps reporting queued operations

Actions:

1. Validate API connectivity (`curl ${API_BASE}/v1/health`).
2. Inspect queued operations:

```bash
sqlite3 ~/.contextanchor/local.db \
  "select operation_id,operation_type,retry_count,next_retry_at,expires_at from offline_queue where completed=0 order by created_at;"
```

3. Check for expired operations (`expires_at` older than now).
4. Retry with valid API key and endpoint.

### 8.4 API 5xx Errors

Actions:

1. Tail relevant Lambda logs.
2. Check recent deployments.
3. Validate DynamoDB table status is `ACTIVE`.
4. Confirm Bedrock invocation permissions for capture function.

## 9. Incident Response Procedure

### 9.1 Triage

1. Classify severity (SEV1/SEV2/SEV3).
2. Open incident record.
3. Assign incident commander.

### 9.2 Mitigation

1. Stabilize API availability first (`/v1/health`).
2. Prefer safe degradation over hard failure (queue locally, retry later).
3. If needed, temporarily disable failing workflow surfaces and announce workaround.

### 9.3 Communication

1. Post initial incident summary within 15 minutes for SEV1/SEV2.
2. Post updates at regular intervals until mitigated.
3. Post recovery confirmation and user impact summary.

### 9.4 Recovery And Follow-Up

1. Validate end-to-end flows after mitigation.
2. Confirm alarms return to OK state.
3. Create postmortem with root cause, contributing factors, and corrective actions.

## 10. Cost Monitoring And Optimization

### 10.1 Guardrail Checks

```bash
aws budgets describe-budget \
  --account-id "$ACCOUNT_ID" \
  --budget-name ContextAnchor-Monthly-Budget

aws cloudwatch describe-alarms \
  --alarm-names contextanchor-dynamodb-reads-high contextanchor-api-requests-high \
  --query 'MetricAlarms[].{Name:AlarmName,State:StateValue,Threshold:Threshold}'
```

### 10.2 Cost Review

```bash
# Example range shown below; adjust dates for your reporting period.
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-03-31 \
  --granularity MONTHLY \
  --metrics UnblendedCost
```

If costs trend upward:

1. Inspect API request volume and throttle settings.
2. Inspect DynamoDB read/write patterns and query shape.
3. Verify S3 lifecycle policies remain active.
4. Review Bedrock invocation counts and prompt volume.

## 11. Periodic Readiness Drills

Run quarterly:

1. Backup and restore dry run.
2. API key rotation dry run.
3. Simulated API outage to validate offline queue behavior.
4. Incident communication drill.
