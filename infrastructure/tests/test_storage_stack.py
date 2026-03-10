"""
Unit tests for Storage stack.

Tests S3 and cost guardrails configuration including:
- S3 bucket creation
- Lifecycle policies
- Budget configuration
- CloudWatch alarms
"""
import aws_cdk as cdk
from aws_cdk import assertions
from stacks.storage_stack import StorageStack


def test_s3_bucket_created():
    """Test that S3 bucket is created."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify S3 bucket exists
    template.resource_count_is("AWS::S3::Bucket", 1)


def test_s3_encryption():
    """Test that S3 bucket has encryption enabled."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify encryption is configured
    template.has_resource_properties("AWS::S3::Bucket", {
        "BucketEncryption": {
            "ServerSideEncryptionConfiguration": [
                {
                    "ServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        }
    })


def test_s3_public_access_blocked():
    """Test that S3 bucket blocks all public access."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify public access is blocked
    template.has_resource_properties("AWS::S3::Bucket", {
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True
        }
    })


def test_s3_lifecycle_policies():
    """Test that S3 bucket has lifecycle policies configured."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify lifecycle rules exist
    template.has_resource_properties("AWS::S3::Bucket", {
        "LifecycleConfiguration": {
            "Rules": assertions.Match.array_with([
                # Transition to IA after 30 days
                assertions.Match.object_like({
                    "Id": "TransitionToIA",
                    "Status": "Enabled",
                    "Transitions": [
                        {
                            "StorageClass": "STANDARD_IA",
                            "TransitionInDays": 30
                        }
                    ]
                }),
                # Delete after 90 days
                assertions.Match.object_like({
                    "Id": "DeleteAfter90Days",
                    "Status": "Enabled",
                    "ExpirationInDays": 90
                }),
                # Cleanup incomplete uploads
                assertions.Match.object_like({
                    "Id": "CleanupIncompleteUploads",
                    "Status": "Enabled",
                    "AbortIncompleteMultipartUpload": {
                        "DaysAfterInitiation": 7
                    }
                })
            ])
        }
    })


def test_sns_topic_created():
    """Test that SNS topic for alerts is created."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify SNS topic exists
    template.resource_count_is("AWS::SNS::Topic", 1)


def test_budget_created():
    """Test that AWS Budget is created."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify budget exists
    template.resource_count_is("AWS::Budgets::Budget", 1)


def test_budget_configuration():
    """Test that budget has correct configuration."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify budget configuration
    template.has_resource_properties("AWS::Budgets::Budget", {
        "Budget": {
            "BudgetType": "COST",
            "TimeUnit": "MONTHLY",
            "BudgetLimit": {
                "Amount": 5.0,
                "Unit": "USD"
            }
        }
    })


def test_budget_notifications():
    """Test that budget has notifications configured."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify notifications exist
    template.has_resource_properties("AWS::Budgets::Budget", {
        "NotificationsWithSubscribers": assertions.Match.array_with([
            # 80% threshold notification
            assertions.Match.object_like({
                "Notification": {
                    "NotificationType": "ACTUAL",
                    "ComparisonOperator": "GREATER_THAN",
                    "Threshold": 80,
                    "ThresholdType": "PERCENTAGE"
                }
            }),
            # Forecasted 100% notification
            assertions.Match.object_like({
                "Notification": {
                    "NotificationType": "FORECASTED",
                    "ComparisonOperator": "GREATER_THAN",
                    "Threshold": 100,
                    "ThresholdType": "PERCENTAGE"
                }
            })
        ])
    })


def test_cloudwatch_alarms_created():
    """Test that CloudWatch alarms are created."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify 3 CloudWatch alarms exist
    template.resource_count_is("AWS::CloudWatch::Alarm", 3)


def test_lambda_invocations_alarm():
    """Test that Lambda invocations alarm is configured."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify Lambda alarm exists
    template.has_resource_properties("AWS::CloudWatch::Alarm", {
        "AlarmName": "contextanchor-lambda-invocations-high",
        "Threshold": 800000,
        "ComparisonOperator": "GreaterThanThreshold"
    })


def test_dynamodb_reads_alarm():
    """Test that DynamoDB reads alarm is configured."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify DynamoDB alarm exists
    template.has_resource_properties("AWS::CloudWatch::Alarm", {
        "AlarmName": "contextanchor-dynamodb-reads-high",
        "Threshold": 20,
        "ComparisonOperator": "GreaterThanThreshold"
    })


def test_api_requests_alarm():
    """Test that API requests alarm is configured."""
    app = cdk.App()
    stack = StorageStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify API Gateway alarm exists
    template.has_resource_properties("AWS::CloudWatch::Alarm", {
        "AlarmName": "contextanchor-api-requests-high",
        "Threshold": 800000,
        "ComparisonOperator": "GreaterThanThreshold"
    })
