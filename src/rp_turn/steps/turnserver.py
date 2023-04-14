"""
Pexip installation wizard step to setup the turnserver
"""

from __future__ import annotations

import base64
import logging
import os
from collections import defaultdict
from functools import partial
from ipaddress import IPv4Address

from passlib.utils import saslprep

from rp_turn import utils
from rp_turn.steps.base_step import MultiStep, Step, StepError

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class TCPTurnStep(Step):
    """TURN Step for tcp_turn_intro and get_tcp_turn"""

    def _intro_tcp_turn(self, _config: defaultdict) -> None:
        """Displays an intro message describing what TURN on 443 can do"""
        self.display(
            """\
The TURN server can be configured to relay media received on port 443, which can allow web clients
behind strict firewalls to make calls.

The TURN server listens on port 3478 by default"""
        )

    def _get_tcp_turn(self, config: defaultdict) -> None:
        """Question asking user whether to use listen on 443 instead"""
        port_443: bool | None = utils.config_get(config["turnserver"]["port443"])
        response = self.ask_yes_no(
            "Do you want the TURN server to listen on port 443 instead of port 3478?",
            default=port_443,
        )
        config["turnserver"]["port443"] = response


class TurnServerStep(TCPTurnStep):
    """Step to configure turn server"""

    def __init__(self) -> None:
        super().__init__("TURN Server")
        self.questions = [self._intro, self._enable_turn]
        self._media_addresses_step = MediaConferenceNodeStep()
        self._client_turn_step = ClientTurnServerStep()

    def _intro(self, _config: defaultdict) -> None:
        """Displays an intro message describing what the TURN server does"""
        self.display(
            """\
The TURN server can be used to relay media to a Conferencing Node or, when using direct media, another participant.
This is useful if the client cannot access the Conferencing Nodes directly or participants are behind a firewall.

The TURN server can either be configured using a restricted configuration mode or a permissive mode
(required for direct-media). Permissive mode configuration requires the TURN device to be deployed
externally (e.g. in a DMZ) as it allows relaying of traffic to any IP address.
"""
        )

    def _enable_turn(self, config: defaultdict) -> None:
        """Question asking user whether to enable turnserver or not"""
        web_enabled = config["enablewebloadbalance"]
        response = True  # Turnserver is enabled if web_enabled is False
        if web_enabled:
            default_enabled: bool | None = utils.config_get(
                config["turnserver"]["enabled"]
            )
            response = self.ask_yes_no("Enable TURN server?", default=default_enabled)
            config["turnserver"]["enabled"] = response

        if response:
            clientturn: bool | None = utils.config_get(
                config["turnserver"]["clientturn"]
            )
            response = self.ask_yes_no(
                "Do you want to configure TURN using the restricted configuration mode?",
                default=not clientturn,
            )
            if response is False:
                config["turnserver"]["clientturn"] = True
                self.questions = [self._run_client_turn_step]
                return
            config["turnserver"]["clientturn"] = False

            if not web_enabled:
                self.questions += [self._intro_tcp_turn, self._get_tcp_turn]
            else:
                config["turnserver"]["port443"] = False

            self.questions += [
                self._get_turn_username,
                self._get_turn_password,
                self._get_media_addresses,
            ]

    def _get_turn_username(self, config: defaultdict) -> None:
        """Question to get the turnserver username"""
        default_username = utils.config_get(config["turnserver"]["username"])
        response = self.ask("TURN username?", default=default_username)
        DEV_LOGGER.info("Response: %s", response)
        if response == "":
            raise StepError("Cannot have an empty username")
        try:
            response = saslprep(str(response))
        except ValueError as exc:
            raise StepError("Username contains an invalid character") from exc
        config["turnserver"]["username"] = response

    def _get_turn_password(self, config: defaultdict) -> None:
        """Question to get the turnserver password"""
        response = self.ask("TURN password (will be displayed onscreen)?")
        DEV_LOGGER.info("Got a response for password prompt")
        if response == "":
            raise StepError("Cannot have an empty password")
        try:
            response = saslprep(response)
        except ValueError as exc:
            raise StepError("Password contains an invalid character") from exc
        config["turnserver"]["password"] = response

    def _get_media_addresses(self, config: defaultdict) -> None:
        """Question to get the addresses to relay to"""
        self._media_addresses_step.run(
            config,
            step_id=self._step_id,
            total_steps=self._total_steps,
            print_header=False,
        )

    def _run_client_turn_step(self, config: defaultdict) -> None:
        """Run the client TURN step to step a client TURN server"""
        self._client_turn_step.run(
            config,
            step_id=self._step_id,
            total_steps=self._total_steps,
            print_header=False,
        )

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        saved_turn_config = saved_config["turnserver"]
        turn_config = config["turnserver"]

        # turnserver.enabled
        DEV_LOGGER.info("Getting turnserver.enabled")
        turn_config["enabled"] = utils.validated_config_value(
            saved_turn_config,
            "enabled",
            partial(utils.validate_type, bool),
            fallback=True,
        )

        # turnserver.clientturn
        DEV_LOGGER.info("Getting turnserver.clientturn")
        turn_config["clientturn"] = utils.validated_config_value(
            saved_turn_config,
            "clientturn",
            partial(utils.validate_type, bool),
            fallback=False,
        )

        # turnserver.port443
        DEV_LOGGER.info("Getting turnserver.port443")
        turn_config["port443"] = utils.validated_config_value(
            saved_turn_config,
            "port443",
            partial(utils.validate_type, bool),
            fallback=False,
        )

        # turnserver.username
        DEV_LOGGER.info("Getting turnserver.username")
        turn_config["username"] = utils.validated_config_value(
            saved_turn_config, "username", partial(utils.validate_type, str)
        )
        if not turn_config["enabled"] and turn_config["username"] is None:
            # Username is not a required field if turnserver is disabled
            turn_config.pop("username", None)
        elif turn_config["clientturn"] and turn_config["username"] is None:
            # Username is not a required field if clientturn is enabled
            turn_config.pop("username", None)

        # turnserver.password
        DEV_LOGGER.info("Getting turnserver.password")
        turn_config["password"] = utils.validated_config_value(
            saved_turn_config,
            "password",
            partial(utils.validate_type, str),
            log_values=False,
        )
        if not turn_config["enabled"] and turn_config["password"] is None:
            # Password is not a required field if turnserver is disabled
            turn_config.pop("password", None)
        elif turn_config["clientturn"] and turn_config["password"] is None:
            # Password is not a required field if clientturn is enabled
            turn_config.pop("password", None)

        self._media_addresses_step.default_config(saved_config, config)
        self._client_turn_step.default_config(saved_config, config)


class MediaConferenceNodeStep(MultiStep):
    """Step to set the conference node ip addresses"""

    def __init__(self) -> None:
        super().__init__("IP Address of Media Conferencing Nodes", "medianodes")

    def _use_default(self, config: defaultdict) -> None:
        if not config["medianodes"]:
            config["medianodes"] = config["conferencenodes"]
        super()._use_default(config)

    def validate(self, response: str) -> IPv4Address:
        DEV_LOGGER.info("Response: %s", response)
        return utils.validate_ip(response)

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        DEV_LOGGER.info("Getting from saved_config: medianodes")
        config["medianodes"] = utils.validated_config_value(
            saved_config, "medianodes", self.validate, value_list=True
        )


class ClientTurnServerStep(TCPTurnStep):
    """Step for asking questions to set up a Client TURN Server"""

    def __init__(self) -> None:
        super().__init__("Client TURN Server")
        self.questions = [
            self._intro,
            self._intro_tcp_turn,
            self._get_tcp_turn,
            self._get_turn_shared_secret,
        ]

    def _intro(self, _config: defaultdict) -> None:
        """Intro to Client Turn Server"""
        self.display(
            """\
Setup a permissive TURN Server. This is useful when using direct media to allow participants behind strict firewalls to
make calls to other participants. This is should only be enabled on external public TURN Servers as any IP Address
will be allowed to connect. A TURN secret key must also be used for authentication instead of a username+password
            """
        )

    def _get_turn_shared_secret(self, config: defaultdict) -> None:
        """Question to get or generate the turnsever secret key"""
        response = self.ask(
            "TURN secret key: If left blank a key will be generated (will be displayed onscreen)?"
        )
        if response == "":
            self.display("Generating a secure key...")
            # RP turn is not FIPs validated so os.urandom is sufficient
            response = base64.b64encode(os.urandom(32)).strip(b"=").decode("ascii")
            self.display(response)
        try:
            response = saslprep(str(response))
        except ValueError as exc:
            raise StepError("Shared secret contains an invalid character") from exc
        config["turnserver"]["sharedsecret"] = response

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        saved_turn_config = saved_config["turnserver"]
        turn_config = config["turnserver"]

        DEV_LOGGER.info("Getting turnserver.sharedsecret")
        turn_config["sharedsecret"] = utils.validated_config_value(
            saved_turn_config,
            "sharedsecret",
            partial(utils.validate_type, str),
            log_values=False,
        )
        if not turn_config["clientturn"] and turn_config["sharedsecret"] is None:
            # sharedsecret is not a required field if clientturn is disabled
            turn_config.pop("sharedsecret", None)
