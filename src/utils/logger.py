"""
Logger Configuration - Marcel Location Simulator
Sets up beautiful loguru-based console and file-based structured logs.
Created by Marcel Afsar
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_level: str = "INFO"):
    """
    Configure loguru logger
    
    Args:
        log_level: Severity level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        logger: Initialized loguru instance
    """
    # Remove default handler
    logger.remove()
    
    # Console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # File handler
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_dir / "app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8"
    )
    
    logger.info("Logger successfully initialized")
    return logger