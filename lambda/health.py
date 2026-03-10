"""
Lambda function for health check endpoint.
"""
import json
from datetime import datetime
from typing import Dict, Any


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Simple health check endpoint.
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "healthy",
            "service": "contextanchor",
            "timestamp": datetime.utcnow().isoformat()
        })
    }
