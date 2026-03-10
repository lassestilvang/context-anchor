"""
Lambda function for context capture with Bedrock AI synthesis.

Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 14.2, 14.3
"""
import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any


dynamodb = boto3.resource("dynamodb")
bedrock = boto3.client("bedrock-runtime")

TABLE_NAME = os.environ["TABLE_NAME"]
BEDROCK_MODEL_ID = os.environ["BEDROCK_MODEL_ID"]


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle context capture requests.
    
    Expected input:
    {
        "repository_id": "string",
        "branch": "string",
        "developer_id": "string",
        "developer_intent": "string",
        "signals": {
            "uncommitted_files": [...],
            "recent_commits": [...],
            "pr_references": [...],
            "issue_references": [...]
        }
    }
    """
    try:
        body = json.loads(event.get("body", "{}"))
        
        # Extract request data
        repository_id = body["repository_id"]
        branch = body["branch"]
        developer_id = body["developer_id"]
        developer_intent = body["developer_intent"]
        signals = body.get("signals", {})
        
        # Generate snapshot using Bedrock
        snapshot = synthesize_context(
            developer_intent=developer_intent,
            signals=signals,
            branch=branch
        )
        
        # Store in DynamoDB
        snapshot_id = store_snapshot(
            repository_id=repository_id,
            branch=branch,
            developer_id=developer_id,
            snapshot=snapshot
        )
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "snapshot_id": snapshot_id,
                "captured_at": snapshot["captured_at"]
            })
        }
        
    except KeyError as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required field: {str(e)}"})
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }


def synthesize_context(developer_intent: str, signals: Dict[str, Any], branch: str) -> Dict[str, Any]:
    """
    Use Bedrock to synthesize context snapshot from signals and intent.
    """
    # Build prompt for Bedrock
    prompt = build_bedrock_prompt(developer_intent, signals, branch)
    
    # Call Bedrock API
    response = bedrock.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
    )
    
    # Parse response
    response_body = json.loads(response["body"].read())
    content = response_body["content"][0]["text"]
    
    # Parse structured output
    snapshot = parse_bedrock_response(content)
    snapshot["captured_at"] = datetime.utcnow().isoformat()
    
    return snapshot


def build_bedrock_prompt(intent: str, signals: Dict[str, Any], branch: str) -> str:
    """
    Build prompt for Bedrock API.
    """
    uncommitted = signals.get("uncommitted_files", [])
    commits = signals.get("recent_commits", [])
    prs = signals.get("pr_references", [])
    issues = signals.get("issue_references", [])
    
    return f"""You are a developer workflow assistant. Analyze the following signals and developer intent to create a structured context snapshot.

DEVELOPER INTENT:
{intent}

GIT SIGNALS:
- Current Branch: {branch}
- Uncommitted Changes: {len(uncommitted)} files
- Recent Commits: {len(commits)} commits
- PR References: {prs}
- Issue References: {issues}

Generate a context snapshot with these sections (use JSON format):

{{
  "goals": "What is the developer trying to accomplish? (1-3 sentences)",
  "rationale": "Why is this work important? What problem does it solve? (2-4 sentences)",
  "open_questions": ["Question 1", "Question 2", ...],  // 2-5 items
  "next_steps": ["Action 1", "Action 2", ...],  // 1-5 items, each starting with a verb
  "relevant_files": ["file1.py", "file2.js", ...]
}}

Keep the total response under 500 words. Be specific and actionable. Each next step must start with an action verb (Add, Update, Fix, Remove, Refactor, Test, Document, Implement, Create, Verify, Investigate, Optimize, Migrate, Review, Ship)."""


def parse_bedrock_response(content: str) -> Dict[str, Any]:
    """
    Parse Bedrock response into structured snapshot.
    """
    # Extract JSON from response
    try:
        # Try to find JSON in the response
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            json_str = content[start:end]
            return json.loads(json_str)
    except:
        pass
    
    # Fallback: return minimal structure
    return {
        "goals": "Context capture in progress",
        "rationale": "Processing developer intent",
        "open_questions": ["Awaiting AI synthesis"],
        "next_steps": ["Review generated context"],
        "relevant_files": []
    }


def store_snapshot(
    repository_id: str,
    branch: str,
    developer_id: str,
    snapshot: Dict[str, Any]
) -> str:
    """
    Store snapshot in DynamoDB.
    """
    import uuid
    
    snapshot_id = str(uuid.uuid4())
    captured_at = snapshot["captured_at"]
    timestamp = datetime.fromisoformat(captured_at).timestamp()
    
    # Calculate retention expiration (90 days)
    retention_expires_at = int(timestamp + (90 * 24 * 60 * 60))
    
    table = dynamodb.Table(TABLE_NAME)
    
    item = {
        "PK": f"REPO#{repository_id}",
        "SK": f"BRANCH#{branch}#TS#{captured_at}",
        "GSI1PK": f"DEV#{developer_id}",
        "GSI1SK": f"TS#{captured_at}",
        "GSI2PK": f"SNAPSHOT#{snapshot_id}",
        "GSI2SK": f"SNAPSHOT#{snapshot_id}",
        "snapshot_id": snapshot_id,
        "repository_id": repository_id,
        "branch": branch,
        "developer_id": developer_id,
        "captured_at": captured_at,
        "goals": snapshot.get("goals", ""),
        "rationale": snapshot.get("rationale", ""),
        "open_questions": snapshot.get("open_questions", []),
        "next_steps": snapshot.get("next_steps", []),
        "relevant_files": snapshot.get("relevant_files", []),
        "related_prs": snapshot.get("related_prs", []),
        "related_issues": snapshot.get("related_issues", []),
        "is_deleted": False,
        "retention_expires_at": retention_expires_at,
    }
    
    table.put_item(Item=item)
    
    return snapshot_id
