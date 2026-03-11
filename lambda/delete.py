"""
Lambda entry point for context deletion.
Standardized to use contextanchor.handlers.
"""
from contextanchor.handlers import delete_context_handler

def handler(event, context):
    return delete_context_handler(event, context)
