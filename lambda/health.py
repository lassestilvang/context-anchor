"""
Lambda entry point for health check.
Standardized to use contextanchor.handlers.
"""
from contextanchor.handlers import health_check_handler

def handler(event, context):
    return health_check_handler(event, context)
