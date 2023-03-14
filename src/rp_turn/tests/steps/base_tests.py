"""
Test the ReverseProxy InstallWizard
"""

import copy

# Standard library imports
import logging
import sys
from functools import partial
from io import StringIO

# 3rd party imports
from unittest import mock

import twisted.trial.unittest

# Local application/library specific imports
import rp_turn.steps.base_step
from rp_turn import utils
from rp_turn.step_error import StepError
from rp_turn.tests import utils as test_utils
from rp_turn.tests.utils import (
    INVALID_YESNO_CASES,
    VALID_DOMAIN_NAMES,
    VALID_IP_ADDRESSES,
    VALID_NO_CASES,
    VALID_YES_CASES,
    make_multi_cases,
)

DEV_LOGGER = logging.getLogger("developer.apps.metrics")


class QuestionUtils(twisted.trial.unittest.TestCase):
    """
    Tests that all types of questions must have
    """

    def setUp(self):
        self._step = partial(rp_turn.steps.base_step.Step, "DummyQuestionUtils")
        self._state_id = None
        self._question = None
        self._valid_cases = []
        self._invalid_cases = []

    def setup_question(self, case, step=None, question_str=None):
        """Setups a step and question with a preloaded answer"""
        if question_str is None:
            if hasattr(self, "_question"):
                question_str = self._question
            elif hasattr(self, "_question_default_config"):
                question_str = self._question_default_config
        if step is None:
            step = self._step()

            # Setup step.ask and step.display to hide stdout
            def fakeask(message, default=None):
                """Hides stdout when calling ask method"""
                fake_out = StringIO()
                sys.stdout = fake_out
                output = step._ask(  # pylint: disable=protected-access
                    message, default=default
                )
                sys.stdout = sys.__stdout__
                return output

            step._ask = copy.copy(step.ask)  # pylint: disable=protected-access
            step.ask = mock.Mock(side_effect=fakeask)
            step.display = mock.Mock(return_value=None)
        if question_str is None:
            raise twisted.trial.unittest.SkipTest("Missing _question")

        step.stdout = mock.Mock()
        step.stdin = mock.Mock()
        if case is None:
            case = ""
        step.stdin.readline = mock.Mock(return_value=case + "\n")

        if hasattr(self, "_config"):
            config = utils.make_nested_dict(self._config)
        else:
            config = utils.nested_dict()
        question = getattr(step, question_str)
        return question, config, step

    def get_config_value(self, config):
        """Gets config value of _state_id"""
        return utils.get_config_value_by_path(config, self._state_id)

    def get_questions_from_step(self, step):
        """Returns a list of question names"""
        return [question.__name__ for question in step.questions]


class TestQuestion(QuestionUtils):
    """Base case to test a question"""

    def setUp(self):
        self._step = partial(rp_turn.steps.base_step.Step, "DummyStep")
        self._state_id = None
        self._question = None
        self._valid_cases = []
        self._invalid_cases = []

    def is_valid(self, _step, config, expected):
        """Checks if expected value is set in config"""
        self.assertEqual(self.get_config_value(config), expected)

    def test_valid_cases(self):
        """Tests valid cases"""
        for case in self._valid_cases:
            question, config, step = self.setup_question(case)
            question(config)
            self.is_valid(step, config, case)

    def test_valid_cases_with_padding(self):
        """Tests valid cases with padding"""
        for case in self._valid_cases:
            padded_case = "     " + case + "     "
            question, config, step = self.setup_question(padded_case)
            question(config)
            self.is_valid(step, config, case)

    def test_default_empty(self):
        """Tests when user just presses enter"""
        question, config, _ = self.setup_question("")
        self.assertRaises(StepError, question, config)

    def test_invalid_cases(self):
        """Tests invalid cases"""
        for case in self._invalid_cases:
            question, config, _ = self.setup_question(case)
            self.assertRaises(StepError, question, config)


class TestMultiQuestion(TestQuestion):
    """Base case to test a question which keeps requesting input until an empty line is supplied"""

    def setUp(self):
        self._state_id = None
        self._step = partial(
            rp_turn.steps.base_step.MultiStep, "DummyStep", self._state_id
        )
        self._question = "_get_another_answer"
        self._valid_cases = []
        self._invalid_cases = []

    def test_use_default(self):
        """Tests that the _use_default method prints the list"""
        step = self._step()
        config = utils.nested_dict()
        default_values = ["a", "bunch", "of value", "with", 3241, "numbers"]
        utils.set_config_value_by_path(
            config,
            step._keyname,  # pylint: disable=protected-access
            default_values,
        )
        fake_out = StringIO()
        sys.stdout = fake_out
        question, _, _ = self.setup_question(
            "Yes", step=step, question_str="_use_default"
        )
        question(config)
        sys.stdout = sys.__stdout__
        self.assertNotIn(self._question, test_utils.question_strs(step.questions))
        stdout = fake_out.getvalue().split("\n")
        for value in default_values:
            self.assertIn("  - " + str(value), stdout)

    def test_invalid_cases_after_valid_cases(self):
        """Tests that an invalid case is not accepted after a list of valid cases"""
        valid_multi_cases = make_multi_cases(self._valid_cases, 2)
        for invalid_case in self._invalid_cases:
            step = self._step()
            config = utils.nested_dict()
            for case in valid_multi_cases:
                question, _, _ = self.setup_question(None, step=step)
                for line in case:
                    step.ask = mock.Mock(return_value=line)
                    question(config)
                step.ask = mock.Mock(return_value=invalid_case)
                self.assertRaises(StepError, question, config)

    def test_valid_cases(self):
        valid_multi_cases = make_multi_cases(self._valid_cases, 3)
        for case in valid_multi_cases:
            step = self._step()
            config = utils.nested_dict()
            question, _, _ = self.setup_question(None, step=step)
            for line in case:
                step.ask = mock.Mock(return_value=line)
                question(config)
            # Must end on an empty line
            step.ask = mock.Mock(return_value="")
            question(config)
            # Verify config is added
            self.assertEqual(set(self.get_config_value(config)), set(case))

    def test_valid_cases_singular(self):
        """Tests MultiStep with one case only"""
        for case in self._valid_cases:
            question, config, step = self.setup_question(case)
            question(config)
            # Must end on an empty line
            step.ask = mock.Mock(return_value="")
            question(config)
            # Verify config is added
            self.assertEqual(self.get_config_value(config), [case])

    def test_valid_cases_with_padding(self):
        valid_multi_cases = make_multi_cases(self._valid_cases, 3)
        for case in valid_multi_cases:
            question, config, step = self.setup_question(None)
            for line in case:
                padded_line = "     " + line + "     "
                step.ask = mock.Mock(return_value=padded_line)
                question(config)
            # Must end on an empty line
            step.ask = mock.Mock(return_value="")
            question(config)
            # Verify config is added
            self.assertEqual(set(self.get_config_value(config)), set(case))

    def test_valid_cases_singular_with_padding(self):
        """Tests MultiStep with padding and one case only"""
        for case in self._valid_cases:
            padded_case = "     " + case + "     "
            question, config, step = self.setup_question(padded_case)
            question(config)
            # Must end on an empty line
            step.ask = mock.Mock(return_value="")
            question(config)
            # Verify config is added
            self.assertEqual(self.get_config_value(config), [case])


class TestYesNoQuestion(QuestionUtils):
    """Base class to test a yes/no question"""

    def setUp(self):
        self._step = partial(rp_turn.steps.base_step.Step, "DummyStep")
        self._state_id = None
        self._question = None
        self._invalid_cases = (
            INVALID_YESNO_CASES + VALID_IP_ADDRESSES + VALID_DOMAIN_NAMES
        )

    def is_valid(self, _step, config, expected):
        """Checks if expected value is set in config"""
        if expected:
            self.assertTrue(self.get_config_value(config))
        else:
            self.assertFalse(self.get_config_value(config))

    def test_valid_true_cases(self):
        """Tests true cases"""
        for case in VALID_YES_CASES:
            question, config, step = self.setup_question(case)
            question(config)
            self.is_valid(step, config, True)

    def test_valid_false_cases(self):
        """Tests false cases"""
        for case in VALID_NO_CASES:
            question, config, step = self.setup_question(case)
            question(config)
            self.is_valid(step, config, False)


class TestDefaultConfig(QuestionUtils):
    """Base class to test the default_config method"""

    def setUp(self):
        self._step = partial(rp_turn.steps.base_step.Step, "DummyStep")
        self._state_id = None
        self._saved_state_id = None
        self._saved_config = utils.nested_dict()
        self._question_default_config = "default_config"
        self._valid_cases = []
        self._invalid_cases = []

    def test_default_config_valid_cases(self):
        """Tests the valid cases"""
        if self._saved_state_id is None:
            self._saved_state_id = self._state_id
        for case in self._valid_cases:
            default_config, config, _ = self.setup_question(
                None, question_str=self._question_default_config
            )
            saved_config = utils.make_nested_dict(self._saved_config)
            utils.set_config_value_by_path(saved_config, self._saved_state_id, case)
            default_config(saved_config, config)
            self.assertEqual(
                utils.get_config_value_by_path(config, self._state_id), case
            )

    def test_default_config_invalid_cases(self):
        """
        Tests the invalid cases are not accidentally accepted
        Only checks that the value in the config is not set to the invalid case
        """

        if self._saved_state_id is None:
            self._saved_state_id = self._state_id
        for case in self._invalid_cases:
            default_config, config, _ = self.setup_question(
                None, question_str=self._question_default_config
            )
            saved_config = utils.make_nested_dict(self._saved_config)
            utils.set_config_value_by_path(saved_config, self._saved_state_id, case)
            default_config(saved_config, config)
            self.assertNotEqual(
                utils.get_config_value_by_path(config, self._state_id), case
            )


class TestMultiDefaultConfig(TestDefaultConfig):
    """Base class to test the default_config method with an expectation of a list"""

    def test_default_config_valid_cases(self):
        """Tests the valid cases"""
        valid_cases = self._valid_cases
        invalid_cases = self._invalid_cases
        self._valid_cases = make_multi_cases(self._valid_cases, 3)
        self._invalid_cases = make_multi_cases(self._invalid_cases, 3)
        TestDefaultConfig.test_default_config_valid_cases(self)
        self._valid_cases = valid_cases
        self._invalid_cases = invalid_cases

    def test_default_config_invalid_cases(self):
        """
        Tests the invalid cases are not accidentally accepted
        Only checks that the value in the config is not set to the invalid case
        """
        valid_cases = self._valid_cases
        invalid_cases = self._invalid_cases
        self._valid_cases = make_multi_cases(self._valid_cases, 3)
        self._invalid_cases = make_multi_cases(self._invalid_cases, 3)
        TestDefaultConfig.test_default_config_invalid_cases(self)
        self._valid_cases = valid_cases
        self._invalid_cases = invalid_cases
