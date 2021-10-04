from pathlib import Path

import argparse
import os
import sys

#
# This is to make it possible to import from conftest
#
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.join(currentdir, '..')
sys.path.append(parentdir)

from conftest import get_devices  # noqa


def run(path: str):
    success = True
    for dev in get_devices():
        print(f'\n🏃🏃🏃 Running {os.path.basename(path)} on {dev.name} 🏃🏃🏃')
        os.environ['CFLIB_URI'] = dev.link_uri

        exit_code = os.WEXITSTATUS(os.system(f'python3 {path}'))
        print(f'🏁🏁🏁 Exited with code: {exit_code} 🏁🏁🏁\n')
        if exit_code != 0:
            success = False

    return success


def run_examples(path: Path):
    examples = [
        'logging/basiclog.py',
        'logging/basiclogSync.py',
        'parameters/basicparam.py',
        'memory/read_deck_mem.py',
        'memory/read-eeprom.py',
        'memory/read-ow.py',
        'step-by-step/sbs_connect_log_param.py'
    ]
    success = True
    for example in examples:
        if not run(os.path.join(path, 'examples/', example)):
            success = False

    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Recover devices from bootloader mode')
    parser.add_argument('--path', type=Path, help='device to recover')
    p = parser.parse_args()

    if not run_examples(p.path):
        sys.exit(1)
