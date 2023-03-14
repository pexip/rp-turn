"""
Tests some of the missing cases from base classes of Step and MultiStep from the installwizard
"""

import sys
from functools import partial

# Standard library imports
from io import StringIO

# Local application/library specific imports
import rp_turn.tests.utils as test_utils
from rp_turn import utils
from rp_turn.step_error import StepError
from rp_turn.steps import Step
from rp_turn.tests.steps import QuestionUtils


class TestBasicStep(QuestionUtils):
    """Makes sure simple properties/methods of Step are set correctly"""

    COUNTER = 0

    def setUp(self):
        self._step = partial(Step, "DummyStep")
        self.step = self._step()
        TestBasicStep.COUNTER = 0

    def test_property(self):
        """Tests property is set"""
        self.assertEqual(self.step.prompt, "> ")

    def test_default(self):
        """Tests default is always True"""
        _, _, step = self.setup_question("", question_str="ask")
        default = "Success"
        self.assertEqual(step.ask("Message", default=default), default)

    def test_display(self):
        """Tests that display prints the message to stdout"""
        cases = ["hello", "world", "something\nsomething"]
        for case in cases:
            fake_out = StringIO()
            sys.stdout = fake_out
            self.step.display(case)
            sys.stdout = sys.__stdout__
            self.assertEqual(fake_out.getvalue(), f"\n{case}\n")

    def test_run_linear(self):
        """Runs each question without raising any StepErrors"""
        num_tests = 100

        def test_question(index, _):
            """Dummy question"""
            self.assertEqual(TestBasicStep.COUNTER, index)
            TestBasicStep.COUNTER += 1

        config = utils.nested_dict()
        self.step.questions = [partial(test_question, i) for i in range(num_tests)]
        for i in range(num_tests):
            fake_out = StringIO()
            sys.stdout = fake_out
            # pylint: disable=protected-access
            self.step._step_id = i
            self.step._total_steps = num_tests
            # pylint: enable=protected-access
            self.step.run_once(config, print_header=True)
            sys.stdout = sys.__stdout__
        self.assertEqual(test_utils.question_strs(self.step.questions), [])

    def test_run_invalid(self):
        """Runs one question which raises a StepError and checks to see if it will be called again"""

        def test_question(_):
            """Dummy question which raises StepError"""
            raise StepError("DummyError")

        config = utils.nested_dict()
        self.step.questions = [test_question]
        fake_out = StringIO()
        sys.stdout = fake_out
        self.step.run_once(config)
        sys.stdout = sys.__stdout__
        self.assertEqual(fake_out.getvalue(), "Invalid: DummyError\n")
        self.assertEqual(
            test_utils.question_strs(self.step.questions), ["test_question"]
        )

    def test_run_invalid_raise(self):
        """Runs one question which raises a StepError and checks to see if it is raised"""

        def test_question(_):
            """Dummy question which raises StepError"""
            raise StepError("DummyError")

        config = utils.nested_dict()
        self.step.questions = [test_question]
        fake_out = StringIO()
        sys.stdout = fake_out
        self.assertRaises(StepError, self.step.run_once, config, raise_invalid=True)
        sys.stdout = sys.__stdout__
