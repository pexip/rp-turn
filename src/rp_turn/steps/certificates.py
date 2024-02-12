"""
Pexip installation wizard step to generate certificates
"""

import logging
from collections import defaultdict
from functools import partial

from rp_turn import utils
from rp_turn.steps.base_step import Step

DEV_LOGGER = logging.getLogger("rp_turn.installwizard")


class CertificatesStep(Step):
    """Generate New Certificates Step"""

    def __init__(self) -> None:
        super().__init__("Certificates")
        self.questions = [self._generate_ssl, self._generate_ssh]

    def _generate_ssl(self, config: defaultdict) -> None:
        """Question asking whether to regenerate ssl certificates"""
        response = self.ask_yes_no(
            "An existing SSL certificate exists.\n"
            + "Do you want to regenerate a new SSL certificate?",
            default=True,
        )
        DEV_LOGGER.info("Response: %s", response)
        config["generate-certs"]["ssl"] = response

    def _generate_ssh(self, config: defaultdict) -> None:
        """Question asking whether to regenerate ssh certificates"""
        response = self.ask_yes_no(
            "An existing SSH certificate exists.\n"
            + "Do you want to regenerate a new SSH certificate?",
            default=True,
        )
        DEV_LOGGER.info("Response: %s", response)
        config["generate-certs"]["ssh"] = response

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        saved_certs = saved_config["generate-certs"]
        config_certs = config["generate-certs"]
        DEV_LOGGER.info("Getting from saved_config: generate-certs.ssl")
        config_certs["ssl"] = utils.validated_config_value(
            saved_certs, "ssl", partial(utils.validate_type, bool), fallback=True
        )
        DEV_LOGGER.info("Getting from saved_config: generate-certs.ssh")
        config_certs["ssh"] = utils.validated_config_value(
            saved_certs, "ssh", partial(utils.validate_type, bool), fallback=True
        )
