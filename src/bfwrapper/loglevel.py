import logging


def set_loglevel(logger_name: str, log_level: str) -> None:
    """Set log level of pybatfish
    Args:
        logger_name (str): Logger name
        log_level (str): Log level
    """
    logger = logging.getLogger(logger_name)
    if log_level == "critical":
        logger.setLevel(logging.CRITICAL)
    elif log_level == "error":
        logger.setLevel(logging.ERROR)
    elif log_level == "warning":
        logger.setLevel(logging.WARNING)
    elif log_level == "info":
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)
