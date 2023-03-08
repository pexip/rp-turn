"""
Tests the NetworkStep from the installwizard
"""
# pylint: disable=too-many-instance-attributes

# Standard library imports
import copy
import subprocess
from functools import partial

# 3rd party imports
from unittest import mock
import si.apps.reverseproxy.tests.utils as test_utils
from unittest.mock import patch

# Local application/library specific imports
import si.apps.reverseproxy.tests.steps as tests
from si.apps.reverseproxy import steps

STEPCLASS = partial(
    steps.NetworkStep,
    nic_name="nic",
    nic_mac="00:11:22:33:44:55:66",
    is_external=True,
    is_internal=True,
)


class TestGetIPAddressQuestion(tests.TestQuestion, tests.TestDefaultConfig):
    """Test the _get_ip_address question from the NetworkStep"""

    def setUp(self):
        tests.TestQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._saved_state_id = "ipaddress"
        self._state_id = ["networks", "nic", "ipaddress"]
        self._question = "_get_ip_address"
        self._question_default_config = "_default_ipaddress"
        self._valid_cases = test_utils.VALID_IP_ADDRESSES
        self._invalid_cases = test_utils.INVALID_IP_ADDRESSES


class TestGetNetmaskQuestion(tests.TestQuestion, tests.TestDefaultConfig):
    """Test the _get_netmask question from the NetworkStep"""

    def setUp(self):
        tests.TestQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._config = {"networks": {"nic": {"ipaddress": "10.44.0.2"}}}
        self._step = STEPCLASS
        self._saved_state_id = "netmask"
        self._state_id = ["networks", "nic", "netmask"]
        self._question = "_get_netmask"
        self._question_default_config = "_default_netmask"
        self._valid_cases = []
        self._invalid_cases = test_utils.INVALID_IP_ADDRESSES + ["3.0.255.3"]

    def test_valid_cases(self):
        cases = test_utils.VALID_NETMASKS
        for index, (case, _) in enumerate(cases):
            question, config, _ = self.setup_question(case)
            ip_address = test_utils.VALID_IP_ADDRESSES[
                index % len(test_utils.VALID_IP_ADDRESSES)
            ]
            config["networks"]["nic"]["ipaddress"] = ip_address
            question(config)
            self.assertEqual(self.get_config_value(config), case)

    def test_valid_cases_with_padding(self):
        cases = test_utils.VALID_NETMASKS
        for index, (case, _) in enumerate(cases):
            padded_case = "     " + case + "     "
            question, config, _ = self.setup_question(padded_case)
            ip_address = test_utils.VALID_IP_ADDRESSES[
                index % len(test_utils.VALID_IP_ADDRESSES)
            ]
            config["networks"]["nic"]["ipaddress"] = ip_address
            question(config)
            self.assertEqual(self.get_config_value(config), case)


class TestGetGatewayQuestion(tests.TestQuestion, tests.TestDefaultConfig):
    """Test the _get_gateway question from the NetworkStep"""

    def setUp(self):
        tests.TestQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._saved_state_id = "gateway"
        self._state_id = ["networks", "nic", "gateway"]
        self._question = "_get_gateway"
        self._question_default_config = "_default_gateway"
        self._valid_cases = test_utils.VALID_IP_ADDRESSES
        self._invalid_cases = test_utils.INVALID_IP_ADDRESSES


class TestDHCPConfigIPAddressNetmask(tests.TestDefaultConfig):
    """Tests getting ip address and netmask from dhcp"""

    def setUp(self):
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._question = "_default_dhcp_ipaddress_netmask"

    def test_default_config_valid_cases(self):
        for index, (ipaddress, (netmask, cidr)) in enumerate(
            zip(test_utils.VALID_IP_ADDRESSES, test_utils.VALID_NETMASKS)
        ):
            nic_name = "nic{}".format(index)
            subprocess_check_output_mock = mock.MagicMock()
            subprocess_check_output_mock.return_value = """\
2: {nic_name}: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1492 qdisc fq_codel state UP group default qlen 1000
    link/ether 01:23:45:67:89:10 brd ff:ff:ff:ff:ff:ff
    inet {ipaddress}{cidr} brd 10.20.255.255 scope global dynamic noprefixroute {nic_name}
       valid_lft 79342sec preferred_lft 79342sec
    inet6 fd00::abc:defa:bcde:fabc/64 scope global temporary dynamic
       valid_lft 86400sec preferred_lft 14400sec
    inet6 fd00::012:3456:7890:1234/64 scope global dynamic mngtmpaddr noprefixroute
       valid_lft 86400sec preferred_lft 14400sec
    inet6 ff80::aaaa:bbbb:cccc:ddd/64 scope link noprefixroute
       valid_lft forever preferred_lft forever
""".format(
                nic_name=nic_name, ipaddress=ipaddress, cidr=cidr
            )
            with patch.object(
                subprocess, "check_output", subprocess_check_output_mock, create=True
            ):
                question, config, step = self.setup_question("")
                step.nic_name = nic_name
                question(config)
                nic_config = config["networks"][nic_name]
                self.assertEqual(nic_config["ipaddress"], ipaddress)
                self.assertEqual(nic_config["netmask"], netmask)


class TestDHCPConfigGateway(tests.TestDefaultConfig):
    """Tests getting gateway from DHCP"""

    def setUp(self):
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._question = "_default_dhcp_gateway"

    def test_default_config_valid_cases(self):
        valid_gateways = copy.deepcopy(test_utils.VALID_IP_ADDRESSES)
        valid_gateways.reverse()
        for index, (ipaddress, gateway) in enumerate(
            zip(test_utils.VALID_IP_ADDRESSES, valid_gateways)
        ):
            nic_name = "nic{}".format(index)
            subprocess_check_output_mock = mock.MagicMock()
            subprocess_check_output_mock.return_value = """\
default via {gateway} proto dhcp metric 100
10.44.0.0/16 proto kernel scope link src {ipaddress} metric 100
169.254.0.0/16 scope link metric 1000
""".format(
                ipaddress=ipaddress, gateway=gateway
            )
            with patch.object(
                subprocess, "check_output", subprocess_check_output_mock, create=True
            ):
                question, config, step = self.setup_question("")
                step.nic_name = nic_name
                question(config)
                self.assertEqual(config["networks"][nic_name]["gateway"], gateway)
