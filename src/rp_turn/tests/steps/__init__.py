"""Tests each question of each step of the installwizard"""

from rp_turn.tests.steps.base_tests import (
    DEV_LOGGER,
    QuestionUtils,
    TestDefaultConfig,
    TestMultiDefaultConfig,
    TestMultiQuestion,
    TestQuestion,
    TestYesNoQuestion,
)
from rp_turn.tests.test_installwizard import get_installwizard
from rp_turn.tests.utils import (
    INVALID_DOMAINS,
    INVALID_IP_ADDRESSES,
    INVALID_YESNO_CASES,
    UNREACHABLE_IP_ADDRESSES,
    VALID_DOMAIN_NAMES,
    VALID_HOSTNAMES,
    VALID_IP_ADDRESSES,
    VALID_NETMASKS,
    VALID_NO_CASES,
    VALID_YES_CASES,
    make_multi_cases,
    pair,
    question_strs,
)
