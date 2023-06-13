"""
Pexip installation wizard step to setup web load balancer
"""

from __future__ import annotations

import logging
from collections import defaultdict
from enum import Enum, auto
from functools import partial
from ipaddress import IPv4Address

from rp_turn import utils
from rp_turn.step_error import StepError
from rp_turn.steps.base_step import MultiStep, Step

DEV_LOGGER = logging.getLogger("rp_turn.installwizard")


class AddressType(Enum):
    """Enum to determine address type"""

    IP_ADDRESS = auto()
    FQDN = auto()


class WebLoadBalanceStep(Step):
    """
    Step to decide whether to enable web load balancer
    """

    def __init__(self) -> None:
        super().__init__("Web Reverse Proxy")
        self.questions = [self._enable_web_load_balance]
        self._extra_steps = [SignalingConferenceNodeStep(), ContentSecurityPolicyStep()]

    def _enable_web_load_balance(self, config: defaultdict) -> None:
        """Question to find out whether to enable web reverseproxy"""
        default_enabled = utils.config_get(config["enablewebloadbalance"])
        response = self.ask_yes_no("Enable web reverse proxy?", default=default_enabled)
        config["enablewebloadbalance"] = response
        if response:
            self.questions.append(self._run_extra_steps)

    def _run_extra_steps(self, config: defaultdict) -> None:
        """Question to run extra steps required for the web load balance"""
        for extra_step in self._extra_steps:
            extra_step.run(
                config,
                step_id=self._step_id,
                total_steps=self._total_steps,
                print_header=False,
            )

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        DEV_LOGGER.info("Getting from saved_config: enablewebloadbalance")
        config["enablewebloadbalance"] = utils.validated_config_value(
            saved_config,
            "enablewebloadbalance",
            partial(utils.validate_type, bool),
            fallback=True,
        )
        for step in self._extra_steps:
            step.default_config(saved_config, config)


class SignalingConferenceNodeStep(MultiStep):
    """Step to set the conference node ip addresses"""

    def __init__(self) -> None:
        super().__init__("Address of Signaling Conferencing Nodes", "conferencenodes")
        self.questions = [self.intro] + self.questions
        self._address_type: AddressType | None = None

    def intro(self, _config: defaultdict) -> None:
        """Explain difference between FQDN and IP addresses"""
        self.display(
            """\
The reverse proxy can be configured to relay to either FQDNs or IP addresses.
If FQDNs are used, the upstream TLS certificates will be verified.
If IP addresses are used, the transport will still be HTTPS, but the certificates will NOT be verified.

Enter in either FQDNs or IP addresses
"""
        )

    def validate(self, response: str) -> IPv4Address | str:
        DEV_LOGGER.info("Response: %s", response)
        # once a type is chosen, all the items must be of this type
        if self._address_type == AddressType.IP_ADDRESS:
            return utils.validate_ip(response)
        if self._address_type == AddressType.FQDN:
            return utils.validate_domain(response)

        # try to guess which type this is
        try:
            parsed_domain = utils.validate_domain(response)
            self._address_type = AddressType.FQDN
            return parsed_domain
        except StepError:
            pass  # wasn't an FQDN

        # try an IP address, fail if not
        parsed_ip: IPv4Address = utils.validate_ip(response)
        self._address_type = AddressType.IP_ADDRESS
        return parsed_ip

    def _final_step(self, config: defaultdict) -> None:
        config["verify_upstream_tls"] = self._address_type == AddressType.FQDN

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        DEV_LOGGER.info("Getting from saved_config: conferencenodes")
        try:
            config["conferencenodes"] = utils.validated_config_value(
                saved_config, "conferencenodes", self.validate, value_list=True
            )
        finally:
            # validate would set the address_type. clear it to allow it to be changed.
            self._address_type = None


class ContentSecurityPolicyStep(Step):
    """Step to decide whether to enable content security policy"""

    def __init__(self) -> None:
        super().__init__("Content-Security-Policy Security")
        self.questions = [self._enable_csp]

    def _enable_csp(self, config: defaultdict) -> None:
        """Question to find out whether to enable the content security policy"""
        default_enabled: bool | None = utils.config_get(config["enablecsp"])
        response = self.ask_yes_no(
            """\
Content-Security-Policy provides enhanced security if you are NOT using optional features such as plug-ins
for Infinity Connect, externally-hosted branding, or externally-hosted pexrtc.js in your Pexip deployment.

Do NOT enable if you want compatibility with these optional features
Otherwise we recommend that you enable this option.

Enable Content-Security-Policy?""",
            default=default_enabled,
        )
        config["enablecsp"] = response

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        DEV_LOGGER.info("Getting from saved_config: enablecsp")
        config["enablecsp"] = utils.validated_config_value(
            saved_config, "enablecsp", partial(utils.validate_type, bool), fallback=True
        )
