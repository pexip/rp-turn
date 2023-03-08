# pylint: disable=consider-using-from-import
"""
Pexip installation wizard step to setup fail2ban
"""

import logging
from functools import partial

import si.apps.reverseproxy.utils as utils
from si.apps.reverseproxy.steps.base_step import Step

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class Fail2BanStep(Step):
    """Step to decide whether to enable fail2ban"""

    def __init__(self):
        Step.__init__(self, "Fail2ban")
        self.questions = [self._enable_fail2ban]

    def _enable_fail2ban(self, config):
        """Question to find out whether to enable fail2ban"""
        default_enabled = utils.config_get(config["enablefail2ban"])
        default_enabled = "Yes" if default_enabled else "No"
        response = self.ask_yes_no(
            """\
Fail2ban bans IP addresses that show signs of malicious behavior.

Enable Fail2ban?""",
            default=default_enabled,
        )
        config["enablefail2ban"] = response

    def default_config(self, saved_config, config):
        DEV_LOGGER.info("Getting from saved_config: enablefail2ban")
        config["enablefail2ban"] = utils.validated_config_value(
            saved_config,
            "enablefail2ban",
            partial(utils.validate_type, bool),
            fallback=False,
        )
