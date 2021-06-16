from pathlib import Path

import argparse
import logging
import os
import sys

#
# This is to make it possible to import from conftest
#
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.join(currentdir, '..')
sys.path.append(parentdir)

from conftest import get_devices  # noqa

logger = logging.getLogger(__name__)

current_frame = 0


def progress_cb(msg: str, percent: int):
    global current_frame
    frames = ['◢', '◣', '◤', '◥']
    frame = frames[current_frame % 4]

    print('{} {}% {}'.format(frame, percent, msg), end='\r')
    current_frame += 1


def program(fw_file: Path) -> bool:
    for dev in get_devices():
        try:
            print('Programming device: {}'.format(dev))
            dev.flash(fw_file, progress_cb)
        except Exception as err:
            print('Programming failed: {}'.format(str(err)), file=sys.stderr)
            return False

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Flash firmware to all devices in site')
    parser.add_argument('--file', type=Path, help='Path to firmware file', required=True)
    p = parser.parse_args()

    if not program(p.file):
        sys.exit(1)
