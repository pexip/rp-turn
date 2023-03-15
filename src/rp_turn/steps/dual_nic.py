"""
Pexip installation wizard step to setup the turnserver
"""

from __future__ import annotations

import copy
import logging
from collections import defaultdict
from functools import partial
from typing import TYPE_CHECKING

from rp_turn import utils
from rp_turn.steps.base_step import Step, StepError
from rp_turn.steps.network import NetworkStep

if TYPE_CHECKING:
    from rp_turn.installwizard import InstallWizard

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class DualNicStep(Step):
    """Step to decide which nics to use"""

    def __init__(
        self, install_wizard: InstallWizard, nics: list[tuple[str, str]]
    ) -> None:
        super().__init__("NIC Configuration")
        self.questions = [self._intro_dual_nic, self._enable_dual_nic]
        self._install_wizard = install_wizard
        self._nics = nics
        self._all_nic_names = [nic_name for nic_name, _ in self._nics]
        self._valid_nic_names = copy.deepcopy(self._all_nic_names)
        DEV_LOGGER.info("_all_nic_names = %s", self._all_nic_names)

    def _intro_dual_nic(self, _config: defaultdict) -> None:
        """Shows list of connected nics"""
        msg = "More than one network interface has been detected:"
        for value in [nic_name + f" ({nic_mac})" for nic_name, nic_mac in self._nics]:
            msg += "\n  - " + value
        self.display(msg)

    def _enable_dual_nic(self, config: defaultdict) -> None:
        """Asks whether to enable dual nic mode"""
        if config["internal"] != "" and config["external"] != "":
            default_enabled = config["internal"] != config["external"]
        else:
            default_enabled = False
        response = self.ask_yes_no(
            "Do you want to configure Dual NIC?", default=default_enabled
        )
        if response:
            self.questions += [
                partial(self._get_nic_name, internal=True),
                partial(self._get_nic_name, external=True),
                self._save_nic_settings,
            ]
        else:
            self.questions += [
                partial(self._get_nic_name, internal=True, external=True),
                self._save_nic_settings,
            ]

    def _get_nic_name(
        self, config: defaultdict, internal: bool = False, external: bool = False
    ) -> None:
        """Chooses which nic to use"""
        DEV_LOGGER.info(
            "Getting nic name for internal=%s, external=%s", internal, external
        )
        assert (
            internal or external
        ), "Both internal and external are False. User choice would not be saved"
        # Find the nic defaults
        if internal and external:
            DEV_LOGGER.info("Single NIC")
            nic_type_str = "Which network interface should be used"
            nic_default = utils.config_get(
                config["internal"]
            )  # should be both the same
        else:
            nic_type_str = f"Which is the {'internal' if internal else 'external'}-facing network interface"
            DEV_LOGGER.info("Dual NIC: %s interface", nic_type_str)
            nic_default = utils.config_get(config[nic_type_str.lower()])
        nic_default = nic_default if nic_default in self._valid_nic_names else None

        # Only ask if we cannot work it out ourselves
        if len(self._valid_nic_names) > 1:
            DEV_LOGGER.info(
                "Could not guess what interface to use: %s", self._valid_nic_names
            )
            available_nics = ""
            for nic_name in self._valid_nic_names:
                available_nics += "/" + nic_name
            available_nics = available_nics[1:]
            ask_str = f"{nic_type_str}? ({available_nics})"
            chosen_nic_name = self.ask(ask_str, default=nic_default).strip()
        else:
            chosen_nic_name = self._valid_nic_names[0]
            self.display(f"{nic_type_str}?\n> {chosen_nic_name}")
        DEV_LOGGER.info("Response: %s", chosen_nic_name)

        # Check that the nic name is valid and has not already been chosen
        if chosen_nic_name not in self._all_nic_names:
            raise StepError("Not a valid network interface")
        if chosen_nic_name not in self._valid_nic_names:
            raise StepError("Cannot select this network interface")
        self._valid_nic_names.remove(chosen_nic_name)

        # Add to config
        if internal:
            config["internal"] = chosen_nic_name
            DEV_LOGGER.info("Set internal interface to: %s", chosen_nic_name)
        if external:
            config["external"] = chosen_nic_name
            DEV_LOGGER.info("Set external interface to: %s", chosen_nic_name)

    def _save_nic_settings(self, config: defaultdict) -> None:
        """Saves the nic settings and adds network steps for chosen nics"""

        def get_mac(chosen_nic_name: str) -> str:
            """Gets mac for chosen_nic_name"""
            return [
                nic_mac
                for nic_name, nic_mac in self._nics
                if nic_name == chosen_nic_name
            ][0]

        internal = config["internal"]
        external = config["external"]

        if internal != external:
            # Internal
            internal_mac = get_mac(internal)
            internal_network_step = NetworkStep(
                internal,
                internal_mac,
                is_external=False,
                is_internal=True,
                nic_str=" for internal interface",
            )
            self._install_wizard.add_next_step(internal_network_step)
            DEV_LOGGER.info(
                "Added NetworkStep for internal interface: %s (%s)",
                internal,
                internal_mac,
            )

            # External
            external_mac = get_mac(external)
            external_network_step = NetworkStep(
                external,
                external_mac,
                is_external=True,
                is_internal=False,
                nic_str=" for external interface",
            )
            self._install_wizard.add_next_step(external_network_step)
            DEV_LOGGER.info(
                "Added NetworkStep for external interface: %s (%s)",
                external,
                external_mac,
            )
        else:
            nic_mac = get_mac(internal)
            network_step = NetworkStep(
                internal, nic_mac, is_external=True, is_internal=True, nic_str=""
            )
            self._install_wizard.add_next_step(network_step)
            DEV_LOGGER.info(
                "Added NetworkStep for interface: %s (%s)", internal, nic_mac
            )

    def default_config(self, saved_config: defaultdict, config: defaultdict) -> None:
        internal = utils.validated_config_value(
            saved_config, "internal", partial(utils.validate_type, str)
        )
        external = utils.validated_config_value(
            saved_config, "external", partial(utils.validate_type, str)
        )
        config["internal"] = internal if internal in self._all_nic_names else None
        config["external"] = external if external in self._all_nic_names else None
        DEV_LOGGER.info(
            "Got internal interface: %s. Using %s", internal, config["internal"]
        )
        DEV_LOGGER.info(
            "Got external interface: %s. Using %s", external, config["external"]
        )
