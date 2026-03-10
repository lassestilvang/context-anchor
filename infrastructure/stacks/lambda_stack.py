"""
Lambda stack for ContextAnchor.

Requirements: 14.3
"""
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class LambdaStack(Stack):
    """
    Stack for Lambda functions used by ContextAnchor.
    
    Creates Lambda functions for:
    - Context capture (with Bedrock integration)
    - Context retrieval
    - Context deletion
    - Context listing
    
    All functions use Python 3.11 runtime with least-privilege IAM roles.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        table: dynamodb.Table,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.table = table
        self.functions = {}

        # Common Lambda configuration
        common_env = {
            "TABLE_NAME": table.table_name,
            "POWERTOOLS_SERVICE_NAME": "contextanchor",
            "LOG_LEVEL": "INFO",
        }

        # Context Capture Lambda
        # Requirement 14.3: Use Lambda for serverless compute
        # Handles context capture with Bedrock AI synthesis
        self.functions["capture"] = lambda_.Function(
            self,
            "ContextCaptureFunction",
            function_name="contextanchor-capture",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="capture.handler",
            code=lambda_.Code.from_asset("lambda"),
            memory_size=512,  # 512MB for Bedrock API calls
            timeout=Duration.seconds(30),  # 30s for AI synthesis
            environment={
                **common_env,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0",
            },
        )

        # Grant DynamoDB write permissions
        table.grant_write_data(self.functions["capture"])

        # Grant Bedrock invoke permissions
        self.functions["capture"].add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{self.region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
                ],
            )
        )

        # Context Retrieval Lambda
        # Handles fetching latest or specific snapshots
        self.functions["retrieve"] = lambda_.Function(
            self,
            "ContextRetrieveFunction",
            function_name="contextanchor-retrieve",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="retrieve.handler",
            code=lambda_.Code.from_asset("lambda"),
            memory_size=256,
            timeout=Duration.seconds(10),
            environment=common_env,
        )

        # Grant DynamoDB read permissions
        table.grant_read_data(self.functions["retrieve"])

        # Context Deletion Lambda
        # Handles soft-delete and purge operations
        self.functions["delete"] = lambda_.Function(
            self,
            "ContextDeleteFunction",
            function_name="contextanchor-delete",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="delete.handler",
            code=lambda_.Code.from_asset("lambda"),
            memory_size=256,
            timeout=Duration.seconds(10),
            environment=common_env,
        )

        # Grant DynamoDB write permissions for soft-delete
        table.grant_write_data(self.functions["delete"])

        # Context Listing Lambda
        # Handles listing snapshots with pagination
        self.functions["list"] = lambda_.Function(
            self,
            "ContextListFunction",
            function_name="contextanchor-list",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="list.handler",
            code=lambda_.Code.from_asset("lambda"),
            memory_size=256,
            timeout=Duration.seconds(10),
            environment=common_env,
        )

        # Grant DynamoDB read permissions
        table.grant_read_data(self.functions["list"])

        # Health Check Lambda
        # Simple health check endpoint
        self.functions["health"] = lambda_.Function(
            self,
            "HealthCheckFunction",
            function_name="contextanchor-health",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="health.handler",
            code=lambda_.Code.from_asset("lambda"),
            memory_size=128,
            timeout=Duration.seconds(3),
            environment={"SERVICE_NAME": "contextanchor"},
        )
