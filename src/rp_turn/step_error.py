"""Exception for if a step fails"""

import logging

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class StepError(Exception):
    """Raised when the user has input something invalid"""

    def __init__(self, msg: str):
        Exception.__init__(self, msg)
        DEV_LOGGER.info("StepError: %s", msg)
