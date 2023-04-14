"""
Pexip installation wizard step to setup dns servers
"""

from __future__ import annotations

import logging
from collections import defaultdict

from rp_turn import utils
from rp_turn.steps.base_step import MultiStep, StepError

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class DNSStep(MultiStep):
    """Step to get dns servers"""

    def __init__(self) -> None:
        super().__init__("DNS Servers", "dns")

    def validate(self, response: str) -> str:
        DEV_LOGGER.info("Response: %s", response)
        return utils.validate_ip(response).exploded

    @staticmethod
    def _dhcp_dns() -> list[str]:
        """
        Gets the dns servers suggested by DHCP
        :return: nameservers suggested by DHCP or googles DNS servers if no other DNS servers could be found
        """
        for filename in ["/run/systemd/resolve/resolv.conf", "/etc/resolv.conf"]:
            DEV_LOGGER.info("Attempting to guess DNS from: %s", filename)
            try:
                with open(filename, "r", encoding="utf-8") as file_obj:
                    resolv = file_obj.read()
            except IOError:
                DEV_LOGGER.exception("Failed to read: %s", filename)
                continue

            ns_prefix = "nameserver "
            nameservers = []
            for line in resolv.split("\n"):
                DEV_LOGGER.info("Got line: %s", line)
                if not line.startswith(ns_prefix):
                    continue
                ip_str = line.replace(ns_prefix, "")
                try:
                    DEV_LOGGER.info("Found a nameserver: %s", ip_str)
                    validated_ip = utils.validate_ip(ip_str)
                    # Ignore local addresses, as that will be the ubuntu dns cache
                    if not validated_ip.is_loopback:
                        nameservers.append(validated_ip.exploded)
                        DEV_LOGGER.info("Added DNS Server: %s", validated_ip.exploded)
                    else:
                        DEV_LOGGER.info("It was a loopback device")
                except StepError:
                    DEV_LOGGER.exception("%s was not an ip address", ip_str)
            if nameservers:
                DEV_LOGGER.info("Found DNS servers from DHCP: %s", nameservers)
                return nameservers
            DEV_LOGGER.info("File %s had no valid dns servers", filename)

        DEV_LOGGER.info(
            "Failed to guess DNS servers from DHCP. Falling back on googles dns servers"
        )
        return ["8.8.8.8", "8.8.4.4"]

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        # Attempt to find out nameservers supplied by DHCP
        dhcp_dns = self._dhcp_dns()
        DEV_LOGGER.info("Getting from saved_config: dns")
        config["dns"] = utils.validated_config_value(
            saved_config, "dns", utils.validate_ip, value_list=True, fallback=dhcp_dns
        )
