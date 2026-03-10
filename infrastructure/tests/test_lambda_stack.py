"""
Unit tests for Lambda stack.

Tests Lambda function configuration including:
- Function creation
- Runtime and memory settings
- IAM permissions
- Environment variables
"""
import aws_cdk as cdk
from aws_cdk import assertions
from stacks.dynamodb_stack import DynamoDBStack
from stacks.lambda_stack import LambdaStack


def test_all_functions_created():
    """Test that all Lambda functions are created."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify 5 Lambda functions exist
    template.resource_count_is("AWS::Lambda::Function", 5)


def test_capture_function_configuration():
    """Test capture function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify capture function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-capture",
        "Runtime": "python3.11",
        "MemorySize": 512,
        "Timeout": 30,
        "Handler": "capture.handler"
    })


def test_retrieve_function_configuration():
    """Test retrieve function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify retrieve function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-retrieve",
        "Runtime": "python3.11",
        "MemorySize": 256,
        "Timeout": 10,
        "Handler": "retrieve.handler"
    })


def test_delete_function_configuration():
    """Test delete function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify delete function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-delete",
        "Runtime": "python3.11",
        "MemorySize": 256,
        "Timeout": 10,
        "Handler": "delete.handler"
    })


def test_list_function_configuration():
    """Test list function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify list function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-list",
        "Runtime": "python3.11",
        "MemorySize": 256,
        "Timeout": 10,
        "Handler": "list.handler"
    })


def test_health_function_configuration():
    """Test health function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify health function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-health",
        "Runtime": "python3.11",
        "MemorySize": 128,
        "Timeout": 3,
        "Handler": "health.handler"
    })


def test_capture_function_environment():
    """Test capture function has required environment variables."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify environment variables include Bedrock model ID
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-capture",
        "Environment": {
            "Variables": assertions.Match.object_like({
                "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
                "POWERTOOLS_SERVICE_NAME": "contextanchor",
                "LOG_LEVEL": "INFO"
            })
        }
    })


def test_dynamodb_permissions():
    """Test Lambda functions have appropriate DynamoDB permissions."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify IAM policies exist for DynamoDB access
    template.has_resource_properties("AWS::IAM::Policy", {
        "PolicyDocument": {
            "Statement": assertions.Match.array_with([
                assertions.Match.object_like({
                    "Action": assertions.Match.array_with([
                        assertions.Match.string_like_regexp("dynamodb:.*")
                    ]),
                    "Effect": "Allow"
                })
            ])
        }
    })


def test_bedrock_permissions():
    """Test capture function has Bedrock invoke permissions."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify Bedrock permissions exist
    template.has_resource_properties("AWS::IAM::Policy", {
        "PolicyDocument": {
            "Statement": assertions.Match.array_with([
                assertions.Match.object_like({
                    "Action": ["bedrock:InvokeModel"],
                    "Effect": "Allow"
                })
            ])
        }
    })


def test_iam_roles_created():
    """Test that IAM roles are created for Lambda functions."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    lambda_stack = LambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify IAM roles exist (one per function)
    template.resource_count_is("AWS::IAM::Role", 5)
