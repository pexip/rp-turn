"""
Pexip installation wizard.
"""

from __future__ import annotations

# Standard library imports
import argparse
import copy
import itertools
import json
import logging.handlers
import os
import signal
import sys
import time
from collections import defaultdict
from functools import partial
from typing import Any, Generator

from rp_turn import steps, utils
from rp_turn.config_applicator import ConfigApplicator

DEV_LOGGER = logging.getLogger("rp_turn.installwizard")


class InstallWizard:
    """
    Installation wizard.
    """

    def __init__(
        self,
        skip_ui: bool = False,
        skip_apply: bool = True,
        config_file_path: str | None = None,
        verify_json: bool = False,
    ) -> None:
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-branches
        # Must verify the JSON file if we are skipping UI
        if skip_ui:
            verify_json = True

        # Initialise variables
        self._config_file_path = os.getenv("HOME", "~") + "/.reverseproxy-config.json"
        if config_file_path:
            self._config_file_path = config_file_path
        self._step_num = 0
        self._skip_ui = skip_ui
        self._skip_apply = skip_apply
        self._steps: list[steps.Step] = []
        self._next_steps: list[steps.Step] = (
            []
        )  # A list used to add additional steps after the current step
        DEV_LOGGER.info("Using config path: %s", self._config_file_path)

        # Load saved_config from file and create an empty config to fill
        self._config = utils.nested_dict()
        saved_config = self._load_saved_config(exit_on_invalid_json=verify_json)
        first_run = False
        if saved_config is None:
            first_run = True
            saved_config = utils.nested_dict()
        # Used the first_run value from the config if it is available
        saved_first_run = utils.validated_config_value(
            saved_config, "first_run", partial(utils.validate_type, bool)
        )
        if saved_first_run:
            first_run = saved_first_run
        saved_config["first_run"] = first_run
        self._config["first_run"] = first_run

        # Find all network interfaces
        self.__nics: list[tuple[str, str]] | None = None  # caching
        nics = self._get_attached_nics()

        # Add nic dependent steps to the wizard
        if len(nics) == 1:
            (nic_name, nic_mac) = nics[0]
            DEV_LOGGER.info(
                "Only found %s (%s). Skipping Dual NIC Step", nic_name, nic_mac
            )
            self._config["internal"] = nic_name
            self._config["external"] = nic_name
            self._steps.append(
                steps.NetworkStep(
                    nic_name, nic_mac, is_external=True, is_internal=True, nic_str=""
                )
            )
            DEV_LOGGER.info("Using internal and external interface as: %s", nic_name)
        else:
            DEV_LOGGER.info("Found %s NICs. Adding DualNicStep", len(nics))
            self._steps.append(steps.DualNicStep(self, nics))

        # Add mandatory steps to the wizard
        DEV_LOGGER.info("Adding Mandatory Steps")
        self._steps += [
            steps.DNSStep(),
            steps.HostnameStep(),
            steps.NTPStep(),
            steps.WebLoadBalanceStep(),
            steps.TurnServerStep(),
            steps.ManagementStep(),
            steps.Fail2BanStep(),
            steps.SNMPStep(),
        ]
        DEV_LOGGER.info("Added Mandatory Steps")

        # Let each step validate the saved_config and copy valid values into self._config
        DEV_LOGGER.info("Validating saved_config")
        if len(nics) > 1:
            # Want to load the config, but these steps aren't added until DualNicStep is run
            for nic_name, nic_mac in nics:
                DEV_LOGGER.info(
                    "Creating special NetworkStep(%s, %s) to validate saved_config",
                    nic_name,
                    nic_mac,
                )
                temp_step = steps.NetworkStep(
                    nic_name, nic_mac, is_external=True, is_internal=True
                )
                temp_step.default_config(saved_config, self._config)
        for step in self._steps:
            step.default_config(saved_config, self._config)
        certs_step = steps.CertificatesStep()
        certs_step.default_config(saved_config, self._config)

        # If first_run is False, we need to really check that this is the case (especially for skip_ui cases)
        # The first run should always regenerate certificates (otherwise man-in-the-middle attacks are possible)
        # If the saved_config was valid (i.e. was not changed by the steps), then I'll allow first_run to be False
        if not first_run and skip_ui:
            config_diff = self._config_diff(exit_on_invalid_json=verify_json)
            if any(config_diff):
                DEV_LOGGER.info(
                    "first_run set to True as the config had differences: %s",
                    config_diff,
                )
                first_run = True

        if first_run:
            self._config["generate-certs"]["ssl"] = True
            self._config["generate-certs"]["ssh"] = True
        else:
            DEV_LOGGER.info("Adding CertificatesSteps")
            self._steps.append(certs_step)
        self._config["first_run"] = first_run

    def _get_attached_nics(self) -> list[tuple[str, str]]:
        """
        Gets the nic names and mac addresses of attached network interfaces
        Ignores the lo interface
        Prints error and exits if there are no NICs attached
        """
        if self.__nics:
            return self.__nics

        net_dir = "/sys/class/net/"
        interface_names = os.listdir(net_dir)
        if "lo" in interface_names:
            interface_names.remove("lo")  # Don't want the local loopback
        DEV_LOGGER.info("Found network interfaces: %s", interface_names)
        nics = []
        for nic_name in interface_names:
            try:
                with open(
                    net_dir + nic_name + "/address", "r", encoding="utf-8"
                ) as file_obj:
                    nic_mac = file_obj.read()[:-1]  # Remove trailing newline
                DEV_LOGGER.info("%s mac address: %s", nic_name, nic_mac)
                nics.append((str(nic_name), str(nic_mac)))
            except (IOError, ValueError):
                DEV_LOGGER.exception("Unable to get mac address for %s", nic_name)

        if not nics:  # has no nics attached, abort!
            DEV_LOGGER.error("No NICs found. Aborting")
            print(
                """\
            No network interfaces have been detected.
            Please shutdown the VM and attach at least one network device
            """
            )
            sys.exit(1)
        self.__nics = nics
        return nics

    def _load_saved_config(
        self, exit_on_invalid_json: bool = True
    ) -> defaultdict | None:
        """
        Loads the saved_config from file and converts to a nested dictionary
        Returns None if file is missing
        Prints error message and exits if JSON file is unparsable
        """
        try:
            with open(self._config_file_path, encoding="utf-8") as file_obj:
                saved_config_raw = json.load(file_obj)
            saved_config: defaultdict = utils.make_nested_dict(saved_config_raw)
            DEV_LOGGER.info("Loaded saved_config: %s", saved_config)
            return saved_config
        except IOError:
            # Saved config file does not exist
            DEV_LOGGER.info("Config file does not exist. Assuming it is the first run")
        except ValueError as error:
            # Saved config file is invalid
            DEV_LOGGER.exception("Config file is invalid")
            if exit_on_invalid_json:
                print(f"{self._config_file_path} is not a valid JSON file")
                print(str(error))
                sys.exit(1)
        return None

    def _gather_user_input(self) -> None:
        """Loops through all the steps calling each run method with a shared config dictionary"""
        # NOTE: Steps can be added part way through so we cannot iterate over self._steps collection
        while self._step_num < len(self._steps):
            if self._step_num > 0:
                # Leave spacing between steps
                print("\n\n")
            step = self._steps[self._step_num]  # arrays start at 0
            step_id = self._step_num + 1  # step_id starts at 1
            total_steps = len(self._steps)
            DEV_LOGGER.info(
                "Step %s/%s: %s", step_id, total_steps, step.__class__.__name__
            )
            step.run(self._config, step_id=step_id, total_steps=total_steps)
            self._insert_next_steps()
            self._step_num += 1

    def _insert_next_steps(self) -> None:
        """Append list of _next_steps into _steps, keeping the same order"""
        self._next_steps.reverse()
        for additional_step in self._next_steps:
            self._steps.insert(self._step_num + 1, additional_step)
        self._next_steps = []

    def add_next_step(self, step: steps.Step) -> None:
        """Adds a step to the list of steps that should be run next"""
        self._next_steps.append(step)

    def _save_user_config(self) -> None:
        """Redacts some fields from the config and saves as a JSON file"""
        try:
            # Some parts of the config should not be saved
            # Redact fields here
            config_saveable = copy.deepcopy(self._config)
            config_saveable["turnserver"].pop("password", None)
            config_saveable["turnserver"].pop("sharedsecret", None)
            config_saveable.pop("first_run", None)
            DEV_LOGGER.info("Attempting to save config_saveable: %s", config_saveable)

            # Save the redacted config
            with open(self._config_file_path, "w", encoding="utf-8") as file_obj:
                json.dump(config_saveable, file_obj, indent=4, sort_keys=True)
            DEV_LOGGER.info("Saved config at: %s", self._config_file_path)
        except (IOError, ValueError) as error:
            DEV_LOGGER.exception("Unable to save config")
            print("Unable to save config: " + str(error))

    def _dict_diff(
        self, path: list[str], saved_config: defaultdict, config: defaultdict
    ) -> list[tuple[list[str], str]]:
        """Works out the differences between two dictionaries"""
        output = []
        for key in set(itertools.chain(saved_config.keys(), config.keys())):
            new_path = path + [key]
            human_path = ".".join([str(path) for path in new_path])
            if key not in saved_config:
                # Required key is missing from saved_config
                output.append((new_path, f"{human_path} is a required key"))
            elif key not in config:
                # Included key is not known to the application
                output.append((new_path, f"{human_path} is an unknown key"))
            elif isinstance(saved_config[key], dict) and isinstance(config[key], dict):
                # Check for diffs in the next level of dictionary
                output += self._dict_diff(new_path, saved_config[key], config[key])
            elif saved_config[key] != config[key]:
                output.append(
                    (
                        new_path,
                        f"{human_path} has invalid value {saved_config[key]}",
                    )
                )
        return output

    def _config_diff(
        self, exit_on_invalid_json: bool = True
    ) -> Generator[tuple[list[str], str], None, None]:
        """Works out the difference between the saved_config and self._config"""
        # Load the saved_config from file again
        saved_config = self._load_saved_config(
            exit_on_invalid_json=exit_on_invalid_json
        )
        if saved_config is None:
            print(f"No config saved at {self._config_file_path}\nAborting")
            DEV_LOGGER.info("No saved_config when trying to skip ui")
            sys.exit(1)

        # Find all the differences between the file and self._config
        differences = self._dict_diff([], saved_config, self._config)

        # Some differences are acceptable, so ignore those
        acceptable_differences = [["first_run"]]
        for nic_name, _nic_mac in self._get_attached_nics():
            # if a new nic is added to the box, but the config doesn't use it, then it doesn't need to be defined
            if nic_name not in (
                saved_config.get("external", None),
                saved_config.get("internal", None),
            ):
                acceptable_differences.append(["networks", nic_name])

        return (
            (path_reason, string_reason)
            for path_reason, string_reason in differences
            if path_reason not in acceptable_differences
        )

    def _apply_user_config(self) -> None:
        """Applies a configuration to the system"""
        if self._skip_ui:
            # We skipped the user input, so we need to check that the saved_config had all the required fields
            # And that it was not modified by a step (otherwise the user would be very confused).
            differences = list(self._config_diff())
            # If there are any differences left, print an error to the user
            if differences:
                print(f"Config saved at {self._config_file_path} was invalid:")
                for _path, reason in differences:
                    print("  - " + reason)
                print("Aborting!")
                sys.exit(1)
        # Apply the configuration to the system
        ConfigApplicator(self._config).apply()

    def run(self) -> None:
        """Runs the installwizard"""
        if not self._skip_ui:
            DEV_LOGGER.info("Going through UI")
            os.system("/usr/bin/clear")
            print(
                """\
==========================================================
|   Pexip Reverse Proxy and TURN Server Install Wizard   |"""
            )
            self._gather_user_input()
            self._save_user_config()
        if not self._skip_apply:
            DEV_LOGGER.info("Going through apply")
            self._apply_user_config()
            reboot()


def reboot() -> None:
    """Reboot the system"""
    print()
    print("Rebooting.")
    print()
    DEV_LOGGER.info("Rebooting VM")
    time.sleep(5)
    os.system("/sbin/reboot")
    print("\r\nSystem going down for reboot\r\n")


def setup_logger(debug: bool = False, dev_log: bool = True) -> None:
    """Sets up the dev logger to output to /dev/log (and optionally stdout)"""
    # Setup logging
    format_pattern = " ".join(
        (
            "%(asctime)-15s",
            'Level="%(levelname)s"',
            'Pid="%(process)d"',
            'Module="%(module)s"',
            'Function="%(funcName)s"',
            'Filename="%(filename)s"',
            'LineNumber="%(lineno)s"',
            "%(message)s",
        )
    )
    formatter = logging.Formatter(format_pattern)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if dev_log:
        syslog_handler = logging.handlers.SysLogHandler(address="/dev/log")
        syslog_handler.setFormatter(formatter)
        logger.addHandler(syslog_handler)

    if debug:
        # Also send log to stdout
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(formatter)
        logger.addHandler(stdout_handler)


def main() -> None:
    """Execute installation wizard."""

    def on_ctrlc(_one: Any, _two: Any) -> None:
        """SIGINT/Ctrl-C handler to exit gracefully on Ctrl-C"""
        sys.exit(-1)

    signal.signal(signal.SIGINT, on_ctrlc)

    parser = argparse.ArgumentParser(description="Configures Pexip Reverse Proxy")
    parser.add_argument(
        "--skip-apply",
        action="store_const",
        const=True,
        default=False,
        help="does not apply the config at the end (default: %(default)s)",
    )
    parser.add_argument(
        "--skip-ui",
        action="store_const",
        const=True,
        default=False,
        help="does not request user input (default: %(default)s)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="specify a different path to store/read the config (default: %(default)s)",
    )
    parser.add_argument(
        "--debug",
        action="store_const",
        const=True,
        default=False,
        help="prints debug to stdout (default: %(default)s)",
    )
    parser.add_argument(
        "--verify-json",
        action="store_const",
        const=True,
        default=False,
        help="exits if the config file is not a valid JSON file (default: %(default)s)",
    )
    args = parser.parse_args()

    # Setup logging
    setup_logger(debug=args.debug)

    DEV_LOGGER.info("Running InstallWizard with %s", sys.argv)
    try:
        wizard = InstallWizard(
            skip_ui=args.skip_ui,
            skip_apply=args.skip_apply,
            config_file_path=args.config,
            verify_json=args.verify_json,
        )
        wizard.run()
    except Exception as error:  # pylint: disable=broad-except
        print("Unexpected error: " + str(error))
        DEV_LOGGER.exception("Unexpected error took the whole program out")


if __name__ == "__main__":
    main()
