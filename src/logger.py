"""
Logging Configuration Module

Provides centralized logging setup with configurable output to console and file.
Uses the standard library logging module with custom formatting.

Usage:
    from src.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Processing document", extra={"doc_id": "123"})
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log output for better readability.
    
    Colors:
    - DEBUG: Cyan
    - INFO: Green
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Bold Red
    """
    
    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[1;31m" # Bold Red
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with colors for terminal output."""
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    use_colors: bool = True
) -> None:
    """
    Configure the root logger with console and optional file handlers.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        use_colors: Whether to use colored output in console
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if use_colors and sys.stdout.isatty():
        console_format = ColoredFormatter(
            "%(asctime)s │ %(levelname)s │ %(name)s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    else:
        console_format = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_format = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Usually __name__ of the calling module
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Starting process")
    """
    return logging.getLogger(name)


# Initialize logging on module import (lazy initialization)
_initialized = False


def init_logging() -> None:
    """
    Initialize logging from settings. Call once at application startup.
    """
    global _initialized
    if _initialized:
        return
    
    try:
        from src.config import settings
        setup_logging(
            level=settings.logging.level,
            log_file=settings.logging.file
        )
    except Exception:
        # Fallback if settings aren't available
        setup_logging(level="INFO")
    
    _initialized = True
