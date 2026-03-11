"""
Context Store component for DynamoDB persistence.

This module provides the ContextStore class for storing and retrieving
context snapshots in DynamoDB with proper indexing and pagination support.

Requirements: 4.1, 4.2, 4.3, 12.6
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
import boto3
from boto3.dynamodb.conditions import Key
import json
import base64

from .models import ContextSnapshot


class ContextStore:
    """
    Persistent storage for context snapshots using DynamoDB.

    Provides methods for storing, retrieving, and listing context snapshots
    with support for multiple indexes and pagination.
    """

    def __init__(self, table_name: Optional[str] = None, dynamodb_resource: Any = None) -> None:
        """
        Initialize ContextStore with DynamoDB client.

        Args:
            table_name: DynamoDB table name (defaults to TABLE_NAME env var)
            dynamodb_resource: Optional boto3 DynamoDB resource for testing
        """
        self.table_name = table_name or os.environ.get("TABLE_NAME", "ContextSnapshots")

        if dynamodb_resource is None:
            self.dynamodb = boto3.resource("dynamodb")
        else:
            self.dynamodb = dynamodb_resource

        self.table = self.dynamodb.Table(self.table_name)

    def store_snapshot(self, snapshot: ContextSnapshot) -> str:
        """
        Persist a context snapshot to DynamoDB.

        Creates a new item with proper partition key (PK), sort key (SK),
        and GSI keys for efficient querying.

        Args:
            snapshot: ContextSnapshot object to store

        Returns:
            snapshot_id: The unique identifier of the stored snapshot

        Requirements: 4.1, 4.2, 4.3
        """
        # Convert captured_at to ISO format string
        captured_at_str = snapshot.captured_at.isoformat()
        timestamp = snapshot.captured_at.timestamp()

        # Calculate retention expiration (90 days from capture)
        retention_expires_at = int(timestamp + (90 * 24 * 60 * 60))

        # Build DynamoDB item with proper key structure
        item = {
            # Primary table keys
            "PK": f"REPO#{snapshot.repository_id}",
            "SK": f"BRANCH#{snapshot.branch}#TS#{captured_at_str}",
            # GSI: ByDeveloper
            "GSI1PK": f"DEV#{snapshot.developer_id}",
            "GSI1SK": f"TS#{captured_at_str}",
            # GSI: BySnapshotId
            "GSI2PK": f"SNAPSHOT#{snapshot.snapshot_id}",
            "GSI2SK": f"SNAPSHOT#{snapshot.snapshot_id}",
            # Snapshot attributes
            "snapshot_id": snapshot.snapshot_id,
            "repository_id": snapshot.repository_id,
            "branch": snapshot.branch,
            "developer_id": snapshot.developer_id,
            "captured_at": captured_at_str,
            "goals": snapshot.goals,
            "rationale": snapshot.rationale,
            "open_questions": snapshot.open_questions,
            "next_steps": snapshot.next_steps,
            "relevant_files": snapshot.relevant_files,
            "related_prs": snapshot.related_prs,
            "related_issues": snapshot.related_issues,
            # Deletion tracking
            "is_deleted": False,
            # TTL for automatic cleanup
            "retention_expires_at": retention_expires_at,
        }

        # Add deleted_at if present
        if snapshot.deleted_at is not None:
            item["deleted_at"] = snapshot.deleted_at.isoformat()
            item["is_deleted"] = True
            # Set purge deadline (7 days after deletion)
            purge_timestamp = snapshot.deleted_at.timestamp() + (7 * 24 * 60 * 60)
            item["purge_after_delete_at"] = int(purge_timestamp)

        # Store in DynamoDB
        self.table.put_item(Item=item)

        return snapshot.snapshot_id

    def get_snapshot_by_id(self, snapshot_id: str) -> Optional[ContextSnapshot]:
        """
        Retrieve a specific snapshot by its unique ID.

        Uses the BySnapshotId GSI for efficient lookup.

        Args:
            snapshot_id: Unique snapshot identifier

        Returns:
            ContextSnapshot object if found and not deleted, None otherwise

        Requirements: 4.1
        """
        response = self.table.query(
            IndexName="BySnapshotId",
            KeyConditionExpression=Key("GSI2PK").eq(f"SNAPSHOT#{snapshot_id}"),
            FilterExpression="attribute_not_exists(is_deleted) OR is_deleted = :false",
            ExpressionAttributeValues={":false": False},
        )

        items = response.get("Items", [])
        if not items:
            return None

        return self._item_to_snapshot(items[0])

    def get_latest_snapshot(
        self, repository_id: str, branch: str, developer_id: Optional[str] = None
    ) -> Optional[ContextSnapshot]:
        """
        Retrieve the most recent snapshot for a repository and branch.

        Queries using PK (repository) and SK prefix (branch), sorted by
        timestamp in descending order.

        Args:
            repository_id: Repository identifier
            branch: Git branch name

        Returns:
            Most recent ContextSnapshot for the branch, or None if not found

        Requirements: 4.2, 4.3
        """
        # Build filter expression
        filter_expr = "attribute_not_exists(is_deleted) OR is_deleted = :false"
        attr_values: dict[str, Any] = {":false": False}

        if developer_id:
            filter_expr = f"({filter_expr}) AND developer_id = :dev_id"
            attr_values[":dev_id"] = developer_id

        response = self.table.query(
            KeyConditionExpression=(
                Key("PK").eq(f"REPO#{repository_id}")
                & Key("SK").begins_with(f"BRANCH#{branch}#TS#")
            ),
            ScanIndexForward=False,  # Descending order (newest first)
            Limit=1,
            FilterExpression=filter_expr,
            ExpressionAttributeValues=attr_values,
        )
        items = response.get("Items", [])
        if not items:
            return None

        return self._item_to_snapshot(items[0])

    def list_snapshots(
        self,
        repository_id: str,
        branch: Optional[str] = None,
        developer_id: Optional[str] = None,
        limit: int = 20,
        next_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List snapshots for a repository with optional branch/developer filter and pagination.

        Args:
            repository_id: Repository identifier
            branch: Optional branch name filter
            developer_id: Optional developer ID filter
            limit: Maximum number of results (default 20, max 100)
            next_token: Pagination token from previous response

        Returns:
            Dictionary containing:
                - snapshots: List of ContextSnapshot objects
                - count: Number of snapshots in this page
                - next_token: Token for next page (if more results exist)

        Requirements: 4.2, 4.3, 12.6
        """
        # Limit to max 100 per page
        limit = min(limit, 100)

        # Build query parameters
        # Build filter expression
        filter_expr = "attribute_not_exists(is_deleted) OR is_deleted = :false"
        attr_values: dict[str, Any] = {":false": False}

        if developer_id:
            filter_expr = f"({filter_expr}) AND developer_id = :dev_id"
            attr_values[":dev_id"] = developer_id

        query_kwargs = {
            "ScanIndexForward": False,  # Descending order (newest first)
            "Limit": limit,
            "FilterExpression": filter_expr,
            "ExpressionAttributeValues": attr_values,
        }

        # Build key condition based on branch filter
        if branch:
            query_kwargs["KeyConditionExpression"] = Key("PK").eq(f"REPO#{repository_id}") & Key(
                "SK"
            ).begins_with(f"BRANCH#{branch}#TS#")
        else:
            query_kwargs["KeyConditionExpression"] = Key("PK").eq(f"REPO#{repository_id}")

        # Add pagination token if provided
        if next_token:
            try:
                decoded_token = json.loads(base64.b64decode(next_token))
                query_kwargs["ExclusiveStartKey"] = decoded_token
            except Exception:
                # Invalid token, ignore and start from beginning
                pass

        # Execute query
        response = self.table.query(**query_kwargs)

        # Convert items to ContextSnapshot objects
        snapshots = [self._item_to_snapshot(item) for item in response.get("Items", [])]

        # Build result
        result = {"snapshots": snapshots, "count": len(snapshots)}

        # Add pagination token if more results exist
        if "LastEvaluatedKey" in response:
            token = base64.b64encode(json.dumps(response["LastEvaluatedKey"]).encode()).decode()
            result["next_token"] = token

        return result

    def soft_delete_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        """
        Mark a snapshot as deleted and set purge deadline.

        Sets is_deleted=true and deleted_at timestamp. The snapshot is
        immediately excluded from active reads (get_snapshot_by_id,
        get_latest_snapshot, list_snapshots) but remains in storage
        for 7 days before permanent purge.

        Args:
            snapshot_id: Unique snapshot identifier

        Returns:
            Dictionary containing:
                - deleted: True if successful
                - purge_after: Timestamp when snapshot will be purged
                - snapshot_id: The deleted snapshot ID

        Requirements: 4.6, 9.4
        """
        # First, find the snapshot using the GSI
        response = self.table.query(
            IndexName="BySnapshotId",
            KeyConditionExpression=Key("GSI2PK").eq(f"SNAPSHOT#{snapshot_id}"),
        )

        items = response.get("Items", [])
        if not items:
            return {
                "deleted": False,
                "error": "Snapshot not found",
                "snapshot_id": snapshot_id,
            }

        item = items[0]

        # Calculate purge deadline (7 days from now)
        deleted_at = datetime.utcnow()
        purge_timestamp = deleted_at.timestamp() + (7 * 24 * 60 * 60)
        purge_after_delete_at = int(purge_timestamp)

        # Update the item to mark as deleted
        self.table.update_item(
            Key={"PK": item["PK"], "SK": item["SK"]},
            UpdateExpression="SET is_deleted = :true, deleted_at = :deleted_at, purge_after_delete_at = :purge_after",
            ExpressionAttributeValues={
                ":true": True,
                ":deleted_at": deleted_at.isoformat(),
                ":purge_after": purge_after_delete_at,
            },
        )

        return {
            "deleted": True,
            "purge_after": datetime.fromtimestamp(purge_timestamp).isoformat(),
            "snapshot_id": snapshot_id,
        }

    def purge_deleted_snapshots(self) -> int:
        """
        Permanently remove snapshots past their purge deadline.

        Scans for items where purge_after_delete_at < now and deletes them
        irreversibly. This should be run periodically (e.g., daily) to clean
        up soft-deleted snapshots.

        Returns:
            Number of snapshots permanently deleted

        Requirements: 4.6, 9.4
        """
        current_timestamp = int(datetime.utcnow().timestamp())
        purged_count = 0

        # Scan for items with purge_after_delete_at < now
        # Note: In production, this should use a GSI or be run as a batch job
        # For now, we'll scan the table (acceptable for MVP with small data volumes)
        scan_kwargs = {
            "FilterExpression": "attribute_exists(purge_after_delete_at) AND purge_after_delete_at < :now",
            "ExpressionAttributeValues": {":now": current_timestamp},
        }

        while True:
            response = self.table.scan(**scan_kwargs)

            # Delete each item
            for item in response.get("Items", []):
                self.table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})
                purged_count += 1

            # Check if there are more items to scan
            if "LastEvaluatedKey" not in response:
                break

            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

        return purged_count

    def _item_to_snapshot(self, item: Dict[str, Any]) -> ContextSnapshot:
        """
        Convert DynamoDB item to ContextSnapshot object.

        Args:
            item: DynamoDB item dictionary

        Returns:
            ContextSnapshot object
        """
        # Parse timestamps
        captured_at = datetime.fromisoformat(item["captured_at"])
        deleted_at = None
        if "deleted_at" in item:
            deleted_at = datetime.fromisoformat(item["deleted_at"])

        return ContextSnapshot(
            snapshot_id=item["snapshot_id"],
            repository_id=item["repository_id"],
            branch=item["branch"],
            developer_id=item["developer_id"],
            captured_at=captured_at,
            goals=item.get("goals", ""),
            rationale=item.get("rationale", ""),
            open_questions=item.get("open_questions", []),
            next_steps=item.get("next_steps", []),
            relevant_files=item.get("relevant_files", []),
            related_prs=item.get("related_prs", []),
            related_issues=item.get("related_issues", []),
            deleted_at=deleted_at,
        )
