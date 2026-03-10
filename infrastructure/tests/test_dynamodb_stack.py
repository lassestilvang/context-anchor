"""
Unit tests for DynamoDB stack.

Tests DynamoDB table configuration including:
- Table creation with correct keys
- GSI configuration
- Encryption settings
- TTL configuration
- Billing mode
"""
import aws_cdk as cdk
from aws_cdk import assertions
from stacks.dynamodb_stack import DynamoDBStack


def test_table_created():
    """Test that ContextSnapshots table is created."""
    app = cdk.App()
    stack = DynamoDBStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify table exists
    template.resource_count_is("AWS::DynamoDB::Table", 1)


def test_table_keys():
    """Test that table has correct partition and sort keys."""
    app = cdk.App()
    stack = DynamoDBStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify partition key (PK)
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "KeySchema": [
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"}
        ]
    })


def test_gsi_by_developer():
    """Test that ByDeveloper GSI is configured correctly."""
    app = cdk.App()
    stack = DynamoDBStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify GSI exists with correct keys
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "GlobalSecondaryIndexes": assertions.Match.array_with([
            assertions.Match.object_like({
                "IndexName": "ByDeveloper",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            })
        ])
    })


def test_gsi_by_snapshot_id():
    """Test that BySnapshotId GSI is configured correctly."""
    app = cdk.App()
    stack = DynamoDBStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify GSI exists with correct keys
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "GlobalSecondaryIndexes": assertions.Match.array_with([
            assertions.Match.object_like({
                "IndexName": "BySnapshotId",
                "KeySchema": [
                    {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI2SK", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"}
            })
        ])
    })


def test_on_demand_billing():
    """Test that table uses on-demand billing mode."""
    app = cdk.App()
    stack = DynamoDBStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify billing mode
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "BillingMode": "PAY_PER_REQUEST"
    })


def test_encryption_enabled():
    """Test that table has encryption enabled (AES-256)."""
    app = cdk.App()
    stack = DynamoDBStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify encryption is configured
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "SSESpecification": {
            "SSEEnabled": True
        }
    })


def test_ttl_configured():
    """Test that TTL is configured on retention_expires_at field."""
    app = cdk.App()
    stack = DynamoDBStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify TTL attribute
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "TimeToLiveSpecification": {
            "AttributeName": "retention_expires_at",
            "Enabled": True
        }
    })


def test_table_name():
    """Test that table has correct name."""
    app = cdk.App()
    stack = DynamoDBStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify table name
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "TableName": "ContextSnapshots"
    })


def test_attribute_definitions():
    """Test that all required attributes are defined."""
    app = cdk.App()
    stack = DynamoDBStack(app, "TestStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify all attributes are defined
    template.has_resource_properties("AWS::DynamoDB::Table", {
        "AttributeDefinitions": assertions.Match.array_with([
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
            {"AttributeName": "GSI2PK", "AttributeType": "S"},
            {"AttributeName": "GSI2SK", "AttributeType": "S"},
        ])
    })
