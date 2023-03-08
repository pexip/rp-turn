# pylint: disable=consider-using-from-import
# pylint: disable=unspecified-encoding
"""
Pexip installation wizard step to setup hostname and domain
"""
# pylint: disable=too-many-nested-blocks

import logging
import si.apps.reverseproxy.utils as utils
from si.apps.reverseproxy.steps.base_step import StepError, Step

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class HostnameStep(Step):
    """Step to get hostname and domain name"""

    def __init__(self):
        Step.__init__(self, "Hostname and Domain")
        self.questions = [self._get_hostname, self._get_domain]

    def _get_hostname(self, config):
        """Question to get the hostname"""
        default_hostname = utils.config_get(config["hostname"])
        response = self.ask("Hostname?", default=default_hostname)
        DEV_LOGGER.info("Response: %s", response)
        hostname = utils.validate_hostname(response)
        config["hostname"] = hostname

    def _get_domain(self, config):
        """Question to get the domain"""
        default_domain = utils.config_get(config["domain"])
        response = self.ask("Domain?", default=default_domain)
        DEV_LOGGER.info("Response: %s", response)
        domain = utils.validate_domain(response)
        config["domain"] = domain

    @staticmethod
    def _dhcp_domain():
        """Uses DHCP to find the default domain"""
        # Attempt to find out domain supplied by DHCP
        for filename in ["/run/systemd/resolve/resolv.conf", "/etc/resolv.conf"]:
            DEV_LOGGER.info("Attempting to guess domain from: %s", filename)
            try:
                with open(filename, "r") as file_obj:
                    resolv = file_obj.read()
                domain_prefix = "search "
                for line in resolv.split("\n"):
                    DEV_LOGGER.info("Got line: %s", line)
                    if line.startswith(domain_prefix):
                        domains = line.replace(domain_prefix, "").split(" ")
                        DEV_LOGGER.info("Found a search: %s", domains)
                        # Find first valid domain
                        for domain in domains:
                            try:
                                dhcp_domain = utils.validate_domain(domain)
                                DEV_LOGGER.info(
                                    "Using domain name suggested by DHCP: %s",
                                    dhcp_domain,
                                )
                                return dhcp_domain
                            except StepError:
                                pass
            except IOError:
                DEV_LOGGER.exception("Unable to read file: %s", filename)
        DEV_LOGGER.info("Failed to guess domain from DHCP. No domain to suggest")
        return None

    def default_config(self, saved_config, config):
        DEV_LOGGER.info("Getting from saved_config: hostname")
        config["hostname"] = utils.validated_config_value(
            saved_config, "hostname", utils.validate_hostname
        )
        dhcp_domain = self._dhcp_domain()
        DEV_LOGGER.info("Getting from saved_config: domain")
        config["domain"] = utils.validated_config_value(
            saved_config, "domain", utils.validate_domain, fallback=dhcp_domain
        )
