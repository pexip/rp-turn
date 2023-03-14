"""
Tests the IPTablesStep from the installwizard
"""

# Standard library imports
import itertools

# 3rd party imports
from unittest import mock

# Local application/library specific imports
import rp_turn.tests.steps as tests
import rp_turn.tests.utils as test_utils
from rp_turn import steps, utils
from rp_turn.step_error import StepError

STEPCLASS = steps.ManagementStep


class TestGetManagementNetworks(tests.TestMultiQuestion):
    """Test the IPTablesStep"""

    def setUp(self):
        self._step = STEPCLASS
        self._state_id = "managementnetworks"
        self._question = "_get_network_ip_address"
        self._valid_cases = list(
            itertools.product(test_utils.VALID_IP_ADDRESSES, test_utils.VALID_NETMASKS)
        )
        self._invalid_cases = (
            test_utils.pair(test_utils.INVALID_IP_ADDRESSES)
            + test_utils.pair(test_utils.INVALID_DOMAINS)
            + test_utils.pair(test_utils.INVALID_IP_ADDRESSES)
            + test_utils.pair(test_utils.INVALID_DOMAINS)
        )

    def setup_step(self):
        """Sets up a step by mocking display"""
        step = self._step()
        config = utils.nested_dict()
        step.display = mock.Mock(return_value=None)
        return step, config

    @staticmethod
    def _ask(step, config, ip_address, netmask):
        """Mocks ask method to fake user input"""
        # Get IP Address
        step.ask = mock.Mock(return_value=ip_address)
        getattr(step, "_get_network_ip_address")(config)
        # Get Netmask
        step.ask = mock.Mock(return_value=netmask)
        getattr(step, "_get_network_netmask")(config)

    @staticmethod
    def _end_input(step, config):
        """Mocks the end of user input"""
        # End Input
        step.ask = mock.Mock(return_value="no")
        getattr(step, "_add_management_network")(config)

    def test_valid_cases_singular(self):
        for ip_address, (netmask, cidr) in self._valid_cases:
            step, config = self.setup_step()
            self._ask(step, config, ip_address, netmask)
            self._end_input(step, config)
            # Verify Config
            self.assertEqual(self.get_config_value(config), [ip_address + cidr])

    def test_valid_cases_singular_with_padding(self):
        for ip_address, (netmask, cidr) in self._valid_cases:
            step, config = self.setup_step()
            self._ask(
                step,
                config,
                "      " + ip_address + "      ",
                "      " + netmask + "      ",
            )
            self._end_input(step, config)
            # Verify Config
            self.assertEqual(self.get_config_value(config), [ip_address + cidr])

    def test_valid_cases(self):
        valid_multi_cases = test_utils.make_multi_cases(self._valid_cases, 3)
        for case in valid_multi_cases:
            step, config = self.setup_step()
            expected_value = []
            for ip_address, (netmask, cidr) in case:
                self._ask(step, config, ip_address, netmask)
                expected_value.append(ip_address + cidr)
            self._end_input(step, config)
            # Verify Config
            self.assertEqual(set(self.get_config_value(config)), set(expected_value))

    def test_valid_cases_with_padding(self):
        valid_multi_cases = test_utils.make_multi_cases(self._valid_cases, 3)
        for case in valid_multi_cases:
            step, config = self.setup_step()
            expected_value = []
            for ip_address, (netmask, cidr) in case:
                self._ask(
                    step,
                    config,
                    "      " + ip_address + "      ",
                    "      " + netmask + "      ",
                )
                expected_value.append(ip_address + cidr)
            self._end_input(step, config)
            # Verify Config
            self.assertEqual(set(self.get_config_value(config)), set(expected_value))

    def test_invalid_cases(self):
        for ip_address, netmask in self._invalid_cases:
            step, config = self.setup_step()
            self.assertRaises(StepError, self._ask, step, config, ip_address, netmask)

    def test_invalid_cases_after_valid_cases(self):
        valid_multi_cases = test_utils.make_multi_cases(self._valid_cases, 2)
        for invalid_ip, invalid_netmask in self._invalid_cases:
            step, config = self.setup_step()
            for case in valid_multi_cases:
                for ip_address, (netmask, _) in case:
                    self._ask(step, config, ip_address, netmask)
                self.assertRaises(
                    StepError, self._ask, step, config, invalid_ip, invalid_netmask
                )


class TestDefaultManagementNetworks(tests.TestMultiDefaultConfig):
    """Tests the managementnetworks field from default_config"""

    def setUp(self):
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = "managementnetworks"
        self._valid_cases = ["10.0.0.0/8", "10.44.0.0/16", "1.2.3.4/32"]
        self._invalid_cases = (
            ["10.0.0.0/33"]
            + test_utils.INVALID_IP_ADDRESSES
            + test_utils.INVALID_DOMAINS
            + test_utils.UNREACHABLE_IP_ADDRESSES
        )
