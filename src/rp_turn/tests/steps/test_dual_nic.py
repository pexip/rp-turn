# pylint: disable=protected-access
"""
Tests the DualNicStep from the installwizard
"""

# Standard library imports
from functools import partial

# 3rd party imports
from unittest import TestCase, mock

# Local application/library specific imports
import rp_turn.tests.steps as tests
import rp_turn.tests.utils as test_utils
from rp_turn import steps, utils
from rp_turn.step_error import StepError


class TestIntroDualNic(TestCase):
    """Tests the _intro_dual_nic Question in DualNicStep with 3 NICs"""

    def setUp(self):
        self._install_wizard = mock.MagicMock()
        self._nic_names = ["nic0", "nic1"]
        self._nic_macs = ["00:00:00:00:00", "11:11:11:11:11"]
        self._nics = list(zip(self._nic_names, self._nic_macs))
        self.step = steps.DualNicStep(
            install_wizard=self._install_wizard, nics=self._nics
        )
        self.step.ask = mock.Mock(return_value=None)
        self.step.display = mock.Mock(return_value=None)

    def test_intro_dual_nics(self):
        """Tests the intro to dual nic"""

        def check_display(msg):
            """Checks that the display method includes all nics names/macs"""
            for nic_name, nic_mac in self._nics:
                self.assertIn(f"  - {nic_name} ({nic_mac})", msg.split("\n"))

        config = utils.nested_dict()
        self.step.display = mock.Mock(side_effect=check_display)
        self.step._intro_dual_nic(config)


class TestEnableDualNic(tests.TestYesNoQuestion):
    """Test _enable_dual_nic question from the DualNicStep"""

    def setUp(self):
        tests.TestYesNoQuestion.setUp(self)
        self._install_wizard = mock.MagicMock()
        self._step = partial(
            steps.DualNicStep,
            install_wizard=self._install_wizard,
            nics=[("nic0", "00:00:00:00:00"), ("nic1", "11:11:11:11:11")],
        )
        self._state_id = None
        self._question = "_enable_dual_nic"

    def is_valid(self, step, config, expected):
        questions = test_utils.question_strs(step.questions)
        if expected:
            self.assertEqual(
                questions,
                [
                    "_intro_dual_nic",
                    "_enable_dual_nic",
                    "_get_nic_name(){'internal': True}",
                    "_get_nic_name(){'external': True}",
                    "_save_nic_settings",
                ],
            )
        else:
            self.assertEqual(
                questions,
                [
                    "_intro_dual_nic",
                    "_enable_dual_nic",
                    "_get_nic_name(){'internal': True, 'external': True}",
                    "_save_nic_settings",
                ],
            )


class TestGetNicName1Nic(tests.QuestionUtils):
    """Tests the _get_nic_name Question in DualNicStep with 1 NIC attached"""

    def __init__(self, obj):
        tests.QuestionUtils.__init__(self, obj)
        self._nic_names = ["nic0"]
        self._nic_macs = ["00:00:00:00:00"]
        self._nics = list(zip(self._nic_names, self._nic_macs))

    def setUp(self):
        self._install_wizard = mock.MagicMock()
        self._step = partial(
            steps.DualNicStep, install_wizard=self._install_wizard, nics=self._nics
        )
        self._state_id = None
        self._question = "_get_nic_name"
        self._valid_cases = self._nic_names
        self._invalid_cases = (
            test_utils.INVALID_IP_ADDRESSES
            + test_utils.VALID_YES_CASES
            + test_utils.VALID_DOMAIN_NAMES
            + test_utils.VALID_HOSTNAMES
        )

    def test_default_empty(self):
        """Tests the default case is used when user just presses enter"""
        question, config, _ = self.setup_question("")
        if len(self._nics) > 1:
            self.assertRaises(
                StepError, question, config, internal=True, external=False
            )
            self.assertRaises(
                StepError, question, config, internal=False, external=True
            )
            self.assertRaises(StepError, question, config, internal=True, external=True)
            self.assertRaises(
                AssertionError, question, config, internal=False, external=False
            )
        else:
            # _get_nic_name should not ask for an input as there is only one nic
            # therefore these should NOT throw a StepError
            question(config, internal=True, external=True)

    def test_invalid_cases(self):
        """Tests invalid cases"""
        for case in self._invalid_cases:
            question, config, _ = self.setup_question(case)
            if len(self._nics) > 1:
                self.assertRaises(
                    StepError, question, config, internal=True, external=False
                )
                self.assertRaises(
                    StepError, question, config, internal=False, external=True
                )
                self.assertRaises(
                    StepError, question, config, internal=True, external=True
                )
                self.assertRaises(
                    AssertionError, question, config, internal=False, external=False
                )
            else:
                # _get_nic_name should not ask for an input as there is only one nic
                # therefore these should NOT throw a StepError
                question(config, internal=True, external=True)
                self.assertNotEqual(config["internal"], case)
                self.assertNotEqual(config["external"], case)


class TestGetNicName2Nics(TestGetNicName1Nic):
    """Tests the _get_nic_name Question in DualNicStep with 2 NICs attached"""

    def __init__(self, obj):
        TestGetNicName1Nic.__init__(self, obj)
        self._nic_names.append("nic1")
        self._nic_macs.append("11:11:11:11:11")
        self._nics = list(zip(self._nic_names, self._nic_macs))

    def test_valid_dual_nic(self):
        """Tests valid dual nic mode"""
        for index, case in enumerate(self._valid_cases):
            other_case = self._valid_cases[(index + 1) % len(self._valid_cases)]
            question, config, step = self.setup_question(case)
            self.assertEqual(step._nics, self._nics)
            self.assertEqual(step._all_nic_names, self._nic_names)
            self.assertEqual(step._valid_nic_names, self._nic_names)
            question(config, internal=True)
            self.assertEqual(step._nics, self._nics)
            self.assertEqual(step._all_nic_names, self._nic_names)
            self.assertNotIn(case, step._valid_nic_names)
            self.assertIn(other_case, step._valid_nic_names)
            self.assertEqual(config["internal"], case)
            self.assertNotEqual(config["external"], case)
            question, _, step = self.setup_question(other_case, step=step)
            question(config, external=True)
            self.assertNotIn(case, step._valid_nic_names)
            self.assertNotIn(other_case, step._valid_nic_names)
            self.assertEqual(config["internal"], case)
            self.assertEqual(config["external"], other_case)

    def test_valid_single_nic(self):
        """Test valid single nic mode"""
        for case in self._valid_cases:
            question, config, step = self.setup_question(case)
            self.assertEqual(step._nics, self._nics)
            self.assertEqual(step._all_nic_names, self._nic_names)
            self.assertEqual(step._valid_nic_names, self._nic_names)
            question(config, internal=True, external=True)
            self.assertEqual(step._nics, self._nics)
            self.assertEqual(step._all_nic_names, self._nic_names)
            self.assertNotIn(case, step._valid_nic_names)
            self.assertEqual(config["internal"], case)
            self.assertEqual(config["external"], case)


class TestGetNicName3Nics(TestGetNicName2Nics):
    """Tests the _get_nic_name Question in DualNicStep with 3 NICs attached"""

    def __init__(self, obj):
        TestGetNicName2Nics.__init__(self, obj)
        self._nic_names.append("nic3")
        self._nic_macs.append("22:22:22:22:22")
        self._nics = list(zip(self._nic_names, self._nic_macs))

    def test_invalid_dual_nic(self):
        """Tests giving an invalid nic name after a valid one"""
        for index, case in enumerate(self._valid_cases):
            other_case = self._valid_cases[(index + 1) % len(self._valid_cases)]
            question, config, step = self.setup_question(case)
            self.assertEqual(step._nics, self._nics)
            self.assertEqual(step._all_nic_names, self._nic_names)
            self.assertEqual(step._valid_nic_names, self._nic_names)
            question(config, internal=True)
            self.assertEqual(step._nics, self._nics)
            self.assertEqual(step._all_nic_names, self._nic_names)
            self.assertNotIn(case, step._valid_nic_names)
            self.assertIn(other_case, step._valid_nic_names)
            self.assertEqual(config["internal"], case)
            self.assertNotEqual(config["external"], case)
            self.assertRaises(StepError, question, config, external=True)


class TestSaveNicSettings(TestCase):
    """Tests the _get_nic_name Question in DualNicStep with 3 NICs"""

    def setUp(self):
        self._install_wizard = tests.get_installwizard()
        self._install_wizard._steps = []
        self._nic_names = ["nic0", "nic1"]
        self._nic_macs = ["00:00:00:00:00", "11:11:11:11:11"]
        self._nics = list(zip(self._nic_names, self._nic_macs))
        self.step = steps.DualNicStep(
            install_wizard=self._install_wizard, nics=self._nics
        )
        self.step.ask = mock.Mock(return_value=None)
        self.step.display = mock.Mock(return_value=None)

    def test_two_nics(self):
        """Tests selecting two nics"""
        config = utils.nested_dict()
        config["internal"] = "nic0"
        config["external"] = "nic1"
        self.step._save_nic_settings(config)
        self._install_wizard._insert_next_steps()
        questions = []
        for question in self._install_wizard._steps:
            if question.__class__.__name__ == "NetworkStep":
                questions.append(
                    f"NetworkStep('{question.nic_name}', '{question.nic_mac}', '{question.nic_str}')"
                )
            else:
                questions.append(question.__class__.__name__)
        self.assertEqual(
            questions,
            [
                "NetworkStep('nic1', '11:11:11:11:11', ' for external interface')",
                "NetworkStep('nic0', '00:00:00:00:00', ' for internal interface')",
            ],
        )

    def test_one_nic(self):
        """Tests selecting one nic"""
        config = utils.nested_dict()
        config["internal"] = "nic0"
        config["external"] = "nic0"
        self.step._save_nic_settings(config)
        self._install_wizard._insert_next_steps()
        questions = []
        for question in self._install_wizard._steps:
            if question.__class__.__name__ == "NetworkStep":
                questions.append(
                    f"NetworkStep('{question.nic_name}', '{question.nic_mac}', '{question.nic_str}')"
                )
            else:
                questions.append(question.__class__.__name__)
        self.assertEqual(questions, ["NetworkStep('nic0', '00:00:00:00:00', '')"])


class TestDefaultInternalNic(tests.TestDefaultConfig):
    """Tests getting the internal interface from the saved_config"""

    def setUp(self):
        tests.TestDefaultConfig.setUp(self)
        # setup step
        self._install_wizard = mock.MagicMock()
        self._nic_names = ["nic0", "nic1", "nic2"]
        self._nic_macs = ["00:00:00:00:00", "11:11:11:11:11", "22:22:22:22:22"]
        self._nics = list(zip(self._nic_names, self._nic_macs))
        self._step = partial(
            steps.DualNicStep, install_wizard=self._install_wizard, nics=self._nics
        )
        self._step.ask = mock.Mock(return_value=None)
        self._step.display = mock.Mock(return_value=None)

        self._state_id = ["internal"]
        self._valid_cases = ["nic0", "nic1", "nic2"]
        self._invalid_cases = (
            ["nic3", "eth0", "lo"]
            + test_utils.VALID_IP_ADDRESSES
            + test_utils.INVALID_DOMAINS,
        )


class TestDefaultExternalNic(TestDefaultInternalNic):
    """Tests getting the external interface from the saved_config"""

    def setUp(self):
        TestDefaultInternalNic.setUp(self)
        self._state_id = ["external"]
