from pathlib import Path

import argparse
import cflib
import logging
import os
import sys

from cflib.bootloader.cloader import Cloader

#
# This is to make it possible to import from conftest
#
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.join(currentdir, '..')
sys.path.append(parentdir)

from conftest import BCDevice, get_devices  # noqa

logger = logging.getLogger(__name__)


def _recover_dev(dev: BCDevice) -> bool:
    cloader = Cloader(None)
    cloader.link = cflib.crtp.get_link_driver(dev.bl_link_uri)
    if cloader.link is None:
        return False

    status = cloader.reset_to_firmware(0xFE)
    cloader.link.close()

    return status


def recover(name: str):
    for dev in get_devices():
        if not name or (name and dev.name == name):
            if not _recover_dev(dev):
                print(f'Failed to recover {dev.name}', file=sys.stderr)
            else:
                print(f'Recovered {dev.name} from bootloader mode')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Recover devices from bootloader mode')
    parser.add_argument('--name', type=Path, help='device to recover')
    p = parser.parse_args()

    recover(p.name)
