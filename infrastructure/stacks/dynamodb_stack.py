"""
DynamoDB stack for ContextAnchor.

Requirements: 4.1, 4.2, 4.3, 4.4, 9.1, 14.1
"""
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class DynamoDBStack(Stack):
    """
    Stack for DynamoDB tables used by ContextAnchor.
    
    Creates the ContextSnapshots table with:
    - Primary key: PK (REPO#id), SK (BRANCH#branch#TS#timestamp)
    - GSI ByDeveloper: PK (DEV#id), SK (TS#timestamp)
    - GSI BySnapshotId: PK (SNAPSHOT#id), SK (SNAPSHOT#id)
    - On-demand billing mode
    - AES-256 encryption at rest
    - TTL on retention_expires_at field
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ContextSnapshots table
        # Requirement 4.1: Persist snapshots with unique identifier
        # Requirement 4.2: Index by repository and branch
        # Requirement 4.3: Index by timestamp
        # Requirement 4.4: 90-day retention with TTL
        # Requirement 9.1: AES-256 encryption at rest
        # Requirement 14.1: Use DynamoDB for persistent storage
        self.table = dynamodb.Table(
            self,
            "ContextSnapshotsTable",
            table_name="ContextSnapshots",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # On-demand for cost efficiency
            encryption=dynamodb.TableEncryption.AWS_MANAGED,  # AES-256 encryption
            point_in_time_recovery=False,  # Disabled to stay within Free Tier
            removal_policy=RemovalPolicy.RETAIN,  # Protect data on stack deletion
            time_to_live_attribute="retention_expires_at",  # TTL for 90-day retention
        )

        # GSI: ByDeveloper
        # Allows querying all snapshots for a specific developer
        # PK: DEV#{developer_id}, SK: TS#{timestamp}
        self.table.add_global_secondary_index(
            index_name="ByDeveloper",
            partition_key=dynamodb.Attribute(
                name="GSI1PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI1SK",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # GSI: BySnapshotId
        # Allows direct lookup by snapshot_id
        # PK: SNAPSHOT#{snapshot_id}, SK: SNAPSHOT#{snapshot_id}
        self.table.add_global_secondary_index(
            index_name="BySnapshotId",
            partition_key=dynamodb.Attribute(
                name="GSI2PK",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="GSI2SK",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )
