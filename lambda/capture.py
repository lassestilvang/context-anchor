"""
Lambda entry point for context capture.
Standardized to use contextanchor.handlers.
"""
from contextanchor.handlers import capture_context_handler

def handler(event, context):
    return capture_context_handler(event, context)
