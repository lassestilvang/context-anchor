"""
Lambda entry point for context listing.
Standardized to use contextanchor.handlers.
"""
from contextanchor.handlers import list_contexts_handler

def handler(event, context):
    return list_contexts_handler(event, context)
