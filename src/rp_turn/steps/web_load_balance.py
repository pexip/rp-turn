"""
Pexip installation wizard step to setup fail2ban
"""

import logging
from collections import defaultdict
from functools import partial
from ipaddress import IPv4Address

from rp_turn import utils
from rp_turn.steps.base_step import MultiStep, Step

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


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
        super().__init__(
            "IP Address of Signaling Conferencing Nodes", "conferencenodes"
        )

    def validate(self, response: str) -> IPv4Address:
        DEV_LOGGER.info("Response: %s", response)
        return utils.validate_ip(response)

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        DEV_LOGGER.info("Getting from saved_config: conferencenodes")
        config["conferencenodes"] = utils.validated_config_value(
            saved_config, "conferencenodes", self.validate, value_list=True
        )


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
