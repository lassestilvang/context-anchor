"""
Unit tests for API Gateway stack.

Tests API Gateway configuration including:
- REST API creation
- Endpoint configuration
- API key authentication
- Method configuration
"""
import aws_cdk as cdk
from aws_cdk import assertions
from aws_cdk import aws_lambda as lambda_
from stacks.api_gateway_stack import ApiGatewayStack


def create_mock_lambda(scope, id: str) -> lambda_.Function:
    """Create a mock Lambda function for testing."""
    return lambda_.Function(
        scope, id,
        runtime=lambda_.Runtime.PYTHON_3_11,
        handler="index.handler",
        code=lambda_.Code.from_inline("def handler(event, context): pass")
    )


def test_rest_api_created():
    """Test that REST API is created."""
    app = cdk.App()
    
    # Create mock Lambda functions
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify REST API exists
    template.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_api_name():
    """Test that API has correct name."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify API name
    template.has_resource_properties("AWS::ApiGateway::RestApi", {
        "Name": "ContextAnchor API"
    })


def test_regional_endpoint():
    """Test that API uses regional endpoint."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify endpoint type
    template.has_resource_properties("AWS::ApiGateway::RestApi", {
        "EndpointConfiguration": {
            "Types": ["REGIONAL"]
        }
    })


def test_api_key_created():
    """Test that API key is created."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify API key exists
    template.resource_count_is("AWS::ApiGateway::ApiKey", 1)


def test_usage_plan_created():
    """Test that usage plan is created with rate limiting."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify usage plan exists
    template.resource_count_is("AWS::ApiGateway::UsagePlan", 1)
    
    # Verify throttle settings
    template.has_resource_properties("AWS::ApiGateway::UsagePlan", {
        "Throttle": {
            "RateLimit": 100,
            "BurstLimit": 200
        }
    })


def test_post_contexts_endpoint():
    """Test that POST /v1/contexts endpoint is configured."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify POST method exists with API key requirement
    template.has_resource_properties("AWS::ApiGateway::Method", {
        "HttpMethod": "POST",
        "ApiKeyRequired": True
    })


def test_get_contexts_latest_endpoint():
    """Test that GET /v1/contexts/latest endpoint is configured."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify GET methods exist
    template.has_resource_properties("AWS::ApiGateway::Method", {
        "HttpMethod": "GET",
        "ApiKeyRequired": True
    })


def test_delete_contexts_endpoint():
    """Test that DELETE /v1/contexts/{snapshot_id} endpoint is configured."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify DELETE method exists
    template.has_resource_properties("AWS::ApiGateway::Method", {
        "HttpMethod": "DELETE",
        "ApiKeyRequired": True
    })


def test_health_endpoint_no_auth():
    """Test that GET /v1/health endpoint does not require authentication."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify at least one GET method without API key requirement (health endpoint)
    template.has_resource_properties("AWS::ApiGateway::Method", {
        "HttpMethod": "GET",
        "ApiKeyRequired": False
    })


def test_deployment_stage():
    """Test that deployment stage is configured."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify deployment stage exists
    template.has_resource_properties("AWS::ApiGateway::Stage", {
        "StageName": "prod"
    })


def test_cors_configuration():
    """Test that CORS is configured."""
    app = cdk.App()
    lambda_stack = cdk.Stack(app, "LambdaStack")
    functions = {
        "capture": create_mock_lambda(lambda_stack, "Capture"),
        "retrieve": create_mock_lambda(lambda_stack, "Retrieve"),
        "delete": create_mock_lambda(lambda_stack, "Delete"),
        "list": create_mock_lambda(lambda_stack, "List"),
        "health": create_mock_lambda(lambda_stack, "Health"),
    }
    
    api_stack = ApiGatewayStack(app, "ApiStack", lambda_functions=functions)
    template = assertions.Template.from_stack(api_stack)
    
    # Verify OPTIONS methods exist for CORS
    template.has_resource_properties("AWS::ApiGateway::Method", {
        "HttpMethod": "OPTIONS"
    })
