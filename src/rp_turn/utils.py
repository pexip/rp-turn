"""
Bunch of utils for the install wizard
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from collections import defaultdict
from functools import partial
from ipaddress import (
    AddressValueError,
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    NetmaskValueError,
)
from typing import Any, Callable, TypeVar

from rp_turn.step_error import StepError

DEV_LOGGER = logging.getLogger("rp_turn.installwizard")

VALID_HOSTNAME_RE = re.compile(
    r"^([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])\Z", re.IGNORECASE
)
VALID_NUMBER_RE = re.compile(r"^([0-9]+)\Z")

_T = TypeVar("_T")


def nested_dict() -> defaultdict:
    """Allows accessing non existent key elements from a dictionary by adding empty dicts on the fly"""
    return defaultdict(nested_dict)


def make_nested_dict(val: Any) -> Any:
    """Converts a standard dict into a nested_dict"""
    if isinstance(val, dict):
        new_dict = nested_dict()
        for key, value in val.items():
            new_dict[key] = make_nested_dict(value)
        return new_dict
    if isinstance(val, list):
        return [make_nested_dict(elem) for elem in val]
    return val


def config_get(val: _T) -> _T | None:
    """
    Replaces an empty dict with None when accessing a value from the config
    """
    if val == {}:
        return None
    return val


def get_config_value_by_path(config: defaultdict, path: str | list[str]) -> Any:
    """Follows the path in the config and returns its value"""
    config_value = config
    if isinstance(path, list):
        for subkey in path:
            config_value = config_value[subkey]
    else:
        config_value = config_value[path]
    return config_get(config_value)


def set_config_value_by_path(
    config: defaultdict, path: str | list[str], value: Any
) -> None:
    """Follows the path in the config and sets its value"""
    config_value = config
    if isinstance(path, list):
        for subkey in path[:-1]:
            config_value = config_value[subkey]
        config_value[path[-1]] = value
    else:
        config_value[path] = value


def validated_config_value(
    saved_config: defaultdict[str, _T],
    key: str,
    validation: Callable[[Any], Any] | partial[_T],
    value_list: bool = False,
    fallback: _T | None = None,
    log_values: bool = True,
) -> _T | None:
    """
    Follows key to a value, and validates if it is correct
    Returns None on an invalid/missing value
    """
    if key in saved_config:
        value = saved_config[key]
        try:
            # Makes sure we get a list only if it should be a list
            if value_list != isinstance(value, list):
                if log_values:
                    DEV_LOGGER.info(
                        "Using default value (%s) for %s as %s %s a list",
                        fallback,
                        key,
                        value,
                        "was" if value_list else "was not",
                    )
                return fallback
            if isinstance(value, list):
                if not value:  # list is empty
                    if log_values:
                        DEV_LOGGER.info(
                            "%s list has no elements, using default value (%s)",
                            key,
                            fallback,
                        )
                    return fallback
                for val in value:
                    validation(val)
            else:
                validation(value)
            if log_values:
                DEV_LOGGER.info("Using saved value (%s) for key %s", value, key)
            return value
        except StepError:
            pass
    if log_values:
        DEV_LOGGER.info("Missing value for key %s using default (%s)", key, fallback)
    return fallback


def validate_type(val_type: type, val: object) -> object:
    """Validates that a value is of type"""
    if isinstance(val, val_type):
        return val
    raise StepError(f"{val} is not of type {val_type} (Has type: {type(val)})")


def validate_interface_name(config: defaultdict, interface: str) -> str:
    """Validates that a value is an interface name"""
    if not isinstance(interface, str):
        raise StepError("Interface is not a string")
    if interface.strip() in config["networks"]:
        return interface.strip()
    raise StepError(f"Cannot find {interface} interface")


def validate_ip(address: str) -> IPv4Address:
    """Validate that something looks like an IPv4 address."""
    try:
        return IPv4Address(str(address.strip()))
    except (AddressValueError, AttributeError) as exc:
        DEV_LOGGER.info("%s failed ip validation", address)
        raise StepError("Does not look like an IPv4 Address") from exc


def validate_network(address: str, netmask: str) -> IPv4Network:
    """
    Validate that something looks like a valid address/netmask and returns as cidr
    """
    return validate_cidr_network(address.strip() + "/" + netmask.strip())


def validate_cidr_network(cidr: str) -> IPv4Network:
    """
    Validate that something looks like a valid network as cidr
    """
    try:
        # strict=False will change the base ip if the netmask isn't covering enough bits
        return IPv4Network(str(cidr.strip()), strict=False)
    except (AddressValueError, NetmaskValueError, ValueError, AttributeError) as exc:
        DEV_LOGGER.error("%s failed cidr validation", cidr)
        raise StepError("Does not look like an IPv4 Netmask") from exc


def validate_cidr_network_string(cidr: str) -> tuple[str, str]:
    """
    Validate that something looks like a valid network as cidr
    :param cidr:
    :return: ip_address and netmask as strings
    """
    try:
        ip_address, netmask = cidr.strip().split("/")
        validate_ip(ip_address)
        validate_network(ip_address, netmask)
        return ip_address.strip(), netmask.strip()
    except (AddressValueError, NetmaskValueError, ValueError, AttributeError) as exc:
        DEV_LOGGER.error("%s failed cidr network string validation", cidr)
        raise StepError("Does not look like an IPv4 Network") from exc


def validate_interface(address: str, netmask: str) -> IPv4Interface:
    """
    Validate that something looks like a valid network interface address/netmask and returns as cidr
    """
    try:
        return IPv4Interface(str(address.strip() + "/" + netmask.strip()))
    except (AddressValueError, NetmaskValueError, ValueError, AttributeError) as exc:
        DEV_LOGGER.info("'%s' '%s' failed interface validation", address, netmask)
        raise StepError("Does not look like an IPv4 Interface") from exc


def validate_cidr_interface_string(cidr: str) -> tuple[str, str]:
    """
    Validate that something looks like a valid network as cidr
    :param cidr:
    :return: ip_address and netmask as strings
    """
    try:
        ip_address, netmask = cidr.strip().split("/")
        validate_ip(ip_address)
        validate_interface(ip_address, netmask)
        return ip_address.strip(), netmask.strip()
    except (AddressValueError, NetmaskValueError, ValueError, AttributeError) as exc:
        DEV_LOGGER.error("%s failed cidr network string validation", cidr)
        raise StepError("Does not look like an IPv4 Interface") from exc


def validate_domain(domain: str) -> str:
    """
    Validate that something looks like a domain name.
    """
    if not isinstance(domain, str):
        raise StepError("Domain is not a string")
    domain = domain.strip()
    parts = domain.split(".")

    if VALID_NUMBER_RE.match(parts[-1]):
        DEV_LOGGER.info("%s failed domain validation", parts)
        raise StepError("Last part of the domain must not be a number")

    for part in parts:
        if len(part) > 63:
            DEV_LOGGER.info("%s failed domain validation", parts)
            raise StepError(
                f"Each part of the domain should be < 64 characters long: {part}"
            )
        if not VALID_HOSTNAME_RE.match(part):
            DEV_LOGGER.info("%s failed domain validation", parts)
            raise StepError(f"Part of the domain contains invalid characters: {part}")

    return domain


def validate_hostname(hostname: str) -> str:
    """
    Validate that something looks like a hostname.
    """
    if not isinstance(hostname, str):
        raise StepError("Hostname is not a string")
    hostname = hostname.strip()
    if not VALID_HOSTNAME_RE.match(hostname):
        DEV_LOGGER.info("%s failed hostname validation", hostname)
        raise StepError("Hostname contains invalid characters")
    return hostname


def run_shell(argl: str, *argv: str) -> None:
    """Runs a list of shell commands"""
    with open(os.devnull, "wb") as fnull:
        for cmd in [argl] + list(argv):
            DEV_LOGGER.info("Running shell command: %s", cmd)
            # TODO: Get subprocess stdout and stderr into DEV_LOGGER
            subprocess.check_call(cmd, stdout=fnull, stderr=fnull, shell=True)
