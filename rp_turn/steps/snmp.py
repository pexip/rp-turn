# pylint: disable=consider-using-from-import
"""
Pexip installation wizard step to configure SNMPv2c read only
"""
import logging
from functools import partial

import si.apps.reverseproxy.utils as utils
from si.apps.reverseproxy.steps.base_step import Step, StepError

DEV_LOGGER = logging.getLogger("developer.apps.reverseproxy")


class SNMPStep(Step):
    """Step for SNMPv2c read only"""

    def __init__(self):
        Step.__init__(self, "SNMPv2c read only")
        self.questions = [self._enable_snmp]

    def _enable_snmp(self, config):
        """Question asking whether to enable SNMPv2c read only"""
        default_enabled = utils.config_get(config["snmp"]["enabled"])
        response = self.ask_yes_no("Enable SNMPv2c read only?", default=default_enabled)
        DEV_LOGGER.info("Response: %s", response)
        config["snmp"]["enabled"] = response
        if response:
            self.questions += [
                self._get_community,
                self._get_location,
                self._get_contact,
                self._get_name,
                self._get_description,
            ]

    @staticmethod
    def _validate_community(value):
        """Validates the community field"""
        value = str(value).strip()
        if len(value) > 16:
            raise StepError("SNMP community is too long")
        return value

    def _get_community(self, config):
        """Question asking what community to use"""
        default_community = utils.config_get(config["snmp"]["community"])
        response = self.ask("SNMP community?", default=default_community)
        DEV_LOGGER.info("Response: %s", response)
        config["snmp"]["community"] = self._validate_community(response)

    @staticmethod
    def _validate_location(value):
        """Validates the location field"""
        value = str(value).strip()
        if len(value) > 70:
            raise StepError("SNMP location is too long")
        return value

    def _get_location(self, config):
        """Question asking what location to use"""
        default_location = utils.config_get(config["snmp"]["location"])
        response = self.ask("SNMP system location?", default=default_location)
        DEV_LOGGER.info("Response: %s", response)
        config["snmp"]["location"] = self._validate_location(response)

    @staticmethod
    def _validate_contact(value):
        """Validates the contact field"""
        value = str(value).strip()
        if len(value) > 70:
            raise StepError("SNMP contact is too long")
        return value

    def _get_contact(self, config):
        """Question asking what contact email to use"""
        default_contact = utils.config_get(config["snmp"]["contact"])
        response = self.ask("SNMP system contact?", default=default_contact)
        DEV_LOGGER.info("Response: %s", response)
        config["snmp"]["contact"] = self._validate_contact(response)

    @staticmethod
    def _validate_name(value):
        """Validates the name field"""
        value = str(value).strip()
        if len(value) > 70:
            raise StepError("SNMP name is too long")
        return value

    def _get_name(self, config):
        """Question asking what name to use"""
        default_name = utils.config_get(config["snmp"]["name"])
        response = self.ask("SNMP system name?", default=default_name)
        DEV_LOGGER.info("Response: %s", response)
        config["snmp"]["name"] = self._validate_name(response)

    @staticmethod
    def _validate_description(value):
        """Validates the description field"""
        value = str(value).strip()
        if len(value) > 70:
            raise StepError("SNMP description is too long")
        return value

    def _get_description(self, config):
        """Question asking what description to use"""
        default_description = utils.config_get(config["snmp"]["description"])
        response = self.ask("SNMP system description?", default=default_description)
        DEV_LOGGER.info("Response: %s", response)
        config["snmp"]["description"] = self._validate_description(response)

    def default_config(self, saved_config, config):
        saved_snmp_config = saved_config["snmp"]
        snmp_config = config["snmp"]
        # enabled
        DEV_LOGGER.info("Getting from saved_config: snmp.enabled")
        snmp_config["enabled"] = utils.validated_config_value(
            saved_snmp_config,
            "enabled",
            partial(utils.validate_type, bool),
            fallback=False,
        )

        # community
        DEV_LOGGER.info("Getting from saved_config: snmp.community")
        snmp_config["community"] = utils.validated_config_value(
            saved_snmp_config, "community", self._validate_community
        )
        if snmp_config["community"] is None:
            if not snmp_config["enabled"]:
                # community is not a required field if snmp is disabled
                snmp_config.pop("community", None)
            else:
                snmp_config["community"] = "public"  # Sensible fallback value

        # location
        DEV_LOGGER.info("Getting from saved_config: snmp.location")
        snmp_config["location"] = utils.validated_config_value(
            saved_snmp_config, "location", self._validate_location
        )
        if not snmp_config["enabled"] and snmp_config["location"] is None:
            # location is not a required field if snmp is disabled
            snmp_config.pop("location", None)

        # contact
        DEV_LOGGER.info("Getting from saved_config: snmp.contact")
        snmp_config["contact"] = utils.validated_config_value(
            saved_snmp_config, "contact", self._validate_contact
        )
        if not snmp_config["enabled"] and snmp_config["contact"] is None:
            # contact is not a required field if snmp is disabled
            snmp_config.pop("contact", None)

        # name
        DEV_LOGGER.info("Getting from saved_config: snmp.name")
        snmp_config["name"] = utils.validated_config_value(
            saved_snmp_config, "name", self._validate_name
        )
        if not snmp_config["enabled"] and snmp_config["name"] is None:
            # name is not a required field if snmp is disabled
            snmp_config.pop("name", None)

        # description
        DEV_LOGGER.info("Getting from saved_config: snmp.description")
        snmp_config["description"] = utils.validated_config_value(
            saved_snmp_config, "description", self._validate_description
        )
        if not snmp_config["enabled"] and snmp_config["description"] is None:
            # description is not a required field if snmp is disabled
            snmp_config.pop("description", None)
