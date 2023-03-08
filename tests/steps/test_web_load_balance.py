"""
Tests the Web Load Balance Step from the installwizard
"""
# pylint: disable=too-many-ancestors

# Import steps and default cases
import si.apps.reverseproxy.tests.steps as tests

# Local application/library specific imports
import si.apps.reverseproxy.tests.utils as test_utils
from si.apps.reverseproxy import steps


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


class TestGetSignalingConfNode(tests.TestMultiQuestion, tests.TestMultiDefaultConfig):
    """Test the SignalingConferenceNodeStep"""

    def setUp(self):
        tests.TestMultiQuestion.setUp(self)
        tests.TestMultiDefaultConfig.setUp(self)
        self._step = steps.SignalingConferenceNodeStep
        self._state_id = "conferencenodes"
        self._question = "_get_another_answer"
        self._valid_cases = test_utils.VALID_IP_ADDRESSES
        self._invalid_cases = (
            test_utils.INVALID_IP_ADDRESSES
            + test_utils.INVALID_DOMAINS
            + test_utils.VALID_DOMAIN_NAMES
        )


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
