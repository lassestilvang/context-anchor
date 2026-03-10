"""
Lambda function for context deletion.

Requirements: 4.6, 9.4
"""
import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any
from boto3.dynamodb.conditions import Key


dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle context deletion requests.
    
    Performs soft-delete: marks snapshot as deleted and sets purge deadline.
    Snapshot is immediately hidden from reads but retained for 7 days.
    """
    try:
        path_params = event.get("pathParameters") or {}
        snapshot_id = path_params["snapshot_id"]
        
        result = soft_delete_snapshot(snapshot_id)
        
        if not result["success"]:
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
            "body": json.dumps({
                "deleted": True,
                "snapshot_id": snapshot_id,
                "deleted_at": result["deleted_at"],
                "purge_after": result["purge_after"]
            })
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


def soft_delete_snapshot(snapshot_id: str) -> Dict[str, Any]:
    """
    Mark snapshot as deleted and set purge deadline (7 days).
    """
    table = dynamodb.Table(TABLE_NAME)
    
    # First, find the snapshot using GSI
    response = table.query(
        IndexName="BySnapshotId",
        KeyConditionExpression=Key("GSI2PK").eq(f"SNAPSHOT#{snapshot_id}")
    )
    
    items = response.get("Items", [])
    if not items:
        return {"success": False}
    
    item = items[0]
    pk = item["PK"]
    sk = item["SK"]
    
    # Mark as deleted
    deleted_at = datetime.utcnow().isoformat()
    purge_after_timestamp = int(datetime.utcnow().timestamp() + (7 * 24 * 60 * 60))
    
    table.update_item(
        Key={"PK": pk, "SK": sk},
        UpdateExpression="SET is_deleted = :true, deleted_at = :deleted_at, purge_after_delete_at = :purge_after",
        ExpressionAttributeValues={
            ":true": True,
            ":deleted_at": deleted_at,
            ":purge_after": purge_after_timestamp
        }
    )
    
    return {
        "success": True,
        "deleted_at": deleted_at,
        "purge_after": purge_after_timestamp
    }
