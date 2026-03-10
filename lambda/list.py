"""
Lambda function for listing context snapshots.

Requirements: 4.5, 11.2, 12.1, 12.5, 12.6
"""
import json
import os
import boto3
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key


dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["TABLE_NAME"]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle context listing requests with pagination.
    
    Query parameters:
    - repository_id (required): Repository identifier
    - branch (optional): Filter by branch
    - limit (optional): Max results per page (default 20)
    - next_token (optional): Pagination token
    """
    try:
        query_params = event.get("queryStringParameters") or {}
        
        repository_id = query_params["repository_id"]
        branch = query_params.get("branch")
        limit = int(query_params.get("limit", "20"))
        next_token = query_params.get("next_token")
        
        # Limit to max 100 per page
        limit = min(limit, 100)
        
        result = list_snapshots(
            repository_id=repository_id,
            branch=branch,
            limit=limit,
            next_token=next_token
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(result)
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


def list_snapshots(
    repository_id: str,
    branch: str = None,
    limit: int = 20,
    next_token: str = None
) -> Dict[str, Any]:
    """
    List snapshots for a repository, optionally filtered by branch.
    """
    table = dynamodb.Table(TABLE_NAME)
    
    # Build query parameters
    query_kwargs = {
        "KeyConditionExpression": Key("PK").eq(f"REPO#{repository_id}"),
        "ScanIndexForward": False,  # Descending order (newest first)
        "Limit": limit,
        "FilterExpression": "attribute_not_exists(is_deleted) OR is_deleted = :false",
        "ExpressionAttributeValues": {":false": False}
    }
    
    # Add branch filter if specified
    if branch:
        query_kwargs["KeyConditionExpression"] = (
            Key("PK").eq(f"REPO#{repository_id}") &
            Key("SK").begins_with(f"BRANCH#{branch}#TS#")
        )
    
    # Add pagination token if provided
    if next_token:
        try:
            import base64
            decoded_token = json.loads(base64.b64decode(next_token))
            query_kwargs["ExclusiveStartKey"] = decoded_token
        except:
            pass  # Invalid token, ignore
    
    # Execute query
    response = table.query(**query_kwargs)
    
    # Format results
    snapshots = [format_snapshot_summary(item) for item in response.get("Items", [])]
    
    # Build response
    result = {
        "snapshots": snapshots,
        "count": len(snapshots)
    }
    
    # Add pagination token if more results exist
    if "LastEvaluatedKey" in response:
        import base64
        token = base64.b64encode(
            json.dumps(response["LastEvaluatedKey"]).encode()
        ).decode()
        result["next_token"] = token
    
    return result


def format_snapshot_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format DynamoDB item as snapshot summary.
    """
    # Truncate goals for summary
    goals = item.get("goals", "")
    if len(goals) > 100:
        goals = goals[:97] + "..."
    
    return {
        "snapshot_id": item["snapshot_id"],
        "repository_id": item["repository_id"],
        "branch": item["branch"],
        "captured_at": item["captured_at"],
        "goals": goals,
        "next_steps_count": len(item.get("next_steps", [])),
    }
