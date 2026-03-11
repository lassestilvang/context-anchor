"""
AWS Lambda handlers for the ContextAnchor API endpoints.
"""

import json
import logging
from typing import Dict, Any

from .agent_core import AgentCore
from .context_store import ContextStore
from .models import CaptureSignals, FileChange, CommitInfo

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global instances for reuse
_agent_core = None
_context_store = None


def get_agent_core() -> AgentCore:
    global _agent_core
    if _agent_core is None:
        _agent_core = AgentCore()
    return _agent_core


def get_context_store() -> ContextStore:
    global _context_store
    if _context_store is None:
        _context_store = ContextStore()
    return _context_store


def _parse_signals(signals_data: Dict[str, Any]) -> CaptureSignals:
    """Helper to parse raw JSON into a CaptureSignals object."""
    uncommitted = []
    for f in signals_data.get("uncommitted_files", []):
        uncommitted.append(
            FileChange(
                path=f["path"],
                status=f["status"],
                lines_added=f.get("lines_added", 0),
                lines_deleted=f.get("lines_deleted", 0),
            )
        )

    commits = []
    # Simplified commit parsing for now
    for c in signals_data.get("recent_commits", []):
        from datetime import datetime

        commits.append(
            CommitInfo(
                hash=c.get("hash", ""),
                message=c.get("message", ""),
                timestamp=datetime.utcnow(),
                files_changed=c.get("files_changed", []),
            )
        )

    return CaptureSignals(
        repository_id=signals_data.get("repository_id", ""),
        branch=signals_data.get("branch", ""),
        uncommitted_files=uncommitted,
        recent_commits=commits,
        pr_references=signals_data.get("pr_references", []),
        issue_references=signals_data.get("issue_references", []),
        github_metadata=None,
        capture_source=signals_data.get("capture_source", "api"),
    )


def capture_context_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    POST /v1/contexts
    Captures a new context snapshot.
    """
    try:
        body = (
            json.loads(event.get("body", "{}"))
            if isinstance(event.get("body"), str)
            else event.get("body", {})
        )

        repository_id = body.get("repository_id")
        branch = body.get("branch")
        developer_id = body.get("developer_id", "unknown")
        intent = body.get("developer_intent")
        raw_signals = body.get("signals", {})

        if not repository_id or not branch or not intent:
            return _build_response(
                400, {"error": "Missing required fields: repository_id, branch, developer_intent"}
            )

        # Check if we are already in the async worker
        if not event.get("is_async_worker"):
            import boto3
            from datetime import datetime
            from .models import generate_snapshot_id

            snapshot_id = generate_snapshot_id()
            event["is_async_worker"] = True
            event["pre_generated_snapshot_id"] = snapshot_id

            # Use json to ensure the payload is serializable
            payload = json.dumps(event)

            try:
                # Need to run in background
                if hasattr(context, "function_name"):
                    lambda_client = boto3.client("lambda")
                    lambda_client.invoke(
                        FunctionName=context.function_name, InvocationType="Event", Payload=payload
                    )
                    return _build_response(
                        201,
                        {
                            "snapshot_id": snapshot_id,
                            "captured_at": datetime.utcnow().isoformat(),
                            "status": "processing",
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to invoke async lambda, falling back to sync: {e}")
                pass  # Fall back to sync
        else:
            snapshot_id = str(event.get("pre_generated_snapshot_id", ""))

        signals = _parse_signals(raw_signals)
        signals.repository_id = str(repository_id)
        signals.branch = str(branch)

        snapshot = get_agent_core().synthesize_context(
            repository_id=str(repository_id),
            branch=str(branch),
            developer_id=str(developer_id) if developer_id else "",
            intent=str(intent) if intent else "",
            signals=signals,
        )

        if event.get("is_async_worker") and event.get("pre_generated_snapshot_id"):
            snapshot.snapshot_id = str(event.get("pre_generated_snapshot_id"))

        final_snapshot_id = get_context_store().store_snapshot(snapshot)

        return _build_response(
            201, {"snapshot_id": final_snapshot_id, "captured_at": snapshot.captured_at.isoformat()}
        )
    except json.JSONDecodeError:
        return _build_response(400, {"error": "Invalid JSON body"})
    except ValueError as e:
        return _build_response(400, {"error": str(e)})
    except Exception as e:
        logger.error(f"Error capturing context: {str(e)}")
        return _build_response(500, {"error": "Internal Server Error"})


def get_latest_context_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    GET /v1/contexts/latest?repository_id=...&branch=...
    Retrieves the most recent snapshot for a repository/branch.
    """
    try:
        qsp = event.get("queryStringParameters") or {}
        repository_id = qsp.get("repository_id")
        branch = qsp.get("branch")
        developer_id = qsp.get("developer_id")

        if not repository_id or not branch:
            return _build_response(
                400, {"error": "Missing required query parameters: repository_id, branch"}
            )

        snapshot = get_context_store().get_latest_snapshot(
            repository_id, branch, developer_id=developer_id
        )
        if not snapshot:
            return _build_response(404, {"error": "Snapshot not found"})

        return _build_response(200, _snapshot_to_dict(snapshot))
    except Exception as e:
        logger.error(f"Error getting latest context: {str(e)}")
        return _build_response(500, {"error": "Internal Server Error"})


def get_context_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    GET /v1/contexts/{snapshot_id}
    Retrieves a specific snapshot by ID.
    """
    try:
        pp = event.get("pathParameters") or {}
        snapshot_id = pp.get("snapshot_id")

        if not snapshot_id:
            return _build_response(400, {"error": "Missing snapshot_id"})

        snapshot = get_context_store().get_snapshot_by_id(snapshot_id)
        if not snapshot:
            return _build_response(404, {"error": "Snapshot not found"})

        return _build_response(200, _snapshot_to_dict(snapshot))
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}")
        return _build_response(500, {"error": "Internal Server Error"})


def list_contexts_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    GET /v1/contexts?repository_id=...&branch=...&limit=...&next_token=...
    Lists snapshots with pagination.
    """
    try:
        qsp = event.get("queryStringParameters") or {}
        repository_id = qsp.get("repository_id")

        if not repository_id:
            return _build_response(
                400, {"error": "Missing required query parameter: repository_id"}
            )

        branch = qsp.get("branch")
        developer_id = qsp.get("developer_id")
        limit = int(qsp.get("limit", 20))
        next_token = qsp.get("next_token")

        result = get_context_store().list_snapshots(
            repository_id=repository_id,
            branch=branch,
            developer_id=developer_id,
            limit=limit,
            next_token=next_token,
        )

        return _build_response(
            200,
            {
                "snapshots": [_snapshot_to_dict(s) for s in result["snapshots"]],
                "count": result["count"],
                "next_token": result.get("next_token"),
            },
        )
    except ValueError:
        return _build_response(400, {"error": "Invalid limit parameter"})
    except Exception as e:
        logger.error(f"Error listing contexts: {str(e)}")
        return _build_response(500, {"error": "Internal Server Error"})


def delete_context_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    DELETE /v1/contexts/{snapshot_id}
    Soft-deletes a snapshot.
    """
    try:
        pp = event.get("pathParameters") or {}
        snapshot_id = pp.get("snapshot_id")

        if not snapshot_id:
            return _build_response(400, {"error": "Missing snapshot_id"})

        result = get_context_store().soft_delete_snapshot(snapshot_id)
        if not result["deleted"]:
            return _build_response(404, {"error": "Snapshot not found"})

        return _build_response(
            200,
            {"deleted": True, "snapshot_id": snapshot_id, "purge_after": result.get("purge_after")},
        )
    except Exception as e:
        logger.error(f"Error deleting context: {str(e)}")
        return _build_response(500, {"error": "Internal Server Error"})


def health_check_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    GET /health
    Basic health check of API and DynamoDB.
    """
    try:
        # Simple scan or describe to verify DynamoDB access
        get_context_store().table.table_status
        return _build_response(
            200, {"status": "healthy", "dynamodb": "connected", "version": "0.1.0"}
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return _build_response(503, {"status": "unhealthy", "error": "DynamoDB connection failed"})


def _build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps(body),
    }


def _snapshot_to_dict(snapshot: Any) -> Dict[str, Any]:
    """Serialize ContextSnapshot to dict."""
    d = {
        "snapshot_id": snapshot.snapshot_id,
        "repository_id": snapshot.repository_id,
        "branch": snapshot.branch,
        "developer_id": snapshot.developer_id,
        "captured_at": snapshot.captured_at.isoformat(),
        "goals": snapshot.goals,
        "rationale": snapshot.rationale,
        "open_questions": snapshot.open_questions,
        "next_steps": snapshot.next_steps,
        "relevant_files": snapshot.relevant_files,
        "related_prs": snapshot.related_prs,
        "related_issues": snapshot.related_issues,
    }
    if snapshot.deleted_at:
        d["deleted_at"] = snapshot.deleted_at.isoformat()
    return d
