# pylint: disable=consider-using-from-import
"""
Pexip installation wizard step to generate certificates
"""
import logging
from functools import partial

import si.apps.reverseproxy.utils as utils
from si.apps.reverseproxy.steps.base_step import Step

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class CertificatesStep(Step):
    """Generate New Certificates Step"""

    def __init__(self):
        Step.__init__(self, "Certificates")
        self.questions = [self._generate_ssl, self._generate_ssh]

    def _generate_ssl(self, config):
        """Question asking whether to regenerate ssl certificates"""
        response = self.ask_yes_no(
            "An existing SSL certificate exists.\n"
            + "Do you want to regenerate a new SSL certificate?",
            default=True,
        )
        DEV_LOGGER.info("Response: %s", response)
        config["generate-certs"]["ssl"] = response

    def _generate_ssh(self, config):
        """Question asking whether to regenerate ssh certificates"""
        response = self.ask_yes_no(
            "An existing SSH certificate exists.\n"
            + "Do you want to regenerate a new SSH certificate?",
            default=True,
        )
        DEV_LOGGER.info("Response: %s", response)
        config["generate-certs"]["ssh"] = response

    def default_config(self, saved_config, config):
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
