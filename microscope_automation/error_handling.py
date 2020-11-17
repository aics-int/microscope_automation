"""
Tools for error handling and logging
Created on Jul 31, 2016

@author: winfriedw
"""

import logging
from .get_path import get_log_file_path

logLevel = "DEBUG"


def setup_logger(prefs, logLevel=logLevel):
    """Initialize logger. Will work over multiple modules

    see https://docs.python.org/2/howto/logging-cookbook.html#using-logging-in-multiple-modules"""  # noqa

    # create logger with 'MicroscopeAutomation'
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    log_file = get_log_file_path(prefs)
    fh = logging.FileHandler(log_file)
    if logLevel == "DEBUG":
        fh.setLevel(logging.DEBUG)
    elif logLevel == "INFO":
        fh.setLevel(logging.INFO)
    elif logLevel == "WARNING":
        fh.setLevel(logging.WARNING)
    elif logLevel == "ERROR":
        fh.setLevel(logging.ERROR)
    elif logLevel == "CRITICAL":
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
