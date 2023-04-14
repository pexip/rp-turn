#!/usr/bin/env python3

"""
Network interface name configurator.
"""

# pylint: disable=unspecified-encoding


from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

from rp_turn.platform import filewriter

LOGGER = logging.getLogger("bootstrap.set_interface_names")


class InterfaceMapper:  # pylint: disable=too-few-public-methods
    """Map physical device locations to logical network interface names"""

    _UDEV_RULES_PATH = "/etc/udev/rules.d/76-nic-names.rules"
    _SYSFS_PATH = "/sys/class/net/"

    def __init__(self, args: argparse.Namespace) -> None:
        self._args = args

        # Path ID -> ( name, hyperv_flag )
        self._interface_map: dict[str, tuple[str, bool]] = {}

        self._read_udev_rules()

    def run(self) -> None:
        """Perform the device name mapping."""
        active_devices = self._read_active_devices()

        new_devices = [
            device for device in active_devices if device not in self._interface_map
        ]
        known_devices = [
            device for device in active_devices if device in self._interface_map
        ]

        if self._interface_map and not known_devices:
            LOGGER.warning("All known NICs have vanished. Resetting.")
            self._interface_map = {}

        if new_devices:
            index = len(self._interface_map)
            for device in sorted(new_devices, key=lambda a: active_devices[a][1]):
                self._interface_map[device] = (f"nic{index}", active_devices[device][2])
                LOGGER.info(
                    'Found new NIC. Path="%s" Name="%s"',
                    device,
                    self._interface_map[device][0],
                )
                index += 1

            self._write_udev_rules()

            if self._args.force:
                # Forcibly set the names of any new devices: udev has already run
                for device in new_devices:
                    subprocess.check_call(
                        [
                            "/bin/ip",
                            "link",
                            "set",
                            "dev",
                            active_devices[device][0],
                            "name",
                            self._interface_map[device][0],
                        ]
                    )

    def _read_active_devices(self) -> dict[str, tuple[str, int, bool]]:
        """Obtain the currently active devices."""
        # Path ID -> ( name, index, hyperv_flag )
        active_devices: dict[str, tuple[str, int, bool]] = {}

        retry = True
        while retry:
            retry = False
            active_devices = {}

            for item in os.listdir(self._SYSFS_PATH):
                path: bytes | None = None
                index: bytes | None = None
                devpath: bytes | None = None
                hyperv: bool = False

                try:
                    output = subprocess.check_output(
                        ["/bin/udevadm", "info", self._SYSFS_PATH + item]
                    )
                    for line in output.splitlines():
                        line = line.strip()

                        if line.startswith(b"E: ID_PATH="):
                            path = line[11:]
                        elif line.startswith(b"E: IFINDEX="):
                            index = line[11:]
                        elif line.startswith(b"E: DEVPATH="):
                            devpath = line[11:]

                    # Hyper-V's bus paths aren't unique so extract the device ID from the devpath
                    if path and path.startswith(b"acpi-VMBUS"):
                        hyperv = True
                        assert isinstance(devpath, bytes)
                        path = devpath.split(b"/")[-3]

                    if path and index:
                        active_devices[path.decode("utf-8")] = (
                            item,
                            int(index),
                            hyperv,
                        )
                except subprocess.CalledProcessError:
                    if not os.path.exists(self._SYSFS_PATH + item):
                        # The path vanished under us, which can happen if
                        # the device itself disappears or we're racing with
                        # systemd-udevd applying our pre-existing udev rules
                        # in response to kernel events.
                        # Either way: retry the enumeration
                        retry = True
                        break
                    # Otherwise, this is some other kind of fatal error,
                    # so reraise the exception.
                    raise

        return active_devices

    def _read_udev_rules(self) -> None:
        """Obtain the currently configured device mapping."""
        if not os.path.exists(self._UDEV_RULES_PATH):
            return

        with open(self._UDEV_RULES_PATH, "r") as udevf:
            for line in udevf:
                line = line.strip()

                if not line or line.startswith("#"):
                    continue

                statements = {}
                for part in line.split(", "):
                    quote = part.index('"')
                    pos = quote
                    while part[pos - 1] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ_{}":
                        pos -= 1
                    statements[part[:pos]] = (part[pos:quote], part[quote:].strip('"'))

                if "NAME" in statements and "ENV{ID_PATH}" in statements:
                    self._interface_map[statements["ENV{ID_PATH}"][1]] = (
                        statements["NAME"][1],
                        False,
                    )
                elif "NAME" in statements and "ATTRS{device_id}" in statements:
                    # Remove the {} around the UUID as it's not in the devpath
                    self._interface_map[statements["ATTRS{device_id}"][1][1:-1]] = (
                        statements["NAME"][1],
                        True,
                    )

    def _write_udev_rules(self) -> None:
        """Persist the current device mapping."""
        content = ['ENV{ID_PATH}=="", IMPORT{builtin}="path_id"']
        for device in sorted(
            self._interface_map, key=lambda a: self._interface_map[a][0]
        ):
            name, hyperv = self._interface_map[device]
            if hyperv:
                content.append(
                    f'SUBSYSTEM=="net", ACTION=="add", ATTRS{{device_id}}=="{{{device}}}", NAME="{name}"'
                )
            else:
                content.append(
                    f'SUBSYSTEM=="net", ACTION=="add", ENV{{ID_PATH}}=="{device}", NAME="{name}"'
                )
        content.append("")
        filewriter.HeadedFileWriter(self._UDEV_RULES_PATH).write("\n".join(content))


def main() -> None:
    """Main"""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)-7s: %(message)s", stream=sys.stdout
    )

    parser = argparse.ArgumentParser(description="Set network interface names")
    parser.add_argument(
        "--force", action="store_true", help="Forcibly set interface names"
    )
    args = parser.parse_args()
    InterfaceMapper(args).run()


if __name__ == "__main__":
    main()
