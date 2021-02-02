"""
Tools for error handling and logging
Created on Jul 31, 2016

@author: winfriedw
"""

import logging
from microscope_automation.util.get_path import get_log_file_path


def setup_logger(prefs, log_level="DEBUG"):
    """Initialize logger. Will work over multiple modules

    see https://docs.python.org/2/howto/logging-cookbook.html#using-logging-in-multiple-modules"""  # noqa

    # create logger with 'microscope_automation'
    logger = logging.getLogger(__name__.split(".")[0])

    # if logger has any old handlers clean them up
    for handler in logger.handlers:
        handler.flush()
        handler.close()
        logger.removeHandler(handler)

    # create file handler which logs even debug messages
    log_file = get_log_file_path(prefs)
    fh = logging.FileHandler(log_file)

    logger.setLevel(logging.DEBUG)
    if log_level == "DEBUG":
        fh.setLevel(logging.DEBUG)
    if log_level == "INFO":
        fh.setLevel(logging.INFO)
    elif log_level == "WARNING":
        fh.setLevel(logging.WARNING)
    elif log_level == "ERROR":
        fh.setLevel(logging.ERROR)
    elif log_level == "CRITICAL":
        fh.setLevel(logging.CRITICAL)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
