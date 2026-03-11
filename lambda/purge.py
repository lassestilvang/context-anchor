"""
Lambda entry point for periodic snapshot purging.
Triggered by EventBridge (CloudWatch Events).
"""
from contextanchor.handlers import purge_snapshots_handler

def handler(event, context):
    return purge_snapshots_handler(event, context)
