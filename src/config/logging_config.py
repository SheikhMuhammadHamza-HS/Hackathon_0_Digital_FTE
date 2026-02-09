import logging
import sys

def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger with a stream handler.

    Args:
        level: Logging level name (e.g., "INFO", "DEBUG").
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(stream=sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

def get_logger(name: str = "__main__") -> logging.Logger:
    """Return a logger for the given module name, configuring logging if necessary."""
    if not logging.getLogger().handlers:
        configure_logging()
    return logging.getLogger(name)

def setup_logging(level: str = "INFO") -> None:
    """Compatibility wrapper for configure_logging used elsewhere."""
    configure_logging(level)
