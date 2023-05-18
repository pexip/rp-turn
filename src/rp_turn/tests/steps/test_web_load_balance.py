"""
Tests the Web Load Balance Step from the installwizard
"""
from __future__ import annotations

from collections import defaultdict

# Import steps and default cases
import rp_turn.tests.steps as tests

# Local application/library specific imports
import rp_turn.tests.utils as test_utils
from rp_turn import steps
from rp_turn.steps import base_step
from rp_turn.steps.web_load_balance import AddressType


class TestEnableWebLoadBalance(tests.TestYesNoQuestion, tests.TestDefaultConfig):
    """Test the WebLoadBalanceStep"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = steps.WebLoadBalanceStep
        self._state_id = "enablewebloadbalance"
        self._question = "_enable_web_load_balance"
        self._valid_cases = [True, False]
        self._invalid_cases = test_utils.VALID_IP_ADDRESSES + test_utils.VALID_HOSTNAMES


class TestGetSignalingConfNodeIPAddress(
    tests.TestMultiQuestion, tests.TestMultiDefaultConfig
):
    """Test the SignalingConferenceNodeStep with IP addresses"""

    def setUp(self):
        tests.TestMultiQuestion.setUp(self)
        tests.TestMultiDefaultConfig.setUp(self)
        self._step = self.make_step
        self._state_id = "conferencenodes"
        self._question = "_get_another_answer"
        self._valid_cases = test_utils.VALID_IP_ADDRESSES
        self._invalid_cases = (
            test_utils.INVALID_IP_ADDRESSES + test_utils.VALID_DOMAIN_NAMES
        )

    def validate_additional_config(
        self, step: base_step.Step, config: defaultdict, success: bool
    ) -> None:
        if success and self._testMethodName != "test_default_config_valid_cases":
            self.assertIs(config["verify_upstream_tls"], False)

    def make_step(self) -> steps.SignalingConferenceNodeStep:
        """Make the step and force IP addresses"""
        step = steps.SignalingConferenceNodeStep()
        step._address_type = AddressType.IP_ADDRESS  # pylint: disable=protected-access
        return step

    # TODO: add test to ensure all values are of the same type


class TestGetSignalingConfNodeFQDNs(
    tests.TestMultiQuestion, tests.TestMultiDefaultConfig
):
    """Test the SignalingConferenceNodeStep with IP addresses"""

    def setUp(self):
        tests.TestMultiQuestion.setUp(self)
        tests.TestMultiDefaultConfig.setUp(self)
        self._step = self.make_step
        self._state_id = "conferencenodes"
        self._question = "_get_another_answer"
        self._valid_cases = test_utils.VALID_DOMAIN_NAMES
        self._invalid_cases = test_utils.VALID_IP_ADDRESSES + test_utils.INVALID_DOMAINS

    def validate_additional_config(
        self, step: base_step.Step, config: defaultdict, success: bool
    ) -> None:
        if success and self._testMethodName != "test_default_config_valid_cases":
            self.assertIs(config["verify_upstream_tls"], True)
        else:
            # either step wasn't successful, or it's loading the default_config
            # verify_upstream_tls must not be defined in the config
            self.assertNotIn("verify_upstream_tls", config)

    def make_step(self) -> steps.SignalingConferenceNodeStep:
        """Make the step and force FQDNs"""
        step = steps.SignalingConferenceNodeStep()
        step._address_type = AddressType.FQDN  # pylint: disable=protected-access
        return step


class TestContentSecurityPolicy(tests.TestYesNoQuestion, tests.TestDefaultConfig):
    """Test the ContentSecurityPolicyStep"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = steps.ContentSecurityPolicyStep
        self._state_id = "enablecsp"
        self._question = "_enable_csp"
        self._valid_cases = [True, False]
        self._invalid_cases = test_utils.VALID_IP_ADDRESSES + test_utils.VALID_HOSTNAMES
