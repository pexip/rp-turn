""" Base Step Types for InstallWizard """

from __future__ import print_function
import logging
import sys
from functools import partial

from si.apps import reverseproxy as rp
from si.apps.reverseproxy.step_error import StepError

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class Step:  # pylint: disable=too-many-instance-attributes
    """
    Base class to provide a step in the install wizard
    Child classes should add functions into Class.questions and use self.ask("message") to get responses
    """

    def __init__(self, step_msg):
        self._step_msg = step_msg
        self._last_ask_errored = False
        self._last_msg = ""
        self.prompt = "> "
        self.questions = []  # Overwritten by child class
        self._step_id = 0  # Overwritten by run
        self._total_steps = 0  # Overwritten by run
        self.stdin = sys.stdin

    @staticmethod
    def display(message):
        """Prints a message to the user"""
        DEV_LOGGER.info("Displayed: %s", message)
        print("\n" + message)

    def ask(self, message, default=None):
        """Asks the user for input to a question"""
        repeat_ask = message == self._last_msg
        self._last_msg = message
        # Only print the question once
        if not repeat_ask:
            DEV_LOGGER.info("Asking for first time: %s", message)
            print("\n" + message)
            if default is not None:
                DEV_LOGGER.info("Has default value of: %s", default)
                print("Press [ENTER] to use the default value: {}".format(default))
        else:
            DEV_LOGGER.info("Asking again for: %s", message)
        print(self.prompt, flush=True, end="")
        response = self.stdin.readline()[:-1]  # Remove new line character at the end
        # Replace the response with the default if it was empty and a default was supplied
        if response == "" and default:
            DEV_LOGGER.info("Using default response")
            response = default
        return response

    def ask_yes_no(self, message, default=None):
        """Asks the user for input to a yes/no question"""
        DEV_LOGGER.info("Expecting Yes/No for next ask")
        if isinstance(default, bool):
            default = "Yes" if default else "No"
        response = self.ask(message + " (Yes/No)", default).lower().strip()
        DEV_LOGGER.info("Response: %s", response)
        if response in ["y", "yes", "true"]:
            return True
        if response in ["n", "no", "false"]:
            return False
        raise StepError("Please enter Yes or No")

    def run_once(self, config, print_header=False, raise_invalid=False):
        """Attempts once to run one question"""
        if print_header:
            print(self.header)
        question = self.questions.pop(0)
        try:
            DEV_LOGGER.info(
                "Calling %s question",
                question.func.__name__
                if isinstance(question, partial)
                else question.__name__,
            )
            question(config)
            self._last_ask_errored = False
        except StepError as error:
            if raise_invalid:
                raise error
            print("Invalid: " + str(error))
            self._last_ask_errored = True
            DEV_LOGGER.info(
                "Question threw StepError. Readding %s as next question",
                question.func.__name__
                if isinstance(question, partial)
                else question.__name__,
            )
            self.questions.insert(0, question)

    def run(
        self, config, step_id, total_steps, print_header=True, raise_invalid=False
    ):  # pylint: disable=too-many-arguments
        """Calls run_once until we run out of questions"""
        self._step_id = step_id
        self._total_steps = total_steps
        while self.questions:
            self.run_once(config, print_header, raise_invalid)
            if print_header:
                print_header = False

    @property
    def header(self):
        """Header for the step"""
        header = """\
==========================================================
|{}|
|{}|
=========================================================="""
        header_width = len(header.split("\n", maxsplit=1)[0]) - 2
        step_num = center(
            "Step {} of {}".format(self._step_id, self._total_steps), header_width
        )
        step_msg = center(self._step_msg, header_width)
        return header.format(step_num, step_msg)

    def default_config(self, _saved_config, _config):
        """Load config from saved config. Suggest values if invalid/missing"""
        DEV_LOGGER.warning("%s has no default_config method", self._step_msg)


def center(message, width):
    """Centers text in a string of fixed length"""
    message_length = len(message)
    padding = max(width - message_length, 0)
    return (" " * (padding // 2)) + message + (" " * ((padding + 1) // 2))


class MultiStep(Step):
    """
    Base step that requests multiple inputs of the same type
    """

    def __init__(self, step_msg, keyname, end_on_enter=True):
        Step.__init__(self, step_msg)
        self.questions = [self._use_default]
        self._keyname = keyname
        self._answers = []
        self._end_on_enter = end_on_enter

    def format_value(self, value):  # pylint: disable=no-self-use
        """Converts stored value into human readable value"""
        return str(value)

    def validate(self, response):
        """Validates whether a stored value is valid"""
        DEV_LOGGER.warning("%s has no validate method", self._step_msg)
        return response

    def _use_default(self, config):
        """Shows user a list of default values and ask whether they want to use them"""
        default_values = rp.utils.get_config_value_by_path(config, self._keyname)
        if default_values:
            msg = "Default {} found:".format(self._step_msg)
            for value in default_values:
                msg += "\n  - " + self.format_value(value)
            msg += "\nUse these default {}?".format(self._step_msg)
            response = self.ask_yes_no(msg, default="Yes")
            if response:
                return
        if self._end_on_enter:
            self.display(
                "This step allows multiple entries. Press [ENTER] when finished"
            )
        self.questions.append(self._get_another_answer)

    def _get_another_answer(self, config):
        """Asks the user for another answer"""
        singular_msg = self._step_msg[:-1]
        response = self.ask("{} {}?".format(singular_msg, len(self._answers) + 1))
        if response == "":
            if not self._answers:
                raise StepError("Must enter at least one {}".format(singular_msg))

            DEV_LOGGER.info("Saving answers to %s", self._keyname)
            rp.utils.set_config_value_by_path(config, self._keyname, self._answers)
            return
        answer = str(self.validate(response))
        self._answers.append(answer)
        DEV_LOGGER.info("Adding another _get_another_answer")
        self.questions.append(self._get_another_answer)
