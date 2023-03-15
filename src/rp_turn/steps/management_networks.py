"""
Pexip installation wizard step to setup iptables
"""

import logging
from collections import defaultdict
from ipaddress import IPv4Address

from rp_turn import utils
from rp_turn.steps.base_step import MultiStep

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class ManagementStep(MultiStep):
    """Step to decide which networks can access this vm via SSH"""

    def __init__(self) -> None:
        super().__init__(
            "IPTables rules for SSH access",
            "managementnetworks",
            end_on_enter=False,
        )
        self.questions = [self._intro_management_network, self._use_default]
        self._last_ip: IPv4Address | None = None

    def _intro_management_network(self, _config: defaultdict) -> None:
        """Displays an intro to this step"""
        self.display(
            """This step allows configuring which networks can access this machine via SSH.
Multiple networks can be chosen.
"""
        )

    def _get_another_answer(self, config: defaultdict) -> None:
        """Adds an ask for another namagement network"""
        self.questions.append(self._add_management_network)

    def _add_management_network(self, config: defaultdict) -> None:
        """Ask whether user wants to add another namagement network"""
        response = self.ask_yes_no(
            f"Add {'another' if self._answers else 'a'} management network?"
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

    def _store_ipaddress(self, _config: defaultdict, ip_address: str) -> None:
        """Store the ip address of the management network"""
        self._last_ip = utils.validate_ip(ip_address)

    def _get_network_ip_address(self, config: defaultdict) -> None:
        """Gets network ip address for the management network"""
        response = self.ask(
            f"IP Address for management network {len(self._answers) + 1}?"
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

    def _store_netmask(self, _config: defaultdict, netmask: str) -> None:
        """Store the netmask of the management network"""
        assert isinstance(self._last_ip, IPv4Address)

        network = utils.validate_network(self._last_ip.exploded, netmask)
        network_hostbits = utils.validate_ip(network.exploded.split("/", maxsplit=1)[0])
        if network_hostbits != self._last_ip:
            warn_msg = f"Warning: network was translated to {network_hostbits.exploded}/{network.netmask.exploded}"
            self.display(warn_msg)
        self.display(
            f"This management network allows ssh access to {network.num_addresses} ip addresses"
        )
        self._answers.append(network.exploded)

    def _get_network_netmask(self, config: defaultdict) -> None:
        """Gets network netmask for the management network"""
        response = self.ask(
            f"Subnet mask for management network {len(self._answers) + 1}?"
        )
        DEV_LOGGER.info("Response: %s", response)
        self._store_netmask(config, response)

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        DEV_LOGGER.info("Getting from saved_config: managementnetworks")
        config["managementnetworks"] = utils.validated_config_value(
            saved_config,
            "managementnetworks",
            utils.validate_cidr_network,
            value_list=True,
        )
