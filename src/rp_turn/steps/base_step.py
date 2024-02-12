""" Base Step Types for InstallWizard """

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from functools import partial
from typing import Any, Callable

from rp_turn import utils
from rp_turn.step_error import StepError

DEV_LOGGER = logging.getLogger("rp_turn.installwizard")


class Step:
    """
    Base class to provide a step in the install wizard
    Child classes should add functions into Class.questions and use self.ask("message") to get responses
    """

    def __init__(self, step_msg: str):
        self._step_msg = step_msg
        self._last_ask_errored = False
        self._last_msg = ""
        self.prompt = "> "
        self.questions: list[Callable[[defaultdict], None] | partial] = (
            []
        )  # Overwritten by child class
        self._step_id = 0  # Overwritten by run
        self._total_steps = 0  # Overwritten by run
        self.stdin = sys.stdin

    @staticmethod
    def display(message: str) -> None:
        """Prints a message to the user"""
        DEV_LOGGER.info("Displayed: %s", message)
        print("\n" + message)

    def ask(self, message: str, default: str | None = None) -> str:
        """Asks the user for input to a question"""
        repeat_ask = message == self._last_msg
        self._last_msg = message
        # Only print the question once
        if not repeat_ask:
            DEV_LOGGER.info("Asking for first time: %s", message)
            print("\n" + message)
            if default is not None:
                DEV_LOGGER.info("Has default value of: %s", default)
                print(f"Press [ENTER] to use the default value: {default}")
        else:
            DEV_LOGGER.info("Asking again for: %s", message)
        print(self.prompt, flush=True, end="")
        response = self.stdin.readline()[:-1]  # Remove new line character at the end
        # Replace the response with the default if it was empty and a default was supplied
        if response == "" and default:
            DEV_LOGGER.info("Using default response")
            response = default
        return response

    def ask_yes_no(self, message: str, default: bool | None = None) -> bool:
        """Asks the user for input to a yes/no question"""
        DEV_LOGGER.info("Expecting Yes/No for next ask")
        default_str: str | None = None
        if isinstance(default, bool):
            default_str = "Yes" if default else "No"
        response = self.ask(message + " (Yes/No)", default_str).lower().strip()
        DEV_LOGGER.info("Response: %s", response)
        if response in ["y", "yes", "true"]:
            return True
        if response in ["n", "no", "false"]:
            return False
        raise StepError("Please enter Yes or No")

    def run_once(
        self,
        config: defaultdict,
        print_header: bool = False,
        raise_invalid: bool = False,
    ) -> None:
        """Attempts once to run one question"""
        if print_header:
            print(self.header)
        question = self.questions.pop(0)
        try:
            DEV_LOGGER.info(
                "Calling %s question",
                (
                    question.func.__name__
                    if isinstance(question, partial)
                    else question.__name__
                ),
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
                (
                    question.func.__name__
                    if isinstance(question, partial)
                    else question.__name__
                ),
            )
            self.questions.insert(0, question)

    def run(
        self,
        config: defaultdict,
        step_id: int,
        total_steps: int,
        print_header: bool = True,
        raise_invalid: bool = False,
    ) -> None:
        """Calls run_once until we run out of questions"""
        self._step_id = step_id
        self._total_steps = total_steps
        while self.questions:
            self.run_once(config, print_header, raise_invalid)
            if print_header:
                print_header = False

    @property
    def header(self) -> str:
        """Header for the step"""
        header = """\
==========================================================
|{}|
|{}|
=========================================================="""
        header_width = len(header.split("\n", maxsplit=1)[0]) - 2
        step_num = center(f"Step {self._step_id} of {self._total_steps}", header_width)
        step_msg = center(self._step_msg, header_width)
        return header.format(step_num, step_msg)

    def default_config(self, _saved_config: defaultdict, _config: defaultdict) -> None:
        """Load config from saved config. Suggest values if invalid/missing"""
        DEV_LOGGER.warning("%s has no default_config method", self._step_msg)


def center(message: str, width: int) -> str:
    """Centers text in a string of fixed length"""
    message_length = len(message)
    padding = max(width - message_length, 0)
    return (" " * (padding // 2)) + message + (" " * ((padding + 1) // 2))


class MultiStep(Step):
    """
    Base step that requests multiple inputs of the same type
    """

    def __init__(
        self, step_msg: str, keyname: str | list[str], end_on_enter: bool = True
    ):
        super().__init__(step_msg)
        self.questions = [self._use_default]
        self._keyname = keyname
        self._answers: list[Any] = []
        self._end_on_enter = end_on_enter

    def format_value(self, value: Any) -> str:
        """Converts stored value into human readable value"""
        return str(value)

    def validate(self, response: str) -> Any:
        """Validates whether a stored value is valid"""
        DEV_LOGGER.warning("%s has no validate method", self._step_msg)
        return response

    def _use_default(self, config: defaultdict) -> None:
        """Shows user a list of default values and ask whether they want to use them"""
        default_values = utils.get_config_value_by_path(config, self._keyname)
        if default_values:
            msg = f"Default {self._step_msg} found:"
            for value in default_values:
                msg += "\n  - " + self.format_value(value)
            msg += f"\nUse these default {self._step_msg}?"
            response = self.ask_yes_no(msg, default=True)
            if response:
                return
        if self._end_on_enter:
            self.display(
                "This step allows multiple entries. Press [ENTER] when finished"
            )
        self.questions.append(self._get_another_answer)

    def _get_another_answer(self, config: defaultdict) -> None:
        """Asks the user for another answer"""
        singular_msg = self._step_msg[:-1]
        response = self.ask(f"{singular_msg} {len(self._answers) + 1}?")
        if response == "":
            if not self._answers:
                raise StepError(f"Must enter at least one {singular_msg}")

            DEV_LOGGER.info("Saving answers to %s", self._keyname)
            utils.set_config_value_by_path(config, self._keyname, self._answers)
            return
        answer = str(self.validate(response))
        self._answers.append(answer)
        DEV_LOGGER.info("Adding another _get_another_answer")
        self.questions.append(self._get_another_answer)
