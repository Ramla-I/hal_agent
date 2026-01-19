import logging
import os
from pathlib import Path


def get_model_string(model_name: str) -> str:
    if model_name == "gpt-oss-120b":
        return f"openai/{model_name}"
    else:
        return model_name

def setup_logger(name: str = None, log_level: str = None, log_file: str = None, log_to_console: bool = False) -> logging.Logger:
    """
    Set up and configure a logger with both file and console handlers.
    
    Args:
        name: Logger name (default: root logger)
        log_level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  If None, uses LOG_LEVEL from config
        log_file: Path to log file. If None, uses LOG_FILE from config.
                 If empty string, only logs to console.
    
    Returns:
        Configured logger instance
    """
    import config
    
    # Get configuration
    level = log_level if log_level is not None else config.LOG_LEVEL
    log_file_path = log_file if log_file is not None else config.LOG_FILE
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d:%(funcName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - [%(filename)s:%(funcName)s] - %(message)s'
    )
    
    # Console handler (if log_to_console is True)
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler (if log_file_path is provided and not empty)
    if log_file_path:
        # Create directory if it doesn't exist
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger
