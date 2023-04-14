"""
Pexip installation wizard step to setup a network interface
"""
from __future__ import annotations

import logging
import subprocess
from collections import defaultdict
from functools import partial
from ipaddress import IPv4Address, IPv4Network

from rp_turn import utils
from rp_turn.steps import Step
from rp_turn.steps.routes import RoutesStep

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class NetworkStep(Step):
    """Step to setup a nic"""

    def __init__(
        self,
        nic_name: str,
        nic_mac: str,
        is_external: bool,
        is_internal: bool,
        nic_str: str | None = None,
    ) -> None:
        super().__init__(f"Configuring {nic_name} ({nic_mac})")
        assert is_external or is_internal
        self.nic_name = nic_name
        self.nic_mac = nic_mac
        self.nic_str = (
            nic_str if nic_str is not None else f" for {nic_name} ({nic_mac})"
        )
        self.questions = [self._start]
        self._routes = RoutesStep(nic_name, nic_mac)
        self._is_external = is_external
        self._is_internal = is_internal
        self._is_dual_nic = is_external != is_internal

    def _start(self, _config: defaultdict) -> None:
        """Determines what kind of interface is going to be setup"""
        self.questions += [self._get_ip_address, self._get_netmask]
        if self._is_external:
            DEV_LOGGER.info("%s is external. Adding _get_gateway", self.nic_name)
            self.questions.append(self._get_gateway)
        if self._is_dual_nic and self._is_internal:
            DEV_LOGGER.info(
                "%s is internal and dual nic is enabled. Adding _get_internal_routes",
                self.nic_name,
            )
            self.questions.append(self._get_internal_routes)

    def _get_ip_address(self, config: defaultdict) -> None:
        """Question to get ip address"""
        default_ip = utils.config_get(config["networks"][self.nic_name]["ipaddress"])
        response = self.ask(f"IP Address{self.nic_str}?", default=default_ip)
        DEV_LOGGER.info("Response: %s", response)
        if "/" in response:
            # Try to validate as a cidr format
            ip_address, netmask = utils.validate_cidr_interface_string(response)
            self._store_ipaddress(config, ip_address)
            self._store_netmask(config, netmask)
            self.questions.pop(0)  # Skip the netmask question as we already have it
        else:
            ip_address_obj = utils.validate_ip(response)
            self._store_ipaddress(config, ip_address_obj.exploded)

    def _store_ipaddress(self, config: defaultdict, ip_address: str) -> None:
        """Stores the ip address in the config"""
        config["networks"][self.nic_name]["ipaddress"] = ip_address

    def _get_netmask(self, config: defaultdict) -> None:
        """Question to get netmask"""
        default_netmask = utils.config_get(config["networks"][self.nic_name]["netmask"])
        response = self.ask(f"Subnet mask{self.nic_str}?", default=default_netmask)
        DEV_LOGGER.info("Response: %s", response)
        self._store_netmask(config, response)

    def _store_netmask(self, config: defaultdict, netmask: str) -> None:
        """Stores the netmask in the config"""
        ip_address: str | None = utils.config_get(
            config["networks"][self.nic_name]["ipaddress"]
        )
        assert isinstance(ip_address, str)
        interface = utils.validate_interface(ip_address, netmask)
        config["networks"][self.nic_name]["netmask"] = interface.netmask.exploded

    def _get_gateway(self, config: defaultdict) -> None:
        """Question to get gateway"""
        default_gateway = utils.config_get(config["networks"][self.nic_name]["gateway"])
        response = self.ask(f"Default gateway{self.nic_str}?", default=default_gateway)
        DEV_LOGGER.info("Response: %s", response)
        gateway = utils.validate_ip(response)
        config["networks"][self.nic_name]["gateway"] = gateway.exploded

    def _get_internal_routes(self, config: defaultdict) -> None:
        """Question to get internal routes"""
        self._routes.run(
            config,
            step_id=self._step_id,
            total_steps=self._total_steps,
            print_header=False,
        )

    def _default_ipaddress(
        self, saved_config_nic: defaultdict, config: defaultdict
    ) -> IPv4Address | None:
        """Find stored ip address"""
        saved_ipaddress: IPv4Address | None = utils.validated_config_value(
            saved_config_nic, "ipaddress", utils.validate_ip
        )
        if saved_ipaddress is not None:
            config["networks"][self.nic_name]["ipaddress"] = saved_ipaddress
            DEV_LOGGER.info(
                "Using saved_ipaddress for %s: %s", self.nic_name, saved_ipaddress
            )
        else:
            DEV_LOGGER.info("No saved_ipaddress for %s", self.nic_name)
        return saved_ipaddress

    def _default_netmask(
        self, saved_config_nic: defaultdict, config: defaultdict
    ) -> IPv4Network | None:
        """Find stored netmask"""
        saved_netmask: IPv4Network | None = utils.validated_config_value(
            saved_config_nic, "netmask", partial(utils.validate_network, "0.0.0.0")
        )
        if saved_netmask is not None:
            config["networks"][self.nic_name]["netmask"] = saved_netmask
            DEV_LOGGER.info(
                "Using saved_netmask for %s: %s", self.nic_name, saved_netmask
            )
        else:
            DEV_LOGGER.info("No saved_netmask for %s", self.nic_name)
        return saved_netmask

    def _default_gateway(
        self, saved_config_nic: defaultdict, config: defaultdict
    ) -> IPv4Address | None:
        """Find stored gateway"""
        saved_gateway: IPv4Address | None = utils.validated_config_value(
            saved_config_nic, "gateway", utils.validate_ip
        )
        if saved_gateway is not None:
            config["networks"][self.nic_name]["gateway"] = saved_gateway
            DEV_LOGGER.info(
                "Using saved_gateway for %s: %s", self.nic_name, saved_gateway
            )
        else:
            DEV_LOGGER.info("No saved_gateway for %s", self.nic_name)
        return saved_gateway

    def _default_dhcp_ipaddress_netmask(
        self, config: defaultdict, get_ipaddress: bool = True, get_netmask: bool = True
    ) -> None:
        """Try to guess ip/netmask from DHCP"""
        try:
            DEV_LOGGER.info(
                "Attempting to guess ip/netmask for %s from ip addr", self.nic_name
            )
            ip_addr_output = subprocess.check_output(
                ["/sbin/ip", "addr", "list", "dev", self.nic_name], encoding="UTF-8"
            )
            for line in ip_addr_output.split("\n"):
                DEV_LOGGER.info("Got line: %s", line)
                parts = line.split(" ")
                try:
                    inet_location = parts.index("inet") + 1
                    dhcp_cidr = parts[inet_location]
                    DEV_LOGGER.info("Found a cidr: %s", dhcp_cidr)
                    dhcp_ip, dhcp_netmask = dhcp_cidr.split("/")
                    interface = utils.validate_interface(dhcp_ip, dhcp_netmask)
                    if get_ipaddress:
                        config["networks"][self.nic_name][
                            "ipaddress"
                        ] = interface.ip.exploded
                        DEV_LOGGER.info(
                            "Using suggested ipaddress %s for %s",
                            interface.ip.exploded,
                            self.nic_name,
                        )
                    if get_netmask:
                        netmask_exploded = interface.netmask.exploded
                        config["networks"][self.nic_name]["netmask"] = netmask_exploded
                        DEV_LOGGER.info(
                            "Using DHCP suggested netmask %s for %s",
                            netmask_exploded,
                            self.nic_name,
                        )
                except ValueError:
                    DEV_LOGGER.exception("%s did not contain a cidr interface", line)
        except subprocess.CalledProcessError:
            DEV_LOGGER.exception(
                "Error running shell command ip addr list dev %s", self.nic_name
            )

    def _default_dhcp_gateway(self, config: defaultdict) -> None:
        """Try to guess gateway from DHCP"""
        try:
            DEV_LOGGER.info(
                "Attempting to guess gateway ip for %s from ip route", self.nic_name
            )
            ip_addr_output = subprocess.check_output(
                ["/sbin/ip", "route", "list", "dev", self.nic_name], encoding="UTF-8"
            )
            for line in ip_addr_output.split("\n"):
                DEV_LOGGER.info("Got line: %s", line)
                parts = line.split(" ")
                try:
                    if "default" in parts:
                        gateway_location = parts.index("via") + 1
                        dhcp_gateway = parts[gateway_location]
                        DEV_LOGGER.info("Found a gateway: %s", dhcp_gateway)
                        gateway = utils.validate_ip(dhcp_gateway)
                        config["networks"][self.nic_name]["gateway"] = gateway.exploded
                        DEV_LOGGER.info(
                            "Using DHCP suggested gateway %s for %s",
                            gateway.exploded,
                            self.nic_name,
                        )
                except ValueError:
                    DEV_LOGGER.exception(
                        "%s did not contain a valid gateway ip address", parts
                    )
        except subprocess.CalledProcessError:
            DEV_LOGGER.exception(
                "Error running shell command ip route list dev %s", self.nic_name
            )

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        saved_config_nic = saved_config["networks"][self.nic_name]
        saved_ipaddress = self._default_ipaddress(saved_config_nic, config)
        saved_netmask = self._default_netmask(saved_config_nic, config)
        saved_gateway = self._default_gateway(saved_config_nic, config)

        # Try to guess ip/netmask from DHCP
        if saved_ipaddress is None or saved_netmask is None:
            self._default_dhcp_ipaddress_netmask(
                config,
                get_ipaddress=(saved_ipaddress is None),
                get_netmask=(saved_netmask is None),
            )

        # Try to guess gateway from DHCP
        if saved_gateway is None:
            self._default_dhcp_gateway(config)

        # Setup Routes
        self._routes.default_config(saved_config, config)
