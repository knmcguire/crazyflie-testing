import binascii
import cflib
import logging
import os
import struct
import sys
import time

from cflib.crtp.crtpstack import CRTPPacket

#
# This is to make it possible to import from conftest
#
currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.join(currentdir, '..')
sys.path.append(parentdir)

from conftest import BCDevice, get_devices  # noqa

logger = logging.getLogger(__name__)

current_frame = 0


def get_bl_address(dev: BCDevice) -> str:
    '''
    Send the BOOTLOADER_CMD_RESET_INIT command to the NRF firmware
    and receive the bootloader radio address in the response
    '''
    address = None
    link = cflib.crtp.get_link_driver(dev.link_uri)
    if link is None:
        return None

    # 0xFF => BOOTLOADER CMD
    # 0xFE => To the NRF firmware
    # 0xFF => BOOTLOADER_CMD_RESET_INIT (to get bl address)
    pk = CRTPPacket(0xFF, [0xFE, 0xFF])
    link.send_packet(pk)

    timeout = 5  # seconds
    ts = time.time()
    while time.time() - ts < timeout:
        pk = link.receive_packet(2)
        if pk is None:
            continue

        # Header 0xFF means port is 0xF ((header & 0xF0) >> 4)) and channel
        # is 0x3 (header & 0x03).
        if pk.port == 0xF and pk.channel == 0x3 and len(pk.data) > 3:
            # 0xFE is NRF target id, 0xFF is BOOTLOADER_CMD_RESET_INIT
            if struct.unpack('<BB', pk.data[0:2]) != (0xFE, 0xFF):
                continue
            address = 'B1' + binascii.hexlify(pk.data[2:6][::-1]).upper().decode('utf8')
            break

    link.close()
    return address


def list_addresses() -> bool:
    for dev in get_devices():
        address = get_bl_address(dev)
        if address is None:
            return False

        print(f'{dev.name}: radio://0/0/2M/{address}?safelink=0')


if __name__ == "__main__":
    if not list_addresses():
        sys.exit(1)
