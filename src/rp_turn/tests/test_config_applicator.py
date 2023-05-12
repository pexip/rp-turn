"""
Test the ReverseProxy Config Applicator
"""
from __future__ import annotations

import copy
import logging
from ipaddress import IPv4Interface
from unittest import SkipTest, TestCase
from unittest.mock import patch

import yaml

# Local application/library specific imports
from rp_turn import installwizard, utils

DEV_LOGGER = logging.getLogger("rp_turn.tests")

VALID_CONFIGS = [
    utils.make_nested_dict(
        {
            "networks": {
                "nic0": {
                    "ipaddress": "10.44.4.1",
                    "netmask": "255.255.0.0",
                    "gateway": "10.44.0.1",
                    "routes": [],
                }
            },
            "enablewebloadbalance": True,
            "dns": ["8.8.8.8"],
            "internal": "nic0",
            "external": "nic0",
            "hostname": "reverseproxy",
            "domain": "rd.pexip.com",
            "turnserver": {
                "enabled": True,
                "port443": False,
                "username": "turnusername",
                "password": "turnpassword",
                "sharedsecret": "turnsharedsecret",
                "clientturn": False,
            },
            "enablecsp": True,
            "enablefail2ban": True,
            "ntp": [
                "0.pexip.pool.ntp.org",
                "1.pexip.pool.ntp.org",
                "2.pexip.pool.ntp.org",
            ],
            "conferencenodes": ["10.44.4.2", "10.44.4.3"],
            "medianodes": ["10.44.4.5", "10.44.4.6"],
            "managementnetworks": ["10.0.0.0/8"],
            "snmp": {
                "enabled": True,
                "community": "public",
                "name": "reverseproxy",
                "description": "Pexip reverseproxy",
                "location": "somewhere secret",
                "contact": "admin@pexip.com",
            },
            "generate-certs": {"ssh": True, "ssl": True},
        }
    ),
    utils.make_nested_dict(
        {
            "networks": {
                "nic0": {
                    "ipaddress": "10.44.4.1",
                    "netmask": "255.255.0.0",
                    "gateway": "10.44.0.1",
                    "routes": [],
                },
                "nic1": {
                    "ipaddress": "10.250.4.1",
                    "netmask": "255.255.0.0",
                    "gateway": "10.250.0.1",
                    "routes": [],
                },
            },
            "enablewebloadbalance": True,
            "dns": ["8.8.8.8", "1.1.1.1"],
            "internal": "nic0",
            "external": "nic1",
            "hostname": "reverseproxy",
            "domain": "rd.pexip.com",
            "turnserver": {
                "enabled": True,
                "port443": True,
                "username": "turnusername",
                "password": "turnpassword",
                "clientturn": False,
                "sharedsecret": "turnsharedsecret",
            },
            "enablecsp": False,
            "enablefail2ban": False,
            "ntp": [
                "0.pexip.pool.ntp.org",
                "1.pexip.pool.ntp.org",
                "2.pexip.pool.ntp.org",
            ],
            "conferencenodes": ["10.44.4.2", "10.44.4.3"],
            "medianodes": ["10.44.4.5", "10.44.4.6"],
            "managementnetworks": ["10.0.0.0/8", "172.0.0.0/8"],
            "snmp": {"enabled": False},
            "generate-certs": {"ssh": False, "ssl": False},
        }
    ),
    utils.make_nested_dict(
        {
            "networks": {
                "nic0": {
                    "ipaddress": "10.44.4.1",
                    "netmask": "255.255.0.0",
                    "gateway": "10.44.0.1",
                    "routes": [],
                },
                "nic1": {
                    "ipaddress": "10.250.4.1",
                    "netmask": "255.255.0.0",
                    "gateway": "10.250.0.1",
                    "routes": [],
                },
            },
            "enablewebloadbalance": True,
            "dns": ["8.8.8.8", "1.1.1.1"],
            "internal": "nic0",
            "external": "nic1",
            "hostname": "reverseproxy",
            "domain": "rd.pexip.com",
            "turnserver": {
                "enabled": True,
                "port443": True,
                "username": "turnusername",
                "password": "turnpassword",
                "clientturn": True,
                "sharedsecret": "turnsharedsecret",
            },
            "enablecsp": False,
            "enablefail2ban": False,
            "ntp": [
                "0.pexip.pool.ntp.org",
                "1.pexip.pool.ntp.org",
                "2.pexip.pool.ntp.org",
            ],
            "conferencenodes": ["10.44.4.2", "10.44.4.3"],
            "medianodes": ["10.44.4.5", "10.44.4.6"],
            "managementnetworks": ["10.0.0.0/8", "172.0.0.0/8"],
            "snmp": {"enabled": False},
            "generate-certs": {"ssh": False, "ssl": False},
        }
    ),
]


class DummyFileWriter:  # pylint: disable=too-few-public-methods
    """A fake filewriter"""

    def __init__(self, path):
        self._path = path
        if path not in TestDefaultSettings.DummyFileSystem:
            TestDefaultSettings.DummyFileSystem[path] = ""

    def write(self, contents, _mode=0o644, _backup=True):
        """Writes contents to a fake file"""
        TestDefaultSettings.DummyFileSystem[self._path] += contents


def mock_check_call(
    command, stdout=None, stderr=None, shell=None  # pylint: disable=unused-argument
):
    """Dummy shell call to verify called commands"""
    if " >> " in command and (
        command.startswith("echo ") or command.startswith("/bin/echo ")
    ):
        path = command.split(" >> ")[1]
        file_writer = DummyFileWriter(path)
        contents = command.split(" >> ")[0].replace("/bin/", "").replace("echo ", "")
        file_writer.write(contents)
    else:
        TestDefaultSettings.DummyTerminal.append(command)


class TestDefaultSettings(TestCase):
    """Base class to check if config values are applied"""

    DummyFileSystem: dict[str, str] = {}
    DummyTerminal: list[str] = []

    def __init__(self, methodname, function_to_test=None):
        super().__init__(methodname)
        self._function_to_test = function_to_test
        self._config = None
        self._applicator = None
        self._function = None

    @patch("os.path.exists")
    @patch("subprocess.check_call")
    @patch("rp_turn.platform.filewriter.HeadedFileWriter")
    @patch("rp_turn.platform.filewriter.FileWriter")
    def _run_settings_applied_test(
        self,
        filewriter_mock,
        headed_filewriter_mock,
        subprocess_mock,
        os_path_exists_mock,
    ):
        """Runs the settings applied test"""
        self._applicator = installwizard.ConfigApplicator(self._config)
        if self._function_to_test:
            self._function = getattr(self._applicator, self._function_to_test)
        else:
            self._function = lambda: None
        TestDefaultSettings.DummyFileSystem = {}
        TestDefaultSettings.DummyTerminal = []

        filewriter_mock.side_effect = DummyFileWriter
        headed_filewriter_mock.side_effect = DummyFileWriter
        subprocess_mock.side_effect = mock_check_call
        os_path_exists_mock.side_effect = (
            lambda path: path in TestDefaultSettings.DummyFileSystem
        )
        self._function()
        self.is_settings_valid()

    def test_simple_settings_applied(
        self,
    ):
        """Tests whether the simple settings are applied"""
        self._config = copy.deepcopy(VALID_CONFIGS[0])
        self._run_settings_applied_test()  # pylint: disable=no-value-for-parameter

    def test_advanced_settings_applied(self):
        """Tests whether the advanced settings are applied"""
        self._config = copy.deepcopy(VALID_CONFIGS[1])
        self._run_settings_applied_test()  # pylint: disable=no-value-for-parameter

    def test_client_turn_settings_applied(self):
        """Tests whether the client turn settings are applied"""
        self._config = copy.deepcopy(VALID_CONFIGS[2])
        self._run_settings_applied_test()  # pylint: disable=no-value-for-parameter

    def is_settings_valid(self):
        """Tests if settings are valid"""
        # pylint: disable=pointless-exception-statement
        SkipTest("Unimplemented")


class TestBaseNetworkSettings(TestDefaultSettings):
    """Test ConfigApplicator._apply_base_network_config"""

    def __init__(self, methodname):
        super().__init__(methodname, "_apply_base_network_config")

    def is_settings_valid(self):
        netplan_yaml = yaml.safe_load(
            TestDefaultSettings.DummyFileSystem["/etc/netplan/01-netcfg.yaml"]
        )
        for nic_name, adapter in self._config["networks"].items():
            nic = netplan_yaml["network"]["ethernets"][nic_name]
            self.assertFalse(nic["dhcp4"])
            self.assertFalse(nic["dhcp6"])
            self.assertEqual(
                nic["addresses"],
                [
                    str(
                        IPv4Interface(
                            str(adapter["ipaddress"] + "/" + adapter["netmask"])
                        )
                    )
                ],
            )
            self.assertEqual(nic["gateway4"], adapter["gateway"])
            self.assertEqual(nic["nameservers"]["addresses"], self._config["dns"])
        self.assertIn(
            self._config["hostname"],
            TestDefaultSettings.DummyFileSystem["/etc/hostname"],
        )
        self.assertIn(
            self._config["hostname"], TestDefaultSettings.DummyFileSystem["/etc/hosts"]
        )
        self.assertIn(
            self._config["domain"], TestDefaultSettings.DummyFileSystem["/etc/hosts"]
        )

    @patch("os.remove")
    @patch("os.path.exists")
    @patch("subprocess.check_call")
    @patch("rp_turn.platform.filewriter.HeadedFileWriter")
    @patch("rp_turn.platform.filewriter.FileWriter")
    def test_remove_cloud_init_fallback(
        self,
        _filewriter_mock,
        _headed_filewriter_mock,
        _subprocess_mock,
        os_path_exists_mock,
        os_remove_mock,
    ):
        """Test removal of cloud-init fallback network config if it exists"""
        config = utils.make_nested_dict(
            {
                "networks": {
                    "nic0": {
                        "ipaddress": "10.44.4.1",
                        "netmask": "255.255.0.0",
                        "gateway": "10.44.0.1",
                        "routes": [],
                    }
                },
                "internal": "nic0",
                "external": "nic0",
                "dns": ["8.8.8.8", "1.1.1.1"],
                "hostname": "reverseproxy",
                "domain": "rd.pexip.com",
            }
        )
        applicator = installwizard.ConfigApplicator(config)

        # Fallback exists
        os_path_exists_mock.return_value = True
        applicator._apply_base_network_config()  # pylint: disable=protected-access
        os_remove_mock.assert_called_once_with("/etc/netplan/50-cloud-init.yaml")

        os_path_exists_mock.reset_mock()
        os_remove_mock.reset_mock()

        # Fallback doesn't exist
        os_path_exists_mock.return_value = False
        applicator._apply_base_network_config()  # pylint: disable=protected-access
        os_remove_mock.assert_not_called()


class TestNtpServerSettings(TestDefaultSettings):
    """Test ConfigApplicator._apply_ntp_server_config"""

    def __init__(self, methodname):
        super().__init__(methodname, "_apply_ntp_server_config")

    def is_settings_valid(self):
        for server in self._config["ntp"]:
            self.assertIn(server, TestDefaultSettings.DummyFileSystem["/etc/ntp.conf"])


class TestNginxServerSettings(TestDefaultSettings):
    """Test ConfigApplicator._apply_nginx_server_config"""

    def __init__(self, methodname):
        super().__init__(methodname, "_apply_nginx_server_config")

    def is_settings_valid(self):
        nginx_filepath = "/etc/nginx/sites-available/pexapp"
        if self._config["enablewebloadbalance"]:
            nginx_file = TestDefaultSettings.DummyFileSystem[nginx_filepath]
            for node in self._config["conferencenodes"]:
                self.assertIn(node, nginx_file)
            for network in self._config["managementnetworks"]:
                self.assertIn(network, nginx_file)
            if self._config["enablecsp"]:
                self.assertIn("add_header Content-Security-Policy", nginx_file)
            else:
                self.assertNotIn("add_header Content-Security-Policy", nginx_file)
        else:
            self.assertNotIn(nginx_filepath, TestDefaultSettings.DummyFileSystem)


class TestIPTablesSettings(TestDefaultSettings):
    """Test ConfigApplicator._apply_iptables_config"""

    def __init__(self, methodname):
        super().__init__(methodname, "_apply_iptables_config")
        self.rules = None

    @staticmethod
    def find_arg(rule, argname):
        """Finds the argument from a rule if it is present"""
        return rule[rule.index(argname) + 1] if argname in rule else None

    def contains_rule(self, expected_rule):
        """Checks whether a set of iptables rules contains an expected rule"""
        for rule in self.rules:
            rule_accepted = True
            for expected_arg, expected_value in expected_rule:
                if TestIPTablesSettings.find_arg(rule, expected_arg) != expected_value:
                    rule_accepted = False
                    break
            if rule_accepted:
                return True
        return False

    def assertRule(self, expected_rule):  # pylint: disable=invalid-name
        """Asserts if IPTables rule is set"""
        self.assertTrue(self.contains_rule(expected_rule))

    def assertNotRule(self, expected_rule):  # pylint: disable=invalid-name
        """Asserts if IPTables rule is not set"""
        self.assertFalse(self.contains_rule(expected_rule))

    def assertStandardRule(self, expected_rule):  # pylint: disable=invalid-name
        """
        Asserts if a standard IPTables rule is set
        Sets some default arguments to the rule
        """
        default_expected_rule = [
            ("-m", "conntrack"),
            ("--ctstate", "NEW"),
            ("-j", "ACCEPT"),
        ]
        self.assertRule(expected_rule + default_expected_rule)

    def assertNotStandardRule(self, expected_rule):  # pylint: disable=invalid-name
        """
        Asserts if a standard IPTables rule is not set
        Sets some default arguments to the rule
        """
        default_expected_rule = [
            ("-m", "conntrack"),
            ("--ctstate", "NEW"),
            ("-j", "ACCEPT"),
        ]
        self.assertNotRule(expected_rule + default_expected_rule)

    def is_settings_valid(self):
        # pylint: disable=too-many-branches
        iptables_filename = "/home/pexip/iptables.rules"
        iptables_file = TestDefaultSettings.DummyFileSystem[iptables_filename]
        external_ip = self._config["networks"][self._config["external"]]["ipaddress"]
        internal_ip = self._config["networks"][self._config["internal"]]["ipaddress"]
        turn_out_port = "49152:65535"
        pexip_media_range = "10000:49999"
        self.rules = [rule.split(" ") for rule in iptables_file.split("\n")]
        # TODO: assert ordering of rules
        # Check all management networks have ssh access
        for network in self._config["managementnetworks"]:
            self.assertStandardRule(
                [
                    ("-A", "INPUT"),
                    ("--source", network),
                    ("--destination", internal_ip),
                    ("-p", "tcp"),
                    ("--dport", "22"),
                ]
            )
        # Check that access to turn ports works, if turn is enabled
        if self._config["turnserver"]["enabled"]:
            if self._config["turnserver"]["clientturn"]:
                turn_ctrl_port = (
                    "443" if self._config["turnserver"]["port443"] else "3478"
                )
                for protocol in ("udp", "tcp"):
                    self.assertStandardRule(
                        [
                            ("-A", "INPUT"),
                            ("-m", "conntrack"),
                            ("--ctstate", "NEW"),
                            ("-p", protocol),
                            ("--dport", turn_ctrl_port),
                            ("-j", "ACCEPT"),
                        ]
                    )
                self.assertStandardRule(
                    [
                        ("-A", "OUTPUT"),
                        ("-m", "conntrack"),
                        ("--ctstate", "NEW"),
                        ("-p", "udp"),
                        ("--sport", "49152:65535"),
                        ("-j", "ACCEPT"),
                    ]
                )
            elif self._config["turnserver"]["port443"]:
                self.assertStandardRule(
                    [
                        ("-A", "INPUT"),
                        ("-p", "tcp"),
                        ("--destination", external_ip),
                        ("--dport", "443"),
                    ]
                )
                for medianode in self._config["medianodes"]:
                    self.assertStandardRule(
                        [
                            ("-A", "OUTPUT"),
                            ("-p", "udp"),
                            ("--destination", medianode),
                            ("--sport", turn_out_port),
                            ("--dport", pexip_media_range),
                        ]
                    )
            else:
                # TODO: check for ('-m', 'u32') in rule below
                self.assertRule(
                    [
                        ("-A", "INPUT"),
                        ("-m", "conntrack"),
                        ("--ctstate", "NEW"),
                        ("-p", "udp"),
                        ("--dport", "3478"),
                        ("--u32", '"26&0xFFFF=0x0001"'),
                        ("-j", "ACCEPT"),
                    ]
                )
                for medianode in self._config["medianodes"]:
                    self.assertRule(
                        [
                            ("-A", "INPUT"),
                            ("-m", "conntrack"),
                            ("--ctstate", "NEW,ESTABLISHED,RELATED"),
                            ("-p", "udp"),
                            ("--source", medianode),
                            ("--dport", "3478"),
                            ("-j", "ACCEPT"),
                        ]
                    )
                self.assertStandardRule(
                    [
                        ("-A", "OUTPUT"),
                        ("-p", "udp"),
                        ("--source", external_ip),
                        ("--sport", turn_out_port),
                    ]
                )
        # Check default is to drop on INPUT and FORWARD execpt for lo
        self.assertIn([":INPUT", "DROP", "[0:0]"], self.rules)
        self.assertIn([":FORWARD", "DROP", "[0:0]"], self.rules)
        self.assertRule([("-A", "INPUT"), ("-i", "lo"), ("-j", "ACCEPT")])
        self.assertRule([("-A", "OUTPUT"), ("-o", "lo"), ("-j", "ACCEPT")])
        # Allow HTTP/HTTPS traffic
        if self._config["enablewebloadbalance"]:
            self.assertStandardRule([("-A", "INPUT"), ("-p", "tcp"), ("--dport", "80")])
            self.assertStandardRule(
                [("-A", "INPUT"), ("-p", "tcp"), ("--dport", "443")]
            )
            for node in self._config["conferencenodes"]:
                self.assertStandardRule(
                    [
                        ("-A", "OUTPUT"),
                        ("-p", "tcp"),
                        ("--destination", node),
                        ("--dport", "443"),
                    ]
                )
        else:
            self.assertNotStandardRule(
                [("-A", "INPUT"), ("-p", "tcp"), ("--dport", "80")]
            )
            if not self._config["turnserver"]["port443"]:
                self.assertNotStandardRule(
                    [("-A", "INPUT"), ("-p", "tcp"), ("--dport", "443")]
                )
            for node in self._config["conferencenodes"]:
                self.assertNotStandardRule(
                    [
                        ("-A", "OUTPUT"),
                        ("-p", "tcp"),
                        ("--destination", node),
                        ("--dport", "443"),
                    ]
                )
        # Allow established connections
        self.assertRule(
            [
                ("-A", "INPUT"),
                ("-m", "conntrack"),
                ("--ctstate", "ESTABLISHED,RELATED"),
                ("-j", "ACCEPT"),
            ]
        )
        # Disable all other outgoing traffic to infinity nodes
        for node in self._config["conferencenodes"] + self._config["medianodes"]:
            self.assertRule(
                [("-A", "OUTPUT"), ("--destination", node), ("-j", "LOGGING")]
            )

        # All ports
        self.assertRule(
            [("-A", "OUTPUT"), ("-p", "tcp"), ("--dport", "1:1023"), ("-j", "LOGGING")]
        )

        # Check commands are run to save the rules
        self.assertEqual(
            TestDefaultSettings.DummyTerminal,
            [
                "/sbin/iptables -F",
                "/sbin/iptables-restore < /home/pexip/iptables.rules",
                "/usr/sbin/netfilter-persistent save",
                "/bin/systemctl enable ssh.service",
            ],
        )


class TestCertificateSettings(TestDefaultSettings):
    """Test ConfigApplicator._apply_certificates"""

    def __init__(self, methodname):
        super().__init__(methodname, "_apply_certificate_config")

    def is_settings_valid(self):
        if (
            self._config["generate-certs"]["ssl"]
            and self._config["generate-certs"]["ssh"]
        ):
            self.assertEqual(
                TestDefaultSettings.DummyTerminal,
                [
                    "/usr/bin/openssl req -x509 -newkey rsa:2048 -keyout /etc/nginx/ssl/pexip.pem -out "
                    "/etc/nginx/ssl/pexip.pem -days 1095 -nodes -config /etc/ssl/pexip.cnf",
                    "/bin/chown root:root /etc/nginx/ssl/pexip.pem",
                    "/bin/chmod 400 /etc/nginx/ssl",
                    "/bin/chmod 400 /etc/nginx/ssl/pexip.pem",
                    "/bin/rm -f /etc/ssh/ssh_host*",
                    "/usr/sbin/dpkg-reconfigure openssh-server",
                ],
            )
        elif (
            not self._config["generate-certs"]["ssl"]
            and not self._config["generate-certs"]["ssh"]
        ):
            self.assertEqual(TestDefaultSettings.DummyTerminal, [])


class TestTurnServerSettings(TestDefaultSettings):
    """Test ConfigApplicator._apply_turn_config"""

    def __init__(self, methodname):
        super().__init__(methodname, "_apply_turn_config")

    def is_settings_valid(self):
        turnconf_file = TestDefaultSettings.DummyFileSystem["/etc/turnserver.conf"]
        external_nic = self._config["networks"][self._config["external"]]
        internal_nic = self._config["networks"][self._config["internal"]]
        self.assertIn("listening-ip=" + internal_nic["ipaddress"], turnconf_file)
        self.assertIn("relay-ip=" + external_nic["ipaddress"], turnconf_file)
        self.assertIn("realm=" + self._config["domain"], turnconf_file)
        self.assertIn("userdb=/etc/turnuserdb.conf", turnconf_file)
        if self._config["turnserver"]["port443"]:
            self.assertIn("listening-port=443", turnconf_file)
            if not self._config["turnserver"]["clientturn"]:
                self.assertIn("allowed-peer-ip=10.44.4.5", turnconf_file)
                self.assertIn("allowed-peer-ip=10.44.4.6", turnconf_file)
                self.assertEqual(turnconf_file.count("allowed-peer-ip="), 2)
                self.assertIn("denied-peer-ip=0.0.0.0-255.255.255.255", turnconf_file)
            else:
                self.assertNotIn(
                    "denied-peer-ip=0.0.0.0-255.255.255.255", turnconf_file
                )
        else:
            self.assertIn("listening-port=3478", turnconf_file)
            self.assertNotIn("denied-peer-ip=0.0.0.0-255.255.255.255", turnconf_file)
            self.assertEqual(turnconf_file.count("allowed-peer-ip="), 0)

        if self._config["turnserver"]["clientturn"]:
            self.assertIn("use-auth-secret", turnconf_file)
        else:
            self.assertNotIn("use-auth-secret", turnconf_file)


class TestFail2BanSettings(TestDefaultSettings):
    """Test ConfigApplicator._apply_fail2ban"""

    def __init__(self, methodname):
        super().__init__(methodname, "_apply_fail2ban")

    def is_settings_valid(self):
        if self._config["enablefail2ban"]:
            self.assertEqual(
                TestDefaultSettings.DummyTerminal,
                ["/bin/systemctl enable fail2ban.service"],
            )
        else:
            self.assertEqual(
                TestDefaultSettings.DummyTerminal,
                ["/bin/systemctl disable fail2ban.service"],
            )


class TestSNMPSettings(TestDefaultSettings):
    """Test ConfigApplicator._apply_snmp"""

    def __init__(self, methodname):
        super().__init__(methodname, "_apply_snmp")

    def is_settings_valid(self):
        if self._config["snmp"]["enabled"]:
            snmpconf_file = TestDefaultSettings.DummyFileSystem["/etc/snmp/snmpd.conf"]
            snmp_config = self._config["snmp"]
            self.assertIn("rocommunity " + snmp_config["community"], snmpconf_file)
            self.assertIn("sysLocation    " + snmp_config["location"], snmpconf_file)
            self.assertIn("sysContact     " + snmp_config["contact"], snmpconf_file)
            self.assertIn("sysName        " + snmp_config["name"], snmpconf_file)
            self.assertIn("sysDescr       " + snmp_config["description"], snmpconf_file)
        else:
            self.assertEqual(
                TestDefaultSettings.DummyTerminal,
                ["/bin/systemctl disable snmpd.service"],
            )
