# pylint: disable=consider-using-from-import
"""
Pexip installation wizard step to setup iptables
"""

import logging
import si.apps.reverseproxy.utils as utils
from si.apps.reverseproxy.steps.base_step import MultiStep

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class ManagementStep(MultiStep):
    """Step to decide which networks can access this vm via SSH"""

    def __init__(self):
        MultiStep.__init__(
            self,
            "IPTables rules for SSH access",
            "managementnetworks",
            end_on_enter=False,
        )
        self.questions = [self._intro_management_network, self._use_default]
        self._last_ip = None

    def _intro_management_network(self, _):
        """Displays an intro to this step"""
        self.display(
            """This step allows configuring which networks can access this machine via SSH.
Multiple networks can be chosen.
"""
        )

    def _get_another_answer(self, config):
        """Adds an ask for another namagement network"""
        self.questions.append(self._add_management_network)

    def _add_management_network(self, config):
        """Ask whether user wants to add another namagement network"""
        response = self.ask_yes_no(
            "Add {} management network?".format("another" if self._answers else "a")
        )
        if response:
            self.questions += [
                self._get_network_ip_address,
                self._get_network_netmask,
                self._add_management_network,
            ]
        else:
            if not self._answers:
                self.display(
                    "No management networks were setup, ssh access will be disabled!"
                )
            config["managementnetworks"] = self._answers
            DEV_LOGGER.info("Set managementnetworks to: %s", self._answers)

    def _store_ipaddress(self, _config, ip_address):
        """Store the ip address of the management network"""
        ip_address = utils.validate_ip(ip_address)
        self._last_ip = ip_address

    def _get_network_ip_address(self, config):
        """Gets network ip address for the management network"""
        response = self.ask(
            "IP Address for management network {}?".format(len(self._answers) + 1)
        )
        DEV_LOGGER.info("Response: %s", response)
        if "/" in response:
            # Try to validate as a cidr format
            ip_address, netmask = utils.validate_cidr_interface_string(response)
            self._store_ipaddress(config, ip_address)
            self._store_netmask(config, netmask)
            self.questions.pop(0)  # Skip the netmask question as we already have it
        else:
            self._store_ipaddress(config, response)

    def _store_netmask(self, _config, netmask):
        """Store the netmask of the management network"""
        network = utils.validate_network(self._last_ip.exploded, netmask)
        network_hostbits = utils.validate_ip(network.exploded.split("/", maxsplit=1)[0])
        if network_hostbits != self._last_ip:
            warn_msg = "Warning: network was translated to {}/{}".format(
                network_hostbits.exploded, network.netmask.exploded
            )
            self.display(warn_msg)
        self.display(
            "This management network allows ssh access to {} ip addresses".format(
                network.num_addresses
            )
        )
        self._answers.append(network.exploded)

    def _get_network_netmask(self, config):
        """Gets network netmask for the management network"""
        response = self.ask(
            "Subnet mask for management network {}?".format(len(self._answers) + 1)
        )
        DEV_LOGGER.info("Response: %s", response)
        self._store_netmask(config, response)

    def default_config(self, saved_config, config):
        DEV_LOGGER.info("Getting from saved_config: managementnetworks")
        config["managementnetworks"] = utils.validated_config_value(
            saved_config,
            "managementnetworks",
            utils.validate_cidr_network,
            value_list=True,
        )
