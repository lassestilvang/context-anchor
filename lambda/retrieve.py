"""
Lambda function for context retrieval.

Requirements: 4.5, 5.1, 5.2
"""
import json
import os
import boto3
from typing import Dict, Any, Optional
from boto3.dynamodb.conditions import Key


dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle context retrieval requests.
    
    Supports two modes:
    1. GET /v1/contexts/latest?repository_id=X&branch=Y - Get latest snapshot
    2. GET /v1/contexts/{snapshot_id} - Get specific snapshot
    """
    try:
        path = event.get("path", "")
        query_params = event.get("queryStringParameters") or {}
        path_params = event.get("pathParameters") or {}
        
        if "latest" in path:
            # Get latest snapshot for branch
            repository_id = query_params["repository_id"]
            branch = query_params["branch"]
            snapshot = get_latest_snapshot(repository_id, branch)
        else:
            # Get specific snapshot by ID
            snapshot_id = path_params["snapshot_id"]
            snapshot = get_snapshot_by_id(snapshot_id)
        
        if snapshot is None:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Snapshot not found"})
            }
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(snapshot)
        }
        
    except KeyError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required parameter: {str(e)}"})
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }


def get_latest_snapshot(repository_id: str, branch: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the most recent snapshot for a repository and branch.
    """
    table = dynamodb.Table(TABLE_NAME)
    
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"REPO#{repository_id}") &
                             Key("SK").begins_with(f"BRANCH#{branch}#TS#"),
        ScanIndexForward=False,  # Descending order (newest first)
        Limit=1,
        FilterExpression="attribute_not_exists(is_deleted) OR is_deleted = :false",
        ExpressionAttributeValues={":false": False}
    )
    
    items = response.get("Items", [])
    if not items:
        return None
    
    return format_snapshot(items[0])


def get_snapshot_by_id(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific snapshot by ID using GSI.
    """
    table = dynamodb.Table(TABLE_NAME)
    
    response = table.query(
        IndexName="BySnapshotId",
        KeyConditionExpression=Key("GSI2PK").eq(f"SNAPSHOT#{snapshot_id}"),
        FilterExpression="attribute_not_exists(is_deleted) OR is_deleted = :false",
        ExpressionAttributeValues={":false": False}
    )
    
    items = response.get("Items", [])
    if not items:
        return None
    
    return format_snapshot(items[0])


def format_snapshot(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format DynamoDB item as snapshot response.
    """
    return {
        "snapshot_id": item["snapshot_id"],
        "repository_id": item["repository_id"],
        "branch": item["branch"],
        "developer_id": item["developer_id"],
        "captured_at": item["captured_at"],
        "goals": item.get("goals", ""),
        "rationale": item.get("rationale", ""),
        "open_questions": item.get("open_questions", []),
        "next_steps": item.get("next_steps", []),
        "relevant_files": item.get("relevant_files", []),
        "related_prs": item.get("related_prs", []),
        "related_issues": item.get("related_issues", []),
    }
