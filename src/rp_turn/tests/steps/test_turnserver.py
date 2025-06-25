"""
Tests the TurnServerStep from the installwizard
"""

import base64

# Third party imports
from unittest import mock

# Import steps and default cases
import rp_turn.tests.steps as tests
import rp_turn.tests.utils as test_utils

# Local application/library specific imports
from rp_turn import steps, utils

STEPCLASS = steps.TurnServerStep


class TestEnableTurnServer(tests.TestYesNoQuestion):
    """Test the _enable_turn question in the TurnServerStep with WebLoadBalance enabled"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["turnserver", "enabled"]
        self._question = "_enable_turn"
        self._config = {
            "enablewebloadbalance": True
        }  # question is only asked if webloadbalance is enabled

    def is_valid(self, step, config, expected):
        tests.TestYesNoQuestion.is_valid(self, step, config, expected)
        question_strs = self.get_questions_from_step(step)
        if expected:
            self.assertEqual(
                question_strs,
                [
                    "_intro",
                    "_enable_turn",
                    "_get_turn_username",
                    "_get_turn_password",
                    "_get_media_addresses",
                ],
            )
        else:
            self.assertEqual(question_strs, ["_intro", "_enable_turn"])

    def test_default_turn(self):
        """
        Test when answering 'Yes' to use shared secret the questions are for
        username and password
        """
        question, config, step = self.setup_question("Yes")
        step.stdin.readline = mock.Mock(side_effect=["Yes\n", "Yes\n"])
        question(config)

        tests.TestYesNoQuestion.is_valid(self, step, config, True)
        question_strs = self.get_questions_from_step(step)
        self.assertEqual(
            question_strs,
            [
                "_intro",
                "_enable_turn",
                "_get_turn_username",
                "_get_turn_password",
                "_get_media_addresses",
            ],
        )

    def test_client_turn(self):
        """
        Test when answering 'No' to use shared secret the client turn step is ran
        """
        question, config, step = self.setup_question("Yes")
        step.stdin.readline = mock.Mock(side_effect=["Yes\n", "No\n"])
        question(config)

        tests.TestYesNoQuestion.is_valid(self, step, config, True)
        question_strs = self.get_questions_from_step(step)
        self.assertEqual(question_strs, ["_run_client_turn_step"])


class TestEnableClientTurn(tests.TestYesNoQuestion):
    """Test Enable Client Turn Question in TurnServerStep"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["turnserver", "clientturn"]
        self._question = "_enable_turn"
        self._config = {"enablewebloadbalance": True}

    def is_valid(self, step, config, expected):
        """Checks if expected value is set in config"""
        # We have to flip clientturn here, as we use if not response in the turn server step
        if "clientturn" in config["turnserver"]:
            expected = not expected

        super().is_valid(step, config, expected)


class TestGetTcpTurn(tests.TestYesNoQuestion):
    """Test the _get_tcp_turn question in the TurnServerStep where WebLoadBalance is disabled"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        self._step = STEPCLASS
        self._state_id = ["turnserver", "port443"]
        self._question = "_get_tcp_turn"
        self._config = {"enablewebloadbalance": False}


class TestGetTurnUsername(tests.TestQuestion):
    """Test the _get_turn_username question in the TurnServerStep"""

    def setUp(self):
        self._step = STEPCLASS
        self._state_id = ["turnserver", "username"]
        self._question = "_get_turn_username"
        self._valid_cases = ["username", "turnuser", "asdjou98fu8w9832sjaod", "3"]
        self._invalid_cases = ["\x1b[5~", "\n", "\x1b[5~password", "password\x1b[5~"]

    def test_valid_cases_with_padding(self):
        # Padding should remain
        for case in self._valid_cases:
            padded_case = "     " + case + "     "
            question, config, _ = self.setup_question(padded_case)
            question(config)
            self.assertEqual(self.get_config_value(config), padded_case)


class TestGetTurnPassword(tests.TestQuestion):
    """Test the _get_turn_password question in the TurnServerStep"""

    def setUp(self):
        self._step = STEPCLASS
        self._state_id = ["turnserver", "password"]
        self._question = "_get_turn_password"
        self._valid_cases = [
            "password",
            "turnpassword",
            "wejiorfjwoijoew0023ejoisdjop#asd'",
            "4",
        ]
        self._invalid_cases = ["\x1b[5~", "\n", "\x1b[5~password", "password\x1b[5~"]

    def test_valid_cases_with_padding(self):
        # Padding should remain
        for case in self._valid_cases:
            padded_case = "     " + case + "     "
            question, config, _ = self.setup_question(padded_case)
            question(config)
            self.assertEqual(self.get_config_value(config), padded_case)


class TestGetMediaConfNode(tests.TestMultiQuestion, tests.TestMultiDefaultConfig):
    """Test the MediaConferenceNodeStep"""

    def setUp(self):
        tests.TestMultiQuestion.setUp(self)
        tests.TestMultiDefaultConfig.setUp(self)
        self._step = steps.MediaConferenceNodeStep
        self._state_id = "medianodes"
        self._question = "_get_another_answer"
        self._valid_cases = test_utils.VALID_IP_ADDRESSES
        self._invalid_cases = (
            test_utils.INVALID_IP_ADDRESSES
            + test_utils.INVALID_DOMAINS
            + test_utils.VALID_DOMAIN_NAMES
        )

    def test_default_from_conferencenodes_fqdn(self):
        """
        Don't suggest to use the conference node addresses as they are fqdn
        """
        step = self._step()
        config = utils.nested_dict()
        config["conferencenodes"] = [
            "conf-1.pexip.local",
            "conf-2.pexip.local",
        ]
        question, _, _ = self.setup_question(
            "Yes", step=step, question_str="_use_default"
        )
        question(config)
        self.assertFalse(config["medianodes"])

    def test_default_from_conferencenodes_ip_address(self):
        """
        Suggest to use the conference node addresses only if they are valid IP addresses
        """
        step = self._step()
        config = utils.nested_dict()
        config["conferencenodes"] = [
            "1.1.1.1",
            "2.2.2.2",
        ]
        question, _, _ = self.setup_question(
            "Yes", step=step, question_str="_use_default"
        )
        question(config)
        self.assertEqual(
            config["medianodes"],
            [
                "1.1.1.1",
                "2.2.2.2",
            ],
        )


class TestClientGetTcpTurn(tests.TestYesNoQuestion):
    """Test the _get_tcp_turn question in the TurnServerStep where WebLoadBalance is disabled"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        self._step = steps.ClientTurnServerStep
        self._state_id = ["turnserver", "port443"]
        self._question = "_get_tcp_turn"
        self._config = {"enablewebloadbalance": False}


class TestGetTurnSharedSecret(tests.TestQuestion):
    """Test the _get_turn_shared_secret question in the TurnServerStep"""

    def setUp(self):
        self._step = steps.ClientTurnServerStep
        self._state_id = ["turnserver", "sharedsecret"]
        self._question = "_get_turn_shared_secret"
        self._valid_cases = ["secretkey", "5"]
        self._invalid_cases = ["\x1b[5~", "\n", "\x1b[5~password", "password\x1b[5~"]

    def test_valid_cases_with_padding(self):
        """Padding should remain"""
        for case in self._valid_cases:
            padded_case = "     " + case + "     "
            question, config, _ = self.setup_question(padded_case)
            question(config)
            self.assertEqual(self.get_config_value(config), padded_case)

    def test_default_empty(self):
        """Default case should generate random key 32 bytes long"""
        question, config, _ = self.setup_question("")
        question(config)

        value = self.get_config_value(config)
        value = base64.b64decode(value.encode("ascii") + b"=")
        self.assertEqual(len(value), 32)
