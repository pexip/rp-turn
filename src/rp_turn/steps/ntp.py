"""
Pexip installation wizard step to setup ntp servers
"""

import logging

from rp_turn import utils
from rp_turn.steps.base_step import MultiStep, StepError

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class NTPStep(MultiStep):
    """Step to get NTP servers"""

    def __init__(self):
        MultiStep.__init__(self, "NTP Servers", "ntp")

    def validate(self, response):
        DEV_LOGGER.info("Response: %s", response)
        try:
            return utils.validate_domain(response)
        except StepError:
            DEV_LOGGER.info("%s is not a domain", response)
        try:
            return utils.validate_ip(response)
        except StepError:
            DEV_LOGGER.info("%s is not an ip address", response)
        raise StepError("Was not an ip address or domain name")

    def default_config(self, saved_config, config):
        DEV_LOGGER.info("Getting from saved_config: ntp")
        fallback = [
            "0.pexip.pool.ntp.org",
            "1.pexip.pool.ntp.org",
            "2.pexip.pool.ntp.org",
        ]
        config["ntp"] = utils.validated_config_value(
            saved_config, "ntp", self.validate, value_list=True, fallback=fallback
        )
