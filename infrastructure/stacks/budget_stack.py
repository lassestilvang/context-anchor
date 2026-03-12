"""
Global Budget Stack for ContextAnchor.
AWS Budgets are a global service that is best managed via us-east-1.
"""
from aws_cdk import (
    Stack,
    aws_budgets as budgets,
    aws_sns as sns,
)
from constructs import Construct


class BudgetStack(Stack):
    """
    Stack for AWS Budgets and cost notifications.
    Deploys to us-east-1 as it manages global/account-wide budget resources.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SNS Topic for budget alerts
        self.alert_topic = sns.Topic(
            self,
            "BudgetAlertTopic",
            topic_name="contextanchor-budget-alerts",
            display_name="ContextAnchor Budget Alerts",
        )

        # Requirement 14.6: Cost guardrails with Free Tier thresholds
        # AWS Budget for monthly spend monitoring ($5/month threshold)
        budgets.CfnBudget(
            self,
            "MonthlyBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_type="COST",
                time_unit="MONTHLY",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=5.0,
                    unit="USD",
                ),
                budget_name="ContextAnchor-Monthly-Budget",
                cost_filters={
                    "TagKeyValue": ["Project$ContextAnchor"],
                },
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="ACTUAL",
                        comparison_operator="GREATER_THAN",
                        threshold=80,  # Alert at 80% of budget
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=self.alert_topic.topic_arn,
                        )
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        notification_type="FORECASTED",
                        comparison_operator="GREATER_THAN",
                        threshold=100,  # Alert if forecasted to exceed budget
                        threshold_type="PERCENTAGE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            subscription_type="SNS",
                            address=self.alert_topic.topic_arn,
                        )
                    ],
                ),
            ],
        )
