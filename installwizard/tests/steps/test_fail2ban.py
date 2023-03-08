"""
Tests the Fail2Ban Step from the installwizard
"""

# Import steps and default cases
import si.apps.reverseproxy.tests.steps as tests

# Local application/library specific imports
import si.apps.reverseproxy.tests.utils as test_utils
from si.apps.reverseproxy import steps

STEPCLASS = steps.Fail2BanStep


class TestFail2Ban(tests.TestYesNoQuestion, tests.TestDefaultConfig):
    """Test the Fail2Ban Step"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = "enablefail2ban"
        self._question = "_enable_fail2ban"
        self._valid_cases = [True, False]
        self._invalid_cases = test_utils.VALID_IP_ADDRESSES + test_utils.VALID_HOSTNAMES
