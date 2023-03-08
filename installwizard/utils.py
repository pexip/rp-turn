"""
Bunch of utils for the install wizard
"""
# pylint: disable=consider-using-with
# pylint: disable=raise-missing-from
# pylint: disable=too-many-arguments


import logging
import os
import re
import subprocess
from collections import defaultdict
from ipaddress import (
    IPv4Address,
    IPv4Network,
    IPv4Interface,
    AddressValueError,
    NetmaskValueError,
)

from si.apps.reverseproxy.step_error import StepError

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")

VALID_HOSTNAME_RE = re.compile(
    r"^([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])\Z", re.IGNORECASE
)
VALID_NUMBER_RE = re.compile(r"^([0-9]+)\Z")


def nested_dict():
    """Allows accessing non existent key elements from a dictionary by adding empty dicts on the fly"""
    return defaultdict(nested_dict)


def make_nested_dict(val):
    """Converts a standard dict into a nested_dict"""
    if isinstance(val, dict):
        new_dict = nested_dict()
        for key, value in val.items():
            new_dict[key] = make_nested_dict(value)
        return new_dict
    if isinstance(val, list):
        return [make_nested_dict(elem) for elem in val]
    return val


def config_get(val):
    """
    Replaces an empty dict with None when accessing a value from the config
    """
    if val == {}:
        return None
    return val


def get_config_value_by_path(config, path):
    """Follows the path in the config and returns its value"""
    config_value = config
    if isinstance(path, list):
        for subkey in path:
            config_value = config_value[subkey]
    else:
        config_value = config_value[path]
    return config_get(config_value)


def set_config_value_by_path(config, path, value):
    """Follows the path in the config and sets its value"""
    config_value = config
    if isinstance(path, list):
        for subkey in path[:-1]:
            config_value = config_value[subkey]
        config_value[path[-1]] = value
    else:
        config_value[path] = value


def validated_config_value(
    saved_config, key, validation, value_list=False, fallback=None, log_values=True
):
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


def validate_type(val_type, val):
    """Validates that a value is of type"""
    if isinstance(val, val_type):
        return val
    raise StepError(
        "{} is not of type {} (Has type: {})".format(val, val_type, type(val))
    )


def validate_interface_name(config, interface):
    """Validates that a value is an interface name"""
    if type(interface) not in [str, bytes]:
        raise StepError("Interface is not a string")
    if interface.strip() in config["networks"]:
        return interface.strip()
    raise StepError("Cannot find {} interface".format(interface))


def validate_ip(address):
    """Validate that something looks like an IPv4 address."""
    try:
        return IPv4Address(str(address.strip()))
    except (AddressValueError, AttributeError):
        DEV_LOGGER.info("%s failed ip validation", address)
        raise StepError("Does not look like an IPv4 Address")


def validate_network(address, netmask):
    """
    Validate that something looks like a valid address/netmask and returns as cidr
    """
    return validate_cidr_network(address.strip() + "/" + netmask.strip())


def validate_cidr_network(cidr):
    """
    Validate that something looks like a valid network as cidr
    """
    try:
        # strict=False will change the base ip if the netmask isn't covering enough bits
        return IPv4Network(str(cidr.strip()), strict=False)
    except (AddressValueError, NetmaskValueError, ValueError, AttributeError):
        DEV_LOGGER.error("%s failed cidr validation", cidr)
        raise StepError("Does not look like an IPv4 Netmask")


def validate_cidr_network_string(cidr):
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
    except (AddressValueError, NetmaskValueError, ValueError, AttributeError):
        DEV_LOGGER.error("%s failed cidr network string validation", cidr)
        raise StepError("Does not look like an IPv4 Network")


def validate_interface(address, netmask):
    """
    Validate that something looks like a valid network interface address/netmask and returns as cidr
    """
    try:
        return IPv4Interface(str(address.strip() + "/" + netmask.strip()))
    except (AddressValueError, NetmaskValueError, ValueError, AttributeError):
        DEV_LOGGER.info("'%s' '%s' failed interface validation", address, netmask)
        raise StepError("Does not look like an IPv4 Interface")


def validate_cidr_interface_string(cidr):
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
    except (AddressValueError, NetmaskValueError, ValueError, AttributeError):
        DEV_LOGGER.error("%s failed cidr network string validation", cidr)
        raise StepError("Does not look like an IPv4 Interface")


def validate_domain(domain):
    """
    Validate that something looks like a domain name.
    """
    if type(domain) not in [str, bytes]:
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
                "Each part of the domain should be < 64 characters long: {}".format(
                    part
                )
            )
        if not VALID_HOSTNAME_RE.match(part):
            DEV_LOGGER.info("%s failed domain validation", parts)
            raise StepError(
                "Part of the domain contains invalid characters: {}".format(part)
            )

    return domain


def validate_hostname(hostname):
    """
    Validate that something looks like a hostname.
    """
    if type(hostname) not in [str, bytes]:
        raise StepError("Hostname is not a string")
    hostname = hostname.strip()
    if not VALID_HOSTNAME_RE.match(hostname):
        DEV_LOGGER.info("%s failed hostname validation", hostname)
        raise StepError("Hostname contains invalid characters")
    return hostname


def run_shell(argl, *argv):
    """Runs a list of shell commands"""
    fnull = open(os.devnull, "wb")
    for cmd in [argl] + list(argv):
        DEV_LOGGER.info("Running shell command: %s", cmd)
        # TODO: Get subprocess stdout and stderr into DEV_LOGGER
        subprocess.check_call(cmd, stdout=fnull, stderr=fnull, shell=True)
