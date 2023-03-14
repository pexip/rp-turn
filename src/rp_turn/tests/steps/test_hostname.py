"""
Tests the HostnameStep from the installwizard
"""
# Standard library imports
import copy
from functools import partial

# 3rd party imports
from unittest import mock
from unittest.mock import patch

# Local application/library specific imports
import rp_turn.tests.steps as tests
import rp_turn.tests.utils as test_utils
from rp_turn import steps, utils

STEPCLASS = steps.hostname.HostnameStep


class TestGetHostname(tests.TestQuestion):
    """Test the __get_hostname question from the HostnameStep"""

    def setUp(self):
        self._step = STEPCLASS
        self._state_id = "hostname"
        self._question = "_get_hostname"
        self._valid_cases = test_utils.VALID_HOSTNAMES
        self._invalid_cases = (
            test_utils.INVALID_DOMAINS
            + test_utils.VALID_IP_ADDRESSES
            + [".", "a.b", "b.", "asfdas3dgadf.b.sdfafas.asdfas"]
        )


class TestGetDomain(tests.TestQuestion):
    """Test the __get_domain question from the HostnameStep"""

    def setUp(self):
        self._step = STEPCLASS
        self._state_id = "domain"
        self._question = "_get_domain"
        self._valid_cases = test_utils.VALID_DOMAIN_NAMES
        self._invalid_cases = test_utils.INVALID_DOMAINS


class TestDefaultConfigHostname(tests.TestDefaultConfig):
    """Test getting the hostname from a default config"""

    def setUp(self):
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = "hostname"
        self._valid_cases = test_utils.VALID_HOSTNAMES


def dummy_file_contents(open_mock, resolver_filepath=None, domains=None):
    """Fakes file read"""
    if resolver_filepath is None:
        resolver_filepath = "/etc/resolv.conf"
    if domains is None:
        domains = []
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
nameserver 10.44.0.1

        """
        output += "\nsearch " + " ".join(domains)
        output += """\
namesever 8.8.8.8
namesever 8.8.4.4
"""
        return output
    raise IOError(filepath + " does not have a fake contents defined")


class TestDefaultConfigDomain(tests.TestDefaultConfig):
    """Test getting the domain from a default config"""

    def setUp(self):
        tests.TestDefaultConfig.setUp(self)
        self._step = STEPCLASS
        self._state_id = "domain"
        self._valid_cases = test_utils.VALID_DOMAIN_NAMES

    def test_dhcp_domain(self):
        """Tests getting the domain from dhcp"""
        domains = test_utils.VALID_DOMAIN_NAMES
        invalid_domains = copy.deepcopy(test_utils.INVALID_DOMAINS)
        invalid_domains.remove(
            "my domain"
        )  # While this is an invalid domain, the DHCP list is space separated
        # mock read
        open_mock = mock.MagicMock(spec=open)
        read_mock = mock.MagicMock()
        for domain in domains:
            read_mock.read.side_effect = partial(
                dummy_file_contents,
                open_mock=open_mock,
                domains=invalid_domains + [domain] + invalid_domains,
            )
            open_mock.return_value.__enter__.return_value = read_mock

            # monkeypatches
            with patch.object(steps.hostname, "open", open_mock, create=True):
                default_config, saved_config, _ = self.setup_question(None)
                config = utils.nested_dict()
                default_config(saved_config, config)
                self.assertEqual(
                    utils.get_config_value_by_path(config, self._state_id), domain
                )
