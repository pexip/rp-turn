"""
Tests the CertificatesStep from the installwizard
"""

# Import steps and default cases
import rp_turn.tests.steps as tests

# Local application/library specific imports
import rp_turn.tests.utils as test_utils
from rp_turn import steps

STEPCLASS = steps.CertificatesStep


class TestGenerateSSLQuestion(tests.TestYesNoQuestion, tests.TestDefaultConfig):
    """Tests the _generate_ssl Question in CertificatesStep"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["generate-certs", "ssl"]
        self._question = "_generate_ssl"
        self._valid_cases = [True, False]
        self._invalid_cases = test_utils.VALID_IP_ADDRESSES + test_utils.VALID_HOSTNAMES


class TestGenerateSSHQuestion(tests.TestYesNoQuestion, tests.TestDefaultConfig):
    """Tests the _generate_ssh Question in CertificatesStep"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["generate-certs", "ssh"]
        self._question = "_generate_ssh"
        self._valid_cases = [True, False]
        self._invalid_cases = test_utils.VALID_IP_ADDRESSES + test_utils.VALID_HOSTNAMES
