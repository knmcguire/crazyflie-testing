# Copyright (C) 2021 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import logging
import os
import sys
import traceback

from pathlib import Path

import cflib.crtp

# Initiate the low level drivers
cflib.crtp.init_drivers()

#
# This is to make it possible to import from conftest
#
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.join(currentdir, '..')
sys.path.append(parentdir)

from conftest import get_crazyswarm  # noqa

logger = logging.getLogger(__name__)

current_frame = 0


def progress_cb(msg: str, percent: int):
    global current_frame
    frames = ['◢', '◣', '◤', '◥']
    frame = frames[current_frame % 4]

    print('{} {}% {}'.format(frame, percent, msg), end='\r')
    current_frame += 1


def program_swarm(fw_file: Path) -> bool:
    for dev in get_crazyswarm():
        try:
            print('Programming device: {}'.format(dev))
            dev.flash(fw_file, progress_cb)
        except Exception as err:
            print('Programming failed: {}'.format(str(err)), file=sys.stderr)
            traceback.print_exc()
            return False

    return True


if __name__ == "__main__":
    if not program_swarm(sys.argv[1]):
        sys.exit(1)
