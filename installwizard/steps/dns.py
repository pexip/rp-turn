# pylint: disable=consider-using-from-import
# pylint: disable=unspecified-encoding
"""
Pexip installation wizard step to setup dns servers
"""
# pylint: disable=too-many-nested-blocks

import logging
import si.apps.reverseproxy.utils as utils
from si.apps.reverseproxy.steps.base_step import StepError, MultiStep

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class DNSStep(MultiStep):
    """Step to get dns servers"""

    def __init__(self):
        MultiStep.__init__(self, "DNS Servers", "dns")

    def validate(self, response):
        DEV_LOGGER.info("Response: %s", response)
        return utils.validate_ip(response).exploded

    @staticmethod
    def _dhcp_dns():
        """
        Gets the dns servers suggested by DHCP
        :return: nameservers suggested by DHCP or googles DNS servers if no other DNS servers could be found
        """
        for filename in ["/run/systemd/resolve/resolv.conf", "/etc/resolv.conf"]:
            DEV_LOGGER.info("Attempting to guess DNS from: %s", filename)
            try:
                with open(filename, "r") as file_obj:
                    resolv = file_obj.read()
                ns_prefix = "nameserver "
                nameservers = []
                for line in resolv.split("\n"):
                    DEV_LOGGER.info("Got line: %s", line)
                    if line.startswith(ns_prefix):
                        ip_str = line.replace(ns_prefix, "")
                        try:
                            DEV_LOGGER.info("Found a nameserver: %s", ip_str)
                            validated_ip = utils.validate_ip(ip_str)
                            # Ignore local addresses, as that will be the ubuntu dns cache
                            if not validated_ip.is_loopback:
                                nameservers.append(validated_ip.exploded)
                                DEV_LOGGER.info(
                                    "Added DNS Server: %s", validated_ip.exploded
                                )
                            else:
                                DEV_LOGGER.info("It was a loopback device")
                        except StepError:
                            DEV_LOGGER.exception("%s was not an ip address", ip_str)
                if nameservers:
                    DEV_LOGGER.info("Found DNS servers from DHCP: %s", nameservers)
                    return nameservers
                DEV_LOGGER.info("File %s had no valid dns servers", filename)
            except IOError:
                DEV_LOGGER.exception("Failed to read: %s", filename)
        DEV_LOGGER.info(
            "Failed to guess DNS servers from DHCP. Falling back on googles dns servers"
        )
        return ["8.8.8.8", "8.8.4.4"]

    def default_config(self, saved_config, config):
        # Attempt to find out nameservers supplied by DHCP
        dhcp_dns = self._dhcp_dns()
        DEV_LOGGER.info("Getting from saved_config: dns")
        config["dns"] = utils.validated_config_value(
            saved_config, "dns", utils.validate_ip, value_list=True, fallback=dhcp_dns
        )
