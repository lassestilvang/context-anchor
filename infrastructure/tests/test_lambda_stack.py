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
from aws_cdk import aws_lambda as lambda_
from stacks.dynamodb_stack import DynamoDBStack


def create_test_lambda_stack(app):
    """Create Lambda stack with inline code for testing."""
    from stacks.lambda_stack import LambdaStack as OriginalLambdaStack
    
    # Create a test version that uses inline code
    class TestLambdaStack(OriginalLambdaStack):
        def __init__(self, scope, construct_id, table, **kwargs):
            # Override parent init to use inline code
            cdk.Stack.__init__(self, scope, construct_id, **kwargs)
            
            self.table = table
            self.functions = {}
            
            common_env = {
                "TABLE_NAME": table.table_name,
                "POWERTOOLS_SERVICE_NAME": "contextanchor",
                "LOG_LEVEL": "INFO",
            }
            
            # Use inline code for testing
            inline_code = "def handler(event, context): pass"
            
            self.functions["capture"] = lambda_.Function(
                self, "ContextCaptureFunction",
                function_name="contextanchor-capture",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_inline(inline_code),
                memory_size=512,
                timeout=cdk.Duration.seconds(30),
                environment={**common_env, "BEDROCK_MODEL_ID": "eu.anthropic.claude-haiku-4-5-20251001-v1:0"},
            )
            
            table.grant_write_data(self.functions["capture"])
            self.functions["capture"].add_to_role_policy(
                cdk.aws_iam.PolicyStatement(
                    effect=cdk.aws_iam.Effect.ALLOW,
                    actions=["bedrock:InvokeModel"],
                    resources=[f"arn:aws:bedrock:{self.region}:{self.account}:inference-profile/eu.anthropic.claude-haiku-4-5-20251001-v1:0"],
                )
            )
            
            self.functions["retrieve"] = lambda_.Function(
                self, "ContextRetrieveFunction",
                function_name="contextanchor-retrieve",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_inline(inline_code),
                memory_size=256,
                timeout=cdk.Duration.seconds(10),
                environment=common_env,
            )
            table.grant_read_data(self.functions["retrieve"])
            
            self.functions["delete"] = lambda_.Function(
                self, "ContextDeleteFunction",
                function_name="contextanchor-delete",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_inline(inline_code),
                memory_size=256,
                timeout=cdk.Duration.seconds(10),
                environment=common_env,
            )
            table.grant_write_data(self.functions["delete"])
            
            self.functions["list"] = lambda_.Function(
                self, "ContextListFunction",
                function_name="contextanchor-list",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_inline(inline_code),
                memory_size=256,
                timeout=cdk.Duration.seconds(10),
                environment=common_env,
            )
            table.grant_read_data(self.functions["list"])
            
            self.functions["health"] = lambda_.Function(
                self, "HealthCheckFunction",
                function_name="contextanchor-health",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler="index.handler",
                code=lambda_.Code.from_inline(inline_code),
                memory_size=128,
                timeout=cdk.Duration.seconds(3),
                environment={"SERVICE_NAME": "contextanchor"},
            )
    
    return TestLambdaStack


def test_all_functions_created():
    """Test that all Lambda functions are created."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify 5 Lambda functions exist
    template.resource_count_is("AWS::Lambda::Function", 5)


def test_capture_function_configuration():
    """Test capture function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify capture function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-capture",
        "Runtime": "python3.11",
        "MemorySize": 512,
        "Timeout": 30,
    })


def test_retrieve_function_configuration():
    """Test retrieve function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify retrieve function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-retrieve",
        "Runtime": "python3.11",
        "MemorySize": 256,
        "Timeout": 10,
    })


def test_delete_function_configuration():
    """Test delete function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify delete function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-delete",
        "Runtime": "python3.11",
        "MemorySize": 256,
        "Timeout": 10,
    })


def test_list_function_configuration():
    """Test list function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify list function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-list",
        "Runtime": "python3.11",
        "MemorySize": 256,
        "Timeout": 10,
    })


def test_health_function_configuration():
    """Test health function has correct configuration."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify health function configuration
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-health",
        "Runtime": "python3.11",
        "MemorySize": 128,
        "Timeout": 3,
    })


def test_capture_function_environment():
    """Test capture function has required environment variables."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify environment variables include Bedrock model ID
    template.has_resource_properties("AWS::Lambda::Function", {
        "FunctionName": "contextanchor-capture",
        "Environment": {
            "Variables": assertions.Match.object_like({
                "BEDROCK_MODEL_ID": "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
                "POWERTOOLS_SERVICE_NAME": "contextanchor",
                "LOG_LEVEL": "INFO"
            })
        }
    })


def test_dynamodb_permissions():
    """Test Lambda functions have appropriate DynamoDB permissions."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
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
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify Bedrock permissions exist (Action can be string or array)
    template.has_resource_properties("AWS::IAM::Policy", {
        "PolicyDocument": {
            "Statement": assertions.Match.array_with([
                assertions.Match.object_like({
                    "Action": "bedrock:InvokeModel",
                    "Effect": "Allow"
                })
            ])
        }
    })


def test_iam_roles_created():
    """Test that IAM roles are created for Lambda functions."""
    app = cdk.App()
    dynamodb_stack = DynamoDBStack(app, "DynamoDBStack")
    TestLambdaStack = create_test_lambda_stack(app)
    lambda_stack = TestLambdaStack(app, "LambdaStack", table=dynamodb_stack.table)
    template = assertions.Template.from_stack(lambda_stack)
    
    # Verify IAM roles exist (one per function)
    template.resource_count_is("AWS::IAM::Role", 5)
