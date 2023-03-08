""" Collection of useful utils functions/cases for tests """
# pylint: disable=line-too-long

import itertools
from functools import partial

VALID_YES_CASES = ["yes", "YES", "YeS", "    YES", "yES    ", "y", "Y"]
VALID_NO_CASES = ["no", "n", "N", "   NO", "nO     "]
INVALID_YESNO_CASES = [
    "yesno",
    "no yes",
    "yn",
    "n y",
    "bad",
    "nono",
    "okay",
    "yup",
    "what?",
    "???",
    "of course I want that",
]
VALID_HOSTNAMES = ["bob", "alice", "ahslda", "0123", "asd0qfj38w", "dskhgro2e-fewf43fs"]
VALID_DOMAIN_NAMES = [
    "local",
    "lan",
    "pexip.com",
    "rd.pexip.com",
    "ab.cd",
    "sadfasdg.dfgjdfkljg.sdfjalsdkgj.ofdsjgods.adfgjklds",
    "ab.cd.ef.gh.ij",
]
INVALID_DOMAINS = ["asdagre@asdasd", "~aasd", "gjtl#", "?cd", "my domain", "1.1.1.1.23"]
VALID_IP_ADDRESSES = [
    "10.1.2.3",
    "192.168.0.1",
    "0.0.0.0",
    "255.255.255.255",
    "3.4.2.1",
]
UNREACHABLE_IP_ADDRESSES = [
    "10.10.10.10.10",
    "1.1.1",
    "1.1",
    "64",
    "....",
    "999.999.999.999",
    "-3.-2.-1.0",
]
INVALID_IP_ADDRESSES = (
    UNREACHABLE_IP_ADDRESSES
    + VALID_HOSTNAMES
    + VALID_DOMAIN_NAMES
    + INVALID_DOMAINS
    + ["wibble", "a.b.c.d"]
)
VALID_NETMASKS = [
    ("255.255.255.255", "/32")
]  # TODO: Rework Netmask test to inlude valid base ip address
# VALID_NETMASKS = [("255.255.255.255", "/32"), ("255.255.255.254", "/31"), ("255.255.255.0", "/24"), ("255.255.240.0", "/20"), ("255.248.0.0", "/13"), ("192.0.0.0", "/2"), ("128.0.0.0", "/1")]


def pair(element_list):
    """Provides a list of all possible pairs with the list separator"""
    return list(itertools.combinations(element_list, 2))


def make_multi_cases(cases, max_length=3):
    """Converts a list of cases into a list of list of cases"""
    return [
        list(item)
        for sublist in [
            list(itertools.combinations(cases, i + 1)) for i in range(max_length - 1)
        ]
        for item in sublist
    ]


def question_strs(questions):
    """Converts a list of question functions into their string names"""
    output = []
    for question in questions:
        if isinstance(question, partial):
            output.append(
                "{}{}{}".format(
                    question.func.__name__, question.args, question.keywords
                )
            )
        elif hasattr(question, "__name__"):
            output.append(question.__name__)
        else:
            output.append(question.__class__.__name__)
    return output
