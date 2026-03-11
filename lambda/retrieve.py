"""
Lambda entry point for context retrieval.
Standardized to use contextanchor.handlers.
"""
from contextanchor.handlers import get_latest_context_handler, get_context_handler

def handler(event, context):
    path = event.get("path", "")
    if "latest" in path:
        return get_latest_context_handler(event, context)
    else:
        return get_context_handler(event, context)
