# pylint: disable=consider-using-from-import
# pylint: disable=consider-using-with
"""
Pexip Configuration Applicator
"""
from __future__ import print_function
import logging
import os
import subprocess
from ipaddress import IPv4Interface
import yaml
import jinja2

import si.apps.reverseproxy.utils as utils
import si.platform.filesystem.filewriter as filewriter

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class ConfigApplicator:
    """
    Configuration applicator.
    """

    def __init__(self, config):
        self._config = config
        # Setup jinja to load templates
        template_loader = jinja2.FileSystemLoader(
            searchpath=os.path.dirname(os.path.abspath(__file__)) + "/templates/"
        )
        self._template_env = jinja2.Environment(loader=template_loader)

    def fqdn(self):
        """
        Returns the fully qualified domain name
        """
        return self._config["hostname"] + "." + self._config["domain"]

    def apply(self):
        """
        Apply collected configuration to system.
        """
        print("Applying configuration...")
        self._apply_base_network_config()
        self._apply_ntp_server_config()
        self._apply_nginx_server_config()
        self._apply_iptables_config()
        self._apply_certificate_config()
        self._apply_turn_config()
        self._apply_fail2ban()
        self._apply_snmp()

    def _apply_base_network_config(self):
        """
        Set base network config (ip, mask, gw), (hostname)
        """
        DEV_LOGGER.info("Applying netplan")
        # Write interfaces file
        netplan = {"network": {"version": 2, "renderer": "networkd", "ethernets": {}}}
        enabled_nics = {self._config["internal"], self._config["external"]}
        for nic in enabled_nics:
            network = self._config["networks"][nic]
            netplan["network"]["ethernets"][nic] = {
                "dhcp4": False,
                "dhcp6": False,
                "addresses": [
                    str(
                        IPv4Interface(
                            str(network["ipaddress"] + "/" + network["netmask"])
                        )
                    )
                ],
                "nameservers": {"addresses": utils.config_get(self._config["dns"])},
            }
            # Only add gateway if it exists
            if utils.config_get(network["gateway"]) not in [None, ""]:
                netplan["network"]["ethernets"][nic]["gateway4"] = network["gateway"]
            # Only add routes if it exists
            if utils.config_get(network["routes"]) not in [None, []]:
                netplan["network"]["ethernets"][nic]["routes"] = [
                    dict(route) for route in network["routes"]
                ]
        DEV_LOGGER.info("Netplan dict: %s", netplan)

        # Disables &id001 aliases in the yaml output
        noalias_dumper = yaml.dumper.SafeDumper
        noalias_dumper.ignore_aliases = lambda self, data: True

        netcfg_yaml = yaml.dump(
            netplan, default_flow_style=False, Dumper=noalias_dumper
        )
        netplan_filepath = "/etc/netplan/01-netcfg.yaml"
        filewriter.HeadedFileWriter(netplan_filepath).write(netcfg_yaml)
        DEV_LOGGER.info("Writing to %s: %s", netplan_filepath, netcfg_yaml)

        # Write hostname file
        hostname = self._config["hostname"]
        domain = self._config["domain"]
        hostname_filepath = "/etc/hostname"
        filewriter.FileWriter(hostname_filepath).write(hostname)
        DEV_LOGGER.info("Writing to %s: %s", hostname_filepath, hostname)

        # Write hosts file
        hosts_template = self._template_env.get_template("hosts")
        hosts = hosts_template.render(hostname=hostname, domain=domain)
        hosts_filepath = "/etc/hosts"
        filewriter.HeadedFileWriter(hosts_filepath).write(hosts)
        DEV_LOGGER.info("Writing to %s: %s", hosts_filepath, hosts)

    def _apply_ntp_server_config(self):
        """
        Set NTP server configuration.
        """
        DEV_LOGGER.info("Applying ntp")
        servers = self._config["ntp"]
        ntp_template = self._template_env.get_template("ntp.conf")
        ntp_config = ntp_template.render(servers=servers)
        ntp_filepath = "/etc/ntp.conf"
        filewriter.HeadedFileWriter(ntp_filepath).write(ntp_config)
        DEV_LOGGER.info("Writing to %s: %s", ntp_filepath, ntp_config)

    def _apply_nginx_server_config(self):
        """
        Write /etc/nginx/sites-available/pexapp
        """
        DEV_LOGGER.info("Applying nginx")
        if self._config["enablewebloadbalance"]:
            confnodes = self._config["conferencenodes"]
            addresses = [
                network["ipaddress"] for network in self._config["networks"].values()
            ]
            fqdn = self.fqdn()
            enablecsp = self._config["enablecsp"]
            mgmtnets = self._config["managementnetworks"]

            template = self._template_env.get_template("nginx")
            nginx_config = template.render(
                confnodes=confnodes,
                addresses=addresses,
                mgmtnets=mgmtnets,
                fqdn=fqdn,
                enablecsp=enablecsp,
            )
            nginx_filepath = "/etc/nginx/sites-available/pexapp"
            filewriter.FileWriter("/etc/nginx/sites-available/pexapp").write(
                nginx_config
            )
            DEV_LOGGER.info("Writing to %s: %s", nginx_filepath, nginx_config)

            utils.run_shell("/bin/systemctl enable nginx")
        else:
            utils.run_shell("/bin/systemctl disable nginx")

    def _apply_iptables_config(self):
        """
        Write /home/pexip/iptables.rules
        """
        # pylint: disable=too-many-locals
        DEV_LOGGER.info("Applying iptables")
        # Allow access to ssh for supplied managementnetworks on internal interface only
        management_networks = self._config["managementnetworks"]
        internal_interface = self._config["internal"]
        external_interface = self._config["external"]
        internal_ip = self._config["networks"][internal_interface]["ipaddress"]
        external_ip = self._config["networks"][external_interface]["ipaddress"]

        webloadbalance_enabled = self._config["enablewebloadbalance"]
        conferencenodes = self._config["conferencenodes"]
        conferencenodes = conferencenodes if conferencenodes else []
        turnserver_enabled = self._config["turnserver"]["enabled"]
        medianodes = self._config["medianodes"]
        medianodes = medianodes if medianodes else []
        turnserver_443 = self._config["turnserver"]["port443"]
        client_turn = self._config["turnserver"]["clientturn"]
        snmp_enabled = self._config["snmp"]["enabled"]

        # Save rules into a temporary file
        template = self._template_env.get_template("iptables.rules")
        iptables_config = template.render(
            management_networks=management_networks,
            internal_ip=internal_ip,
            external_ip=external_ip,
            webloadbalance_enabled=webloadbalance_enabled,
            turnserver_enabled=turnserver_enabled,
            snmp_enabled=snmp_enabled,
            turnserver_443=turnserver_443,
            client_turn=client_turn,
            medianodes=medianodes,
            conferencenodes=conferencenodes,
            allnodes=set(conferencenodes + medianodes),
        )
        iptables_filepath = "/home/pexip/iptables.rules"
        # iptables-restore crashes without this newline
        filewriter.FileWriter(iptables_filepath).write(iptables_config + "\n")
        DEV_LOGGER.info("Writing to %s: %s", iptables_filepath, iptables_config)

        # Make rules persistent
        utils.run_shell(
            "/sbin/iptables -F",
            "/sbin/iptables-restore < /home/pexip/iptables.rules",
            "/usr/sbin/netfilter-persistent save",
        )

        if management_networks:
            # Enable SSH
            utils.run_shell("/bin/systemctl enable ssh.service")
        else:
            # Disable SSH
            utils.run_shell("/bin/systemctl disable ssh.service")

    def _apply_certificate_config(self):
        """
        Create self-signed certificate and store as /etc/nginx/ssl/pexip.pem
        Should be readable only by root and www-data
        """
        # pylint: disable=line-too-long
        DEV_LOGGER.info("Applying generating certificates")
        if utils.config_get(self._config["generate-certs"]["ssl"]):
            utils.run_shell(
                "/usr/bin/openssl req -x509 -newkey rsa:2048 -keyout /etc/nginx/ssl/pexip.pem -out /etc/nginx/ssl/pexip.pem -days 1095 -nodes -config /etc/ssl/pexip.cnf",
                "/bin/chown root:root /etc/nginx/ssl/pexip.pem",
                "/bin/chmod 400 /etc/nginx/ssl",
                "/bin/chmod 400 /etc/nginx/ssl/pexip.pem",
            )
        else:
            DEV_LOGGER.info("Skipped generating SSL")

        # Also create new SSH keys on initial setup
        if utils.config_get(self._config["generate-certs"]["ssh"]):
            utils.run_shell(
                "/bin/rm -f /etc/ssh/ssh_host*",
                "/usr/sbin/dpkg-reconfigure openssh-server",
            )
        else:
            DEV_LOGGER.info("Skipped generating SSH")

    def _apply_turn_config(self):
        """
        Write turnserver config files.
        """

        DEV_LOGGER.info("Applying turnserver")
        turnserver = self._config["turnserver"]
        if turnserver["enabled"]:
            listening_ip = self._config["networks"][self._config["internal"]][
                "ipaddress"
            ]
            relay_ip = self._config["networks"][self._config["external"]]["ipaddress"]
            realm = self._config["domain"]
            tcp_turn = turnserver["port443"]
            medianodes = self._config["medianodes"]
            client_turn = turnserver["clientturn"]

            template = self._template_env.get_template("turnserver.conf")
            turn_conf = template.render(
                listening_ip=listening_ip,
                relay_ip=relay_ip,
                domain=realm,
                tcp_turn=tcp_turn,
                medianodes=medianodes,
                client_turn=client_turn,
            )
            filewriter.HeadedFileWriter("/etc/turnserver.conf").write(turn_conf)

            fnull = open(os.devnull, "wb")

            filewriter.HeadedFileWriter("/etc/default/coturn").write(
                "TURNSERVER_ENABLED=1"
            )
            DEV_LOGGER.info("Enabled turnserver")
            try:
                os.remove("/etc/turnuserdb.conf")  # Clear previous turn users
                DEV_LOGGER.info("Removed previous turnuserdb")
            except OSError:
                DEV_LOGGER.exception("Unable to remove previous turnuserdb")

            run_turnuserdb_chmod = False
            if all(k in turnserver for k in ("username", "password")) and all(
                turnserver[k] for k in ("username", "password")
            ):
                turnuser = turnserver["username"]
                turnpassword = turnserver["password"]
                subprocess.check_call(
                    [
                        "/usr/bin/turnadmin",
                        "-k",
                        "-a",
                        "-b",
                        "/etc/turnuserdb.conf",
                        "-u",
                        turnuser,
                        "-r",
                        realm,
                        "-p",
                        turnpassword,
                    ],
                    stdout=fnull,
                    stderr=fnull,
                )
                DEV_LOGGER.info("Run turnadmin add-user shell command")
                run_turnuserdb_chmod = True
            if (
                client_turn
                and "sharedsecret" in turnserver
                and turnserver["sharedsecret"] is not None
            ):
                shared_secret = turnserver["sharedsecret"]
                subprocess.check_call(
                    [
                        "/usr/bin/turnadmin",
                        "-b",
                        "/etc/turnuserdb.conf",
                        "-r",
                        realm,
                        "-s",
                        shared_secret,
                    ],
                    stdout=fnull,
                    stderr=fnull,
                )
                DEV_LOGGER.info("Run turnadmin shared-secret shell command")
                run_turnuserdb_chmod = True
            if run_turnuserdb_chmod:
                utils.run_shell("/bin/chmod 660 /etc/turnuserdb.conf")
            utils.run_shell("/bin/systemctl enable coturn")
        else:
            filewriter.HeadedFileWriter("/etc/default/coturn").write(
                "TURNSERVER_ENABLED=0"
            )
            utils.run_shell("/bin/systemctl disable coturn")
            DEV_LOGGER.info("Disabled turnserver")

    def _apply_fail2ban(self):
        """
        Enables/disables fail2ban
        """
        if self._config["enablefail2ban"]:
            utils.run_shell("/bin/systemctl enable fail2ban.service")
        else:
            utils.run_shell("/bin/systemctl disable fail2ban.service")

    def _apply_snmp(self):
        """
        Write SNMPv2c read only config files.
        """
        DEV_LOGGER.info("Applying SNMPv2c read only")
        snmp = self._config["snmp"]
        if snmp["enabled"]:
            internal_address = self._config["networks"][self._config["internal"]][
                "ipaddress"
            ]
            snmp_community = self._config["snmp"]["community"]
            snmp_location = self._config["snmp"]["location"]
            snmp_contact = self._config["snmp"]["contact"]
            snmp_name = self._config["snmp"]["name"]
            snmp_description = self._config["snmp"]["description"]

            template = self._template_env.get_template("snmpd.conf")
            snmp_conf = template.render(
                internal_address=internal_address,
                snmp_community=snmp_community,
                snmp_location=snmp_location,
                snmp_contact=snmp_contact,
                snmp_name=snmp_name,
                snmp_description=snmp_description,
            )
            filewriter.HeadedFileWriter("/etc/snmp/snmpd.conf").write(snmp_conf)
            utils.run_shell("/bin/systemctl enable snmpd.service")
        else:
            utils.run_shell("/bin/systemctl disable snmpd.service")
            DEV_LOGGER.info("Disabled turnserver")
