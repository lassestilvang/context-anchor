#!/usr/bin/env python3
"""
CDK application entry point for ContextAnchor infrastructure.
"""
import aws_cdk as cdk
from stacks.dynamodb_stack import DynamoDBStack
from stacks.lambda_stack import LambdaStack
from stacks.api_gateway_stack import ApiGatewayStack
from stacks.storage_stack import StorageStack
from stacks.budget_stack import BudgetStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "eu-north-1"
)

# Global environment for Budgets (must be us-east-1)
env_global = cdk.Environment(
    account=app.node.try_get_context("account"),
    region="us-east-1"
)

# DynamoDB Stack - Data layer
dynamodb_stack = DynamoDBStack(
    app,
    "ContextAnchorDynamoDBStack",
    env=env,
    description="DynamoDB tables for ContextAnchor context snapshots"
)

# Lambda Stack - Compute layer
lambda_stack = LambdaStack(
    app,
    "ContextAnchorLambdaStack",
    table=dynamodb_stack.table,
    env=env,
    description="Lambda functions for ContextAnchor API operations"
)

# API Gateway Stack - API layer
api_stack = ApiGatewayStack(
    app,
    "ContextAnchorApiGatewayStack",
    lambda_functions=lambda_stack.functions,
    env=env,
    description="API Gateway REST API for ContextAnchor"
)

# Storage Stack - Regional S3 and Monitoring
storage_stack = StorageStack(
    app,
    "ContextAnchorStorageStack",
    env=env,
    description="S3 storage and regional monitoring for ContextAnchor"
)

# Budget Stack - Global Cost Monitoring
budget_stack = BudgetStack(
    app,
    "ContextAnchorBudgetStack",
    env=env_global,
    description="Global cost guardrails for ContextAnchor"
)

# Add tags to all stacks
for stack in [dynamodb_stack, lambda_stack, api_stack, storage_stack, budget_stack]:
    cdk.Tags.of(stack).add("Project", "ContextAnchor")
    cdk.Tags.of(stack).add("ManagedBy", "CDK")

app.synth()
