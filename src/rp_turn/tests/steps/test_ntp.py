"""
Tests the NTPServerStep from the installwizard
"""

# Local application/library specific imports
import rp_turn.tests.steps as tests
import rp_turn.tests.utils as test_utils
from rp_turn import steps


class TestGetNTP(tests.TestMultiQuestion, tests.TestMultiDefaultConfig):
    """Test the NTPServerStep"""

    def setUp(self):
        tests.TestMultiQuestion.setUp(self)
        tests.TestMultiDefaultConfig.setUp(self)
        self._step = steps.NTPStep
        self._state_id = "ntp"
        self._valid_cases = (
            test_utils.VALID_IP_ADDRESSES + test_utils.VALID_DOMAIN_NAMES
        )
        self._invalid_cases = (
            test_utils.INVALID_DOMAINS + test_utils.UNREACHABLE_IP_ADDRESSES
        )
