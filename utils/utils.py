import logging
import os
from pathlib import Path


def get_model_string(model_name: str) -> str:
    if model_name == "gpt-oss-120b":
        return f"openai/{model_name}"
    else:
        return model_name


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens in *text* using tiktoken; returns 0 on any failure."""
    try:
        import tiktoken
        return len(tiktoken.get_encoding(encoding_name).encode(text))
    except Exception as e:
        logging.getLogger(__name__).warning("Could not count tokens: %s", e)
        return 0

_DETAILED_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d:%(funcName)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
_CONSOLE_FORMAT = logging.Formatter('%(levelname)s - [%(filename)s:%(funcName)s] - %(message)s')

_ROOT_CONFIGURED = False


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _configure_root_logging(numeric_level: int, log_file_path: str, log_to_console: bool) -> None:
    """Attach handlers to the ROOT logger exactly once.

    Module loggers created by ``setup_logger`` carry no handlers of their own and
    propagate here, so the log file is opened once for the whole process instead
    of once per module (the previous behaviour attached a FileHandler to each of
    the ~12 module loggers, all writing to the same file).
    """
    global _ROOT_CONFIGURED
    root = logging.getLogger()
    root.setLevel(numeric_level)

    if not _ROOT_CONFIGURED:
        if log_file_path:
            log_path = Path(log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_handler.setFormatter(_DETAILED_FORMAT)
            root.addHandler(file_handler)
        _ROOT_CONFIGURED = True

    # Console handler can be requested on any call; add it once if missing.
    if log_to_console and not any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
        for h in root.handlers
    ):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(_CONSOLE_FORMAT)
        root.addHandler(console_handler)


def setup_logger(name: str = None, log_level: str = None, log_file: str = None,
                 log_to_console: bool = None) -> logging.Logger:
    """
    Return a module logger, configuring shared handlers on the root logger.

    Handlers live on the root logger (configured once per process); the returned
    module logger only carries its name and level and propagates records upward.

    Args:
        name: Logger name (typically ``__name__``).
        log_level: Level string (DEBUG/INFO/WARNING/ERROR/CRITICAL). Falls back to
            env ``HAL_AGENT_LOG_LEVEL`` then ``config.LOG_LEVEL``.
        log_file: Log file path. Falls back to ``config.LOG_FILE``; empty disables.
        log_to_console: Whether to also log to the console. ``None`` falls back to
            env ``HAL_AGENT_LOG_TO_CONSOLE`` then ``config.LOG_TO_CONSOLE``
            (default True), so errors surface during interactive/Docker runs.
    """
    import config

    level = log_level or os.environ.get("HAL_AGENT_LOG_LEVEL") or config.LOG_LEVEL
    log_file_path = log_file if log_file is not None else config.LOG_FILE
    if log_to_console is None:
        log_to_console = _env_bool(
            "HAL_AGENT_LOG_TO_CONSOLE",
            getattr(config, "LOG_TO_CONSOLE", True),
        )

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    _configure_root_logging(numeric_level, log_file_path, log_to_console)

    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    return logger
