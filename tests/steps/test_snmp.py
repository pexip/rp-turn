"""
Tests the SNMPStep from the installwizard
"""

import si.apps.reverseproxy.tests.steps as tests
import si.apps.reverseproxy.tests.utils as test_utils
from si.apps.reverseproxy import steps

STEPCLASS = steps.SNMPStep


class TestEnableSNMPQuestion(tests.TestYesNoQuestion, tests.TestDefaultConfig):
    """Test the _enable_snmp question from the SNMPStep"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["snmp", "enabled"]
        self._question = "_enable_snmp"
        self._valid_cases = [True, False]
        self._invalid_cases = test_utils.VALID_IP_ADDRESSES + test_utils.INVALID_DOMAINS

    def is_valid(self, step, config, expected):
        tests.TestYesNoQuestion.is_valid(self, step, config, expected)
        if expected:
            self.assertEqual(
                test_utils.question_strs(step.questions),
                [
                    "_enable_snmp",
                    "_get_community",
                    "_get_location",
                    "_get_contact",
                    "_get_name",
                    "_get_description",
                ],
            )
        else:
            self.assertEqual(test_utils.question_strs(step.questions), ["_enable_snmp"])


class TestGetCommunityQuestion(tests.TestQuestion, tests.TestDefaultConfig):
    """Test the _get_community question from the SNMPStep"""

    def setUp(self):
        tests.TestQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["snmp", "community"]
        self._question = "_get_community"
        self._valid_cases = ["public", "private", "community", "default"]
        self._invalid_cases = ["abcdefghijklmnopq"]

    def test_default_empty(self):
        question, config, _ = self.setup_question("")
        question(config)  # Empty value is acceptable for this question


class TestGetLocationQuestion(tests.TestQuestion, tests.TestDefaultConfig):
    """Test the _get_location question from the SNMPStep"""

    def setUp(self):
        tests.TestQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["snmp", "location"]
        self._question = "_get_location"
        self._valid_cases = map(str, ["home", "work", "uk", "oslo"])
        self._invalid_cases = (
            []
        )  # Question contains no validation, so everything is valid

    def test_default_empty(self):
        question, config, _ = self.setup_question("")
        question(config)  # Empty value is acceptable for this question


class TestGetContactQuestion(tests.TestQuestion, tests.TestDefaultConfig):
    """Test the _get_location question from the SNMPStep"""

    def setUp(self):
        tests.TestQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["snmp", "contact"]
        self._question = "_get_contact"
        self._valid_cases = ["a@b.com", "administrator", "admin@pexip.com"]
        self._invalid_cases = (
            []
        )  # Question contains no validation, so everything is valid

    def test_default_empty(self):
        question, config, _ = self.setup_question("")
        question(config)  # Empty value is acceptable for this question


class TestGetNameQuestion(tests.TestQuestion, tests.TestDefaultConfig):
    """Test the _get_name question from the SNMPStep"""

    def setUp(self):
        tests.TestQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["snmp", "name"]
        self._question = "_get_name"
        self._valid_cases = map(str, ["alice bob", "admin"])
        self._invalid_cases = (
            []
        )  # Question contains no validation, so everything is valid

    def test_default_empty(self):
        question, config, _ = self.setup_question("")
        question(config)  # Empty value is acceptable for this question


class TestGetDescriptionQuestion(tests.TestQuestion, tests.TestDefaultConfig):
    """Test the _get_name question from the SNMPStep"""

    def setUp(self):
        tests.TestQuestion.setUp(self)
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["snmp", "description"]
        self._question = "_get_description"
        self._valid_cases = [
            "description",
            "Some really specific description",
            "Room10",
        ]
        self._invalid_cases = (
            []
        )  # Question contains no validation, so everything is valid

    def test_default_empty(self):
        question, config, _ = self.setup_question("")
        question(config)  # Empty value is acceptable for this question
