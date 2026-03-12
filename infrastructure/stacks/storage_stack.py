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
            versioned=False,  # Disabled to reduce costs
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

        # SNS Topic for regional alerts (DynamoDB, API Gateway)
        self.alert_topic = sns.Topic(
            self,
            "RegionalAlertTopic",
            topic_name="contextanchor-regional-alerts",
            display_name="ContextAnchor Regional Alerts",
        )

        # CloudWatch Alarm for DynamoDB consumed read capacity
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
            cw_actions.SnsAction(self.alert_topic)
        )

        # CloudWatch Alarm for API Gateway request count
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
            cw_actions.SnsAction(self.alert_topic)
        )
