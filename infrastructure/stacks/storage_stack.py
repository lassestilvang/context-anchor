"""
Storage and cost guardrails stack for ContextAnchor.

Requirements: 14.5, 14.6
"""
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_s3 as s3,
    aws_budgets as budgets,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
)
from constructs import Construct


class StorageStack(Stack):
    """
    Stack for S3 storage and cost guardrails.
    
    Creates:
    - S3 bucket with lifecycle policies for cost management
    - AWS Budgets with Free Tier thresholds
    - CloudWatch alarms for cost alerts
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Requirement 14.5: S3 with lifecycle policies
        # S3 bucket for optional file storage (exports, large payloads)
        self.bucket = s3.Bucket(
            self,
            "ContextAnchorBucket",
            bucket_name=None,  # Auto-generated name
            encryption=s3.BucketEncryption.S3_MANAGED,  # AES-256 encryption
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioning=False,  # Disabled to reduce costs
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
            lifecycle_rules=[
                # Transition to Infrequent Access after 30 days
                s3.LifecycleRule(
                    id="TransitionToIA",
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        )
                    ],
                ),
                # Delete objects after 90 days (matches snapshot retention)
                s3.LifecycleRule(
                    id="DeleteAfter90Days",
                    enabled=True,
                    expiration=Duration.days(90),
                ),
                # Delete incomplete multipart uploads after 7 days
                s3.LifecycleRule(
                    id="CleanupIncompleteUploads",
                    enabled=True,
                    abort_incomplete_multipart_upload_after=Duration.days(7),
                ),
            ],
        )

        # SNS Topic for budget alerts
        alert_topic = sns.Topic(
            self,
            "BudgetAlertTopic",
            topic_name="contextanchor-budget-alerts",
            display_name="ContextAnchor Budget Alerts",
        )

        # Requirement 14.6: Cost guardrails with Free Tier thresholds
        # AWS Budget for monthly spend monitoring
        # Free Tier limits:
        # - Lambda: 1M requests/month, 400k GB-seconds compute
        # - DynamoDB: 25 GB storage, 25 WCU, 25 RCU
        # - API Gateway: 1M requests/month
        # - S3: 5 GB storage, 20k GET, 2k PUT
        budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=5.0,  # $5/month threshold
                    unit="USD",
                ),
                budget_name="ContextAnchor-Monthly-Budget",
                cost_filters={
                    "TagKeyValue": ["user:Project$ContextAnchor"],
                },
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=80,  # Alert at 80% of budget
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=alert_topic.topic_arn,
                        )
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="FORECASTED",
                        comparison_operator="GREATER_THAN",
                        threshold=100,  # Alert if forecasted to exceed budget
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=alert_topic.topic_arn,
                        )
                    ],
                ),
            ],
        )

        # CloudWatch Alarm for Lambda invocation count
        # Alert if approaching Free Tier limit (1M requests/month)
        lambda_invocations_alarm = cloudwatch.Alarm(
            self,
            "LambdaInvocationsAlarm",
            alarm_name="contextanchor-lambda-invocations-high",
            alarm_description="Alert when Lambda invocations approach Free Tier limit",
            metric=cloudwatch.Metric(
                namespace="AWS/Lambda",
                metric_name="Invocations",
                statistic="Sum",
                period=Duration.days(1),
                dimensions_map={
                    "FunctionName": "contextanchor-*",
                },
            ),
            threshold=800000,  # 800k invocations (80% of 1M monthly limit)
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        lambda_invocations_alarm.add_alarm_action(
            cw_actions.SnsAction(alert_topic)
        )

        # CloudWatch Alarm for DynamoDB consumed read capacity
        # Alert if consistently high usage
        dynamodb_reads_alarm = cloudwatch.Alarm(
            self,
            "DynamoDBReadsAlarm",
            alarm_name="contextanchor-dynamodb-reads-high",
            alarm_description="Alert when DynamoDB read capacity is consistently high",
            metric=cloudwatch.Metric(
                namespace="AWS/DynamoDB",
                metric_name="ConsumedReadCapacityUnits",
                statistic="Sum",
                period=Duration.hours(1),
                dimensions_map={
                    "TableName": "ContextSnapshots",
                },
            ),
            threshold=20,  # 20 RCU average (approaching Free Tier limit of 25)
            evaluation_periods=3,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        dynamodb_reads_alarm.add_alarm_action(
            cw_actions.SnsAction(alert_topic)
        )

        # CloudWatch Alarm for API Gateway request count
        # Alert if approaching Free Tier limit (1M requests/month)
        api_requests_alarm = cloudwatch.Alarm(
            self,
            "ApiRequestsAlarm",
            alarm_name="contextanchor-api-requests-high",
            alarm_description="Alert when API requests approach Free Tier limit",
            metric=cloudwatch.Metric(
                namespace="AWS/ApiGateway",
                metric_name="Count",
                statistic="Sum",
                period=Duration.days(1),
            ),
            threshold=800000,  # 800k requests (80% of 1M monthly limit)
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        api_requests_alarm.add_alarm_action(
            cw_actions.SnsAction(alert_topic)
        )
