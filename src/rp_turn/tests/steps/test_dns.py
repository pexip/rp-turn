"""
Tests the DNSStep from the installwizard
"""

# Standard library imports
from functools import partial

# 3rd party imports
from unittest import mock
from unittest.mock import patch

# Import steps and default cases
import rp_turn.tests.steps as tests
import rp_turn.tests.utils as test_utils

# Local application/library specific imports
from rp_turn import steps, utils


class TestDNSStep(tests.TestMultiQuestion):
    """Test the DNSStep"""

    def setUp(self):
        self._config = {}
        self._step = steps.DNSStep
        self._state_id = "dns"
        self._question = "_get_another_answer"
        self._valid_cases = test_utils.VALID_IP_ADDRESSES
        self._invalid_cases = test_utils.INVALID_IP_ADDRESSES


def dummy_file_contents(open_mock, resolver_filepath=None, dns_servers=None):
    """Fakes reading of a file"""
    if resolver_filepath is None:
        resolver_filepath = "/etc/resolv.conf"
    if dns_servers is None:
        dns_servers = []
    filepath = open_mock.call_args_list[-1][0][0]
    if filepath == resolver_filepath:
        output = """\
# This file is managed by man:systemd-resolved(8). Do not edit.
#
# This is a dynamic resolv.conf file for connecting local clients directly to
# all known uplink DNS servers. This file lists all configured search domains.
#
# Third party programs must not access this file directly, but only through the
# symlink at /etc/resolv.conf. To manage man:resolv.conf(5) in a different way,
# replace this symlink by a static file or a different symlink.
#
# See man:systemd-resolved.service(8) for details about the supported modes of
# operation for /etc/resolv.conf.
search rd.pexip.com hurst.pexip.com
        """
        for server in dns_servers:
            output += "\nnameserver " + server
        output += "\nsearch rd.pexip.com hurst.pexip.com"
        return output
    raise IOError(filepath + " does not have a fake contents defined")


class TestDefaultConfig(tests.TestDefaultConfig):
    """Tests getting dns servers from saved config file"""

    def setUp(self):
        tests.TestDefaultConfig.setUp(self)
        self._step = steps.DNSStep
        self._state_id = "dns"
        self._valid_cases = [
            list(a) for a in test_utils.make_multi_cases(test_utils.VALID_IP_ADDRESSES)
        ]

    def test_dhcp_resolve(self):
        """Tests getting dns servers from dhcp"""
        dns_servers = ["1.2.3.4", "5.6.7.8"]
        # mock read
        open_mock = mock.MagicMock(spec=open)
        read_mock = mock.MagicMock()
        read_mock.read.side_effect = partial(
            dummy_file_contents,
            open_mock=open_mock,
            dns_servers=dns_servers + ["127.0.0.1", "badip"],
        )
        open_mock.return_value.__enter__.return_value = read_mock

        # monkeypatches
        with patch.object(steps.dns, "open", open_mock, create=True):
            default_config, saved_config, _ = self.setup_question(
                None, question_str=self._question_default_config
            )
            config = utils.nested_dict()
            default_config(saved_config, config)
            self.assertEqual(
                utils.get_config_value_by_path(config, self._state_id), dns_servers
            )
