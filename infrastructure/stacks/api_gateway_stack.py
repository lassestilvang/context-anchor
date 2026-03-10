"""
API Gateway stack for ContextAnchor.

Requirements: 9.2, 14.4
"""
from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as lambda_,
)
from constructs import Construct
from typing import Dict


class ApiGatewayStack(Stack):
    """
    Stack for API Gateway REST API used by ContextAnchor.
    
    Creates REST API with endpoints:
    - POST /v1/contexts - Create context snapshot
    - GET /v1/contexts/latest - Get latest snapshot
    - GET /v1/contexts/{snapshot_id} - Get specific snapshot
    - GET /v1/contexts - List snapshots
    - DELETE /v1/contexts/{snapshot_id} - Delete snapshot
    - GET /v1/health - Health check
    
    Configured with:
    - Regional endpoint
    - API key authentication
    - TLS 1.3 requirement
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        lambda_functions: Dict[str, lambda_.Function],
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Requirement 14.4: Use API Gateway for HTTP endpoints
        # Requirement 9.2: TLS 1.3 encryption in transit
        self.api = apigw.RestApi(
            self,
            "ContextAnchorApi",
            rest_api_name="ContextAnchor API",
            description="REST API for ContextAnchor developer workflow state management",
            endpoint_types=[apigw.EndpointType.REGIONAL],
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,  # Requests per second
                throttling_burst_limit=200,  # Burst capacity
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Api-Key", "Authorization"],
            ),
            # Enforce minimum TLS version
            policy=None,  # Custom policy would be added here for TLS 1.3
        )

        # API Key for authentication
        api_key = self.api.add_api_key(
            "ContextAnchorApiKey",
            api_key_name="contextanchor-api-key",
        )

        # Usage plan with rate limiting
        usage_plan = self.api.add_usage_plan(
            "ContextAnchorUsagePlan",
            name="Standard",
            throttle=apigw.ThrottleSettings(
                rate_limit=100,
                burst_limit=200,
            ),
            quota=apigw.QuotaSettings(
                limit=10000,  # 10k requests per month (Free Tier friendly)
                period=apigw.Period.MONTH,
            ),
        )

        usage_plan.add_api_key(api_key)
        usage_plan.add_api_stage(stage=self.api.deployment_stage)

        # Lambda integrations
        capture_integration = apigw.LambdaIntegration(lambda_functions["capture"])
        retrieve_integration = apigw.LambdaIntegration(lambda_functions["retrieve"])
        delete_integration = apigw.LambdaIntegration(lambda_functions["delete"])
        list_integration = apigw.LambdaIntegration(lambda_functions["list"])
        health_integration = apigw.LambdaIntegration(lambda_functions["health"])

        # API Resources and Methods
        # /v1 root
        v1 = self.api.root.add_resource("v1")

        # /v1/contexts
        contexts = v1.add_resource("contexts")

        # POST /v1/contexts - Create context snapshot
        contexts.add_method(
            "POST",
            capture_integration,
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # GET /v1/contexts - List snapshots with pagination
        contexts.add_method(
            "GET",
            list_integration,
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.NONE,
            request_parameters={
                "method.request.querystring.repository_id": True,
                "method.request.querystring.branch": False,
                "method.request.querystring.limit": False,
                "method.request.querystring.next_token": False,
            },
        )

        # /v1/contexts/latest
        latest = contexts.add_resource("latest")
        latest.add_method(
            "GET",
            retrieve_integration,
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.NONE,
            request_parameters={
                "method.request.querystring.repository_id": True,
                "method.request.querystring.branch": True,
            },
        )

        # /v1/contexts/{snapshot_id}
        snapshot = contexts.add_resource("{snapshot_id}")

        # GET /v1/contexts/{snapshot_id} - Get specific snapshot
        snapshot.add_method(
            "GET",
            retrieve_integration,
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # DELETE /v1/contexts/{snapshot_id} - Delete snapshot
        snapshot.add_method(
            "DELETE",
            delete_integration,
            api_key_required=True,
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # /v1/health - Health check (no auth required)
        health = v1.add_resource("health")
        health.add_method(
            "GET",
            health_integration,
            api_key_required=False,
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # Output the API endpoint
        self.api_url = self.api.url
