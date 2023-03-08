"""
Test the ReverseProxy InstallWizard
"""
# pylint: disable=protected-access

# Standard library imports
from io import StringIO
import json
import logging
import os
import subprocess
import sys
import time
import copy
import twisted.trial.unittest
from functools import partial
from ipaddress import IPv4Address

# 3rd party imports
from unittest import mock
from unittest.mock import patch

# Local application/library specific imports
from si.apps.reverseproxy import steps, installwizard
from si.apps.reverseproxy.tests import utils as test_utils
from si.apps.reverseproxy.tests.test_config_applicator import VALID_CONFIGS

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


def dummy_file_contents(open_mock, saved_config, nics):
    """Fakes open/read to provide fake files"""
    filepath = open_mock.call_args_list[-1][0][0]
    if filepath == "config.json":
        if saved_config:
            try:
                return json.dumps(saved_config, indent=4, sort_keys=True)
            except TypeError:
                # saved_config was not JSON encodable
                return str(saved_config)
        else:
            raise IOError("No saved_config")
    elif filepath.startswith("/sys/class/net/"):
        file_nic_name = filepath.replace("/sys/class/net/", "").replace("/address", "")
        nic_mac = [nic_mac for nic_name, nic_mac in nics if nic_name == file_nic_name][
            0
        ]
        return nic_mac + "\n"
    else:
        raise IOError(filepath + " does not have a fake contents defined")


def dummy_cmd_contents(cmd, saved_config, nics, encoding=None):
    """Fakes subprocess.check_output"""
    # pylint: disable=unused-argument
    return ""


def step_names(wizard):
    """Returns string names of all the steps"""
    wizard._insert_next_steps()
    return [step.__class__.__name__ for step in wizard._steps]


def nic_list_add_local(nics_list):
    """Adds local interfaces to a copy of all the cases"""
    return nics_list + [nics + [("lo", "aa:bb:cc:dd:ee:ff")] for nics in nics_list]


def get_installwizard(
    saved_config=None, nics=None, skip_ui=False, skip_apply=False, verify_json=False
):
    """Creates a new installwizard instance"""
    if nics is None:
        nics = [("nic0", "00:11:22:33:44:55")]
    if saved_config is None:
        saved_config = {}
    # mock read
    open_mock = mock.MagicMock(spec=open)
    read_mock = mock.MagicMock()
    read_mock.read.side_effect = partial(
        dummy_file_contents, open_mock=open_mock, saved_config=saved_config, nics=nics
    )
    open_mock.return_value.__enter__.return_value = read_mock

    # mock print
    print_mock = mock.MagicMock()

    # mock os.listdir
    os_listdir_mock = mock.MagicMock()

    def listdir(filepath):
        """Returns a list of names of nics if the filepath is correct"""
        if filepath == "/sys/class/net/":
            return [nic_name for nic_name, _ in nics]
        return []

    os_listdir_mock.side_effect = listdir

    # mock subprocess.check_output
    subprocess_check_output_mock = mock.MagicMock()
    subprocess_check_output_mock.side_effect = partial(
        dummy_cmd_contents, saved_config=saved_config, nics=nics
    )

    # monkeypatches
    with patch.object(installwizard, "open", open_mock, create=True), patch.object(
        sys, "stdout", print_mock, create=True
    ), patch.object(steps.dns, "open", open_mock, create=True), patch.object(
        steps.hostname, "open", open_mock, create=True
    ), patch.object(
        os, "listdir", os_listdir_mock, create=True
    ), patch.object(
        subprocess, "check_output", subprocess_check_output_mock, create=True
    ):

        return installwizard.InstallWizard(
            skip_ui=skip_ui,
            skip_apply=skip_apply,
            config_file_path="config.json",
            verify_json=verify_json,
        )


class DummyStep:
    """A Dummy Step"""

    NUMTESTS = 100

    def __init__(self, testcase, i):
        self._my_testcase = testcase
        self._my_test_id = i
        self._step_id = None
        self._total_steps = None

    def run(self, config, step_id, total_steps):
        """Fakes the run method of a Step"""
        self._my_testcase.assertEqual(step_id - 1, self._my_test_id)
        self._my_testcase.assertEqual(total_steps, DummyStep.NUMTESTS)
        # Tests that same config is passed between steps
        config["testitem{}".format(self._my_test_id)] = "testvalue{}".format(
            self._my_test_id
        )
        for i in range(self._my_test_id):
            self._my_testcase.assertEqual(
                config["testitem{}".format(i)], "testvalue{}".format(i)
            )


class TestInstallWizard(twisted.trial.unittest.TestCase):
    """Tests the InstallWizard class"""

    nic_configs = {
        "nic0": {"mac": "00:11:22:33:44:55"},
        "eth0": {"mac": "ab:cd:ef:01:23:45"},
        "enxe4b97a8b645a": {"mac": "66:66:66:66:66:66"},
        "lo": {"mac": "aa:bb:cc:dd:ee:ff"},
    }
    COUNTER = 0

    def setUp(self):
        TestInstallWizard.COUNTER = 0

    def test_installwizard_first_run(self):
        """Tests first_run"""
        wizard = get_installwizard()
        self.assertTrue(wizard._config["first_run"])
        self.assertNotIn("CertificatesStep", step_names(wizard))
        self.assertTrue(wizard._config["generate-certs"]["ssl"])
        self.assertTrue(wizard._config["generate-certs"]["ssh"])

        # Second run
        for config in VALID_CONFIGS:
            wizard = get_installwizard(
                saved_config=copy.deepcopy(config), verify_json=True
            )
            self.assertFalse(wizard._config["first_run"])
            self.assertIn("CertificatesStep", step_names(wizard))

    def test_installwizard_no_nics(self):
        """Tests with no nics"""
        nics_list = nic_list_add_local([[]])
        for nics in nics_list:
            # Tried to use self.assertRaises(SystemExit) but it fails with SystemExit error....
            try:
                get_installwizard(nics=nics)
                self.fail("Did not raise SystemExit")
            except SystemExit as error:
                self.assertEqual(error.code, 1)

    def test_installwizard_one_nic(self):
        """Tests with 1 nic"""
        nics_list = nic_list_add_local(
            [
                [("nic0", "00:11:22:33:44:55")],
                [("eth0", "ab:cd:ef:01:23:45")],
                [("enxe4b97a8b645a", "66:66:66:66:66")],
            ]
        )
        for nics in nics_list:
            wizard = get_installwizard(nics=nics)
            self.assertNotIn("DualNicStep", step_names(wizard))
            self.assertEqual(step_names(wizard).count("NetworkStep"), 1)
            network_step = wizard._steps[step_names(wizard).index("NetworkStep")]
            nic_name, nic_mac = nics[0]
            self.assertEqual(network_step.nic_name, nic_name)
            self.assertEqual(network_step.nic_mac, nic_mac)

    def test_installwizard_multi_nics(self):
        """Tests with multiple nics"""
        nics_list = nic_list_add_local(
            [
                [("nic0", "00:11:22:33:44:55"), ("eth0", "ab:cd:ef:01:23:45")],
                [
                    ("nic0", "00:11:22:33:44:55"),
                    ("eth0", "ab:cd:ef:01:23:45"),
                    ("enxe4b97a8b645a", "66:66:66:66:66"),
                ],
            ]
        )
        for nics in nics_list:
            wizard = get_installwizard(nics=nics)
            self.assertIn("DualNicStep", step_names(wizard))
            self.assertNotIn("NetworkStep", step_names(wizard))

    def test_save_user_config_redacts_fields(self):
        """Tests save user config redacts the required fields"""
        json_dump_mock = mock.MagicMock()

        def json_dump(config_saveable, _, indent, sort_keys):
            """Checks redacted config"""
            self.assertEqual(indent, 4)
            self.assertTrue(sort_keys)
            self.assertNotIn("first_run", config_saveable)
            self.assertNotIn("password", config_saveable["turnserver"])

        json_dump_mock.side_effect = json_dump

        with patch.object(json, "dump", json_dump_mock, create=True):
            wizard = get_installwizard()
            wizard._config["turnserver"]["password"] = "removethispassword"
            wizard._config["first_run"] = True
            wizard._save_user_config()

    def test_save_user_config_fails(self):
        """Tests _save_user_config with an IOError"""
        json_dump_mock = mock.MagicMock()
        json_dump_mock.side_effect = IOError("Permission denied")

        with patch.object(json, "dump", json_dump_mock, create=True):
            fake_out = StringIO()
            sys.stdout = fake_out
            wizard = get_installwizard()
            wizard._save_user_config()
            sys.stdout = sys.__stdout__
            self.assertEqual(
                fake_out.getvalue(), "Unable to save config: Permission denied\n"
            )

    def test_load_saved_config_invalid_json(self):
        """Tests _load_saved_config with an invalid JSON file"""
        saved_config = IPv4Address(
            "1.2.3.4"
        )  # IPv4Address is not JSON encodable/decodable
        get_installwizard(
            verify_json=False, saved_config=saved_config
        )  # Should not raise an exception
        # Test all cases that should exit with an invalid JSON file
        self.assertRaises(
            SystemExit,
            get_installwizard,
            verify_json=True,
            skip_ui=False,
            saved_config=saved_config,
        )
        self.assertRaises(
            SystemExit,
            get_installwizard,
            verify_json=False,
            skip_ui=True,
            saved_config=saved_config,
        )
        self.assertRaises(
            SystemExit,
            get_installwizard,
            verify_json=True,
            skip_ui=True,
            saved_config=saved_config,
        )

    def test_gather_user_input(self):
        """Tests _gather_user_input"""
        fake_out = StringIO()
        sys.stdout = fake_out
        wizard = get_installwizard()
        wizard._steps = [DummyStep(self, i) for i in range(DummyStep.NUMTESTS)]
        wizard._gather_user_input()
        sys.stdout = sys.__stdout__
        self.assertEqual(wizard._step_num, DummyStep.NUMTESTS)

    def test_missing_invalid_keys_apply_user_config(self):
        """Tests _apply_user_config detects missing and invalid keys"""
        required_keys = [
            "domain",
            "dns",
            "turnserver",
            "ntp",
            "hostname",
            "snmp",
            "networks",
            "internal",
            "external",
            "conferencenodes",
            "enablecsp",
            "generate-certs",
        ]
        # Create a collection of invalid configs, each missing some keys
        multi_keys = test_utils.make_multi_cases(required_keys, 3)
        invalid_configs = []
        for multi_key in multi_keys:
            invalid_config = {}
            for key in multi_key:
                invalid_config[key] = "bad_value"
            invalid_configs.append(invalid_config)

        # Try to apply the config and check that the method complains about the right missing keys
        for invalid_config in invalid_configs:
            fake_out = StringIO()
            sys.stdout = fake_out
            wizard = get_installwizard()
            wizard._skip_ui = True
            wizard._load_saved_config = mock.Mock(return_value=invalid_config)
            self.assertRaises(SystemExit, wizard._apply_user_config)
            sys.stdout = sys.__stdout__
            output = fake_out.getvalue().split("\n")
            for required_key in required_keys:
                if required_key not in invalid_config.keys():
                    self.assertIn(
                        "  - {} is a required key".format(required_key), output
                    )
                else:
                    self.assertIn(
                        "  - {} has invalid value bad_value".format(required_key),
                        output,
                    )

    def test_unknown_keys_apply_user_config(self):
        """Tests _apply_user_config detects unknown keys"""
        required_keys = ["some", "unknown", "keys", "that are bad", 3]
        # Create a collection of invalid configs, each missing some keys
        multi_keys = test_utils.make_multi_cases(required_keys, 3)
        invalid_configs = []
        for multi_key in multi_keys:
            invalid_config = {}
            for key in multi_key:
                invalid_config[key] = "bad_value"
            invalid_configs.append(invalid_config)

            # Try to apply the config and check that the method complains about the right missing keys
            for invalid_config in invalid_configs:
                fake_out = StringIO()
                sys.stdout = fake_out
                wizard = get_installwizard()
                wizard._skip_ui = True
                wizard._load_saved_config = mock.Mock(return_value=invalid_config)
                self.assertRaises(SystemExit, wizard._apply_user_config)
                sys.stdout = sys.__stdout__
                output = fake_out.getvalue().split("\n")
                for unknown_key in invalid_config.keys():
                    self.assertIn(
                        "  - {} is an unknown key".format(unknown_key), output
                    )

    def test_run(self):
        """Tests _run method"""
        wizard = get_installwizard()
        wizard._skip_ui = False
        wizard._skip_apply = False
        wizard._gather_user_input = mock.MagicMock()
        wizard._save_user_config = mock.MagicMock()
        wizard._apply_user_config = mock.MagicMock()
        with patch.object(os, "system", mock.MagicMock(), create=True), patch.object(
            time, "sleep", mock.MagicMock(), create=True
        ):
            fake_out = StringIO()
            sys.stdout = fake_out
            wizard.run()
            sys.stdout = sys.__stdout__
            self.assertEqual(
                fake_out.getvalue(),
                """\
==========================================================
|   Pexip Reverse Proxy and TURN Server Install Wizard   |

Rebooting.

\r
System going down for reboot\r

""",
            )
