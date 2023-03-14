# pylint: disable=protected-access
"""
Tests the RoutesStep from the installwizard
"""

# Standard library imports
import copy
from functools import partial
from ipaddress import IPv4Interface, IPv4Network

# 3rd party imports
from unittest import TestCase, mock

# Import steps and default cases
# Local application/library specific imports
import rp_turn.tests.steps as tests
import rp_turn.tests.utils as test_utils
from rp_turn import steps, utils
from rp_turn.step_error import StepError

STEPCLASS = partial(steps.RoutesStep, nic_name="nic", nic_mac="00:11:22:33:44:55:66")


class TestIntroQuestion(TestCase):
    """Tests the _intro question from the RoutesStep"""

    def setUp(self):
        self.step = STEPCLASS()
        self.step.ask = mock.Mock(return_value=None)
        self.step.display = mock.Mock(return_value=None)

    def test_intro(self):
        """Tests intro quesion removes invalid routes"""
        config = utils.nested_dict()
        nic_config = config["networks"]["nic"]
        nic_config["ipaddress"] = "10.44.5.3"
        nic_config["netmask"] = "255.255.0.0"
        routes = [
            {"to": "192.168.0.0/16", "via": "10.44.0.1"},  # Valid
            {"to": "172.0.0.0/8", "via": "1.2.3.4"},
        ]  # Invalid
        nic_config["routes"] = copy.deepcopy(routes)
        self.step._intro(config)
        self.assertEqual(nic_config["routes"], [routes[0]])


class TestGetAnotherAnswerQuestion(tests.TestYesNoQuestion):
    """Test the _get_another_answer question from the RoutesStep"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        self._step = STEPCLASS
        self._state_id = None
        self._question = "_get_another_answer"
        self._answers = [{"to": "192.168.0.0/16", "via": "10.44.0.1"}]

    def setup_question(self, case, step=None, question_str=None):
        question, config, step = tests.TestYesNoQuestion.setup_question(self, case)
        step._answers = copy.deepcopy(self._answers)
        return question, config, step

    def is_valid(self, step, config, expected):
        if expected:
            self.assertEqual(
                test_utils.question_strs(step.questions),
                [
                    "_intro",
                    "_use_default",
                    "_get_network_ip_address",
                    "_get_network_netmask",
                    "_get_via_address",
                    "_get_another_answer",
                ],
            )
        else:
            self.assertEqual(config["networks"][step.nic_name]["routes"], self._answers)


class TestGetNetworkIPAddressQuestion(tests.TestQuestion):
    """Test the _get_network_ip_address question from the RoutesStep"""

    def setUp(self):
        self._step = STEPCLASS
        self._state_id = None
        self._question = "_get_network_ip_address"
        self._valid_cases = test_utils.VALID_IP_ADDRESSES
        self._invalid_cases = test_utils.INVALID_IP_ADDRESSES

    def is_valid(self, step, config, expected):
        self.assertEqual(step._last_ip, expected)


class TestGetNetworkNetmaskQuestion(tests.TestQuestion):
    """Test the _get_network_netmask question from the RoutesStep"""

    def setUp(self):
        self._step = STEPCLASS
        self._state_id = None
        self._question = "_get_network_netmask"
        self._invalid_cases = test_utils.INVALID_IP_ADDRESSES + ["3.0.255.3"]

    def setup_question(self, case, step=None, question_str=None):
        question, config, step = tests.TestQuestion.setup_question(self, case)
        step._last_ip = "10.44.0.0"
        return question, config, step

    def test_valid_cases(self):
        cases = test_utils.VALID_NETMASKS
        for index, (case, cidr) in enumerate(cases):
            ip_address = test_utils.VALID_IP_ADDRESSES[
                index % len(test_utils.VALID_IP_ADDRESSES)
            ]
            question, config, step = self.setup_question(case)
            step._last_ip = ip_address
            question(config)
            self.assertEqual(step._last_to, IPv4Network(str(ip_address + cidr)))

    def test_valid_cases_with_padding(self):
        cases = test_utils.VALID_NETMASKS
        for index, (case, cidr) in enumerate(cases):
            padded_case = "     " + case + "     "
            ip_address = test_utils.VALID_IP_ADDRESSES[
                index % len(test_utils.VALID_IP_ADDRESSES)
            ]
            question, config, step = self.setup_question(padded_case)
            step._last_ip = ip_address
            question(config)
            self.assertEqual(step._last_to, IPv4Network(str(ip_address + cidr)))


class TestGetViaAddressQuestion(tests.TestQuestion):
    """Test the _get_via_address question from the RoutesStep"""

    def setUp(self):
        self._step = STEPCLASS
        self._state_id = None
        self._question = "_get_via_address"
        self._valid_cases = test_utils.VALID_IP_ADDRESSES
        self._invalid_cases = test_utils.INVALID_IP_ADDRESSES

    def setup_question(self, case, step=None, question_str=None):
        question, config, step = tests.TestQuestion.setup_question(self, case)
        step._last_to = IPv4Network("10.44.0.0/16")
        step._nic_interface = IPv4Interface("0.0.0.0/0")
        return question, config, step

    def is_valid(self, step, config, expected):
        self.assertIn(
            utils.make_nested_dict({"to": step._last_to.exploded, "via": expected}),
            step._answers,
        )

    def test_unreachable_via(self):
        """Tests that an unreachable via address raises a StepError"""
        unreachable = [("10.44.0.4/24", "192.168.0.1")]
        for nic_interface_str, via_str in unreachable:
            question, config, step = self.setup_question(via_str)
            step._nic_interface = IPv4Interface(str(nic_interface_str))
            self.assertRaises(StepError, question, config)


class TestDefaultRoutes(tests.TestMultiDefaultConfig):
    """Tests the routes field from default_config"""

    def setUp(self):
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["networks", "nic", "routes"]
        self._valid_cases = [
            {"to": "192.168.0.0/16", "via": "10.44.0.1"},
            {"to": "172.0.0.0/8", "via": "1.2.3.4"},
        ]
        self._invalid_cases = [
            {"to": "192.168.0.0/33", "via": "10.44.0.1"},
            {"to": "172.0.0.0/8", "via": "1.2.3sdf"},
            {"to": "192.168.0.0/16"},
            {"via": "1.2.3.4"},
            "nothing",
            True,
            6,
            {"to": "192.168.0.0/16", "via": "10.44.0.1", "junk": "junk"},
        ]
