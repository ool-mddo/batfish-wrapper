import logging


def set_pybf_loglevel(log_level):
    # set log level
    logger = logging.getLogger("pybatfish")
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
