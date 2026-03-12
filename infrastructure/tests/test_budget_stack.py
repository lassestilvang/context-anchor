"""
Unit tests for Budget stack.

Tests AWS Budgets and cost notification configuration.
"""
import aws_cdk as cdk
from aws_cdk import assertions
from stacks.budget_stack import BudgetStack


def test_budget_created():
    """Test that AWS Budget is created."""
    app = cdk.App()
    stack = BudgetStack(app, "TestBudgetStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify budget exists
    template.resource_count_is("AWS::Budgets::Budget", 1)


def test_budget_configuration():
    """Test that budget has correct configuration."""
    app = cdk.App()
    stack = BudgetStack(app, "TestBudgetStack")
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


def test_sns_topic_created():
    """Test that SNS topic for alerts is created."""
    app = cdk.App()
    stack = BudgetStack(app, "TestBudgetStack")
    template = assertions.Template.from_stack(stack)
    
    # Verify SNS topic exists
    template.resource_count_is("AWS::SNS::Topic", 1)
    template.has_resource_properties("AWS::SNS::Topic", {
        "TopicName": "contextanchor-budget-alerts"
    })


def test_budget_notifications():
    """Test that budget has notifications configured."""
    app = cdk.App()
    stack = BudgetStack(app, "TestBudgetStack")
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
