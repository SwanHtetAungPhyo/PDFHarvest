"""
Logging setup utilities.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any


def setup_logging(cfg: Dict[str, Any], out_dir: Path) -> logging.Logger:
    """
    Set up logging with file rotation and console output.
    
    Parameters
    ----------
    cfg : dict
        Configuration dictionary containing logging settings
    out_dir : Path
        Output directory where log files will be stored
        
    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    log_cfg = cfg.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    
    # Create logs directory
    (out_dir / "logs").mkdir(parents=True, exist_ok=True)
    log_file = (out_dir / "logs" / log_cfg.get("file", "harvest.log")).resolve()
    
    # Set up rotating file handler
    handler = logging.handlers.RotatingFileHandler(
        log_file, 
        maxBytes=int(log_cfg.get("rotate_bytes", 10_485_760)),
        backupCount=int(log_cfg.get("backup_count", 5)), 
        encoding="utf-8"
    )
    
    # Set up console handler
    console_handler = logging.StreamHandler()
    
    # Configure formatting
    fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=level, 
        format=fmt, 
        handlers=[handler, console_handler],
        force=True
    )
    
    # Reduce httpx logging noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return logging.getLogger("harvest")