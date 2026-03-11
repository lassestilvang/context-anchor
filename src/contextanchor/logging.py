"""
Logging infrastructure for ContextAnchor.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

def setup_logging(db_path: Optional[Path] = None) -> None:
    """
    Configure global logging to file and console.
    
    Args:
        db_path: Base directory for logs. Defaults to ~/.contextanchor/
    """
    if db_path is None:
        log_dir = Path.home() / ".contextanchor" / "logs"
    else:
        log_dir = db_path / "logs"
        
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "contextanchor.log"
    
    root_logger = logging.getLogger("contextanchor")
    root_logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers if setup is called multiple times
    if not root_logger.handlers:
        # Rotating file handler: 10MB max, keep 5 backups
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Also add console handler for warnings/errors if needed
        # (CLI usually handles console output itself, so we keep this quiet)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance prefixed with 'contextanchor'."""
    if not name.startswith("contextanchor"):
        name = f"contextanchor.{name}"
    return logging.getLogger(name)
