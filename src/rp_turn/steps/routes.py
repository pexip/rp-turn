"""
Pexip installation wizard step to setup internal routes
"""

import logging
from collections import defaultdict
from ipaddress import IPv4Interface, IPv4Network

from rp_turn import utils
from rp_turn.steps.base_step import MultiStep, StepError

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class RoutesStep(MultiStep):
    """Step to get custom routes for an interface"""

    def __init__(self, nic_name: str, nic_mac: str) -> None:
        super().__init__(
            f"Custom Routes for {nic_name} ({nic_mac})",
            ["networks", nic_name, "routes"],
            end_on_enter=False,
        )
        self.nic_name = nic_name
        self.nic_mac = nic_mac
        self.questions.insert(0, self._intro)
        self._last_ip: str | None = None
        self._last_to: IPv4Network | None = None
        self._nic_interface: IPv4Interface | None = None

    def format_value(self, value: dict[str, str]) -> str:
        return f"{value['to']} via {value['via']}"

    def _intro(self, config: defaultdict) -> None:
        """Verifies default routes are still valid before suggesting them"""
        self.display(
            "Custom routes can be configured on the internal-facing interface "
            "as an alternative to the default gateway. You will be asked for a"
            "subnet and then a via address."
        )
        nic_config = config["networks"][self.nic_name]
        self._nic_interface = utils.validate_interface(
            nic_config["ipaddress"], nic_config["netmask"]
        )

        valid_defaults = []
        # Verify routes are still valid (the nic ip/netmask might have changed)
        for route in nic_config["routes"]:
            # Check that via address is accessible
            if self._nic_interface.network.overlaps(
                IPv4Network(utils.validate_ip(route["via"]))
            ):
                valid_defaults.append(route)
        nic_config["routes"] = valid_defaults

    def _get_another_answer(self, config: defaultdict) -> None:
        another = "another" if self._answers else "a"
        response = self.ask_yes_no(
            f"Add {another} custom network route for {self.nic_name}?"
        )
        if response:
            self.questions += [
                self._get_network_ip_address,
                self._get_network_netmask,
                self._get_via_address,
                self._get_another_answer,
            ]
        else:
            config["networks"][self.nic_name]["routes"] = self._answers

    def _store_network_ipaddress(
        self, _config: defaultdict, network_ip_address: str
    ) -> None:
        """Stores the network ip address"""
        self._last_ip = utils.validate_ip(network_ip_address).exploded

    def _get_network_ip_address(self, config: defaultdict) -> None:
        """Question to get the route network ip address"""
        response = self.ask("Network IP Address?")
        DEV_LOGGER.info("Response: %s", response)
        if "/" in response:
            # Try to validate as a cidr format
            ip_address, netmask = utils.validate_cidr_interface_string(response)
            self._store_network_ipaddress(config, ip_address)
            self._store_network_netmask(config, netmask)
            self.questions.pop(0)  # Skip the netmask question as we already have it
        else:
            self._store_network_ipaddress(config, response)

    def _store_network_netmask(
        self, _config: defaultdict, network_netmask: str
    ) -> None:
        """Stores the network netmask"""
        assert isinstance(self._last_ip, str)
        self._last_to = utils.validate_network(self._last_ip, network_netmask)

    def _get_network_netmask(self, config: defaultdict) -> None:
        """Question to get the route network netmask"""
        response = self.ask("Network Netmask?")
        DEV_LOGGER.info("Response: %s", response)
        self._store_network_netmask(config, response)

    def _get_via_address(self, _config: defaultdict) -> None:
        """Question to get the route via ip address"""
        assert isinstance(self._nic_interface, IPv4Interface)
        assert isinstance(self._last_to, IPv4Network)

        via_address_str = self.ask("Via IP Address?")
        DEV_LOGGER.info("Response: %s", via_address_str)
        via_address = utils.validate_ip(via_address_str)
        # Throw exception if via address is not accessible
        assert isinstance(self._nic_interface, IPv4Interface)
        if not self._nic_interface.network.overlaps(IPv4Network(via_address)):
            raise StepError(
                f"{via_address} is not reachable from {self.nic_name} ({self._nic_interface.exploded})"
            )
        self._answers.append(
            utils.make_nested_dict(
                {"to": self._last_to.exploded, "via": via_address.exploded}
            )
        )

    @staticmethod
    def verify_route(value: dict[str, str]) -> tuple[str, str]:
        """Verifies if a stored value is a valid route"""
        try:
            if list(value.keys()) != ["to", "via"]:
                raise StepError(
                    "Route contains an invalid key (only accepts to and via)"
                )
            to_network = utils.validate_cidr_network(value["to"]).exploded
            via_address = utils.validate_ip(value["via"]).exploded
            return to_network, via_address
        except (KeyError, TypeError, AttributeError) as exc:
            raise StepError('Route needs a "to" network and a "via" address') from exc

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        saved_config_nic = saved_config["networks"][self.nic_name]
        config_nic = config["networks"][self.nic_name]
        DEV_LOGGER.info("Getting saved_config key: networks.%s.routes", self.nic_name)
        config_nic["routes"] = utils.validated_config_value(
            saved_config_nic,
            "routes",
            RoutesStep.verify_route,
            value_list=True,
            fallback=[],
        )
